from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import Product, get_db
from services.backup_service import backup_service
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import zipfile
import httpx
from io import BytesIO

# Pydantic схемы для очков
class ProductBase(BaseModel):
    images: Optional[str] = None               # Ссылки на изображения очков в S3
    manufacturer_name: Optional[str] = None    # Производитель очков
    part_number: Optional[str] = None          # Артикул модели очков
    part_name: Optional[str] = None            # Название модели очков
    category: Optional[str] = None             # Бренд очков (Gucci, Ray-Ban и т.д.)
    type: Optional[str] = None                 # Тип очков (солнцезащитные, оптические и т.д.)
    size: Optional[str] = None                 # Размер очков
    color: Optional[str] = None                # Цвет оправы/линз
    brand: Optional[str] = None                # Бренд (дублирует category)
    producer: Optional[str] = None             # Производитель (может отличаться от бренда)
    gender: Optional[str] = None               # Пол (мужские, женские, унисекс)
    width: Optional[float] = None              # Ширина оправы в мм
    height: Optional[float] = None             # Высота линзы в мм
    age: Optional[str] = None                  # Возрастная группа
    shape: Optional[str] = None                # Форма оправы (круглые, квадратные, авиаторы и т.д.)
    year: Optional[int] = None                 # Год выпуска модели

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True

class ProductsListResponse(BaseModel):
    products: List[ProductResponse]
    total_count: int
    page: int
    size: int
    total_pages: int

router = APIRouter()

