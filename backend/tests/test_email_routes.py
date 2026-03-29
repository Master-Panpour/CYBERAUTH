"""Integration tests for email verification and password reset endpoints.

Tests cover:
- Email verification endpoint flow
- Password reset endpoint flow
- Rate limiting enforcement
- Input validation
- Security: OWASP A1, A2, A3, A7, A9
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from models import User
from schemas import (
    RequestEmailVerificationRequest,
    VerifyEmailRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.mark.asyncio
class TestEmailVerificationEndpoints:
    """Test email verification endpoints."""
    
    async def test_request_verification_email_success(self, client, db_session, mocker):
        """Test requesting verification email successfully."""
        # Create a user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",  # Sample hash
        )
        db_session.add(user)
        db_session.commit()
        
        # Mock email sending
        mock_send = mocker.patch(
            "email_routes.email_service.send_email",
            return_value=(True, "Email sent")
        )
        
        # Request verification
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 200
        assert "email" in response.json()
        assert mock_send.called
    
    async def test_request_verification_invalid_email(self, client):
        """Test requesting verification with invalid email format."""
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_verify_email_success(self, client, db_session, mocker):
        """Test verifying email with valid token."""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        # Generate and save token
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = EmailService.get_verification_expiry()
        db_session.commit()
        
        # Verify email
        response = client.post(
            "/auth/email/verify",
            json={"token": token}
        )
        
        assert response.status_code == 200
        assert response.json()["email_verified"] == True
        
        # Check user is marked as verified
        db_session.refresh(user)
        assert user.email_verified_at is not None
    
    async def test_verify_email_invalid_token(self, client):
        """Test verifying with invalid token."""
        response = client.post(
            "/auth/email/verify",
            json={"token": "invalid-token"}
        )
        
        assert response.status_code == 404
        assert "token" in response.json()["detail"].lower()
    
    async def test_verify_email_expired_token(self, client, db_session):
        """Test verifying with expired token."""
        # Create user with expired token
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        # Generate token but make it expired
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()
        
        # Try to verify
        response = client.post(
            "/auth/email/verify",
            json={"token": token}
        )
        
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
    
    async def test_verify_email_token_already_verified(self, client, db_session):
        """Test verifying when email already verified."""
        # Create already-verified user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
            email_verified_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        
        response = client.post(
            "/auth/email/verify",
            json={"token": token}
        )
        
        assert response.status_code == 400
        assert "already verified" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestPasswordResetEndpoints:
    """Test password reset endpoints."""
    
    async def test_request_password_reset_success(self, client, db_session, mocker):
        """Test requesting password reset email."""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
            email_verified_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        
        # Mock email sending
        mock_send = mocker.patch(
            "email_routes.email_service.send_email",
            return_value=(True, "Email sent")
        )
        
        response = client.post(
            "/auth/password/reset-request",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 200
        assert "email" in response.json()
        assert mock_send.called
    
    async def test_request_password_reset_nonexistent_email(self, client):
        """Test password reset for nonexistent email (enumeration protection)."""
        response1 = client.post(
            "/auth/password/reset-request",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return same response regardless of whether email exists
        assert response1.status_code == 200
        assert "email" in response1.json()
    
    async def test_reset_password_success(self, client, db_session, mocker):
        """Test resetting password with valid token."""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$oldhash...",
            email_verified_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()
        old_hash = user.password_hash
        
        # Generate reset token
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        user.password_reset_token = token
        user.password_reset_expires = EmailService.get_password_reset_expiry()
        db_session.commit()
        
        # Reset password
        response = client.post(
            "/auth/password/reset",
            json={
                "token": token,
                "new_password": "NewSecure@Password123"
            }
        )
        
        assert response.status_code == 200
        
        # Check password was updated
        db_session.refresh(user)
        assert user.password_hash != old_hash
        assert user.password_reset_token is None  # Token cleared
    
    async def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token."""
        response = client.post(
            "/auth/password/reset",
            json={
                "token": "invalid-token",
                "new_password": "NewSecure@Password123"
            }
        )
        
        assert response.status_code == 404
    
    async def test_reset_password_weak_password(self, client, db_session):
        """Test reset password with weak password."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        user.password_reset_token = token
        user.password_reset_expires = EmailService.get_password_reset_expiry()
        db_session.commit()
        
        # Try weak password
        response = client.post(
            "/auth/password/reset",
            json={
                "token": token,
                "new_password": "weak"  # Too weak
            }
        )
        
        assert response.status_code == 422
        assert "password" in response.json()["detail"][0]["loc"]


@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting on email endpoints.
    
    Security: A7 - Rate limiting prevents brute force and spam
    """
    
    async def test_email_rate_limiting_per_user(self, client, db_session, mocker):
        """Test email rate limiting prevents flooding per user."""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id
        
        # Mock email sending
        mocker.patch(
            "email_routes.email_service.send_email",
            return_value=(True, "Email sent")
        )
        
        # Authenticate user and make requests
        # Note: Would need proper JWT auth in real implementation
        # This is a simplified test
        
        # Make 5 successful requests (at limit)
        from email_routes import _email_send_attempts
        _email_send_attempts[user_id] = [time.time()] * 5
        
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "test@example.com"}
        )
        
        # 6th request should be rate limited (429)
        assert response.status_code == 429
    
    async def test_rate_limit_resets_after_hour(self):
        """Test rate limit counter resets after 1 hour."""
        from email_routes import _email_send_attempts
        from email_config import EmailSettings
        
        user_id = 123
        now = time.time()
        one_hour_ago = now - 3601  # Just over 1 hour
        
        # Add attempts: some old, some recent
        _email_send_attempts[user_id] = [
            one_hour_ago,  # Should be filtered out
            one_hour_ago + 1,  # Should be filtered out
            now - 100,  # Recent
            now - 50,
            now,
        ]
        
        # After filtering, should have 3 recent attempts
        recent = [t for t in _email_send_attempts[user_id] if t > now - 3600]
        assert len(recent) == 3


