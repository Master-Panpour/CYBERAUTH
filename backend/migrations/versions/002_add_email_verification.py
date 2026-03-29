"""Add email verification and password reset fields to users table

Revision ID: 002_add_email_verification
Revises: 001_initial
Create Date: 2026-03-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_email_verification"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add email verification and password reset fields to users table."""
    # Add email verification fields
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True, unique=True))
    op.add_column('users', sa.Column('verification_token_expires', sa.DateTime(), nullable=True))
    
    # Add password reset fields
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True, unique=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    
    # Add tracking fields
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('users', sa.Column('last_login_ip', sa.String(), nullable=True))
    
    # Create indexes for performance
    op.create_index(op.f('ix_users_verification_token'), 'users', ['verification_token'], unique=True)
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=True)
    op.create_index(op.f('ix_users_email_verified_at'), 'users', ['email_verified_at'])


def downgrade() -> None:
    """Revert email verification and password reset fields."""
    op.drop_index(op.f('ix_users_email_verified_at'), table_name='users')
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_index(op.f('ix_users_verification_token'), table_name='users')
    
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'verification_token_expires')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_verified_at')
