from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Импорт моделей для создания таблиц при старте
from models import engine, Base

# Роуты (добавим позже)
# from routes import api, chat, files

# Lifespan для инициализации БД
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц при старте
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Очистка при завершении, если нужно

app = FastAPI(
    title="AI Database Platform",
    description="Платформа для управления базой данных товаров с ИИ",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:3000", "http://127.0.0.1:3000", "https://databaseprotrade.ru", "https://www.databaseprotrade.ru"],  # Для локального запуска и production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов (раскомментировать по мере реализации)
from routes import api, chat, files, mapping_settings, images
app.include_router(api.router, prefix="/api", tags=["products"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(files.router, prefix="/api/upload", tags=["files"])
app.include_router(mapping_settings.router, prefix="/api", tags=["mapping-settings"])
app.include_router(images.router, prefix="/api/images", tags=["images"])

@app.get("/")
async def root():
    return {"message": "AI Database Platform API"}

# Для простого health check
@app.get("/health")
async def health():
    return {"status": "ok"}
