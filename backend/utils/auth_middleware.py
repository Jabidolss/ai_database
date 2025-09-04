from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from models import get_db, User
from services.auth_service import AuthService

# Схема безопасности для JWT
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Получает текущего авторизованного пользователя"""
    token = credentials.credentials
    user = await AuthService.get_current_user(db, token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Проверяет что пользователь активен"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Неактивный пользователь"
        )
    return current_user

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Требует роль администратора"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user

async def require_admin_or_support(current_user: User = Depends(get_current_active_user)) -> User:
    """Требует роль администратора или поддержки"""
    if current_user.role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user
