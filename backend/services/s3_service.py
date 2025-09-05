import boto3
from botocore.config import Config
import zipfile
import io
from typing import List, Dict
import os
from datetime import datetime
import hashlib

class S3Service:
    def __init__(self):
        # Настройки для TWC Storage (S3-совместимое хранилище)
        endpoint_url = os.getenv('S3_ENDPOINT_URL')
        
        if endpoint_url:
            # Для S3-совместимых хранилищ (TWC Storage)
            self.s3 = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'ru-1'),
                config=Config(signature_version='s3v4')
            )
        else:
            # Для оригинального AWS S3
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                config=Config(signature_version='s3v4')
            )
        
        self.bucket = os.getenv('S3_BUCKET_NAME', 'ai-database-images')
        self.endpoint_url = endpoint_url

    def _build_object_url(self, key: str, expires_in: int = 60 * 60 * 24 * 7) -> str:
        """Строит URL для доступа к объекту. Пытается сгенерировать presigned URL, иначе возвращает прямой путь."""
        try:
            # Предпочитаем presigned URL, чтобы работало даже без публичного доступа
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except Exception:
            # Фолбэк на прямой URL
            if self.endpoint_url:
                return f"{self.endpoint_url}/{self.bucket}/{key}"
            else:
                return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    async def upload_images_from_zip(self, zip_content: bytes) -> Dict[str, List[str]]:
        """Распаковка ZIP и загрузка изображений в S3"""
        uploaded = []
        failed = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        try:
                            file_content = zip_ref.read(file_info.filename)
                            filename = os.path.basename(file_info.filename)
                            key = f"products/{filename}"

                            self.s3.put_object(
                                Bucket=self.bucket,
                                Key=key,
                                Body=file_content,
                                ContentType=self._get_content_type(filename)
                            )
                            # Формируем URL для просмотра
                            url = self._build_object_url(key)
                            
                            uploaded.append({"filename": filename, "url": url})
                        except Exception as e:
                            failed.append({"filename": file_info.filename, "error": str(e)})
                    else:
                        failed.append({"filename": file_info.filename, "error": "Неподдерживаемый формат"})
        except Exception as e:
            return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Ошибка распаковки: {e}"}]}

        return {"uploaded": uploaded, "failed": failed}

    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """Загрузка одного изображения в S3"""
        key = f"products/{filename}"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=image_data,
            ContentType=self._get_content_type(filename)
        )
        # Возвращаем URL для просмотра (presigned)
        return self._build_object_url(key)

    async def list_folder_contents(self, folder_path: str = "/") -> Dict[str, List[Dict]]:
        """Получение содержимого папки (эмуляция файловой системы в S3)"""
        try:
            # Нормализуем путь
            prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''
            print(f"DEBUG S3: Получение содержимого папки '{folder_path}', prefix: '{prefix}'")
            print(f"DEBUG S3: S3 настройки - bucket: {self.bucket}, endpoint: {self.endpoint_url}")

            paginator = self.s3.get_paginator('list_objects_v2')
            folders_set = set()
            images = []

            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter='/'):
                for prefix_info in page.get('CommonPrefixes', []):
                    folders_set.add(prefix_info['Prefix'])

                for obj in page.get('Contents', []):
                    if obj['Key'] == prefix:
                        continue
                    if not obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        continue
                    filename = obj['Key'].split('/')[-1]
                    url = self._build_object_url(obj['Key'])
                    images.append({
                        'id': obj['Key'],
                        'name': filename,
                        'path': '/' + obj['Key'],
                        'url': url,
                        'thumbnailUrl': url,
                        'size': obj.get('Size', 0),
                        'updatedAt': obj.get('LastModified').isoformat() if obj.get('LastModified') else datetime.now().isoformat()
                    })

            folders = []
            for folder_prefix in sorted(folders_set):
                folder_name = folder_prefix.rstrip('/').split('/')[-1]
                if not folder_name:
                    continue
                folders.append({
                    'id': folder_prefix,
                    'name': folder_name,
                    'path': '/' + folder_prefix.rstrip('/'),
                    'itemCount': await self._count_folder_items(folder_prefix),
                    'updatedAt': datetime.now().isoformat()
                })

            print(f"DEBUG S3: Найдено папок: {len(folders)}, изображений: {len(images)}")

            return {'folders': folders, 'images': images}
            
        except Exception as e:
            print(f"DEBUG S3: ОШИБКА получения содержимого папки {folder_path}: {e}")
            print(f"DEBUG S3: Тип ошибки: {type(e)}")
            import traceback
            traceback.print_exc()
            return {'folders': [], 'images': []}

    async def create_folder(self, parent_path: str, folder_name: str) -> str:
        """Создание папки (загрузка пустого объекта с суффиксом /)"""
        # Нормализуем путь
        parent = parent_path.strip('/') + '/' if parent_path != '/' else ''
        folder_key = f"{parent}{folder_name}/"
        
        # Создаем пустой объект, представляющий папку
        self.s3.put_object(
            Bucket=self.bucket,
            Key=folder_key,
            Body=b'',
            ContentType='application/x-directory'
        )
        
        return folder_key

    async def delete_folder(self, folder_path: str):
        """Удаление папки и всего её содержимого"""
        prefix = folder_path.strip('/') + '/'

        paginator = self.s3.get_paginator('list_objects_v2')
        batch = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                batch.append({'Key': obj['Key']})
                if len(batch) == 1000:
                    self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': batch})
                    batch = []
        if batch:
            self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': batch})

    async def rename_folder(self, old_path: str, new_name: str) -> str:
        """Переименование папки (копирование всех объектов с новым префиксом)"""
        old_prefix = old_path.strip('/') + '/'
        
        # Определяем новый префикс
        path_parts = old_path.strip('/').split('/')
        path_parts[-1] = new_name
        new_prefix = '/'.join(path_parts) + '/'

        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=old_prefix):
            for obj in page.get('Contents', []):
                old_key = obj['Key']
                new_key = old_key.replace(old_prefix, new_prefix, 1)
                self.s3.copy_object(
                    Bucket=self.bucket,
                    CopySource={'Bucket': self.bucket, 'Key': old_key},
                    Key=new_key
                )
                self.s3.delete_object(Bucket=self.bucket, Key=old_key)
        
        return new_prefix

    async def check_duplicate_image(self, image_data: bytes, hash_cache: Dict[str, Dict] = None) -> Dict:
        """Проверка дубликата изображения по хешу с кешированием"""
        try:
            # Вычисляем MD5 хеш изображения
            image_hash = hashlib.md5(image_data).hexdigest()
            
            # Используем кеш если передан (для массовых операций)
            if hash_cache is not None:
                if image_hash in hash_cache:
                    existing = hash_cache[image_hash]
                    return {
                        'is_duplicate': True,
                        'existing_file': existing
                    }
                return {'is_duplicate': False}
            
            # Ищем все изображения с таким же хешем в S3 (только для одиночных проверок)
            paginator = self.s3.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket):
                for obj in page.get('Contents', []):
                    if not obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')):
                        continue
                        
                    try:
                        # Получаем метаданные объекта
                        response = self.s3.head_object(Bucket=self.bucket, Key=obj['Key'])
                        metadata = response.get('Metadata', {})
                        
                        # Если хеш есть в метаданных и совпадает - это дубликат
                        if metadata.get('image-hash') == image_hash:
                            return {
                                'is_duplicate': True,
                                'existing_file': {
                                    'key': obj['Key'],
                                    'url': self._build_object_url(obj['Key']),
                                    'size': obj['Size'],
                                    'last_modified': obj['LastModified'].isoformat()
                                }
                            }
                            
                    except Exception as e:
                        # Если не можем получить метаданные - продолжаем поиск
                        continue
                        
            return {'is_duplicate': False}
            
        except Exception as e:
            print(f"Ошибка проверки дубликата: {e}")
            return {'is_duplicate': False}

    async def _build_hash_cache(self) -> Dict[str, Dict]:
        """Создание кеша хешей всех изображений в S3 для быстрой проверки дубликатов"""
        hash_cache = {}
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket):
                for obj in page.get('Contents', []):
                    if not obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')):
                        continue
                        
                    try:
                        # Получаем метаданные объекта
                        response = self.s3.head_object(Bucket=self.bucket, Key=obj['Key'])
                        metadata = response.get('Metadata', {})
                        image_hash = metadata.get('image-hash')
                        
                        if image_hash:
                            hash_cache[image_hash] = {
                                'key': obj['Key'],
                                'url': self._build_object_url(obj['Key']),
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            }
                    except Exception:
                        continue
                        
            print(f"Создан кеш хешей для {len(hash_cache)} изображений")
            return hash_cache
            
        except Exception as e:
            print(f"Ошибка создания кеша хешей: {e}")
            return {}

    async def upload_image_to_path(self, image_data: bytes, file_path: str, check_duplicate: bool = True) -> Dict:
        """Загрузка изображения по указанному пути с проверкой дубликатов"""
        key = file_path.lstrip('/')
        
        # Проверяем на дубликаты если включена опция
        if check_duplicate:
            duplicate_check = await self.check_duplicate_image(image_data)
            if duplicate_check['is_duplicate']:
                existing = duplicate_check['existing_file']
                # Если дубликат найден, заменяем старый файл новым
                await self.delete_image_by_key(existing['key'])
        
        # Вычисляем хеш изображения для сохранения в метаданных
        image_hash = hashlib.md5(image_data).hexdigest()
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=image_data,
            ContentType=self._get_content_type(file_path),
            Metadata={'image-hash': image_hash},
            ACL='public-read'
        )
        
        url = self._build_object_url(key)
        
        return {
            'url': url,
            'replaced_duplicate': duplicate_check.get('is_duplicate', False) if check_duplicate else False,
            'replaced_file': duplicate_check.get('existing_file') if check_duplicate and duplicate_check.get('is_duplicate') else None
        }

    async def upload_zip_to_folder(self, zip_content: bytes, folder_path: str) -> Dict:
        """Оптимизированная загрузка ZIP: локальная распаковка → S3 батчи"""
        import asyncio
        import time
        import tempfile
        import os
        import shutil
        from concurrent.futures import ThreadPoolExecutor
        
        uploaded = []
        failed = []
        start_time = time.time()
        temp_dir = None

        try:
            # Валидация размера архива (макс 2GB)
            if len(zip_content) > 2 * 1024 * 1024 * 1024:
                return {"uploaded": [], "failed": [{"filename": "archive", "error": "Архив слишком большой (максимум 2GB)"}]}

            base_prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''
            
            print(f"📦 Начинаем оптимизированную обработку ZIP архива размером {len(zip_content) / (1024*1024):.1f} MB")
            
            # Этап 1: Создаем временную папку и распаковываем архив
            print("�️  Создаем временную папку для распаковки...")
            temp_dir = tempfile.mkdtemp(prefix='zip_upload_')
            
            print("📂 Распаковываем архив локально...")
            extract_start = time.time()
            
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                # Фильтруем и извлекаем только изображения
                image_files = []
                
                for file_info in zip_ref.infolist():
                    name = file_info.filename
                    # Нормализуем путь и предотвращаем zip slip
                    norm = os.path.normpath(name)
                    if norm.startswith('..') or norm.startswith('/'):
                        failed.append({"filename": name, "error": "Invalid path in zip"})
                        continue

                    # Пропускаем каталоги
                    if name.endswith('/'):
                        continue
                    
                    # Проверяем формат файла
                    if not name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')):
                        failed.append({"filename": name, "error": "Неподдерживаемый формат файла"})
                        continue

                    try:
                        # Извлекаем файл в временную папку
                        safe_path = os.path.join(temp_dir, os.path.basename(norm))
                        with open(safe_path, 'wb') as f:
                            f.write(zip_ref.read(file_info))
                        
                        image_files.append({
                            'original_name': norm,
                            'local_path': safe_path,
                            's3_key': f"{base_prefix}{norm}"
                        })
                    except Exception as e:
                        failed.append({"filename": name, "error": f"Ошибка извлечения: {e}"})

            extract_time = time.time() - extract_start
            total_files = len(image_files)
            print(f"✅ Распаковано {total_files} файлов за {extract_time:.2f}с")
            
            # Проверяем лимит файлов
            if total_files > 10000:
                return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Слишком много файлов в архиве (максимум 10000, найдено {total_files})"}]}

            if total_files == 0:
                return {"uploaded": [], "failed": [], "message": "В архиве не найдено изображений для загрузки"}

            # Этап 2: Получаем список существующих файлов в целевой папке S3
            print(f"🔍 Получаем список существующих файлов в S3 папке '{folder_path}'...")
            s3_list_start = time.time()
            
            existing_files = {}
            try:
                response = self.s3.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=base_prefix,
                    MaxKeys=10000
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        filename = key.replace(base_prefix, '')
                        if filename:  # Пропускаем папки
                            existing_files[filename] = {
                                'key': key,
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            }
                            
            except Exception as e:
                print(f"⚠️ Ошибка получения списка S3 файлов: {e}")
            
            s3_list_time = time.time() - s3_list_start
            print(f"✅ Найдено {len(existing_files)} существующих файлов в S3 за {s3_list_time:.2f}с")

            # Этап 3: Сравниваем и определяем что загружать
            print("📊 Анализируем какие файлы нужно загрузить/заменить...")
            
            files_to_upload = []  # Новые файлы
            files_to_replace = []  # Файлы для замены
            replaced_count = 0
            
            for file_info in image_files:
                filename = os.path.basename(file_info['original_name'])
                
                if filename in existing_files:
                    # Сравниваем размеры файлов для определения изменений
                    local_size = os.path.getsize(file_info['local_path'])
                    s3_size = existing_files[filename]['size']
                    
                    if local_size != s3_size:
                        files_to_replace.append(file_info)
                        replaced_count += 1
                        print(f"🔄 Заменим {filename} (размер изменился: {s3_size} → {local_size})")
                    else:
                        print(f"⏭️  Пропускаем {filename} (уже существует)")
                else:
                    files_to_upload.append(file_info)
            
            all_upload_files = files_to_upload + files_to_replace
            upload_count = len(all_upload_files)
            
            print(f"📈 К загрузке: {len(files_to_upload)} новых + {len(files_to_replace)} замен = {upload_count} файлов")
            
            if upload_count == 0:
                return {
                    "uploaded": [],
                    "failed": failed,
                    "message": "Все файлы уже существуют в S3, загрузка не требуется",
                    "replaced_duplicates": 0,
                    "total_processed": total_files,
                    "processing_time": round(time.time() - start_time, 1)
                }

            # Этап 4: Параллельная загрузка в S3 с отчетом о прогрессе
            print(f"🚀 Начинаем параллельную загрузку {upload_count} файлов в S3...")
            
            uploaded_count = 0
            failed_count = 0
            last_progress_report = 0
            
            # Увеличиваем параллелизм для лучшей скорости
            semaphore = asyncio.Semaphore(75)  # Увеличено с 50 до 75
            
            async def upload_single_file(file_info):
                nonlocal uploaded_count, failed_count, last_progress_report
                
                async with semaphore:
                    try:
                        # Читаем файл с диска
                        with open(file_info['local_path'], 'rb') as f:
                            file_content = f.read()
                        
                        content_type = self._get_content_type(file_info['original_name'])
                        image_hash = hashlib.md5(file_content).hexdigest()
                        
                        # Асинхронная загрузка в S3
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: self.s3.put_object(
                                Bucket=self.bucket,
                                Key=file_info['s3_key'],
                                Body=file_content,
                                ContentType=content_type,
                                Metadata={'image-hash': image_hash}
                            )
                        )
                        
                        # Обновляем счетчики
                        uploaded_count += 1
                        
                        # Прогресс каждые 5% или каждые 50 файлов
                        progress_percent = (uploaded_count + failed_count) / upload_count * 100
                        if progress_percent - last_progress_report >= 5 or (uploaded_count + failed_count) % 50 == 0:
                            elapsed = time.time() - start_time
                            rate = (uploaded_count + failed_count) / elapsed if elapsed > 0 else 0
                            eta = (upload_count - uploaded_count - failed_count) / rate if rate > 0 else 0
                            print(f"📈 Прогресс: {uploaded_count + failed_count}/{upload_count} ({progress_percent:.1f}%) | "
                                  f"Скорость: {rate:.1f} файлов/сек | ETA: {eta:.0f}сек")
                            last_progress_report = progress_percent
                        
                        url = self._build_object_url(file_info['s3_key'])
                        return {
                            "filename": file_info['original_name'],
                            "url": url,
                            "size": len(file_content),
                            "status": "success"
                        }
                        
                    except Exception as e:
                        failed_count += 1
                        print(f"❌ Ошибка загрузки {file_info['original_name']}: {e}")
                        return {
                            "filename": file_info['original_name'],
                            "error": str(e),
                            "status": "failed"
                        }

            # Создаем и выполняем задачи параллельно
            tasks = [upload_single_file(file_info) for file_info in all_upload_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Обрабатываем результаты
            for result in results:
                if isinstance(result, Exception):
                    failed.append({"filename": "unknown", "error": str(result)})
                elif result.get("status") == "success":
                    uploaded.append({
                        "filename": result["filename"],
                        "url": result["url"],
                        "size": result["size"]
                    })
                else:
                    failed.append({
                        "filename": result["filename"],
                        "error": result["error"]
                    })

            # Финальная статистика
            total_time = time.time() - start_time
            success_count = len(uploaded)
            failed_count = len(failed)
            
            print(f"🎉 Загрузка завершена!")
            print(f"📊 Итоговая статистика:")
            print(f"   ✅ Успешно загружено: {success_count}")
            print(f"   🔄 Дубликатов заменено: {replaced_count}")
            print(f"   ❌ Ошибок: {failed_count}")
            print(f"   ⏱️  Общее время: {total_time:.1f}с")
            print(f"   🚀 Средняя скорость: {total_files / total_time:.1f} файлов/сек")
            
            message = f"Загружено {success_count} из {total_files} файлов за {total_time:.1f}с"
            if replaced_count > 0:
                message += f" ({replaced_count} дубликатов заменено)"

            return {
                "uploaded": uploaded,
                "failed": failed,
                "message": message,
                "replaced_duplicates": replaced_count,
                "total_processed": total_files,
                "processing_time": round(total_time, 1)
            }

        except zipfile.BadZipFile:
            return {"uploaded": [], "failed": [{"filename": "archive", "error": "Поврежденный ZIP архив"}]}
        except Exception as e:
            print(f"❌ Критическая ошибка при обработке ZIP: {e}")
            return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Ошибка обработки архива: {e}"}]}
        finally:
            # Очищаем временную папку
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"🧹 Временная папка {temp_dir} очищена")
                except Exception as e:
                    print(f"⚠️ Не удалось очистить временную папку: {e}")

    async def delete_image_by_key(self, key: str):
        """Удаление изображения по ключу S3"""
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    async def delete_image_by_path(self, image_path: str):
        """Удаление изображения по пути"""
        key = image_path.lstrip('/')
        await self.delete_image_by_key(key)

    def _is_image_path(self, path: str) -> bool:
        """Проверка по расширению, что путь указывает на файл изображения."""
        p = path.lower()
        return any(p.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'])

    async def delete_images_batch(self, image_paths: list[str]) -> dict:
        """
        Удаление набора изображений батчами через S3 DeleteObjects (до 1000 за раз).
        Возвращает { deleted: int, errors: [keys...] } где keys — S3-ключи не удалённых объектов.
        """
        keys = [p.lstrip('/') for p in image_paths]
        total_deleted = 0
        error_keys: list[str] = []

        for i in range(0, len(keys), 1000):
            chunk = keys[i:i + 1000]
            try:
                resp = self.s3.delete_objects(
                    Bucket=self.bucket,
                    Delete={'Objects': [{'Key': k} for k in chunk]}
                )
                total_deleted += len(resp.get('Deleted', []) or [])
                for err in resp.get('Errors', []) or []:
                    if err.get('Key'):
                        error_keys.append(err['Key'])
            except Exception:
                # Если удаление чанка упало, считаем все ключи из него ошибочными
                error_keys.extend(chunk)

        return {"deleted": total_deleted, "errors": error_keys}

    async def rename_image(self, old_path: str, new_name: str) -> str:
        """Переименование изображения"""
        old_key = old_path.lstrip('/')
        
        # Определяем новый ключ
        path_parts = old_key.split('/')
        path_parts[-1] = new_name
        new_key = '/'.join(path_parts)
        
        # Копируем объект с новым именем
        self.s3.copy_object(
            Bucket=self.bucket,
            CopySource={'Bucket': self.bucket, 'Key': old_key},
            Key=new_key
        )
        
        # Удаляем старый объект
        self.s3.delete_object(Bucket=self.bucket, Key=old_key)
        
        return new_key

    async def move_folder(self, old_path: str, new_path: str):
        """Перемещение папки"""
        old_prefix = old_path.strip('/') + '/'
        new_prefix = new_path.strip('/') + '/'

        paginator = self.s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket, Prefix=old_prefix):
            for obj in page.get('Contents', []):
                old_key = obj['Key']
                new_key = old_key.replace(old_prefix, new_prefix, 1)
                self.s3.copy_object(
                    Bucket=self.bucket,
                    CopySource={'Bucket': self.bucket, 'Key': old_key},
                    Key=new_key
                )
                self.s3.delete_object(Bucket=self.bucket, Key=old_key)

    async def move_image(self, old_path: str, new_path: str):
        """Перемещение изображения"""
        old_key = old_path.lstrip('/')
        new_key = new_path.lstrip('/')
        
        # Копируем объект
        self.s3.copy_object(
            Bucket=self.bucket,
            CopySource={'Bucket': self.bucket, 'Key': old_key},
            Key=new_key
        )
        
        # Удаляем старый объект
        self.s3.delete_object(Bucket=self.bucket, Key=old_key)

    async def move_images_concurrent(self, pairs: list[tuple[str, str]], max_workers: int = 20) -> dict:
        """
        Параллельное перемещение набора изображений.
        pairs: список кортежей (old_path, new_path)
        Возвращает: { moved: int, errors: [{src, dst, error}] }
        """
        import asyncio

        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(max_workers)

        async def move_one(src: str, dst: str):
            async with semaphore:
                old_key = src.lstrip('/')
                new_key = dst.lstrip('/')
                def op():
                    # copy + delete
                    self.s3.copy_object(
                        Bucket=self.bucket,
                        CopySource={'Bucket': self.bucket, 'Key': old_key},
                        Key=new_key
                    )
                    self.s3.delete_object(Bucket=self.bucket, Key=old_key)
                await loop.run_in_executor(None, op)

        moved = 0
        errors: list[dict] = []
        tasks = []
        for src, dst in pairs:
            async def wrapper(s=src, d=dst):
                nonlocal moved, errors
                try:
                    await move_one(s, d)
                    moved += 1
                except Exception as e:
                    errors.append({"src": s, "dst": d, "error": str(e)})
            tasks.append(wrapper())

        await asyncio.gather(*tasks, return_exceptions=False)
        return {"moved": moved, "errors": errors}

    async def search_images(self, query: str, folder_path: str = "/") -> List[Dict]:
        """Поиск изображений по названию"""
        try:
            prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''

            results = []
            max_results = 500
            paginator = self.s3.get_paginator('list_objects_v2')
            q = query.lower()
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        continue
                    if q and q not in key.lower():
                        continue
                    filename = key.split('/')[-1]
                    url = self._build_object_url(key)
                    results.append({
                        'id': key,
                        'name': filename,
                        'path': '/' + key,
                        'url': url,
                        'size': obj.get('Size', 0),
                        'updatedAt': obj.get('LastModified').isoformat() if obj.get('LastModified') else datetime.now().isoformat()
                    })
                    if len(results) >= max_results:
                        return results

            return results
            
        except Exception as e:
            print(f"Ошибка поиска изображений: {e}")
            return []

    async def _count_folder_items(self, prefix: str) -> int:
        """Подсчет количества элементов в папке (только прямые дети: файлы и подпапки)"""
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            total = 0
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter='/'):
                total += len(page.get('Contents', []))
                total += len(page.get('CommonPrefixes', []))
            return total
        except Exception as e:
            print(f"DEBUG S3: Ошибка подсчета элементов для {prefix}: {e}")
            return 0

    def _get_content_type(self, filename: str) -> str:
        """Определение Content-Type по расширению"""
        ext = filename.lower().split('.')[-1]
        types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return types.get(ext, 'application/octet-stream')

    async def delete_image(self, url: str):
        """Удаление изображения из S3"""
        try:
            # Обрабатываем как TWC Storage, так и AWS S3 URL
            if self.endpoint_url and self.endpoint_url in url:
                key = url.split(f"{self.endpoint_url}/{self.bucket}/")[-1]
            else:
                key = url.split(f"https://{self.bucket}.s3.amazonaws.com/")[-1]
            
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            print(f"Ошибка удаления {url}: {e}")

# Глобальный экземпляр
s3_service = S3Service()
