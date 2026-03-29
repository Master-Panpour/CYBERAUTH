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


# ── Email Verification Schemas ────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    """Request to verify email with token."""
    token: str = Field(min_length=1, max_length=256)


class VerifyEmailResponse(BaseModel):
    """Response after email verification."""
    message: str
    email_verified: bool


class RequestEmailVerificationRequest(BaseModel):
    """Request to send verification email."""
    email: EmailStr


class RequestEmailVerificationResponse(BaseModel):
    """Response after requesting verification email."""
    message: str
    email: str


# ── Password Reset Schemas ────────────────────────────────────────────

class RequestPasswordResetRequest(BaseModel):
    """Request password reset email."""
    email: EmailStr


class RequestPasswordResetResponse(BaseModel):
    """Response after requesting password reset."""
    message: str


class VerifyPasswordResetTokenRequest(BaseModel):
    """Verify password reset token is valid."""
    token: str = Field(min_length=1, max_length=256)


class VerifyPasswordResetTokenResponse(BaseModel):
    """Response after verifying token."""
    valid: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """Reset password with token."""
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=PASSWORD_MIN_LEN, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength (same as registration)."""
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


class ResetPasswordResponse(BaseModel):
    """Response after password reset."""
    message: str
    success: bool