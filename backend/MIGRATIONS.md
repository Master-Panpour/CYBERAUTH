# Database Migrations Guide

This guide explains how to use Alembic for managing database schema changes.

## Setup

Alembic is already installed in `requirements.txt`. The migrations directory structure is:

```
backend/
├── alembic.ini                    # Alembic configuration
├── manage_migrations.py           # CLI management script
├── migrations_helper.py           # Python helper functions
└── migrations/
    ├── env.py                     # Alembic environment
    ├── script.py.mako             # Migration template
    └── versions/
        └── 001_initial.py         # Initial schema migration
```

## Commands

### Apply All Pending Migrations
```bash
cd backend
python manage_migrations.py upgrade
# or
alembic upgrade head
```

### Revert One Migration
```bash
python manage_migrations.py downgrade
# or
alembic downgrade -1
```

### View Migration History
```bash
python manage_migrations.py history
# or
alembic history
```

### Show Current Revision
```bash
python manage_migrations.py current
# or
alembic current
```

### Create New Migration
```bash
python manage_migrations.py revision -m "Add new column to users"
# or
alembic revision -m "Add new column to users"
```

This creates a new file in `migrations/versions/` that you must edit to add your SQL.

## How to Create a Migration

1. **Create migration file:**
   ```bash
   python manage_migrations.py revision -m "Add email_verified_at to users"
   ```

2. **Edit the generated file** (`migrations/versions/00X_*.py`):
   ```python
   def upgrade() -> None:
       """Apply migration."""
       op.add_column('users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
   
   
   def downgrade() -> None:
       """Revert migration."""
       op.drop_column('users', 'email_verified_at')
   ```

3. **Test the migration:**
   ```bash
   python manage_migrations.py upgrade
   ```

4. **Verify and commit:**
   ```bash
   git add migrations/
   git commit -m "Add email verification timestamp"
   ```

## Best Practices

### Security
- ✅ Use parameterized queries (SQLAlchemy does this automatically)
- ✅ Avoid `op.execute()` with string formatting
- ✅ Always add `NOT NULL` constraints when appropriate
- ✅ Use `server_default` for important fields
- ❌ Never hardcode sensitive data in migrations

### Performance
- ✅ Add indexes for frequently queried columns
- ✅ Use `batch_op` for altering large tables
- ✅ Create indexes **before** adding foreign key constraints
- ❌ Don't create indexes on low-cardinality columns

### Backwards Compatibility
- ✅ Make migrations reversible (always write `downgrade`)
- ✅ Test both upgrade and downgrade
- ✅ Use default values when adding new columns
- ✅ Don't drop columns in initial deployment

## Testing Migrations

Run the migration tests:
```bash
cd backend
pytest tests/test_migrations.py -v
```

Tests verify:
- ✅ Migrations apply successfully
- ✅ Schema is created correctly
- ✅ Constraints are enforced
- ✅ Indexes are created
- ✅ Data integrity is maintained

## Common Pattern: Adding a Table

```python
# migrations/versions/002_add_sessions.py

def upgrade() -> None:
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Always index foreign keys
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_table('sessions')
```

## Troubleshooting

### Migration won't apply
```bash
# Check current revision
python manage_migrations.py current

# Check if there's a conflict
python manage_migrations.py history

# Rollback and try again
python manage_migrations.py downgrade
python manage_migrations.py upgrade
```

### Need to revert a migration in production
```bash
python manage_migrations.py downgrade
# This will run the `downgrade()` function from the migration
```

### Current database doesn't match migrations
```bash
# Reset (DANGER: Data loss!)
python manage_migrations.py downgrade base
# Then reapply
python manage_migrations.py upgrade head
```

## OWASP Security Considerations

### A1: Broken Access Control
- ✅ Migrations run with database admin credentials only
- ✅ Restrict migration scripts to admins

### A2: Cryptographic Failures
- ✅ Use secure column types (no storing passwords in plain text)
- ✅ Hash functions applied in application, not database

### A3: Injection (SQL Injection)
- ✅ SQLAlchemy ORM prevents SQL injection
- ✅ Use `op.execute()` with parameters only
- ❌ Never use f-strings or format() for SQL in migrations

### A5: Security Misconfiguration
- ✅ Alembic config reads from environment variables
- ✅ Secrets not stored in alembic.ini

### A6: Outdated Components
- ✅ Keep SQLAlchemy and Alembic updated
- ✅ Run `pip audit` regularly

## References

- [Alembic Official Docs](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Operations](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [OWASP Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html)
