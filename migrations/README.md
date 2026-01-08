# Database Migrations

This directory contains SQL migration scripts for database schema changes.

## Running Migrations

### Option 1: Using Docker Exec

```bash
# Copy migration file to container
docker cp migrations/001_add_content_hash_to_sync_log.sql spca-db:/tmp/

# Execute migration
docker exec -i spca-db psql -U spca -d spca -f /tmp/001_add_content_hash_to_sync_log.sql
```

### Option 2: Using psql Directly

If you have access to the database host:

```bash
psql -U spca -d spca -f migrations/001_add_content_hash_to_sync_log.sql
```

### Option 3: Via Python Script

Run the migration script:

```bash
python scripts/run_migrations.py
```

## Migration Files

- `001_add_content_hash_to_sync_log.sql` - Adds content_hash column to sync_log table for deduplication
- `002_convert_images_url_to_jsonb.sql` - Converts images_url column from json to jsonb type for better performance and JSONB function support

## Notes

- Migrations use `IF NOT EXISTS` or `IF EXISTS` where possible to be idempotent
- Always backup your database before running migrations
- Migrations are numbered sequentially (001, 002, etc.)