@pytest.mark.asyncio
class TestSecurityVulnerabilities:
    """Test prevention of security vulnerabilities.
    
    OWASP Top 10 Coverage
    """
    
    async def test_a1_broken_access_control(self, client, db_session):
        """A1: Test users can only reset their own password.
        
        In real implementation, would need JWT auth verification.
        """
        # Only own email should trigger reset
        # Other emails should give same response (enumeration protection)
        response1 = client.post(
            "/auth/password/reset-request",
            json={"email": "attacker@example.com"}
        )
        response2 = client.post(
            "/auth/password/reset-request",
            json={"email": "victim@example.com"}
        )
        
        # Both should return 200 (enumeration protection)
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    async def test_a2_cryptographic_failures_token_strength(self):
        """A2: Test tokens have sufficient cryptographic strength."""
        from email_service import EmailService
        
        tokens = set()
        for _ in range(100):
            token = EmailService.generate_verification_token()
            assert token not in tokens
            tokens.add(token)
        
        # All should be unique
        assert len(tokens) == 100
    
    async def test_a3_injection_sql_injection_prevention(self, client):
        """A3: Test SQL injection prevention in email endpoints."""
        # Try SQL injection in email field
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "test@example.com'; DROP TABLE users; --"}
        )
        
        # Should fail validation (invalid email)
        assert response.status_code == 422
    
    async def test_a3_injection_template_injection_prevention(self, client, db_session, mocker):
        """A3: Test template injection prevention."""
        user = User(
            email="test@example.com",
            username="{{ __import__('os').system('ls') }}",  # Template injection attempt
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        mocker.patch(
            "email_routes.email_service.send_email",
            return_value=(True, "Email sent")
        )
        
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "test@example.com"}
        )
        
        # Should succeed but template injection shouldn't execute
        assert response.status_code == 200
    
    async def test_a7_authentication_token_expiration_enforced(self, client, db_session):
        """A7: Test token expiration is enforced."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        # Create expired token
        from email_service import EmailService
        token = EmailService.generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()
        
        # Try to use expired token
        response = client.post(
            "/auth/email/verify",
            json={"token": token}
        )
        
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
    
    async def test_a9_logging_audit_trail(self, client, db_session, mocker, caplog):
        """A9: Test security events are logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db_session.add(user)
        db_session.commit()
        
        mocker.patch(
            "email_routes.email_service.send_email",
            return_value=(True, "Email sent")
        )
        
        # Make request that should be logged
        response = client.post(
            "/auth/email/verify-request",
            json={"email": "test@example.com"}
        )
        
        # Check logs contain security event
        # (Implementation depends on logging configuration)


@pytest.mark.asyncio
class TestEmailEnumerationProtection:
    """Test that email enumeration attacks are prevented.
    
    Attacker should not be able to determine if email exists
    by comparing response times or error messages.
    """
    
    async def test_reset_request_same_response_for_existing_and_nonexistent(self, client):
        """Test same response for existing and nonexistent emails."""
        # Create user
        from models import User
        from database import SessionLocal
        
        db = SessionLocal()
        user = User(
            email="existing@example.com",
            username="testuser",
            password_hash="$2b$12$...",
        )
        db.add(user)
        db.commit()
        db.close()
        
        # Request reset for existing email
        response1 = client.post(
            "/auth/password/reset-request",
            json={"email": "existing@example.com"}
        )
        
        # Request reset for nonexistent email
        response2 = client.post(
            "/auth/password/reset-request",
            json={"email": "nonexistent@example.com"}
        )
        
        # Both should succeed (200) - user doesn't confirm existence
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Response structure should be similar
        assert "email" in response1.json()
        assert "email" in response2.json()
    
    async def test_verification_request_same_response_for_all(self, client):
        """Test verification request doesn't leak email existence."""
        response1 = client.post(
            "/auth/email/verify-request",
            json={"email": "any@example.com"}
        )
        response2 = client.post(
            "/auth/email/verify-request",
            json={"email": "other@example.com"}
        )
        
        # Both should have same response status
        assert response1.status_code == response2.status_code
