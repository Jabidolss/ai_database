from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from models import get_db, User, ChatMessage
from services.ai_service import ai_service
from services.backup_service import backup_service
from utils.auth_middleware import get_current_active_user
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

class ChatQuery(BaseModel):
    query: str
    history: List[str] = []

class ChatResponse(BaseModel):
    sql: str
    results: List[Dict[str, Any]] = []
    error: Optional[str] = None

router = APIRouter()

async def save_ai_message(user_id: int, db: AsyncSession, sql: Optional[str] = None, results: Optional[List[Dict[str, Any]]] = None, text: Optional[str] = None, error: Optional[str] = None):
    msg = ChatMessage(
        user_id=user_id,
        role='ai',
        text=text,
        sql=sql,
        error=error,
        results=results if results is not None else None,
    )
    db.add(msg)
    await db.commit()
    return msg

@router.post("/query", response_model=ChatResponse)
async def process_query(
    chat_query: ChatQuery, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
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

        # Сохраняем в историю: ответ ИИ, вместе с результатами если они есть
        try:
            await save_ai_message(current_user.id, db, sql=sql, results=results)
        except Exception:
            pass
        return ChatResponse(sql=sql, results=results)

    except Exception as e:
        try:
            await save_ai_message(current_user.id, db, sql=sql, error=f"Ошибка выполнения: {str(e)}")
        except Exception:
            pass
        return ChatResponse(sql=sql, results=[], error=f"Ошибка выполнения: {str(e)}")

class ChatMessageIn(BaseModel):
    role: str  # 'user' | 'ai'
    text: Optional[str] = None
    sql: Optional[str] = None
    error: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None

class ChatMessageOut(BaseModel):
    id: int
    role: str
    text: Optional[str]
    sql: Optional[str]
    error: Optional[str]
    results: Optional[List[Dict[str, Any]]]
    created_at: str

    class Config:
        from_attributes = True

@router.get("/history", response_model=List[ChatMessageOut])
async def get_history(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить последние N сообщений текущего пользователя (по умолчанию 10)."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    # Возвращаем в хронологическом порядке (от старых к новым)
    return list(reversed(rows))

@router.post("/history", response_model=ChatMessageOut)
async def add_history(
    msg: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Добавить сообщение в историю текущего пользователя."""
    if msg.role not in ("user", "ai"):
        raise HTTPException(status_code=400, detail="Некорректная роль сообщения")

    entity = ChatMessage(
        user_id=current_user.id,
        role=msg.role,
        text=msg.text,
        sql=msg.sql,
    error=msg.error,
    results=msg.results,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity

@router.delete("/history")
async def clear_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Очистить историю сообщений текущего пользователя."""
    # Используем raw SQL для эффективности
    await db.execute(text("DELETE FROM chat_messages WHERE user_id = :uid"), {"uid": current_user.id})
    await db.commit()
    return {"message": "История очищена"}

# Заглушка для генерации отчетов (расширить позже)
@router.post("/generate-report")
async def generate_report(
    chat_query: ChatQuery,
    current_user: User = Depends(get_current_active_user)
):
    """Генерация отчета на основе запроса"""
    # TODO: Реализовать генерацию Excel/PDF
    return {"message": "Генерация отчетов пока не реализована", "query": chat_query.query, "history": chat_query.history}
