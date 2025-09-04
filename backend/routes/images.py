from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import get_db
from services.s3_service import s3_service
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

class BrowseResponse(BaseModel):
    folders: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    currentPath: str

@router.get("/browse", response_model=BrowseResponse)
async def browse_images(path: str = "/", db: AsyncSession = Depends(get_db)):
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
async def create_folder(folder_data: FolderCreate, db: AsyncSession = Depends(get_db)):
    """Создание новой папки"""
    try:
        result = await s3_service.create_folder(folder_data.parentPath, folder_data.name)
        return {"message": "Папка создана", "path": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка создания папки: {e}")

@router.delete("/folders")
async def delete_folder(delete_data: DeleteRequest, db: AsyncSession = Depends(get_db)):
    """Удаление папки"""
    try:
        await s3_service.delete_folder(delete_data.path)
        return {"message": "Папка удалена"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка удаления папки: {e}")

@router.put("/folders/rename")
async def rename_folder(rename_data: FolderRename, db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db)
):
    """Загрузка изображений в указанную папку"""
    try:
        uploaded_files = []
        failed_files = []
        
        for image in images:
            if not image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                failed_files.append({
                    "filename": image.filename,
                    "error": "Неподдерживаемый формат файла"
                })
                continue
            
            try:
                content = await image.read()
                file_path = f"{folderPath.strip('/')}/{image.filename}" if folderPath != "/" else image.filename
                url = await s3_service.upload_image_to_path(content, file_path)
                
                uploaded_files.append({
                    "filename": image.filename,
                    "url": url,
                    "size": len(content)
                })
            except Exception as e:
                failed_files.append({
                    "filename": image.filename,
                    "error": str(e)
                })
        
        return {
            "uploaded": uploaded_files,
            "failed": failed_files,
            "message": f"Загружено {len(uploaded_files)} из {len(images)} файлов"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки изображений: {e}")

@router.post("/upload-zip")
async def upload_zip_to_folder(
    folderPath: str = Form(...),
    zipFile: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
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
async def delete_image(delete_data: DeleteRequest, db: AsyncSession = Depends(get_db)):
    """Удаление изображения"""
    try:
        await s3_service.delete_image_by_path(delete_data.path)
        return {"message": "Изображение удалено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка удаления изображения: {e}")

@router.put("/rename")
async def rename_image(rename_data: ImageRename, db: AsyncSession = Depends(get_db)):
    """Переименование изображения"""
    try:
        result = await s3_service.rename_image(rename_data.oldPath, rename_data.newName)
        return {"message": "Изображение переименовано", "newPath": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка переименования изображения: {e}")

@router.get("/search")
async def search_images(
    query: str = "",
    folder: str = "/",
    db: AsyncSession = Depends(get_db)
):
    """Поиск изображений по названию"""
    try:
        results = await s3_service.search_images(query, folder)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка поиска: {e}")
