"""Migration utilities and helpers."""

import subprocess
import sys
from pathlib import Path


def run_migrations(direction: str = "upgrade") -> None:
    """Run database migrations.
    
    Args:
        direction: "upgrade" to apply migrations, "downgrade" to revert
        
    Security:
        - Uses subprocess with shell=False to prevent command injection
        - Validates direction parameter
    """
    if direction not in ("upgrade", "downgrade"):
        raise ValueError(f"Invalid direction: {direction}. Must be 'upgrade' or 'downgrade'")
    
    backend_dir = Path(__file__).parent.parent
    cmd = ["alembic", "-c", str(backend_dir / "alembic.ini")]
    
    if direction == "upgrade":
        cmd.extend(["upgrade", "head"])
    else:
        cmd.extend(["downgrade", "-1"])
    
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Migration failed:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"Migration {direction} failed")
    
    print(result.stdout)


def create_migration(message: str) -> None:
    """Create a new migration file.
    
    Args:
        message: Migration description
        
    Security:
        - Sanitizes message to prevent injection
        - Uses subprocess with shell=False
    """
    if not message or len(message) > 255:
        raise ValueError("Message must be between 1-255 characters")
    
    # Sanitize message - remove problematic characters
    safe_message = "".join(c for c in message if c.isalnum() or c in (" ", "-", "_"))
    
    backend_dir = Path(__file__).parent.parent
    cmd = ["alembic", "-c", str(backend_dir / "alembic.ini"), "revision", "-m", safe_message]
    
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Migration creation failed:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError("Failed to create migration")
    
    print(result.stdout)


def get_current_revision() -> str:
    """Get current database revision."""
    backend_dir = Path(__file__).parent.parent
    cmd = ["alembic", "-c", str(backend_dir / "alembic.ini"), "current"]
    
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError("Failed to get current revision")
    
    return result.stdout.strip()


def get_migration_history() -> str:
    """Get migration history."""
    backend_dir = Path(__file__).parent.parent
    cmd = ["alembic", "-c", str(backend_dir / "alembic.ini"), "history"]
    
    result = subprocess.run(cmd, cwd=backend_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError("Failed to get migration history")
    
    return result.stdout
