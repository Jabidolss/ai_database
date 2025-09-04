from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import Product, ColumnMappingSetting, get_db
from services.ai_service import ai_service
from services.excel_processor import excel_processor
from services.advanced_excel_processor import advanced_excel_processor
from services.s3_service import s3_service
from pydantic import BaseModel
from typing import Dict, List, Any
import pandas as pd
import json
from io import BytesIO

class UploadResponse(BaseModel):
    columns: List[str]
    mapping: Dict[str, str]
    structure_info: Dict[str, Any]
    sample_data: List[Dict[str, Any]]

class ConfirmResponse(BaseModel):
    inserted: int
    updated: int
    errors: List[str]
    summary: str

router = APIRouter()

@router.post("/excel", response_model=UploadResponse)
async def upload_excel(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Загрузка Excel файла с расширенным анализом структуры"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Файл должен быть Excel (.xlsx или .xls)")

    content = await file.read()
    try:
        # Используем расширенный процессор
        result = advanced_excel_processor.process_excel_advanced(content, file.filename)
        
        # Получаем пользовательские правила маппинга из БД
        mapping_settings_result = await db.execute(select(ColumnMappingSetting))
        mapping_settings = mapping_settings_result.scalars().all()
        
        user_mapping_rules = {}
        for setting in mapping_settings:
            if setting.excel_patterns:
                patterns = json.loads(setting.excel_patterns)
                if patterns:  # Проверяем что паттерны не пустые
                    user_mapping_rules[setting.db_column] = patterns
        
        # Получаем предложенный маппинг
        suggested_mapping = advanced_excel_processor.suggest_column_mapping(
            result['available_columns']
        )
        
        # Дополнительно используем ИИ для улучшения маппинга с пользовательскими правилами
        ai_mapping = await ai_service.map_columns(
            result['available_columns'], 
            user_mapping_rules if user_mapping_rules else None
        )
        
        # Комбинируем маппинги (ИИ имеет приоритет)
        final_mapping = {**suggested_mapping, **ai_mapping}
        
        return UploadResponse(
            columns=result['available_columns'],
            mapping=final_mapping,
            structure_info=result['structure_info'],
            sample_data=result['sample_data']
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки файла: {e}")

@router.post("/confirm-mapping", response_model=ConfirmResponse)
async def confirm_mapping(
    file: UploadFile = File(...),
    mapping_data: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение маппинга и вставка данных с обработкой извлеченных изображений"""
    content = await file.read()
    try:
        # Парсим mapping_data из JSON строки
        mapping_dict = json.loads(mapping_data)
        mapping = mapping_dict.get('mapping', {})
        
        # Валидируем mapping
        if not isinstance(mapping, dict):
            raise HTTPException(status_code=422, detail="Mapping должен быть объектом")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
            raise HTTPException(status_code=422, detail="Ключи и значения mapping должны быть строками")
        
        # Используем расширенный процессор для получения данных
        result = advanced_excel_processor.process_excel_advanced(content, file.filename)
        
        # Обрабатываем данные с учетом маппинга
        df = result['dataframe']
        print(f"DEBUG: Original columns: {list(df.columns)}")
        print(f"DEBUG: Mapping: {mapping}")
        
        df = df.rename(columns=mapping)
        print(f"DEBUG: Columns after mapping: {list(df.columns)}")
        
        # Оставляем только замаппенные колонки
        mapped_columns = list(mapping.values())
        print(f"DEBUG: Mapped columns to keep: {mapped_columns}")
        
        existing_columns = [col for col in mapped_columns if col in df.columns]
        print(f"DEBUG: Existing mapped columns: {existing_columns}")
        
        df = df[existing_columns]
        print(f"DEBUG: Final dataframe shape: {df.shape}")
        
        # Преобразуем в records
        df = df.where(pd.notnull(df), None)
        records = df.to_dict('records')
        
        print(f"DEBUG: Total records to process: {len(records)}")
        print(f"DEBUG: Sample record: {records[0] if records else 'No records'}")
        
        # Валидируем данные
        errors = excel_processor.validate_data(records)
        print(f"DEBUG: Validation errors count: {len(errors)}")
        if errors:
            print(f"DEBUG: First 10 validation errors:")
            for i, error in enumerate(errors[:10]):
                print(f"  {i+1}: {error}")
        
        # Если ошибок слишком много, логируем предупреждение но продолжаем
        if len(errors) > 100:
            print(f"WARNING: {len(errors)} validation errors found, but proceeding with valid records")
            print(f"DEBUG: First 5 validation errors:")
            for i, error in enumerate(errors[:5]):
                print(f"  {i+1}: {error}")
        
        # Фильтруем валидные записи
        valid_records = []
        invalid_count = 0
        
        for i, record in enumerate(records):
            try:
                # Удаляем не маппированные колонки
                filtered_record = {k: v for k, v in record.items() if k in mapped_columns}
                
                # Проверяем width, height, year
                if 'width' in filtered_record and filtered_record['width'] is not None:
                    try:
                        filtered_record['width'] = float(filtered_record['width'])
                    except (ValueError, TypeError):
                        filtered_record['width'] = None  # Устанавливаем None если не число
                
                if 'height' in filtered_record and filtered_record['height'] is not None:
                    try:
                        filtered_record['height'] = float(filtered_record['height'])
                    except (ValueError, TypeError):
                        filtered_record['height'] = None
                
                if 'year' in filtered_record and filtered_record['year'] is not None:
                    try:
                        filtered_record['year'] = int(filtered_record['year'])
                    except (ValueError, TypeError):
                        filtered_record['year'] = None
                    
                # Проверяем длину строк и обрезаем если нужно
                for field in ['manufacturer_name', 'part_number', 'part_name', 'category', 'type', 'size', 'color', 'brand', 'producer', 'gender', 'age', 'shape']:
                    if field in filtered_record and filtered_record[field] is not None:
                        value_str = str(filtered_record[field])
                        if len(value_str) > 255:
                            filtered_record[field] = value_str[:255]
                        elif len(value_str.strip()) == 0:
                            filtered_record[field] = None  # Пустые строки -> None
                
                # Удаляем None значения
                clean_record = {k: v for k, v in filtered_record.items() if v is not None}
                
                if clean_record:  # Только если есть хоть какие-то данные
                    valid_records.append(clean_record)
                else:
                    invalid_count += 1
                    
            except Exception as e:
                invalid_count += 1
                if invalid_count <= 5:  # Логируем только первые 5
                    print(f"DEBUG: Invalid record {i}: {e}")
                continue
        
        print(f"DEBUG: Valid records: {len(valid_records)}, Invalid: {invalid_count}")

        # Проверка на дублирование и вставка/обновление данных
        inserted = 0
        updated = 0
        failed = 0
        
        # Группируем записи по part_number для оптимизации запросов
        records_with_part_number = {}
        records_without_part_number = []
        
        for record in valid_records:
            part_number = record.get('part_number')
            if part_number and part_number.strip():
                part_number = part_number.strip()
                if part_number not in records_with_part_number:
                    records_with_part_number[part_number] = []
                records_with_part_number[part_number].append(record)
            else:
                records_without_part_number.append(record)
        
        print(f"DEBUG: Records with part_number: {len(records_with_part_number)}, without: {len(records_without_part_number)}")
        
        # Если есть записи с part_number, получаем все существующие из БД за один запрос
        existing_products = {}
        if records_with_part_number:
            part_numbers = list(records_with_part_number.keys())
            print(f"DEBUG: Checking {len(part_numbers)} unique part_numbers in database")
            
            # Делаем запрос батчами для больших объемов
            batch_size = 1000
            for i in range(0, len(part_numbers), batch_size):
                batch_part_numbers = part_numbers[i:i + batch_size]
                existing_products_result = await db.execute(
                    select(Product).where(Product.part_number.in_(batch_part_numbers))
                )
                batch_existing = existing_products_result.scalars().all()
                
                for product in batch_existing:
                    existing_products[product.part_number] = product
                
                print(f"DEBUG: Processed batch {i//batch_size + 1}, found {len(batch_existing)} existing products")
        
        print(f"DEBUG: Total existing products found: {len(existing_products)}")
        
        # Обрабатываем записи с part_number
        for part_number, records in records_with_part_number.items():
            try:
                existing_product = existing_products.get(part_number)
                
                # Берем последнюю запись (самую актуальную) для данного part_number
                record = records[-1]  # Последняя запись имеет приоритет
                
                if existing_product:
                    # Обновляем существующую запись
                    for key, value in record.items():
                        if hasattr(existing_product, key):
                            setattr(existing_product, key, value)
                    updated += 1
                    
                    if updated % 500 == 0:
                        print(f"DEBUG: Updated {updated} products so far")
                else:
                    # Создаем новую запись
                    db_product = Product(**record)
                    db.add(db_product)
                    inserted += 1
                    
                    if inserted % 500 == 0:
                        print(f"DEBUG: Inserted {inserted} products so far")
                        
            except Exception as e:
                failed += 1
                print(f"DEBUG: Failed to process part_number {part_number}: {e}")
                if failed > 10:
                    print(f"DEBUG: Too many failures ({failed}), continuing anyway")
        
        # Обрабатываем записи без part_number (всегда добавляем как новые)
        for record in records_without_part_number:
            try:
                db_product = Product(**record)
                db.add(db_product)
                inserted += 1
                
                if inserted % 500 == 0:
                    print(f"DEBUG: Inserted {inserted} products so far (no part_number)")
                    
            except Exception as e:
                failed += 1
                print(f"DEBUG: Failed to insert record without part_number: {e}")
                if failed > 10:
                    print(f"DEBUG: Too many failures ({failed}), stopping")
                    break

        print(f"DEBUG: Final count - inserted: {inserted}, updated: {updated}, failed: {failed}")
        
        # Создаем сводку для пользователя
        total_processed = inserted + updated
        if total_processed > 0:
            summary = f"Импорт завершен успешно! Всего обработано: {total_processed} товаров"
            if inserted > 0:
                summary += f", добавлено новых: {inserted}"
            if updated > 0:
                summary += f", обновлено существующих: {updated}"
        else:
            summary = "Не было обработано ни одного товара"
            
        if failed > 0:
            summary += f". Ошибок при обработке: {failed}"
        
        await db.commit()
        return ConfirmResponse(
            inserted=inserted, 
            updated=updated, 
            errors=errors[:10] if errors else [],
            summary=summary
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка вставки данных: {e}")

@router.post("/images")
async def upload_images(file: UploadFile = File(...)):
    """Загрузка архива с изображениями"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Файл должен быть ZIP архивом")

    content = await file.read()
    try:
        result = await s3_service.upload_images_from_zip(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки изображений: {e}")
