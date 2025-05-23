#!/bin/bash

# Production Update Script for Order Fulfillment System
# Performs rolling updates with zero-downtime deployment

set -e  # Exit on any error

echo "=============================================="
echo "   Order Fulfillment Production Update"
echo "=============================================="

# Configuration
BACKUP_BEFORE_UPDATE=true
RUN_MIGRATIONS=true
UPDATE_DEPENDENCIES=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            BACKUP_BEFORE_UPDATE=false
            shift
            ;;
        --no-migrations)
            RUN_MIGRATIONS=false
            shift
            ;;
        --no-deps)
            UPDATE_DEPENDENCIES=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-backup      Skip backup before update"
            echo "  --no-migrations  Skip database migrations"
            echo "  --no-deps        Skip dependency updates"
            echo "  --help           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if production is running
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "ERROR: Production services are not running!"
    echo "Please start them first with: docker-compose -f docker-compose.prod.yml up -d"
    exit 1
fi

echo "Current system status:"
docker-compose -f docker-compose.prod.yml ps

# 1. Pre-update backup
if [ "$BACKUP_BEFORE_UPDATE" = true ]; then
    echo ""
    echo "Creating pre-update backup..."
    ./scripts/backup_production.sh

    if [ $? -ne 0 ]; then
        echo "ERROR: Backup failed! Aborting update."
        exit 1
    fi
    echo "✓ Pre-update backup completed"
fi

# 2. Pull latest code (if using git)
if [ -d ".git" ]; then
    echo ""
    echo "Pulling latest code..."

    # Stash any local changes
    git stash push -m "Auto-stash before production update $(date)"

    # Pull latest changes
    CURRENT_COMMIT=$(git rev-parse HEAD)
    git pull origin main
    NEW_COMMIT=$(git rev-parse HEAD)

    if [ "$CURRENT_COMMIT" = "$NEW_COMMIT" ]; then
        echo "✓ Already up to date"
    else
        echo "✓ Updated from $CURRENT_COMMIT to $NEW_COMMIT"
    fi
fi

# 3. Update dependencies if requested
if [ "$UPDATE_DEPENDENCIES" = true ]; then
    echo ""
    echo "Rebuilding Docker images with latest dependencies..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    echo "✓ Docker images rebuilt"
fi

# 4. Run database migrations if requested
if [ "$RUN_MIGRATIONS" = true ]; then
    echo ""
    echo "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate

    if [ $? -eq 0 ]; then
        echo "✓ Database migrations completed"
    else
        echo "✗ Database migrations failed!"
        exit 1
    fi
fi

# 5. Update static files
echo ""
echo "Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput
echo "✓ Static files updated"

# 6. Rolling update of web services
echo ""
echo "Performing rolling update of web services..."

# Scale up new web instances
echo "  Scaling up new web instances..."
docker-compose -f docker-compose.prod.yml up -d --scale web=2 --no-recreate

# Wait for new instances to be healthy
echo "  Waiting for new instances to be ready..."
sleep 15

# Health check on new instances
echo "  Performing health check..."
for i in {1..5}; do
    if curl -f http://localhost/health/ > /dev/null 2>&1; then
        echo "  ✓ New instances are healthy"
        break
    fi

    if [ $i -eq 5 ]; then
        echo "  ✗ Health check failed after 5 attempts!"
        echo "  Rolling back..."
        docker-compose -f docker-compose.prod.yml up -d --scale web=1
        exit 1
    fi

    echo "  Attempt $i failed, retrying in 10s..."
    sleep 10
done

# Scale down to single instance
echo "  Scaling back to single web instance..."
docker-compose -f docker-compose.prod.yml up -d --scale web=1

# 7. Update worker services
echo ""
echo "Updating worker services..."
docker-compose -f docker-compose.prod.yml stop worker beat
docker-compose -f docker-compose.prod.yml up -d worker beat
echo "✓ Worker services updated"

# 8. Clear application cache
echo ""
echo "Clearing application cache..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared successfully')
"

# 9. Cleanup old Docker images
echo ""
echo "Cleaning up old Docker images..."
docker image prune -f
echo "✓ Docker cleanup completed"

# 10. Final health check
echo ""
echo "Performing final health check..."
sleep 5

HEALTH_CHECK_PASSED=false
for i in {1..3}; do
    if curl -f http://localhost/health/ > /dev/null 2>&1; then
        HEALTH_CHECK_PASSED=true
        break
    fi
    echo "Health check attempt $i failed, retrying..."
    sleep 5
done

if [ "$HEALTH_CHECK_PASSED" = true ]; then
    echo "✓ Final health check passed"
else
    echo "⚠ Final health check failed!"
    echo "Service status:"
    docker-compose -f docker-compose.prod.yml ps
    exit 1
fi

# 11. Display update summary
echo ""
echo "=============================================="
echo "   Update Summary"
echo "=============================================="
echo "Update completed at: $(date)"

if [ -d ".git" ]; then
    echo "Git commit: $(git rev-parse --short HEAD)"
    echo "Last commit: $(git log -1 --pretty=format:'%s (%an, %ar)')"
fi

echo ""
echo "Services status:"
docker-compose -f docker-compose.prod.yml ps

# Get system statistics
echo ""
echo "System Statistics:"
echo "  CPU Usage: $(docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}' | grep web | awk '{print $2}')"
echo "  Memory Usage: $(docker stats --no-stream --format 'table {{.Container}}\t{{.MemUsage}}' | grep web | awk '{print $2}')"

# Check for any failed services
FAILED_SERVICES=$(docker-compose -f docker-compose.prod.yml ps --services --filter "status=exited")
if [ -n "$FAILED_SERVICES" ]; then
    echo ""
    echo "⚠ WARNING: Some services have failed:"
    echo "$FAILED_SERVICES"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs <service>"
fi

echo ""
echo "Application URLs:"
echo "  • Application: https://localhost"
echo "  • API Documentation: https://localhost/swagger/"
echo "  • Admin Panel: https://localhost/admin/"
echo "  • Health Check: https://localhost/health/"
echo ""
echo "Update completed successfully! 🚀"

# Optional: Send notification (uncomment and configure as needed)
# curl -X POST -H 'Content-type: application/json' \
#     --data '{"text":"Order Fulfillment System updated successfully"}' \
#     YOUR_SLACK_WEBHOOK_URL