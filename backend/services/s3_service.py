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

    async def check_duplicate_image(self, image_data: bytes) -> Dict:
        """Проверка дубликата изображения по хешу"""
        try:
            # Вычисляем MD5 хеш изображения
            image_hash = hashlib.md5(image_data).hexdigest()
            
            # Ищем все изображения с таким же хешем в S3
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
        """Загрузка и распаковка ZIP в указанную папку с сохранением структуры (параллельная обработка)"""
        import asyncio
        
        uploaded = []
        failed = []

        try:
            # Валидация размера архива (макс 2GB)
            if len(zip_content) > 2 * 1024 * 1024 * 1024:
                return {"uploaded": [], "failed": [{"filename": "archive", "error": "Архив слишком большой (максимум 2GB)"}]}

            base_prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''

            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                files_to_process = []
                
                # Сначала собираем все файлы для обработки
                for file_info in zip_ref.infolist():
                    name = file_info.filename
                    # Нормализуем путь и предотвращаем zip slip
                    norm = os.path.normpath(name)
                    if norm.startswith('..') or norm.startswith('/'):
                        failed.append({"filename": name, "error": "Invalid path in zip"})
                        continue

                    # Пропускаем каталоги (S3 папки создаются неявно ключами)
                    if name.endswith('/'):
                        continue
                    
                    # Проверяем формат файла
                    if not name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')):
                        failed.append({"filename": name, "error": "Неподдерживаемый формат файла"})
                        continue

                    try:
                        file_content = zip_ref.read(file_info)
                        files_to_process.append((norm, file_content))
                    except Exception as e:
                        failed.append({"filename": name, "error": f"Ошибка чтения файла: {str(e)}"})

                # Ограничиваем количество файлов
                if len(files_to_process) > 10000:
                    return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Слишком много файлов в архиве (максимум 10000, найдено {len(files_to_process)})"}]}

                # Семафор для ограничения параллельных операций (максимум 20 одновременных загрузок)
                semaphore = asyncio.Semaphore(20)
                
                async def upload_single_file(norm_path: str, file_content: bytes):
                    """Загрузка одного файла с семафором"""
                    async with semaphore:
                        try:
                            key = f"{base_prefix}{norm_path}"
                            
                            # Проверяем на дубликаты
                            duplicate_check = await self.check_duplicate_image(file_content)
                            replaced_duplicate = False
                            replaced_file = None
                            
                            if duplicate_check['is_duplicate']:
                                # Удаляем старый дубликат
                                existing = duplicate_check['existing_file']
                                await self.delete_image_by_key(existing['key'])
                                replaced_duplicate = True
                                replaced_file = existing
                            
                            # Вычисляем хеш для метаданных
                            image_hash = hashlib.md5(file_content).hexdigest()
                            content_type = self._get_content_type(norm_path)

                            # Используем asyncio для неблокирующего выполнения
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None,
                                lambda: self.s3.put_object(
                                    Bucket=self.bucket,
                                    Key=key,
                                    Body=file_content,
                                    ContentType=content_type,
                                    Metadata={'image-hash': image_hash}
                                )
                            )
                            
                            url = self._build_object_url(key)
                            return {
                                "filename": norm_path, 
                                "url": url, 
                                "size": len(file_content), 
                                "status": "success",
                                "replaced_duplicate": replaced_duplicate,
                                "replaced_file": replaced_file
                            }
                        except Exception as e:
                            return {"filename": norm_path, "error": str(e), "status": "failed"}

                # Создаем задачи для параллельной обработки
                tasks = [
                    upload_single_file(norm_path, file_content) 
                    for norm_path, file_content in files_to_process
                ]

                # Выполняем все задачи параллельно
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Обрабатываем результаты
                replaced_count = 0
                for result in results:
                    if isinstance(result, Exception):
                        failed.append({"filename": "unknown", "error": str(result)})
                    elif result.get("status") == "success":
                        uploaded.append({
                            "filename": result["filename"],
                            "url": result["url"],
                            "size": result["size"]
                        })
                        if result.get("replaced_duplicate"):
                            replaced_count += 1
                    else:
                        failed.append({
                            "filename": result["filename"],
                            "error": result["error"]
                        })

        except Exception as e:
            return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Ошибка распаковки: {e}"}]}

        message = f"Загружено {len(uploaded)} из {len(uploaded) + len(failed)} файлов"
        if replaced_count > 0:
            message += f" ({replaced_count} дубликатов заменено)"

        return {
            "uploaded": uploaded, 
            "failed": failed,
            "message": message,
            "replaced_duplicates": replaced_count
        }

    async def delete_image_by_key(self, key: str):
        """Удаление изображения по ключу S3"""
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    async def delete_image_by_path(self, image_path: str):
        """Удаление изображения по пути"""
        key = image_path.lstrip('/')
        await self.delete_image_by_key(key)

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
