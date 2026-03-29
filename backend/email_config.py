"""Email configuration and SMTP initialization.

OWASP Security Considerations:
- A2: Cryptographic Failures - Use TLS/SSL for SMTP
- A5: Security Misconfiguration - Credentials from environment only
- A7: Authentication Bugs - Support both OAuth XOAUTH2 and password auth
"""

from pydantic import Field
from config import settings


class EmailSettings:
    """Email configuration settings."""
    
    # SMTP server configuration
    SMTP_HOST: str = settings.SMTP_SERVER if hasattr(settings, 'SMTP_SERVER') else "smtp.gmail.com"
    SMTP_PORT: int = settings.SMTP_PORT if hasattr(settings, 'SMTP_PORT') else 587
    SMTP_USER: str = settings.SMTP_USER if hasattr(settings, 'SMTP_USER') else ""
    SMTP_PASSWORD: str = settings.SMTP_PASSWORD if hasattr(settings, 'SMTP_PASSWORD') else ""
    SMTP_FROM_EMAIL: str = settings.SMTP_FROM_EMAIL if hasattr(settings, 'SMTP_FROM_EMAIL') else "noreply@cyberauth.app"
    
    # Email configuration
    VERIFY_EMAIL_ON_SIGNUP: bool = True
    EMAIL_VERIFICATION_TIMEOUT_HOURS: int = 24
    PASSWORD_RESET_TIMEOUT_HOURS: int = 1  # Short timeout for security
    
    # Rate limiting for email sends
    MAX_EMAIL_PER_HOUR: int = 5  # Max emails per user per hour
    MAX_VERIFICATION_ATTEMPTS: int = 3  # Max verification attempts before requiring new email
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if email is configured and enabled."""
        return bool(EmailSettings.SMTP_USER and EmailSettings.SMTP_PASSWORD)
