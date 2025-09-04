import boto3
import zipfile
import io
from typing import List, Dict
import os
from datetime import datetime

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
                region_name=os.getenv('AWS_REGION', 'ru-1')
            )
        else:
            # Для оригинального AWS S3
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
        
        self.bucket = os.getenv('S3_BUCKET_NAME', 'ai-database-images')
        self.endpoint_url = endpoint_url

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

                            # Формируем URL с учетом endpoint
                            if self.endpoint_url:
                                url = f"{self.endpoint_url}/{self.bucket}/{key}"
                            else:
                                url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
                            
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
        
        # Формируем URL с учетом endpoint
        if self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket}/{key}"
        else:
            return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    async def list_folder_contents(self, folder_path: str = "/") -> Dict[str, List[Dict]]:
        """Получение содержимого папки (эмуляция файловой системы в S3)"""
        try:
            # Нормализуем путь
            prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''
            
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            )
            
            folders = []
            images = []
            
            # Получаем "папки" (префиксы)
            for prefix_info in response.get('CommonPrefixes', []):
                folder_name = prefix_info['Prefix'].rstrip('/').split('/')[-1]
                if folder_name:  # Исключаем пустые названия
                    folders.append({
                        'id': prefix_info['Prefix'],
                        'name': folder_name,
                        'path': '/' + prefix_info['Prefix'].rstrip('/'),
                        'itemCount': await self._count_folder_items(prefix_info['Prefix']),
                        'updatedAt': datetime.now().isoformat()
                    })
            
            # Получаем файлы (изображения)
            for obj in response.get('Contents', []):
                if obj['Key'] != prefix and obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    filename = obj['Key'].split('/')[-1]
                    
                    # Формируем URL с учетом endpoint
                    if self.endpoint_url:
                        url = f"{self.endpoint_url}/{self.bucket}/{obj['Key']}"
                    else:
                        url = f"https://{self.bucket}.s3.amazonaws.com/{obj['Key']}"
                    
                    images.append({
                        'id': obj['Key'],
                        'name': filename,
                        'path': '/' + obj['Key'],
                        'url': url,
                        'thumbnailUrl': url,  # Можно добавить генерацию миниатюр
                        'size': obj['Size'],
                        'updatedAt': obj['LastModified'].isoformat()
                    })
            
            return {
                'folders': folders,
                'images': images
            }
            
        except Exception as e:
            print(f"Ошибка получения содержимого папки {folder_path}: {e}")
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
        
        # Получаем все объекты в папке
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        
        if 'Contents' in response:
            # Удаляем все объекты
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            
            self.s3.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': objects_to_delete}
            )

    async def rename_folder(self, old_path: str, new_name: str) -> str:
        """Переименование папки (копирование всех объектов с новым префиксом)"""
        old_prefix = old_path.strip('/') + '/'
        
        # Определяем новый префикс
        path_parts = old_path.strip('/').split('/')
        path_parts[-1] = new_name
        new_prefix = '/'.join(path_parts) + '/'
        
        # Получаем все объекты в старой папке
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=old_prefix)
        
        if 'Contents' in response:
            for obj in response['Contents']:
                old_key = obj['Key']
                new_key = old_key.replace(old_prefix, new_prefix, 1)
                
                # Копируем объект
                self.s3.copy_object(
                    Bucket=self.bucket,
                    CopySource={'Bucket': self.bucket, 'Key': old_key},
                    Key=new_key
                )
                
                # Удаляем старый объект
                self.s3.delete_object(Bucket=self.bucket, Key=old_key)
        
        return new_prefix

    async def upload_image_to_path(self, image_data: bytes, file_path: str) -> str:
        """Загрузка изображения по указанному пути"""
        key = file_path.lstrip('/')
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=image_data,
            ContentType=self._get_content_type(file_path)
        )
        
        # Формируем URL с учетом endpoint
        if self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket}/{key}"
        else:
            return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    async def upload_zip_to_folder(self, zip_content: bytes, folder_path: str) -> Dict:
        """Загрузка и распаковка ZIP в указанную папку"""
        uploaded = []
        failed = []
        
        try:
            folder_prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''
            
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        try:
                            file_content = zip_ref.read(file_info.filename)
                            filename = os.path.basename(file_info.filename)
                            key = f"{folder_prefix}{filename}"

                            self.s3.put_object(
                                Bucket=self.bucket,
                                Key=key,
                                Body=file_content,
                                ContentType=self._get_content_type(filename)
                            )

                            # Формируем URL с учетом endpoint
                            if self.endpoint_url:
                                url = f"{self.endpoint_url}/{self.bucket}/{key}"
                            else:
                                url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
                            
                            uploaded.append({"filename": filename, "url": url, "size": len(file_content)})
                        except Exception as e:
                            failed.append({"filename": file_info.filename, "error": str(e)})
                    else:
                        failed.append({"filename": file_info.filename, "error": "Неподдерживаемый формат"})
        except Exception as e:
            return {"uploaded": [], "failed": [{"filename": "archive", "error": f"Ошибка распаковки: {e}"}]}

        return {"uploaded": uploaded, "failed": failed}

    async def delete_image_by_path(self, image_path: str):
        """Удаление изображения по пути"""
        key = image_path.lstrip('/')
        self.s3.delete_object(Bucket=self.bucket, Key=key)

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

    async def search_images(self, query: str, folder_path: str = "/") -> List[Dict]:
        """Поиск изображений по названию"""
        try:
            prefix = folder_path.strip('/') + '/' if folder_path != '/' else ''
            
            response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            
            results = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if (obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) and
                        query.lower() in obj['Key'].lower()):
                        
                        filename = obj['Key'].split('/')[-1]
                        
                        # Формируем URL с учетом endpoint
                        if self.endpoint_url:
                            url = f"{self.endpoint_url}/{self.bucket}/{obj['Key']}"
                        else:
                            url = f"https://{self.bucket}.s3.amazonaws.com/{obj['Key']}"
                        
                        results.append({
                            'id': obj['Key'],
                            'name': filename,
                            'path': '/' + obj['Key'],
                            'url': url,
                            'size': obj['Size'],
                            'updatedAt': obj['LastModified'].isoformat()
                        })
            
            return results
            
        except Exception as e:
            print(f"Ошибка поиска изображений: {e}")
            return []

    async def _count_folder_items(self, prefix: str) -> int:
        """Подсчет количества элементов в папке"""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return len(response.get('Contents', []))
        except:
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
