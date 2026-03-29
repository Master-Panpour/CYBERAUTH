from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    # ── Environment ───────────────────────────────────
    PRODUCTION: bool = False          # set True in prod; hides docs, enforces HTTPS cookies

    # ── Database ──────────────────────────────────────
    # REQUIRED: Must be set in .env or environment variables
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")

    # ── JWT ───────────────────────────────────────────
    # REQUIRED: Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = Field(..., description="JWT secret key (64 hex characters minimum)")
    ALGORITHM: str = Field(..., description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., description="Access token expiration time in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(..., description="Refresh token expiration time in days")

    # ── Google OAuth ──────────────────────────────────
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google OAuth Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(..., description="Google OAuth Redirect URI")

    # ── GitHub OAuth ──────────────────────────────────
    GITHUB_CLIENT_ID: str = Field(default="", description="GitHub OAuth Client ID")
    GITHUB_CLIENT_SECRET: str = Field(default="", description="GitHub OAuth Client Secret")
    GITHUB_REDIRECT_URI: str = Field(..., description="GitHub OAuth Redirect URI")

    # ── CORS / Frontend ───────────────────────────────
    ALLOWED_ORIGINS: List[str] = Field(..., description="Allowed CORS origins")
    FRONTEND_URL: str = Field(..., description="Frontend URL for redirects")

    class Config:
        env_file = ".env"


settings = Settings()