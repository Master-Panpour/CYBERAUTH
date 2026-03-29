from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Environment ───────────────────────────────────
    PRODUCTION: bool = False          # set True in prod; hides docs, enforces HTTPS cookies

    # ── Database ──────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/cyberauth"

    # ── JWT ───────────────────────────────────────────
    # FIX: no valid default — startup guard in main.py rejects "CHANGE_ME" prefix
    SECRET_KEY: str = "CHANGE_ME_to_64_random_bytes_from_secrets.token_hex(32)"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Google OAuth ──────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # ── GitHub OAuth ──────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/auth/github/callback"

    # ── CORS / Frontend ───────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()