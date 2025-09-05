from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import get_db, User
from services.s3_service import s3_service
from utils.auth_middleware import get_current_active_user
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
from pathlib import Path

router = APIRouter()

# Pydantic модели
class FolderCreate(BaseModel):
    parentPath: str
    name: str

class FolderRename(BaseModel):
    oldPath: str
    newName: str

class ImageRename(BaseModel):
    oldPath: str
    newName: str

class DeleteRequest(BaseModel):
    path: str

class BulkDeleteRequest(BaseModel):
    paths: List[str]

class MoveRequest(BaseModel):
    sourcePaths: List[str] 
    targetPath: str

class BrowseResponse(BaseModel):
    folders: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    currentPath: str

@router.get("/browse", response_model=BrowseResponse)
async def browse_images(
    path: str = "/", 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Просмотр папок и изображений в указанном пути"""
    try:
        result = await s3_service.list_folder_contents(path)
        return BrowseResponse(
            folders=result.get('folders', []),
            images=result.get('images', []),
            currentPath=path
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка просмотра папки: {e}")

@router.post("/folders")
async def create_folder(
    folder_data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Создание новой папки"""
    try:
        result = await s3_service.create_folder(folder_data.parentPath, folder_data.name)
        return {"message": "Папка создана", "path": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка создания папки: {e}")

@router.delete("/folders")
async def delete_folder(
    delete_data: DeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удаление папки"""
    try:
        await s3_service.delete_folder(delete_data.path)
        return {"message": "Папка удалена"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка удаления папки: {e}")

@router.put("/folders/rename")
async def rename_folder(
    rename_data: FolderRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Переименование папки"""
    try:
        result = await s3_service.rename_folder(rename_data.oldPath, rename_data.newName)
        return {"message": "Папка переименована", "newPath": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка переименования папки: {e}")

@router.post("/upload")
async def upload_images_to_folder(
    folderPath: str = Form(...),
    images: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Загрузка изображений в указанную папку с проверкой дубликатов"""
    try:
        uploaded_files = []
        failed_files = []
        replaced_count = 0

        for image in images:
            try:
                content = await image.read()
                file_path = f"{folderPath.strip('/')}/{image.filename}" if folderPath != "/" else image.filename
                
                # Проверка дубликатов всегда включена
                result = await s3_service.upload_image_to_path(content, file_path, True)
                
                uploaded_files.append({
                    "filename": image.filename,
                    "url": result['url'],
                    "size": len(content)
                })
                
                if result.get('replaced_duplicate'):
                    replaced_count += 1
                    
            except Exception as e:
                failed_files.append({
                    "filename": image.filename,
                    "error": str(e)
                })

        message = f"Загружено {len(uploaded_files)} из {len(images)} файлов"
        if replaced_count > 0:
            message += f" ({replaced_count} дубликатов заменено)"

        return {
            "uploaded": uploaded_files,
            "failed": failed_files,
            "message": message,
            "replaced_duplicates": replaced_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки изображений: {e}")

@router.post("/upload-zip")
async def upload_zip_to_folder(
    folderPath: str = Form(...),
    zipFile: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Загрузка и распаковка ZIP архива в указанную папку"""
    if not zipFile.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Файл должен быть ZIP архивом")
    
    try:
        content = await zipFile.read()
        result = await s3_service.upload_zip_to_folder(content, folderPath)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки ZIP: {e}")

@router.delete("/delete")
async def delete_image(
    delete_data: DeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удаление изображения"""
    try:
        await s3_service.delete_image_by_path(delete_data.path)
        return {"message": "Изображение удалено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка удаления изображения: {e}")

@router.put("/rename")
async def rename_image(
    rename_data: ImageRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Переименование изображения"""
    try:
        result = await s3_service.rename_image(rename_data.oldPath, rename_data.newName)
        return {"message": "Изображение переименовано", "newPath": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка переименования изображения: {e}")

@router.delete("/bulk-delete")
async def bulk_delete_items(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Множественное удаление изображений и папок"""
    try:
        # Разделяем входные пути на папки и файлы изображений
        folder_paths: list[str] = []
        image_paths: list[str] = []
        for p in delete_data.paths:
            if p.endswith('/') or not any(p.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff']):
                folder_paths.append(p)
            else:
                image_paths.append(p)

        failed_items = []
        deleted_count = 0

        # Папки удаляем последовательно; внутри используется батчевое удаление содержимого
        for folder in folder_paths:
            try:
                await s3_service.delete_folder(folder)
                deleted_count += 1
            except Exception as e:
                failed_items.append({"path": folder, "error": str(e)})

        # Файлы удаляем батчами через S3 DeleteObjects
        if image_paths:
            try:
                result = await s3_service.delete_images_batch(image_paths)
                deleted_count += result.get('deleted', 0)
                for k in result.get('errors', []) or []:
                    failed_items.append({"path": '/' + k if not k.startswith('/') else k, "error": "delete failed"})
            except Exception as e:
                for p in image_paths:
                    failed_items.append({"path": p, "error": str(e)})

        return {
            "message": f"Удалено {deleted_count} из {len(delete_data.paths)} элементов",
            "deleted": deleted_count,
            "failed": failed_items
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка множественного удаления: {e}")

@router.post("/move-items")
async def move_items(
    move_data: MoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Перемещение элементов в другую папку"""
    try:
        folders: list[str] = []
        images: list[str] = []
        for src in move_data.sourcePaths:
            if src.endswith('/') or not any(src.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff']):
                folders.append(src)
            else:
                images.append(src)

        failed_items = []
        moved_count = 0

        # Папки перемещаем последовательно
        for src in folders:
            try:
                item_name = src.rstrip('/').split('/')[-1]
                dst = f"{move_data.targetPath.rstrip('/')}/{item_name}"
                await s3_service.move_folder(src, dst)
                moved_count += 1
            except Exception as e:
                failed_items.append({"path": src, "error": str(e)})

        # Файлы — конкурентно
        if images:
            pairs = []
            for src in images:
                item_name = src.split('/')[-1]
                dst = f"{move_data.targetPath.rstrip('/')}/{item_name}"
                pairs.append((src, dst))
            result = await s3_service.move_images_concurrent(pairs)
            moved_count += result.get('moved', 0)
            for err in result.get('errors', []):
                failed_items.append({"path": err.get('src'), "error": err.get('error')})

        return {
            "message": f"Перемещено {moved_count} из {len(move_data.sourcePaths)} элементов",
            "moved": moved_count,
            "failed": failed_items
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка перемещения: {e}")

@router.get("/search")
async def search_images(
    query: str = "",
    folder: str = "/",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Поиск изображений по названию"""
    try:
        results = await s3_service.search_images(query, folder)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка поиска: {e}")