@router.get("/products", response_model=ProductsListResponse)
async def get_products(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    search: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка очков с фильтрами и пагинацией"""
    # Базовый запрос для подсчета общего количества
    base_query = select(Product)
    
    # Применяем фильтры
    if brand:
        base_query = base_query.where(Product.brand == brand)
    if category:
        base_query = base_query.where(Product.category == category)
    if color:
        base_query = base_query.where(Product.color == color)
    if search:
        base_query = base_query.where(Product.part_name.ilike(f"%{search}%"))
    
    # Получаем общее количество записей
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Получаем данные с пагинацией и сортировкой
    data_query = base_query
    
    # Применяем сортировку
    if sort_field:
        if hasattr(Product, sort_field):
            sort_column = getattr(Product, sort_field)
            if sort_order == 'desc':
                data_query = data_query.order_by(sort_column.desc())
            else:
                data_query = data_query.order_by(sort_column.asc())
    else:
        # Сортировка по умолчанию по ID
        data_query = data_query.order_by(Product.id.asc())
    
    data_query = data_query.limit(limit).offset(offset)
    data_result = await db.execute(data_query)
    products = data_result.scalars().all()
    
    # Рассчитываем общее количество страниц
    total_pages = (total_count + limit - 1) // limit
    current_page = offset // limit
    
    return ProductsListResponse(
        products=products,
        total_count=total_count,
        page=current_page,
        size=limit,
        total_pages=total_pages
    )

@router.post("/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Создание нового товара"""
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/products/columns")
async def get_product_columns():
    """Получение списка всех колонок таблицы продуктов с человеческими названиями"""
    try:
        # ВАЖНО: порядок соответствует требованию выгрузки
        columns = [
            {"field": "images", "header": "Изображения"},
            {"field": "manufacturer_name", "header": "Название производителя"},
            {"field": "part_number", "header": "Номер детали"},
            {"field": "part_name", "header": "Название детали"},
            {"field": "description", "header": "Описание"},  # виртуальная колонка (пустая)
            {"field": "category", "header": "category"},
            {"field": "type", "header": "Тип"},
            {"field": "size", "header": "Размер"},
            {"field": "color", "header": "Цвет"},
            {"field": "brand", "header": "Бренд"},
            {"field": "producer", "header": "Производитель"},
            {"field": "gender", "header": "Пол"},
            {"field": "width", "header": "Ширина"},
            {"field": "height", "header": "Высота"},
            {"field": "age", "header": "Возраст"},
            {"field": "shape", "header": "Форма"},
            {"field": "year", "header": "Год"}
        ]
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения колонок: {str(e)}")

@router.get("/products/filter-options")
async def get_filter_options(db: AsyncSession = Depends(get_db)):
    """Получение опций для фильтров"""
    try:
        # Получаем уникальные значения для фильтров
        brands_query = select(Product.brand).distinct().where(Product.brand.isnot(None))
        categories_query = select(Product.category).distinct().where(Product.category.isnot(None))
        colors_query = select(Product.color).distinct().where(Product.color.isnot(None))
        
        brands_result = await db.execute(brands_query)
        categories_result = await db.execute(categories_query)
        colors_result = await db.execute(colors_query)
        
        brands = [row[0] for row in brands_result.fetchall() if row[0]]
        categories = [row[0] for row in categories_result.fetchall() if row[0]]
        colors = [row[0] for row in colors_result.fetchall() if row[0]]
        
        return {
            "brands": sorted(brands),
            "categories": sorted(categories),
            "colors": sorted(colors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения фильтров: {str(e)}")

# ВАЖНО: динамические маршруты должны идти после статических, иначе
# запросы вида /products/columns будут интерпретированы как /products/{product_id}
# и вернут 422 из-за невозможности преобразовать 'columns' в int.
@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Получение товара по ID"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_update: ProductUpdate, db: AsyncSession = Depends(get_db)):
    """Обновление товара по ID"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    for key, value in product_update.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Удаление товара по ID"""
    result = await db.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    await db.delete(db_product)
    await db.commit()
    return {"message": "Товар удален"}
@router.post("/products/export")
async def export_products(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Экспорт товаров в Excel с возможностью экспорта изображений"""
    try:
        # Получение параметров из запроса
        selected_brands = request.get('brands', [])
        selected_columns = request.get('columns', [])
        include_images = request.get('include_images', False)
        
        if not selected_brands:
            raise HTTPException(status_code=400, detail="Необходимо выбрать хотя бы один бренд")
        if not selected_columns:
            raise HTTPException(status_code=400, detail="Необходимо выбрать хотя бы одну колонку")

        # Создание запроса с фильтрацией по брендам
        query = select(Product).where(Product.brand.in_(selected_brands))
        result = await db.execute(query)
        products = result.scalars().all()

        if not products:
            raise HTTPException(status_code=404, detail="Товары не найдены")

        # Маппинг колонок БД к человеческим названиям
        column_mapping = {
            'id': 'ID',
            'images': 'Изображения',
            'manufacturer_name': 'Название производителя',
            'part_number': 'Номер детали',
            'part_name': 'Название',
            'category': 'Категория',
            'type': 'Тип',
            'size': 'Размер',
            'color': 'Цвет',
            'brand': 'Бренд',
            'producer': 'Производитель',
            'gender': 'Пол',
            'width': 'Ширина',
            'height': 'Высота',
            'age': 'Возраст',
            'shape': 'Форма',
            'year': 'Год'
        }

        # Подготовка данных для экспорта
        export_data = []
        for product in products:
            row = {}
            for col_config in selected_columns:
                field = col_config['field']
                display_name = col_config['display_name']
                
                # Получение значения
                if field == 'description':
                    # Виртуальная колонка — всегда пустая строка
                    value = ""
                else:
                    value = getattr(product, field, None)
                
                # Специальная обработка для category
                if field == 'category':
                    value = f"category/{product.brand}" if product.brand else "category/"
                elif field == 'images' and value:
                    # Форматирование изображений с .jpg
                    images = value.split(',')
                    formatted_images = []
                    for img in images:
                        img = img.strip()
                        if not img.endswith('.jpg'):
                            img += '.jpg'
                        formatted_images.append(img)
                    value = ', '.join(formatted_images)
                
                row[display_name] = value or ""
            
            export_data.append(row)

        # Если экспорт без изображений - только Excel файл
        if not include_images:
            df = pd.DataFrame(export_data)
            # Гарантируем порядок колонок согласно выбору пользователя
            ordered_headers = [c['display_name'] for c in selected_columns]
            # На случай, если какие-то заголовки отсутствуют (не должны) — фильтруем по пересечению
            ordered_headers = [h for h in ordered_headers if h in df.columns]
            df = df.reindex(columns=ordered_headers)
            
            # Создание Excel файла в памяти
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Данные')
            output.seek(0)
            
            return StreamingResponse(
                BytesIO(output.getvalue()),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": "attachment; filename=data.xlsx"}
            )
        else:
            # Экспорт с изображениями - создание архива
            # Создание Excel файла
            df = pd.DataFrame(export_data)
            ordered_headers = [c['display_name'] for c in selected_columns]
            ordered_headers = [h for h in ordered_headers if h in df.columns]
            df = df.reindex(columns=ordered_headers)
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Данные')
            excel_buffer.seek(0)
            
            # Создание ZIP архива
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Добавление Excel файла
                zip_file.writestr('data.xlsx', excel_buffer.getvalue())
                
                # Сбор всех уникальных изображений
                unique_images = set()
                for product in products:
                    if product.images:
                        images = product.images.split(',')
                        for img in images:
                            img = img.strip()
                            if img:
                                unique_images.add(img)
                
                # Создание папки media и загрузка изображений
                if unique_images:
                    async with httpx.AsyncClient() as client:
                        for image_url in unique_images:
                            try:
                                # Попытка загрузить изображение
                                response = await client.get(image_url, timeout=10)
                                if response.status_code == 200:
                                    # Определение имени файла
                                    filename = image_url.split('/')[-1]
                                    if not filename.endswith('.jpg'):
                                        filename += '.jpg'
                                    
                                    # Добавление в архив
                                    zip_file.writestr(f'media/{filename}', response.content)
                            except Exception as e:
                                print(f"Ошибка загрузки изображения {image_url}: {e}")
                                continue
            
            zip_buffer.seek(0)
            
            return StreamingResponse(
                BytesIO(zip_buffer.getvalue()),
                media_type='application/zip',
                headers={"Content-Disposition": "attachment; filename=export_with_images.zip"}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")

@router.post("/restore-database")
async def restore_database():
    """Восстановление базы данных из последнего бэкапа"""
    try:
        success = await backup_service.restore_backup()
        if success:
            return {"message": "База данных успешно восстановлена из бэкапа"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка восстановления базы данных")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
