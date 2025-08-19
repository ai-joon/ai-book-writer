# Database Migrations

This directory contains Alembic database migrations for sopher.ai.

## Setup

1. Install Alembic (included in dev dependencies):
```bash
pip install alembic
```

2. Configure database URL:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/sopherai"
```

## Running Migrations

### Apply all migrations:
```bash
alembic upgrade head
```

### Apply specific migration:
```bash
alembic upgrade 001
```

### Rollback last migration:
```bash
alembic downgrade -1
```

### Rollback all migrations:
```bash
alembic downgrade base
```

## Creating New Migrations

### Auto-generate from model changes:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Create empty migration:
```bash
alembic revision -m "Description of changes"
```

## Migration History

### 001 - Add User table and Session foreign key
- Creates `users` table for OAuth authentication
- Adds `user_id` foreign key to `sessions` table
- Handles existing sessions by creating legacy user
- Safe rollback preserves data

## Production Deployment

1. **Backup database** before running migrations
2. Run migrations during low-traffic period
3. Test rollback procedure in staging first

### Docker deployment:
```bash
docker-compose exec api alembic upgrade head
```

### Kubernetes deployment:
```bash
kubectl exec -it deployment/sopher-api -- alembic upgrade head
```

## Troubleshooting

### Migration fails with "relation already exists"
The database may already have the tables. Check with:
```sql
SELECT * FROM alembic_version;
```

### AsyncIO errors
Ensure you're using the async PostgreSQL driver:
```python
postgresql+asyncpg://  # Correct
postgresql://          # Wrong for async
```

### Permission errors
Ensure the database user has CREATE/ALTER permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE sopherai TO myuser;
```