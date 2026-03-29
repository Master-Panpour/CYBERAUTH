"""Tests for database migrations.

Tests ensure:
- Migrations apply without errors
- Schema is created correctly
- Data integrity is maintained
- Security constraints are enforced
"""

import pytest
import subprocess
from pathlib import Path
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings


class TestMigrations:
    """Test database migrations."""
    
    @pytest.fixture
    async def db_engine(self):
        """Create async database engine for testing."""
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        yield engine
        await engine.dispose()
    
    @pytest.fixture
    async def db_session(self, db_engine):
        """Create database session."""
        async_session_local = sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session_local() as session:
            yield session
    
    def test_migration_runs_successfully(self):
        """Test that alembic migrations run without errors."""
        backend_dir = Path(__file__).parent.parent
        cmd = [
            "alembic", "-c", str(backend_dir / "alembic.ini"),
            "upgrade", "head"
        ]
        
        result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
        assert result.returncode == 0, f"Migration failed: {result.stderr}"
    
    @pytest.mark.asyncio
    async def test_users_table_exists(self, db_engine):
        """Test that users table is created."""
        async with db_engine.connect() as conn:
            inspector = inspect(await conn.connection.run_sync(lambda x: x))
            tables = inspector.get_table_names()
            assert "users" in tables, "Users table not created"
    
    @pytest.mark.asyncio
    async def test_users_table_columns(self, db_engine):
        """Test that users table has all required columns."""
        async with db_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='users'")
            )
            columns = {row[0]: row for row in result.fetchall()}
            
            # Required columns
            assert "id" in columns
            assert "email" in columns
            assert "username" in columns
            assert "hashed_password" in columns
            assert "auth_provider" in columns
            assert "is_active" in columns
            assert "is_verified" in columns
            assert "created_at" in columns
            assert "last_login" in columns
            
            # Email should be unique
            assert columns["email"][1] == "character varying"  # String type
    
    @pytest.mark.asyncio
    async def test_email_unique_constraint(self, db_engine):
        """Test that email has unique constraint."""
        async with db_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='users' AND unique=true")
            )
            indexes = [row[0] for row in result.fetchall()]
            assert any("email" in idx for idx in indexes), "Email unique constraint not found"
    
    @pytest.mark.asyncio
    async def test_migration_down_succeeds(self):
        """Test that downgrading migrations works."""
        backend_dir = Path(__file__).parent.parent
        
        # Go up
        cmd_up = ["alembic", "-c", str(backend_dir / "alembic.ini"), "upgrade", "head"]
        result = subprocess.run(cmd_up, cwd=backend_dir, capture_output=True, text=True)
        assert result.returncode == 0
        
        # Go down
        cmd_down = ["alembic", "-c", str(backend_dir / "alembic.ini"), "downgrade", "-1"]
        result = subprocess.run(cmd_down, cwd=backend_dir, capture_output=True, text=True)
        assert result.returncode == 0
        
        # Go back up
        result = subprocess.run(cmd_up, cwd=backend_dir, capture_output=True, text=True)
        assert result.returncode == 0
    
    @pytest.mark.asyncio
    async def test_no_sql_injection_in_migration_files(self):
        """Test that migration files don't contain suspicious SQL patterns."""
        migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"
        
        dangerous_patterns = [
            "%(", "%s", "${", "{}", "exec(", "eval("
        ]
        
        for migration_file in migrations_dir.glob("*.py"):
            if migration_file.name == "__init__.py":
                continue
            
            content = migration_file.read_text()
            
            for pattern in dangerous_patterns:
                assert pattern not in content, f"Dangerous pattern '{pattern}' found in {migration_file.name}"
    
    @pytest.mark.asyncio
    async def test_indexes_created(self, db_engine):
        """Test that required indexes are created."""
        async with db_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='users'")
            )
            indexes = [row[0] for row in result.fetchall()]
            
            assert any("email" in idx for idx in indexes), "Email index not found"
            assert any("id" in idx for idx in indexes), "ID index not found"
    
    def test_migration_message_sanitization(self):
        """Test that migration messages are properly sanitized."""
        from migrations_helper import create_migration
        
        # Should reject messages that are too long
        with pytest.raises(ValueError):
            create_migration("x" * 256)
        
        # Should reject empty messages
        with pytest.raises(ValueError):
            create_migration("")
    
    @pytest.mark.asyncio
    async def test_users_table_constraints(self, db_engine):
        """Test that users table has proper constraints."""
        async with db_engine.connect() as conn:
            # Check NOT NULL constraints
            result = await conn.execute(
                text("""
                    SELECT column_name, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND is_nullable='NO'
                """)
            )
            not_null_columns = [row[0] for row in result.fetchall()]
            
            assert "id" in not_null_columns
            assert "email" in not_null_columns
            assert "username" in not_null_columns
            assert "is_active" in not_null_columns
            assert "is_verified" in not_null_columns


@pytest.mark.asyncio
async def test_insert_into_users(db_engine):
    """Test inserting a user into the migrated database."""
    async with db_engine.connect() as conn:
        # Insert test user
        await conn.execute(
            text("""
                INSERT INTO users 
                (email, username, hashed_password, auth_provider, is_active, is_verified)
                VALUES (:email, :username, :hashed_password, :auth_provider, :is_active, :is_verified)
            """),
            {
                "email": "test@example.com",
                "username": "testuser",
                "hashed_password": "hashed_pwd_123",
                "auth_provider": "local",
                "is_active": True,
                "is_verified": False
            }
        )
        
        # Verify insert
        result = await conn.execute(
            text("SELECT email, username FROM users WHERE email=:email"),
            {"email": "test@example.com"}
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "test@example.com"
        assert row[1] == "testuser"
        
        # Cleanup
        await conn.execute(text("DELETE FROM users WHERE email=:email"), {"email": "test@example.com"})
        await conn.commit()
