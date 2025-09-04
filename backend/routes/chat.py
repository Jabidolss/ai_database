from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models import get_db
from services.ai_service import ai_service
from services.backup_service import backup_service
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

class ChatQuery(BaseModel):
    query: str
    history: List[str] = []

class ChatResponse(BaseModel):
    sql: str
    results: List[Dict[str, Any]]
    error: Optional[str] = None

router = APIRouter()

@router.post("/query", response_model=ChatResponse)
async def process_query(chat_query: ChatQuery, db: AsyncSession = Depends(get_db)):
    """Обработка запроса на естественном языке"""
    sql = await ai_service.generate_sql(chat_query.query, chat_query.history)

    if not sql:
        return ChatResponse(sql="", results=[], error="Не удалось сгенерировать SQL")

    try:
        # Проверка безопасности: только разрешенные команды
        sql_upper = sql.upper().strip()
        allowed_commands = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        if not any(sql_upper.startswith(cmd) for cmd in allowed_commands):
            return ChatResponse(sql=sql, results=[], error="Недопустимый тип запроса")

        result = await db.execute(text(sql))

        if sql_upper.startswith("SELECT"):
            rows = result.fetchall()
            # Преобразование в dict
            results = []
            for row in rows:
                results.append(dict(row._mapping))
        else:
            # Создание бэкапа перед изменением данных (кроме SELECT)
            await backup_service.create_backup()
            await db.commit()
            results = [{"message": "Запрос выполнен успешно"}]

        return ChatResponse(sql=sql, results=results)

    except Exception as e:
        return ChatResponse(sql=sql, results=[], error=f"Ошибка выполнения: {str(e)}")

# Заглушка для генерации отчетов (расширить позже)
@router.post("/generate-report")
async def generate_report(chat_query: ChatQuery):
    """Генерация отчета на основе запроса"""
    # TODO: Реализовать генерацию Excel/PDF
    return {"message": "Генерация отчетов пока не реализована", "query": chat_query.query, "history": chat_query.history}
