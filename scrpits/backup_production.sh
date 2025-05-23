#!/bin/bash

# Production Backup Script for Order Fulfillment System
# Creates backups of database, media files, and logs

set -e  # Exit on any error

echo "=============================================="
echo "   Order Fulfillment Production Backup"
echo "=============================================="

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=${DB_NAME:-order_fulfillment}
DB_USER=${DB_USER:-postgres}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup process at $(date)"

# 1. Database Backup
echo "Creating database backup..."
docker-compose -f docker-compose.prod.yml exec -T db pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists | gzip > "$BACKUP_DIR/database_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    echo "✓ Database backup completed: database_$DATE.sql.gz"
    DB_SIZE=$(du -h "$BACKUP_DIR/database_$DATE.sql.gz" | cut -f1)
    echo "  Size: $DB_SIZE"
else
    echo "✗ Database backup failed!"
    exit 1
fi

# 2. Media Files Backup
echo "Creating media files backup..."
if [ -d "media" ] && [ "$(ls -A media 2>/dev/null)" ]; then
    tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" media/
    echo "✓ Media files backup completed: media_$DATE.tar.gz"
    MEDIA_SIZE=$(du -h "$BACKUP_DIR/media_$DATE.tar.gz" | cut -f1)
    echo "  Size: $MEDIA_SIZE"
else
    echo "⚠ No media files found to backup"
fi

# 3. Logs Backup
echo "Creating logs backup..."
if [ -d "logs" ] && [ "$(ls -A logs 2>/dev/null)" ]; then
    tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" logs/
    echo "✓ Logs backup completed: logs_$DATE.tar.gz"
    LOGS_SIZE=$(du -h "$BACKUP_DIR/logs_$DATE.tar.gz" | cut -f1)
    echo "  Size: $LOGS_SIZE"
else
    echo "⚠ No logs found to backup"
fi

# 4. Configuration Backup
echo "Creating configuration backup..."
CONFIG_FILES=()
[ -f ".env.prod" ] && CONFIG_FILES+=(".env.prod")
[ -f "docker-compose.prod.yml" ] && CONFIG_FILES+=("docker-compose.prod.yml")
[ -d "nginx" ] && CONFIG_FILES+=("nginx/")

if [ ${#CONFIG_FILES[@]} -gt 0 ]; then
    tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" "${CONFIG_FILES[@]}"
    echo "✓ Configuration backup completed: config_$DATE.tar.gz"
else
    echo "⚠ No configuration files found to backup"
fi

# 5. Application State Backup
echo "Creating application state backup..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --exclude=simple_history \
    --indent=2 | gzip > "$BACKUP_DIR/appdata_$DATE.json.gz"

if [ $? -eq 0 ]; then
    echo "✓ Application data backup completed: appdata_$DATE.json.gz"
    APP_SIZE=$(du -h "$BACKUP_DIR/appdata_$DATE.json.gz" | cut -f1)
    echo "  Size: $APP_SIZE"
else
    echo "⚠ Application data backup failed"
fi

# 6. Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/manifest_$DATE.txt" << EOF
Order Fulfillment System Backup
Generated: $(date)
Backup ID: $DATE

Files:
$(ls -lh "$BACKUP_DIR"/*_$DATE.* 2>/dev/null || echo "No backup files created")

System Info:
- Docker version: $(docker --version)
- Docker Compose version: $(docker-compose --version)
- Application version: $(docker-compose -f docker-compose.prod.yml exec -T web python manage.py version 2>/dev/null || echo "Unknown")

Database Info:
- Database: $DB_NAME
- User: $DB_USER

Services Status:
$(docker-compose -f docker-compose.prod.yml ps)
EOF

echo "✓ Backup manifest created: manifest_$DATE.txt"

# 7. Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "*_*.sql.gz" -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*_*.tar.gz" -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*_*.json.gz" -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "manifest_*.txt" -mtime +30 -delete 2>/dev/null || true
echo "✓ Old backups cleaned up (kept last 30 days)"

# 8. Display backup summary
echo ""
echo "=============================================="
echo "   Backup Summary"
echo "=============================================="
echo "Backup completed at: $(date)"
echo "Backup location: $BACKUP_DIR"
echo "Backup files:"
ls -lh "$BACKUP_DIR"/*_$DATE.* 2>/dev/null || echo "No backup files found"

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "Total backup directory size: $TOTAL_SIZE"
echo ""
echo "To restore from this backup:"
echo "  ./scripts/restore_production.sh $DATE"
echo ""
echo "Backup completed successfully! 💾"