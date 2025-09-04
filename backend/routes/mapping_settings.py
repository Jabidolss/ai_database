from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from models import ColumnMappingSetting, get_db
from pydantic import BaseModel
from typing import List, Dict, Any
import json

class MappingSettingCreate(BaseModel):
    db_column: str
    excel_patterns: List[str]

class MappingSettingUpdate(BaseModel):
    excel_patterns: List[str]

class MappingSettingResponse(BaseModel):
    id: int
    db_column: str
    excel_patterns: List[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

router = APIRouter()

@router.get("/mapping-settings", response_model=List[MappingSettingResponse])
async def get_mapping_settings(db: AsyncSession = Depends(get_db)):
    """Получить все настройки маппинга"""
    try:
        result = await db.execute(select(ColumnMappingSetting))
        settings = result.scalars().all()
        
        response = []
        for setting in settings:
            response.append(MappingSettingResponse(
                id=setting.id,
                db_column=setting.db_column,
                excel_patterns=json.loads(setting.excel_patterns),
                created_at=setting.created_at.isoformat(),
                updated_at=setting.updated_at.isoformat()
            ))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения настроек: {e}")

@router.post("/mapping-settings", response_model=MappingSettingResponse)
async def create_mapping_setting(
    setting_data: MappingSettingCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новую настройку маппинга"""
    try:
        # Проверяем, не существует ли уже настройка для этой колонки
        result = await db.execute(
            select(ColumnMappingSetting).where(
                ColumnMappingSetting.db_column == setting_data.db_column
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Настройка для колонки {setting_data.db_column} уже существует"
            )
        
        # Создаем новую настройку
        new_setting = ColumnMappingSetting(
            db_column=setting_data.db_column,
            excel_patterns=json.dumps(setting_data.excel_patterns, ensure_ascii=False)
        )
        
        db.add(new_setting)
        await db.commit()
        await db.refresh(new_setting)
        
        return MappingSettingResponse(
            id=new_setting.id,
            db_column=new_setting.db_column,
            excel_patterns=json.loads(new_setting.excel_patterns),
            created_at=new_setting.created_at.isoformat(),
            updated_at=new_setting.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания настройки: {e}")

@router.put("/mapping-settings/{setting_id}", response_model=MappingSettingResponse)
async def update_mapping_setting(
    setting_id: int,
    setting_data: MappingSettingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить настройку маппинга"""
    try:
        result = await db.execute(
            select(ColumnMappingSetting).where(ColumnMappingSetting.id == setting_id)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise HTTPException(status_code=404, detail="Настройка не найдена")
        
        # Обновляем настройку
        await db.execute(
            update(ColumnMappingSetting)
            .where(ColumnMappingSetting.id == setting_id)
            .values(excel_patterns=json.dumps(setting_data.excel_patterns, ensure_ascii=False))
        )
        
        await db.commit()
        await db.refresh(setting)
        
        return MappingSettingResponse(
            id=setting.id,
            db_column=setting.db_column,
            excel_patterns=json.loads(setting.excel_patterns),
            created_at=setting.created_at.isoformat(),
            updated_at=setting.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления настройки: {e}")

@router.delete("/mapping-settings/{setting_id}")
async def delete_mapping_setting(
    setting_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удалить настройку маппинга"""
    try:
        result = await db.execute(
            select(ColumnMappingSetting).where(ColumnMappingSetting.id == setting_id)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise HTTPException(status_code=404, detail="Настройка не найдена")
        
        await db.execute(
            delete(ColumnMappingSetting).where(ColumnMappingSetting.id == setting_id)
        )
        
        await db.commit()
        
        return {"message": "Настройка успешно удалена"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления настройки: {e}")

@router.get("/mapping-settings/export")
async def export_mapping_settings(db: AsyncSession = Depends(get_db)):
    """Экспортировать настройки маппинга в формате для ИИ"""
    try:
        result = await db.execute(select(ColumnMappingSetting))
        settings = result.scalars().all()
        
        mapping_rules = {}
        for setting in settings:
            patterns = json.loads(setting.excel_patterns)
            mapping_rules[setting.db_column] = patterns
        
        return {"mapping_rules": mapping_rules}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта настроек: {e}")

@router.post("/mapping-settings/bulk-create")
async def bulk_create_default_settings(db: AsyncSession = Depends(get_db)):
    """Создать настройки по умолчанию для всех колонок БД"""
    try:
        # Определяем настройки по умолчанию
        default_settings = {
            'manufacturer_name': [
                'manufacturer', 'производитель', 'manufacturer_name', 'изготовитель', 'завод'
            ],
            'part_number': [
                'part_number', 'партномер', 'артикул', 'upc', 'upc code', 'code', 'код товара', 'товарный код'
            ],
            'part_name': [
                'part_name', 'name', 'название', 'наименование', 'style name', 'product name', 'товар'
            ],
            'category': [
                'category', 'категория', 'тип товара', 'группа товара', 'класс'
            ],
            'type': [
                'type', 'тип', 'material', 'материал', 'вид'
            ],
            'size': [
                'size', 'размер', 'габарит', 'dimension'
            ],
            'color': [
                'color', 'цвет', 'colour', 'окрас', 'расцветка'
            ],
            'brand': [
                'brand', 'бренд', 'торговая марка', 'марка', 'trademark'
            ],
            'producer': [
                'producer', 'производитель', 'поставщик', 'supplier', 'vendor'
            ],
            'gender': [
                'gender', 'пол', 'для кого', 'целевая аудитория'
            ],
            'width': [
                'width', 'ширина', 'w', 'широта'
            ],
            'height': [
                'height', 'высота', 'h', 'рост'
            ],
            'age': [
                'age', 'возраст', 'возрастная группа', 'для возраста'
            ],
            'shape': [
                'shape', 'форма', 'фасон', 'силуэт'
            ],
            'year': [
                'year', 'год', 'год выпуска', 'модельный год'
            ],
            'images': [
                'picture', 'image', 'фото', 'изображение', 'картинка', 'photo'
            ]
        }
        
        created_count = 0
        
        for db_column, patterns in default_settings.items():
            # Проверяем, не существует ли уже настройка
            result = await db.execute(
                select(ColumnMappingSetting).where(
                    ColumnMappingSetting.db_column == db_column
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                new_setting = ColumnMappingSetting(
                    db_column=db_column,
                    excel_patterns=json.dumps(patterns, ensure_ascii=False)
                )
                db.add(new_setting)
                created_count += 1
        
        await db.commit()
        
        return {
            "message": f"Создано {created_count} настроек по умолчанию",
            "created_count": created_count
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания настроек по умолчанию: {e}")
