#!/usr/bin/env python
"""Database migration management CLI.

Usage:
    python manage_migrations.py upgrade      # Apply all pending migrations
    python manage_migrations.py downgrade    # Revert one migration
    python manage_migrations.py history      # Show migration history
    python manage_migrations.py revision -m "description"  # Create migration
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    """Parse arguments and run migrations."""
    parser = argparse.ArgumentParser(description="Database migration management")
    subparsers = parser.add_subparsers(dest="command", help="Migration command")
    
    # Upgrade command
    subparsers.add_parser("upgrade", help="Apply all pending migrations")
    
    # Downgrade command
    subparsers.add_parser("downgrade", help="Revert one migration")
    
    # History command
    subparsers.add_parser("history", help="Show migration history")
    
    # Current command
    subparsers.add_parser("current", help="Show current database revision")
    
    # Revision (create) command
    revision_parser = subparsers.add_parser("revision", help="Create new migration")
    revision_parser.add_argument("-m", "--message", required=True, help="Migration description")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    backend_dir = Path(__file__).parent
    alembic_ini = backend_dir / "alembic.ini"
    
    cmd = ["alembic", "-c", str(alembic_ini)]
    
    if args.command == "upgrade":
        cmd.extend(["upgrade", "head"])
    elif args.command == "downgrade":
        cmd.extend(["downgrade", "-1"])
    elif args.command == "history":
        cmd.append("history")
    elif args.command == "current":
        cmd.append("current")
    elif args.command == "revision":
        cmd.extend(["revision", "-m", args.message])
    
    # Security: don't use shell=True to prevent injection
    result = subprocess.run(cmd, cwd=backend_dir)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
