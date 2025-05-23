#!/bin/bash

# Production Restore Script for Order Fulfillment System
# Restores from backups created by backup_production.sh

set -e  # Exit on any error

echo "=============================================="
echo "   Order Fulfillment Production Restore"
echo "=============================================="

# Check if backup ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_id>"
    echo ""
    echo "Available backups:"
    ls -1 backups/database_*.sql.gz 2>/dev/null | sed 's/.*database_\(.*\)\.sql\.gz/  \1/' || echo "  No backups found"
    exit 1
fi

BACKUP_ID="$1"
BACKUP_DIR="./backups"
DB_NAME=${DB_NAME:-order_fulfillment}
DB_USER=${DB_USER:-postgres}

# Validate backup files exist
DB_BACKUP="$BACKUP_DIR/database_$BACKUP_ID.sql.gz"
APP_BACKUP="$BACKUP_DIR/appdata_$BACKUP_ID.json.gz"
MEDIA_BACKUP="$BACKUP_DIR/media_$BACKUP_ID.tar.gz"
CONFIG_BACKUP="$BACKUP_DIR/config_$BACKUP_ID.tar.gz"
MANIFEST="$BACKUP_DIR/manifest_$BACKUP_ID.txt"

if [ ! -f "$DB_BACKUP" ]; then
    echo "ERROR: Database backup not found: $DB_BACKUP"
    exit 1
fi

echo "Found backup: $BACKUP_ID"

# Display backup manifest if available
if [ -f "$MANIFEST" ]; then
    echo ""
    echo "Backup Information:"
    echo "==================="
    cat "$MANIFEST"
    echo ""
fi

# Confirmation prompt
echo "⚠ WARNING: This will replace all current data!"
echo "Are you sure you want to restore from backup $BACKUP_ID?"
read -p "Type 'yes' to continue: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Stop application services (keep database running)
echo "Stopping application services..."
docker-compose -f docker-compose.prod.yml stop web worker beat flower

# 1. Restore Database
echo "Restoring database..."
echo "  Dropping existing database..."
docker-compose -f docker-compose.prod.yml exec -T db dropdb -U "$DB_USER" "$DB_NAME" --if-exists

echo "  Creating new database..."
docker-compose -f docker-compose.prod.yml exec -T db createdb -U "$DB_USER" "$DB_NAME"

echo "  Restoring database from backup..."
gunzip -c "$DB_BACKUP" | docker-compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Database restored successfully"
else
    echo "✗ Database restore failed!"
    exit 1
fi

# 2. Restore Media Files
if [ -f "$MEDIA_BACKUP" ]; then
    echo "Restoring media files..."
    rm -rf media/
    tar -xzf "$MEDIA_BACKUP"
    echo "✓ Media files restored"
else
    echo "⚠ No media backup found for $BACKUP_ID"
fi

# 3. Restore Configuration (optional, with confirmation)
if [ -f "$CONFIG_BACKUP" ]; then
    echo ""
    read -p "Restore configuration files? (y/N): " restore_config
    if [ "$restore_config" = "y" ] || [ "$restore_config" = "Y" ]; then
        echo "Restoring configuration files..."
        tar -xzf "$CONFIG_BACKUP"
        echo "✓ Configuration files restored"
        echo "⚠ Note: You may need to restart services for config changes"
    fi
fi

# 4. Start services
echo "Starting application services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 15

# 5. Run post-restore tasks
echo "Running post-restore tasks..."

# Collect static files
echo "  Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# Clear cache
echo "  Clearing cache..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared')
"

# Health check
echo "Performing health check..."
sleep 5

if curl -f http://localhost/health/ > /dev/null 2>&1; then
    echo "✓ Health check passed"
else
    echo "⚠ Health check failed - checking service status..."
    docker-compose -f docker-compose.prod.yml ps
fi

echo ""
echo "=============================================="
echo "   Restore Complete!"
echo "=============================================="
echo ""
echo "Restored from backup: $BACKUP_ID"
echo "Services status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "Application URLs:"
echo "  • Application: https://localhost"
echo "  • Admin: https://localhost/admin/"
echo "  • Health Check: https://localhost/health/"
echo ""
echo "Restore completed successfully! ✅"