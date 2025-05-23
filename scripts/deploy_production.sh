#!/bin/bash

# Production Deployment Script for Order Fulfillment System
# This script deploys the application to production using Docker

set -e  # Exit on any error

echo "=============================================="
echo "   Order Fulfillment Production Deployment"
echo "=============================================="

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    echo "ERROR: .env.prod file not found!"
    echo "Please create a .env.prod file with production environment variables."
    exit 1
fi

# Load production environment variables
export $(cat .env.prod | grep -v '^#' | xargs)

# Validate required environment variables
REQUIRED_VARS=(
    "SECRET_KEY"
    "DB_PASSWORD"
    "ALLOWED_HOSTS"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set in .env.prod"
        exit 1
    fi
done

echo "✓ Environment variables validated"

# Create SSL directory if it doesn't exist
mkdir -p ssl

# Check if SSL certificates exist
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo "WARNING: SSL certificates not found in ssl/ directory"
    echo "Creating self-signed certificates for testing..."

    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem \
        -days 365 -nodes -subj '/CN=localhost'

    echo "✓ Self-signed SSL certificates created"
    echo "⚠ WARNING: Replace with proper SSL certificates for production!"
fi

# Create necessary directories
mkdir -p logs
mkdir -p media
mkdir -p backups

echo "✓ Directories created"

# Build and start production containers
echo "Building production Docker images..."
docker-compose -f docker-compose.prod.yml build

echo "Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 15

# Run database migrations
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate

# Collect static files
echo "Collecting static files..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# Create superuser (if it doesn't exist)
echo "Creating superuser (if needed)..."
docker-compose -f docker-compose.prod.yml exec -T web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print("Creating superuser...")
    import os
    User.objects.create_superuser(
        username=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'),
        email=os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'),
        password=os.getenv('DJANGO_SUPERUSER_PASSWORD', 'changeme123')
    )
    print("Superuser created successfully!")
else:
    print("Superuser already exists")
EOF

# Load initial data (optional)
if [ "$LOAD_DEMO_DATA" = "true" ]; then
    echo "Loading demo data..."
    docker-compose -f docker-compose.prod.yml exec -T web python manage.py setup_demo_data --products 100
fi

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
echo "   Production Deployment Complete!"
echo "=============================================="
echo ""
echo "Services:"
echo "  • Application: https://localhost"
echo "  • API Documentation: https://localhost/swagger/"
echo "  • Admin Panel: https://localhost/admin/"
echo "  • Flower (Celery Monitor): http://localhost:5555"
echo "  • Health Check: https://localhost/health/"
echo ""
echo "Management Commands:"
echo "  • View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  • Scale workers: docker-compose -f docker-compose.prod.yml up -d --scale worker=3"
echo "  • Update deployment: ./scripts/update_production.sh"
echo "  • Backup database: ./scripts/backup_production.sh"
echo ""

# Display service status
echo "Current service status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "Deployment completed successfully! 🚀"