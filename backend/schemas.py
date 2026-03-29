from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re

PASSWORD_MIN_LEN = 12
COMMON_PASSWORDS = {"password", "password123", "123456789012", "qwertyuiop12", "letmein123456"}


class RegisterRequest(BaseModel):
    email: EmailStr
    # FIX: enforce length limits to prevent DoS via giant inputs
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=PASSWORD_MIN_LEN, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Password is too common")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", v))
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, a digit, and a special character"
            )
        return v

    @field_validator("username")
    @classmethod
    def username_safe(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("Username may only contain letters, numbers, _, -, .")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(max_length=512)


class OAuthCodeRequest(BaseModel):
    code: str = Field(max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    avatar_url: Optional[str] = None
    auth_provider: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse