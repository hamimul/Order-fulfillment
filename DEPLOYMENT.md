# Deployment Guide

This guide covers deploying the Order Fulfillment System in various environments.

## Table of Contents

1. [Development Deployment](#development-deployment)
2. [Production Deployment](#production-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Performance Tuning](#performance-tuning)
5. [Monitoring Setup](#monitoring-setup)

## Development Deployment

### Quick Start (Windows)

```cmd
# One-command setup and start
scripts\quickstart.bat
```

### Manual Development Setup

1. **Prerequisites**
   - Python 3.8+
   - Docker Desktop
   - Git

2. **Setup Steps**
   ```cmd
   git clone <repository-url>
   cd order-fulfillment
   scripts\setup.bat
   scripts\start_services.bat
   ```

3. **Verify Installation**
   - API: http://localhost:8000/swagger/
   - Health: http://localhost:8000/health/
   - Admin: http://localhost:8000/admin/

## Production Deployment

### Docker Production Setup

1. **Create Production Docker Compose**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    build: 
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "80:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/order_fulfillment
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A order_fulfillment worker -l info --concurrency=4
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/order_fulfillment
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  beat:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A order_fulfillment beat -l info
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/order_fulfillment
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=order_fulfillment
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

2. **Create Production Dockerfile**

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "order_fulfillment.wsgi:application"]
```

3. **Environment Variables (.env.prod)**

```env
SECRET_KEY=your-super-secret-production-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=secure-database-password
DATABASE_URL=postgresql://postgres:secure-database-password@db:5432/order_fulfillment
REDIS_URL=redis://redis:6379/0
```

4. **Deploy**

```bash
# Build and start production containers
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Load initial data
docker-compose -f docker-compose.prod.yml exec web python manage.py setup_demo_data
```

### NGINX Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream web {
        server web:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://web;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }

        location /static/ {
            alias /app/staticfiles/;
        }

        location /media/ {
            alias /app/media/;
        }
    }
}
```

## Cloud Deployment

### AWS ECS Deployment

1. **Create ECS Task Definition**

```json
{
  "family": "order-fulfillment",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "your-ecr-repo/order-fulfillment:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:order-fulfillment-secrets"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/order-fulfillment",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

2. **Create ECS Service**

```bash
aws ecs create-service \
    --cluster order-fulfillment-cluster \
    --service-name order-fulfillment-service \
    --task-definition order-fulfillment:1 \
    --desired-count 2 \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/order-fulfillment-tg,containerName=web,containerPort=8000
```

### Kubernetes Deployment

1. **Create Kubernetes Manifests**

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-fulfillment-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-fulfillment-web
  template:
    metadata:
      labels:
        app: order-fulfillment-web
    spec:
      containers:
      - name: web
        image: your-registry/order-fulfillment:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "False"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: order-fulfillment-secrets
              key: secret-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: order-fulfillment-service
spec:
  selector:
    app: order-fulfillment-web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Performance Tuning

### Database Optimization

1. **PostgreSQL Configuration**

```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.7
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

2. **Database Indexing**

```sql
-- Additional indexes for performance
CREATE INDEX CONCURRENTLY idx_orders_status_created 
ON orders (status, created_at);

CREATE INDEX CONCURRENTLY idx_inventory_available 
ON inventory_items ((quantity - reserved_quantity));

CREATE INDEX CONCURRENTLY idx_order_items_product 
ON order_items (product_id, order_id);
```

### Application Optimization

1. **Django Settings**

```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'OPTIONS': {
                'MAX_CONNS': 20,
            }
        },
        'CONN_MAX_AGE': 600,
    }
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

2. **Celery Optimization**

```python
# celery.py
from celery import Celery

app = Celery('order_fulfillment')

app.conf.update(
    broker_pool_limit=20,
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_compression='gzip',
    result_compression='gzip',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,
    timezone='UTC',
    enable_utc=True,
)
```

## Monitoring Setup

### Health Checks

1. **Application Health**

```python
# Custom health check
from django.http import JsonResponse
from django.db import connection
import redis

def detailed_health_check(request):
    health = {"status": "healthy", "checks": {}}
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health["checks"]["database"] = "healthy"
    except Exception as e:
        health["checks"]["database"] = f"unhealthy: {e}"
        health["status"] = "unhealthy"
    
    # Redis check
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        health["checks"]["redis"] = "healthy"
    except Exception as e:
        health["checks"]["redis"] = f"unhealthy: {e}"
        health["status"] = "unhealthy"
    
    return JsonResponse(health)
```

2. **Prometheus Metrics**

```python
# Install django-prometheus
pip install django-prometheus

# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Add metrics endpoint
urlpatterns = [
    path('metrics/', include('django_prometheus.urls')),
]
```

### Logging Configuration

```python
# settings/production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS everywhere
- [ ] Set secure Django settings
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Enable database SSL
- [ ] Set up Web Application Firewall (WAF)
- [ ] Configure rate limiting
- [ ] Set up log monitoring
- [ ] Regular security updates
- [ ] Database backup strategy

### Django Security Settings

```python
# settings/production.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
```

## Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="order_fulfillment"

# Create backup
docker-compose exec -T db pg_dump -U postgres $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

### Application Data Backup

```bash
# Backup uploaded files and logs
tar -czf /backups/app_data_$(date +%Y%m%d).tar.gz /app/media /app/logs
```

## Rollback Strategy

1. **Database Rollback**
   ```bash
   # Restore from backup
   gunzip -c backup_20240123_120000.sql.gz | docker-compose exec -T db psql -U postgres order_fulfillment
   ```

2. **Application Rollback**
   ```bash
   # Deploy previous version
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

This deployment guide provides comprehensive coverage for deploying the Order Fulfillment System in various environments with proper monitoring, security, and backup strategies.