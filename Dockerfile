FROM ubuntu:latest
LABEL authors="Hamimul Hasan"

ENTRYPOINT ["top", "-b"]

# Multi-stage build for production
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Install development dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Development command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production

# Install production dependencies only
COPY requirements.txt .
RUN pip install -r requirements.txt && \
    pip install gunicorn==21.2.0

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=order_fulfillment.settings

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /app/scripts/*.sh 2>/dev/null || true
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Production command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "order_fulfillment.wsgi:application"]