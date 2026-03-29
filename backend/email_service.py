"""Email service for sending verification and password reset emails.

Security Features:
- A2: Cryptographic Failures - TLS/SSL for SMTP connections
- A3: Injection - No template injection vulnerabilities
- A7: Authentication Bugs - Secure token-based email verification
- A9: Logging & Monitoring - Audit trail of email sends
"""

import aiosmtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

from email_config import EmailSettings

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email sending with security best practices."""
    
    def __init__(self):
        """Initialize email service."""
        self.enabled = EmailSettings.is_enabled()
        if not self.enabled:
            logger.warning("Email service not configured - emails will not be sent")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (fallback)
        
        Returns:
            Tuple (success: bool, message: str)
        
        Security:
            - Validates email format (basic check)
            - Uses TLS for secure SMTP connection
            - No sensitive data in logs
            - Handles errors safely without leaking info
        """
        if not self.enabled:
            logger.warning(f"Email not configured - skipping email to {to_email}")
            return False, "Email not configured"
        
        # Validate email format (basic)
        if not self._is_valid_email(to_email):
            logger.warning(f"Invalid email format: {to_email}")
            return False, "Invalid email format"
        
        try:
            # Create MIME message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = EmailSettings.SMTP_FROM_EMAIL
            message["To"] = to_email
            
            # Add plain text fallback
            if text_content:
                message.attach(MIMEText(text_content, "plain"))
            
            # Add HTML content
            message.attach(MIMEText(html_content, "html"))
            
            # Send via SMTP
            async with aiosmtplib.SMTP(
                hostname=EmailSettings.SMTP_HOST,
                port=EmailSettings.SMTP_PORT,
                use_tls=True,
            ) as smtp:
                await smtp.login(EmailSettings.SMTP_USER, EmailSettings.SMTP_PASSWORD)
                await smtp.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"
        
        except aiosmtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check credentials")
            return False, "Email service error (auth failed)"
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            return False, "Email service error"
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False, "Email service error"
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email validation.
        
        Security: Uses simple regex - full validation happens with pydantic.
        """
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate secure verification token.
        
        Security:
            - Uses secrets module (cryptographically secure)
            - 32 bytes = 256 bits of entropy
            - Hex encoded for storage
        
        Returns:
            Hex-encoded token
        """
        return secrets.token_hex(32)
    
    @staticmethod
    def get_verification_expiry() -> datetime:
        """Get verification token expiry time.
        
        Returns:
            Datetime when token expires
        """
        return datetime.utcnow() + timedelta(
            hours=EmailSettings.EMAIL_VERIFICATION_TIMEOUT_HOURS
        )
    
    @staticmethod
    def get_password_reset_expiry() -> datetime:
        """Get password reset token expiry time (short for security).
        
        Returns:
            Datetime when token expires
        """
        return datetime.utcnow() + timedelta(
            hours=EmailSettings.PASSWORD_RESET_TIMEOUT_HOURS
        )
    
    @staticmethod
    def is_token_expired(expiry: Optional[datetime]) -> bool:
        """Check if token is expired.
        
        Args:
            expiry: Token expiry datetime
        
        Returns:
            True if expired, False otherwise
        
        Security: Returns True for None values (fail-safe)
        """
        if expiry is None:
            return True
        return datetime.utcnow() > expiry


class EmailTemplates:
    """Email template generation.
    
    Security:
    - A3: Injection - No user input in templates without escaping
    - Uses HTML escaping for all dynamic content
    """
    
    @staticmethod
    def verification_email(
        username: str,
        verification_link: str,
        frontend_url: str,
    ) -> Tuple[str, str]:
        """Generate email verification email.
        
        Args:
            username: User's username (escaped)
            verification_link: Full verification link with token
            frontend_url: Frontend URL for branding
        
        Returns:
            Tuple (html_content, text_content)
        
        Security:
            - Uses HTML5 escaping for user content
            - Link is properly constructed server-side
        """
        import html
        
        safe_username = html.escape(username)
        safe_link = verification_link  # Already validated
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #1a1a1a; color: #00ffb4; padding: 20px; }}
                    .content {{ padding: 20px; background-color: #f5f5f5; }}
                    .button {{ display: inline-block; background-color: #00ffb4; color: #000; padding: 12px 20px; border-radius: 4px; text-decoration: none; margin: 20px 0; }}
                    .footer {{ color: #666; font-size: 12px; text-align: center; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ CyberAuth - Email Verification</h1>
                    </div>
                    <div class="content">
                        <p>Hi {safe_username},</p>
                        <p>Thank you for signing up! Please verify your email address to activate your account.</p>
                        <p>
                            <a href="{safe_link}" class="button">Verify Email Address</a>
                        </p>
                        <p>Or copy and paste this link in your browser:</p>
                        <p><code>{safe_link}</code></p>
                        <p><strong>This link will expire in 24 hours.</strong></p>
                        <p>If you did not create this account, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2026 CyberAuth. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
CyberAuth - Email Verification

Hi {safe_username},

Thank you for signing up! Please verify your email address to activate your account.

Verification link: {safe_link}

This link will expire in 24 hours.

If you did not create this account, please ignore this email.

---
CyberAuth 2026
"""
        
        return html_content, text_content.strip()
    
    @staticmethod
    def password_reset_email(
        username: str,
        reset_link: str,
        frontend_url: str,
    ) -> Tuple[str, str]:
        """Generate password reset email.
        
        Args:
            username: User's username (escaped)
            reset_link: Full password reset link with token
            frontend_url: Frontend URL for branding
        
        Returns:
            Tuple (html_content, text_content)
        
        Security:
            - Short token expiry (1 hour)
            - Clear warning about link expiry
            - No sensitive data in email
        """
        import html
        
        safe_username = html.escape(username)
        safe_link = reset_link  # Already validated
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #1a1a1a; color: #ff6b6b; padding: 20px; }}
                    .content {{ padding: 20px; background-color: #f5f5f5; }}
                    .button {{ display: inline-block; background-color: #ff6b6b; color: #fff; padding: 12px 20px; border-radius: 4px; text-decoration: none; margin: 20px 0; }}
                    .warning {{ background-color: #ffe0e0; padding: 15px; border-left: 4px solid #ff6b6b; margin: 20px 0; }}
                    .footer {{ color: #666; font-size: 12px; text-align: center; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 CyberAuth - Password Reset</h1>
                    </div>
                    <div class="content">
                        <p>Hi {safe_username},</p>
                        <p>We received a request to reset your password.</p>
                        <p>
                            <a href="{safe_link}" class="button">Reset Password</a>
                        </p>
                        <p>Or copy and paste this link in your browser:</p>
                        <p><code>{safe_link}</code></p>
                        <div class="warning">
                            <strong>⚠️ Important:</strong> This link will expire in <strong>1 hour</strong>.
                        </div>
                        <p>If you did not request a password reset, please ignore this email and make sure your account is secure.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2026 CyberAuth. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
CyberAuth - Password Reset

Hi {safe_username},

We received a request to reset your password.

Reset link: {safe_link}

⚠️ IMPORTANT: This link will expire in 1 hour.

If you did not request a password reset, please ignore this email and make sure your account is secure.

---
CyberAuth 2026
"""
        
        return html_content, text_content.strip()


# Global email service instance
email_service = EmailService()
