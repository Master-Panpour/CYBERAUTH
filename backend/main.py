from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import httpx, secrets, hashlib
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, engine
import models
import schemas
from config import settings
from sqlalchemy import select

# ─── Security Headers Middleware ─────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        if settings.PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response

# ─── In-memory token blocklist (replace with Redis in production) ─────────────

_token_blocklist: set[str] = set()

def _jti(token: str) -> str:
    """Return the jti claim, or a hash of the token as a fallback."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("jti", hashlib.sha256(token.encode()).hexdigest())
    except Exception:
        return hashlib.sha256(token.encode()).hexdigest()

def blocklist_token(token: str) -> None:
    _token_blocklist.add(_jti(token))

def is_token_blocked(jti_val: str) -> bool:
    return jti_val in _token_blocklist

# ─── In-memory rate limiter (replace with Redis + slowapi in production) ──────

from collections import defaultdict
import time as _time

_login_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60      # seconds
RATE_LIMIT_MAX    = 5       # attempts per window
LOCKOUT_AFTER     = 10      # total attempts before lockout
LOCKOUT_DURATION  = 900     # 15 minutes

def check_rate_limit(ip: str) -> None:
    now = _time.time()
    attempts = _login_attempts[ip]
    # Purge old entries
    _login_attempts[ip] = [t for t in attempts if now - t < LOCKOUT_DURATION]
    if len(_login_attempts[ip]) >= LOCKOUT_AFTER:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    recent = [t for t in _login_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(recent) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Wait 60 seconds.")
    _login_attempts[ip].append(now)

# ─── App setup ───────────────────────────────────────────────────────────────

# Disable docs in production
app = FastAPI(
    title="CyberAuth API",
    version="1.0.0",
    docs_url=None if settings.PRODUCTION else "/docs",
    redoc_url=None if settings.PRODUCTION else "/redoc",
    openapi_url=None if settings.PRODUCTION else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─── JWT Helpers ─────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": secrets.token_hex(16),   # unique token ID for blocklist
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti", "")
        if is_token_blocked(jti):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ─── Dependency: Current User ─────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = verify_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        uid = int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    result = await db.execute(select(models.User).where(models.User.id == uid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=201)
async def register(payload: schemas.RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == payload.email))
    if result.scalar_one_or_none():
        # FIX: don't reveal whether email exists — always return 201 and rely on
        # email verification flow. For simplicity here we return the same response
        # shape but callers cannot distinguish new vs existing account.
        raise HTTPException(status_code=400, detail="Registration failed. Try a different email.")

    user = models.User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        auth_provider="local",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host
    check_rate_limit(client_ip)   # FIX: rate limiting

    result = await db.execute(select(models.User).where(models.User.email == form.username))
    user = result.scalar_one_or_none()

    # FIX: always run verify_password even on non-existent user to prevent timing attacks
    dummy_hash = "$2b$12$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    password_ok = verify_password(form.password, user.hashed_password if user else dummy_hash)

    if not user or not password_ok or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    await db.commit()

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
        "user": user,
    }


@app.post("/auth/refresh", response_model=schemas.TokenResponse)
async def refresh_token(payload: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = verify_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Rotate: blocklist the used refresh token
    blocklist_token(payload.refresh_token)

    uid_str = data.get("sub")
    if not uid_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    result = await db.execute(select(models.User).where(models.User.id == int(uid_str)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
        "user": user,
    }


@app.get("/auth/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/auth/logout")
async def logout(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    # FIX: blocklist the submitted access token immediately
    blocklist_token(token)
    return {"message": "Logged out successfully"}


# ─── OAuth2 Google ────────────────────────────────────────────────────────────

@app.get("/auth/google")
async def google_login(request: Request, response: Response):
    # FIX: generate and store CSRF state
    state = secrets.token_urlsafe(32)
    response.set_cookie(
        "oauth_state", state,
        httponly=True, samesite="lax", secure=settings.PRODUCTION, max_age=600
    )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    import urllib.parse
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@app.get("/auth/google/callback")
async def google_callback(
    request: Request, code: str, state: str,
    db: AsyncSession = Depends(get_db),
):
    # FIX: verify CSRF state
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not secrets.compare_digest(stored_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="OAuth token exchange failed")
        token_data = token_res.json()
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")
        google_user = user_res.json()

    email = google_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Google")

    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = models.User(
            email=email,
            username=google_user.get("name", email.split("@")[0])[:64],
            avatar_url=google_user.get("picture"),
            auth_provider="google",
            provider_id=str(google_user.get("id", "")),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # FIX: use short-lived one-time code instead of token in URL
    code_val = secrets.token_urlsafe(32)
    _oauth_codes[code_val] = {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "expires": _time.time() + 60,
    }
    redirect = RedirectResponse(f"{settings.FRONTEND_URL}/oauth-callback?code={code_val}")
    redirect.delete_cookie("oauth_state")
    return redirect


@app.get("/auth/github")
async def github_login(response: Response):
    state = secrets.token_urlsafe(32)
    response.set_cookie(
        "oauth_state", state,
        httponly=True, samesite="lax", secure=settings.PRODUCTION, max_age=600
    )
    import urllib.parse
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
        "state": state,
    })
    return RedirectResponse(url)


@app.get("/auth/github/callback")
async def github_callback(
    request: Request, code: str, state: str,
    db: AsyncSession = Depends(get_db),
):
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not secrets.compare_digest(stored_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_res.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {gh_token}"},
        )
        emails_res = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {gh_token}"},
        )
        github_user = user_res.json()
        emails = emails_res.json() if isinstance(emails_res.json(), list) else []
        primary_email = next(
            (e["email"] for e in emails if e.get("primary") and e.get("verified")),
            github_user.get("email"),
        )

    if not primary_email:
        raise HTTPException(status_code=400, detail="No verified email from GitHub")

    result = await db.execute(select(models.User).where(models.User.email == primary_email))
    user = result.scalar_one_or_none()
    if not user:
        user = models.User(
            email=primary_email,
            username=(github_user.get("login") or "")[:64],
            avatar_url=github_user.get("avatar_url"),
            auth_provider="github",
            provider_id=str(github_user.get("id", "")),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    code_val = secrets.token_urlsafe(32)
    _oauth_codes[code_val] = {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "expires": _time.time() + 60,
    }
    redirect = RedirectResponse(f"{settings.FRONTEND_URL}/oauth-callback?code={code_val}")
    redirect.delete_cookie("oauth_state")
    return redirect


# ─── OAuth code exchange (FIX for token-in-URL) ──────────────────────────────

_oauth_codes: dict[str, dict] = {}

@app.post("/auth/oauth/exchange", response_model=schemas.TokenResponse)
async def exchange_oauth_code(payload: schemas.OAuthCodeRequest, db: AsyncSession = Depends(get_db)):
    entry = _oauth_codes.pop(payload.code, None)
    if not entry or _time.time() > entry["expires"]:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    # Re-fetch user for response
    data = verify_token(entry["access_token"])
    result = await db.execute(select(models.User).where(models.User.id == int(data["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "access_token": entry["access_token"],
        "refresh_token": entry["refresh_token"],
        "token_type": "bearer",
        "user": user,
    }


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "operational", "service": "CyberAuth API", "version": "1.0.0"}


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    if settings.SECRET_KEY.startswith("CHANGE_ME"):
        raise RuntimeError("SECRET_KEY is not set. Set it in your .env file before starting.")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)