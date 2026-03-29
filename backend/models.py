from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model with email verification and password reset support.
    
    Security features:
    - Email verification token for account verification
    - Password reset token for password recovery
    - Token expiration tracking for security
    - Email verification timestamp for audit
    """
    __tablename__ = "users"

    id                          = Column(Integer, primary_key=True, index=True)
    email                       = Column(String, unique=True, index=True, nullable=False)
    username                    = Column(String, nullable=False)
    hashed_password             = Column(String, nullable=True)          # null for OAuth users
    avatar_url                  = Column(String, nullable=True)
    auth_provider               = Column(String, default="local")        # local | google | github
    provider_id                 = Column(String, nullable=True)
    is_active                   = Column(Boolean, default=True)
    is_verified                 = Column(Boolean, default=False)
    
    # Email verification fields
    email_verified_at           = Column(DateTime, nullable=True)        # When email was verified
    verification_token          = Column(String, nullable=True, unique=True)  # Current verification token
    verification_token_expires  = Column(DateTime, nullable=True)        # When token expires
    
    # Password reset fields
    password_reset_token        = Column(String, nullable=True, unique=True)  # Current reset token
    password_reset_expires      = Column(DateTime, nullable=True)        # When reset token expires
    
    # Tracking fields
    created_at                  = Column(DateTime, default=datetime.utcnow)
    updated_at                  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login                  = Column(DateTime, nullable=True)
    last_login_ip               = Column(String, nullable=True)          # For security tracking
