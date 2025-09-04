from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
