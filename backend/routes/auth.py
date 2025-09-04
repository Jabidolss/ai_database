from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from models import get_db, User
from schemas.auth_schemas import LoginRequest, TokenResponse, UserInfo, PasswordChangeRequest
from services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from utils.auth_middleware import get_current_active_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    user = await AuthService.authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Получить информацию о текущем пользователе"""
    return current_user

@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Смена пароля"""
    # Проверяем старый пароль
    if not AuthService.verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )
    
    # Устанавливаем новый пароль
    current_user.hashed_password = AuthService.get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Пароль успешно изменен"}

@router.post("/logout")
async def logout():
    """Выход из системы (на стороне клиента нужно удалить токен)"""
    return {"message": "Успешный выход из системы"}
