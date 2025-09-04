from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
import os

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-it-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Настройки для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Создает хеш пароля"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Создает JWT токен"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
        """Аутентифицирует пользователя"""
        result = await db.execute(select(User).where(User.username == username, User.is_active == True))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        # Обновляем время последнего входа
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Декодирует JWT токен"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
        """Получает текущего пользователя по токену"""
        payload = AuthService.decode_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        result = await db.execute(select(User).where(User.username == username, User.is_active == True))
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def create_default_users(db: AsyncSession):
        """Создает пользователей по умолчанию если их нет"""
        # Проверяем есть ли пользователи
        result = await db.execute(select(User))
        existing_users = result.scalars().all()
        
        if not existing_users:
            # Создаем админа
            admin_user = User(
                username="admin",
                hashed_password=AuthService.get_password_hash("admin123"),
                role="admin"
            )
            
            # Создаем саппорт
            support_user = User(
                username="support",
                hashed_password=AuthService.get_password_hash("support123"),
                role="support"
            )
            
            db.add(admin_user)
            db.add(support_user)
            await db.commit()
            
            print("Созданы пользователи по умолчанию:")
            print("admin / admin123 (роль: admin)")
            print("support / support123 (роль: support)")
