from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import Text, DateTime, func, String
from typing import Optional, AsyncGenerator
from datetime import datetime

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# Модель пользователей
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))  # admin или support
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

# Модель очков
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    images: Mapped[Optional[str]]  # Ссылки на изображения очков в S3, разделенные запятыми
    manufacturer_name: Mapped[Optional[str]]  # Производитель очков
    part_number: Mapped[Optional[str]]        # Артикул модели очков
    part_name: Mapped[Optional[str]]          # Название модели очков
    category: Mapped[Optional[str]]           # Бренд очков (Gucci, Ray-Ban, Prada и т.д.)
    type: Mapped[Optional[str]]               # Тип очков (солнцезащитные, для чтения и т.д.)
    size: Mapped[Optional[str]]               # Размер очков
    color: Mapped[Optional[str]]              # Цвет оправы/линз
    brand: Mapped[Optional[str]]              # Бренд (дублирует category для совместимости)
    producer: Mapped[Optional[str]]           # Производитель (может отличаться от бренда)
    gender: Mapped[Optional[str]]             # Пол (мужские, женские, унисекс)
    width: Mapped[Optional[float]]            # Ширина оправы в мм
    height: Mapped[Optional[float]]           # Высота линзы в мм
    age: Mapped[Optional[str]]                # Возрастная группа
    shape: Mapped[Optional[str]]              # Форма оправы (круглые, квадратные, авиаторы и т.д.)
    year: Mapped[Optional[int]]               # Год выпуска модели

# Модель настроек маппинга колонок
class ColumnMappingSetting(Base):
    __tablename__ = "column_mapping_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    db_column: Mapped[str]  # Название колонки в БД (manufacturer_name, part_number, и т.д.)
    excel_patterns: Mapped[str] = mapped_column(Text)  # JSON массив паттернов для поиска
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

# Настройки для асинхронной работы с БД
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/ai_database")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Функция для получения сессии
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
