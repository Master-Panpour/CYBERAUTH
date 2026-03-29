"""Email verification and password reset endpoints.

OWASP Security Considerations:
- A1: Broken Access Control - Only verify own email
- A2: Cryptographic Failures - Secure token generation
- A3: Injection - Parameterized queries via SQLAlchemy
- A5: Security Misconfiguration - Rate limiting applied
- A7: Authentication Bugs - Token expiration enforced
- A9: Logging & Monitoring - Email sends logged
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from database import get_db
import models
import schemas
from email_service import email_service, EmailTemplates, EmailService
from email_config import EmailSettings
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["email"])

# Rate limiting: track email sends per user
_email_send_attempts: dict[int, list[float]] = {}


async def check_email_rate_limit(user_id: int, max_per_hour: int = 5) -> None:
    """Rate limit email sends to prevent spam.
    
    Security: Prevents email flooding attacks.
    
    Args:
        user_id: User ID
        max_per_hour: Max emails per hour
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    import time
    
    now = time.time()
    one_hour_ago = now - 3600
    
    if user_id not in _email_send_attempts:
        _email_send_attempts[user_id] = []
    
    # Remove old attempts
    _email_send_attempts[user_id] = [
        t for t in _email_send_attempts[user_id] if t > one_hour_ago
    ]
    
    # Check limit
    if len(_email_send_attempts[user_id]) >= max_per_hour:
        logger.warning(f"Email rate limit exceeded for user {user_id}")
        raise HTTPException(
            status_code=429,
            detail="Too many email requests. Try again later.",
        )
    
    # Record attempt
    _email_send_attempts[user_id].append(now)


@router.post("/email/verify-request", response_model=schemas.RequestEmailVerificationResponse)
async def request_email_verification(
    payload: schemas.RequestEmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request email verification.
    
    Security:
    - A7: Rate limited to prevent spam
    - A2: Generates cryptographically secure token
    - A1: Can only request for own email (after login in future)
    """
    # Find user by email
    result = await db.execute(select(models.User).where(models.User.email == payload.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # FIX: Don't reveal if email exists (prevent enumeration)
        logger.info(f"Verification requested for non-existent email: {payload.email}")
        return schemas.RequestEmailVerificationResponse(
            message="If email exists, verification link has been sent",
            email=payload.email,
        )
    
    # Check if already verified
    if user.is_verified and user.email_verified_at:
        return schemas.RequestEmailVerificationResponse(
            message="Email already verified",
            email=payload.email,
        )
    
    # Check rate limit
    await check_email_rate_limit(user.id, EmailSettings.MAX_EMAIL_PER_HOUR)
    
    # Generate token
    token = EmailService.generate_verification_token()
    user.verification_token = token
    user.verification_token_expires = EmailService.get_verification_expiry()
    
    # Build verification link
    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    # Send email
    if email_service.enabled:
        html_content, text_content = EmailTemplates.verification_email(
            username=user.username,
            verification_link=verify_link,
            frontend_url=settings.FRONTEND_URL,
        )
        
        success, message = await email_service.send_email(
            to_email=user.email,
            subject="Verify Your Email - CyberAuth",
            html_content=html_content,
            text_content=text_content,
        )
        
        if not success:
            logger.error(f"Failed to send verification email to {user.email}")
            # Still save token but return generic message
    else:
        logger.warning("Email service not configured - verification email not sent")
    
    # Save token to database
    await db.commit()
    
    # FIX: Generic message doesn't reveal if email exists
    return schemas.RequestEmailVerificationResponse(
        message="If email exists, verification link has been sent",
        email=payload.email,
    )


@router.post("/email/verify", response_model=schemas.VerifyEmailResponse)
async def verify_email(
    payload: schemas.VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email with token.
    
    Security:
    - A2: Token validation with expiration
    - A3: Parameterized query prevents SQL injection
    """
    # Find user with token
    result = await db.execute(
        select(models.User).where(models.User.verification_token == payload.token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"Verification attempted with invalid token")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Check token expiration
    if EmailService.is_token_expired(user.verification_token_expires):
        logger.warning(f"Verification token expired for user {user.id}")
        raise HTTPException(status_code=400, detail="Token has expired")
    
    # Mark as verified
    user.is_verified = True
    user.email_verified_at = datetime.utcnow()
    user.verification_token = None
    user.verification_token_expires = None
    
    await db.commit()
    
    logger.info(f"Email verified for user {user.id}")
    
    return schemas.VerifyEmailResponse(
        message="Email verified successfully",
        email_verified=True,
    )


@router.post("/password/reset-request", response_model=schemas.RequestPasswordResetResponse)
async def request_password_reset(
    payload: schemas.RequestPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset.
    
    Security:
    - A7: Rate limited to prevent brute force
    - A2: Generates cryptographically secure token (1-hour expiry)
    - A1: Can't be used by attacker without email access
    """
    # Find user by email
    result = await db.execute(select(models.User).where(models.User.email == payload.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # FIX: Don't reveal if email exists
        logger.info(f"Password reset requested for non-existent email: {payload.email}")
        return schemas.RequestPasswordResetResponse(
            message="If email exists, password reset link has been sent"
        )
    
    # Check rate limit
    await check_email_rate_limit(user.id, EmailSettings.MAX_EMAIL_PER_HOUR)
    
    # Generate token (short expiry for security)
    token = EmailService.generate_verification_token()
    user.password_reset_token = token
    user.password_reset_expires = EmailService.get_password_reset_expiry()
    
    # Build reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    # Send email
    if email_service.enabled:
        html_content, text_content = EmailTemplates.password_reset_email(
            username=user.username,
            reset_link=reset_link,
            frontend_url=settings.FRONTEND_URL,
        )
        
        success, message = await email_service.send_email(
            to_email=user.email,
            subject="Reset Your Password - CyberAuth",
            html_content=html_content,
            text_content=text_content,
        )
        
        if not success:
            logger.error(f"Failed to send password reset email to {user.email}")
    else:
        logger.warning("Email service not configured - password reset email not sent")
    
    # Save token
    await db.commit()
    
    return schemas.RequestPasswordResetResponse(
        message="If email exists, password reset link has been sent"
    )


@router.post("/password/reset", response_model=schemas.ResetPasswordResponse)
async def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password with token.
    
    Security:
    - A2: Token validation with expiration (1 hour)
    - A3: Parameterized queries prevent SQL injection
    - A7: Password validated for strength
    """
    # Find user with token
    result = await db.execute(
        select(models.User).where(models.User.password_reset_token == payload.token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning("Password reset attempted with invalid token")
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Check token expiration
    if EmailService.is_token_expired(user.password_reset_expires):
        logger.warning(f"Password reset token expired for user {user.id}")
        raise HTTPException(status_code=400, detail="Token has expired")
    
    # Hash new password
    from main import hash_password
    
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    
    await db.commit()
    
    logger.info(f"Password reset for user {user.id}")
    
    return schemas.ResetPasswordResponse(
        message="Password reset successfully",
        success=True,
    )
