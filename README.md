# Distributed Order Fulfillment System

A scalable, production-grade backend system that simulates a distributed order fulfillment workflow with Django, PostgreSQL, Redis, and Celery.

## 🎯 Features

- **Product & Inventory Management** - Track products and maintain accurate stock levels with real-time updates
- **Asynchronous Order Processing** - Multi-stage workflow with simulated real-world delays using Celery
- **Bulk Order Operations** - Handle high volume of concurrent orders with atomic transactions
- **Automatic Stale Order Detection** - Background tasks to identify and resolve stuck orders
- **Comprehensive History Tracking** - Complete audit trail with model versioning using django-simple-history
- **Event-Driven Architecture** - Django signals for decoupled component communication
- **Concurrency Control** - Database-level locking to prevent race conditions
- **RESTful API** - Complete API with OpenAPI/Swagger documentation
- **Real-time Monitoring** - Health checks and system status endpoints

## 🏗️ Architecture

The system uses a modern Django architecture with the following components:

- **Django REST Framework** - API layer with comprehensive serialization
- **PostgreSQL** - Primary database with ACID compliance
- **Redis** - Message broker for Celery and caching
- **Celery** - Asynchronous task processing and scheduling
- **Docker** - Containerized services for easy deployment

### Key Design Patterns

1. **Event-Driven Architecture** - Django signals handle cross-cutting concerns
2. **Command Query Responsibility Segregation (CQRS)** - Separate read/write operations
3. **Optimistic Concurrency Control** - Database-level locking for inventory management
4. **Version Control** - Complete audit trail for all data changes

## 📋 Prerequisites

### Required Software (Windows)

1. **Python 3.8+** - [Download from python.org](https://www.python.org/downloads/windows/)
2. **Docker Desktop** - [Download from docker.com](https://www.docker.com/products/docker-desktop/)
3. **Git for Windows** - [Download from git-scm.com](https://git-scm.com/download/win)
4. **Visual Studio Code** (Recommended) - [Download from code.visualstudio.com](https://code.visualstudio.com/)

## 🚀 Quick Start (Windows)

### 1. Clone the Repository

```cmd
git clone https://github.com/yourusername/order-fulfillment.git
cd order-fulfillment
```

### 2. Run Setup Script

```cmd
scripts\setup.bat
```

This script will:
- Create a Python virtual environment
- Install all dependencies
- Start Docker services (PostgreSQL, Redis, PgAdmin)
- Run database migrations
- Create demo data
- Prompt for Django admin user creation

### 3. Start All Services

```cmd
scripts\start_services.bat
```

This will start:
- Django development server (http://localhost:8000)
- Celery worker for background tasks
- Celery beat scheduler for periodic tasks

### 4. Access the System

- **API Documentation**: http://localhost:8000/swagger/
- **Django Admin**: http://localhost:8000/admin/
- **PgAdmin**: http://localhost:5050 (admin@example.com / admin123)
- **Health Check**: http://localhost:8000/health/

## 🛠️ Manual Setup (Alternative)

<details>
<summary>Click to expand manual setup instructions</summary>

### 1. Create Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```cmd
pip install -r requirements.txt
```

### 3. Start Docker Services

```cmd
docker-compose up -d
```

### 4. Configure Environment

Create `.env` file:
```env
DB_NAME=order_fulfillment
DB_USER=postgres
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 5. Run Migrations

```cmd
python manage.py migrate
```

### 6. Load Demo Data

```cmd
python manage.py setup_demo_data --products 50
```

### 7. Create Superuser

```cmd
python manage.py createsuperuser
```

### 8. Start Services

```cmd
# Terminal 1: Django Server
python manage.py runserver

# Terminal 2: Celery Worker
celery -A order_fulfillment worker -l info

# Terminal 3: Celery Beat
celery -A order_fulfillment beat -l info
```

</details>

## 📚 API Documentation

The system provides a comprehensive RESTful API documented with OpenAPI/Swagger.

### Core Endpoints

#### Products
- `GET /api/v1/products/` - List all products
- `POST /api/v1/products/` - Create a new product
- `GET /api/v1/products/{id}/` - Get product details
- `GET /api/v1/products/low_stock/` - Get products with low stock
- `GET /api/v1/products/{id}/stock_history/` - Get stock history

#### Orders
- `GET /api/v1/orders/` - List all orders
- `POST /api/v1/orders/` - Create a single order
- `POST /api/v1/orders/bulk_create/` - Create multiple orders
- `GET /api/v1/orders/{order_id}/` - Get order details
- `POST /api/v1/orders/{order_id}/cancel/` - Cancel an order
- `GET /api/v1/orders/{order_id}/history/` - Get order version history
- `GET /api/v1/orders/statistics/` - Get order statistics

#### Inventory
- `GET /api/v1/inventory/` - List inventory items
- `POST /api/v1/inventory/{id}/adjust/` - Manually adjust inventory
- `GET /api/v1/inventory/{id}/transactions/` - Get transaction history
- `GET /api/v1/inventory/summary/` - Get inventory summary

### Example API Calls

#### Create a Single Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "priority": "normal",
    "items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 3, "quantity": 1}
    ]
  }'
```

#### Create Bulk Orders

```bash
curl -X POST http://localhost:8000/api/v1/orders/bulk_create/ \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [
      {
        "customer_name": "Customer 1",
        "customer_email": "customer1@example.com",
        "items": [{"product_id": 1, "quantity": 1}]
      },
      {
        "customer_name": "Customer 2",
        "customer_email": "customer2@example.com",
        "items": [{"product_id": 2, "quantity": 2}]
      }
    ]
  }'
```

#### Check Order Status

```bash
curl http://localhost:8000/api/v1/orders/{order_id}/
```

## 🧪 Testing

### Run Unit Tests

```cmd
scripts\run_tests.bat
```

Or manually:

```cmd
python manage.py test
```

### Load Testing

The system includes built-in load testing capabilities:

```cmd
# Small load test
python manage.py load_test --orders 50 --threads 5

# Medium load test  
python manage.py load_test --orders 100 --threads 10

# Custom load test
python manage.py load_test --orders 200 --threads 20 --delay 0.05
```

### Test Coverage

Run tests with coverage:

```cmd
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generates HTML report in htmlcov/
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_NAME` | Database name | `order_fulfillment` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `password123` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | Django secret key | (required) |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |

### Celery Configuration

The system uses Celery for background task processing:

- **Order Processing** - Asynchronous order lifecycle management
- **Stale Order Detection** - Periodic task to handle stuck orders
- **Inventory Management** - Stock adjustments and notifications
- **Cleanup Tasks** - Maintenance and data retention

#### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `check_stale_orders` | Every minute | Detect and resolve stale orders |
| `generate_daily_report` | Daily at midnight | Generate order statistics |
| `cleanup_old_history` | Weekly | Clean up old audit records |

## 🏃‍♂️ Performance Considerations

### Database Optimization

1. **Indexing** - Strategic indexes on frequently queried fields
2. **Connection Pooling** - Efficient database connection management
3. **Query Optimization** - Use of `select_related` and `prefetch_related`
4. **Batch Operations** - Bulk operations for improved throughput

### Concurrency Control

1. **Database Locking** - Row-level locking with `select_for_update()`
2. **Atomic Transactions** - Ensuring data consistency
3. **Optimistic Concurrency** - Version-based conflict detection
4. **Race Condition Prevention** - Careful design of critical sections

### Scalability Features

1. **Horizontal Scaling** - Stateless application design
2. **Caching Strategy** - Redis for session and query caching
3. **Asynchronous Processing** - Background task queues
4. **Load Balancing Ready** - Session-independent architecture

## 📊 Monitoring and Observability

### Health Checks

The system provides comprehensive health monitoring:

```bash
curl http://localhost:8000/health/
```

Response includes:
- Database connectivity
- Redis connectivity  
- Celery worker status
- System resource usage

### Logging

Comprehensive logging is configured for:
- Order processing events
- Inventory changes
- Error tracking
- Performance metrics

Logs are written to:
- Console (development)
- Files in `logs/` directory
- Can be configured for external services (ELK, Splunk, etc.)

### Metrics and Analytics

The system tracks:
- Order processing rates
- Inventory turnover
- System performance
- Error rates
- Customer behavior

## 🔒 Security Considerations

### Data Protection

1. **Input Validation** - Comprehensive request validation
2. **SQL Injection Prevention** - Django ORM protection
3. **CSRF Protection** - Built-in Django middleware
4. **Rate Limiting** - API throttling (configurable)

### Authentication & Authorization

The demo system allows anonymous access. For production:

1. **JWT Authentication** - Token-based API access
2. **Role-Based Access Control** - User permission management
3. **API Key Management** - Service-to-service authentication
4. **Audit Logging** - User action tracking

## 🚀 Deployment

### Development Deployment

Use the provided scripts for local development:

```cmd
scripts\start_services.bat
```

### Production Deployment

For production deployment, consider:

1. **Container Orchestration** - Kubernetes or Docker Swarm
2. **Database Clustering** - PostgreSQL high availability
3. **Load Balancing** - Multiple application instances
4. **Monitoring** - Prometheus, Grafana, ELK stack
5. **SSL/TLS** - HTTPS termination
6. **Environment Secrets** - Secure configuration management

### Docker Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "80:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
    depends_on:
      - db
      - redis
  
  worker:
    build: .
    command: celery -A order_fulfillment worker -l info
    depends_on:
      - db
      - redis
  
  beat:
    build: .
    command: celery -A order_fulfillment beat -l info
    depends_on:
      - db
      - redis
```

## 🛠️ Troubleshooting

### Common Issues

<details>
<summary>Docker services won't start</summary>

1. Ensure Docker Desktop is running
2. Check port conflicts (5432, 6379, 5050)
3. Run `docker-compose down` then `docker-compose up -d`
4. Check Docker logs: `docker-compose logs`
</details>

<details>
<summary>Database connection errors</summary>

1. Verify PostgreSQL is running: `docker-compose ps`
2. Check database credentials in `.env`
3. Ensure database exists: `docker-compose exec postgres psql -U postgres -l`
4. Reset database: `docker-compose down -v` then `docker-compose up -d`
</details>

<details>
<summary>Celery tasks not processing</summary>

1. Check Redis connection: `redis-cli ping`
2. Verify Celery worker is running
3. Check for errors in Celery logs
4. Restart worker: `celery -A order_fulfillment worker -l info`
</details>

<details>
<summary>API returns 500 errors</summary>

1. Check Django logs in console
2. Verify database migrations: `python manage.py showmigrations`
3. Check for missing environment variables
4. Ensure demo data is loaded: `python manage.py setup_demo_data`
</details>

### Debug Commands

```cmd
# Check system status
python manage.py check

# View database migrations
python manage.py showmigrations

# Reset database
python manage.py flush

# Check Celery worker status
celery -A order_fulfillment inspect active

# Monitor Celery tasks
celery -A order_fulfillment events
```

## 📝 Development

### Project Structure

```
order-fulfillment/
├── order_fulfillment/          # Django project settings
├── products/                   # Product management app
├── inventory/                  # Inventory management app  
├── orders/                     # Order processing app
├── core/                       # Core utilities and health checks
├── scripts/                    # Windows batch scripts
├── tests/                      # Test suite
├── logs/                       # Application logs
├── docker-compose.yml          # Docker services configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Development Workflow

1. **Make Changes** - Modify code in appropriate app
2. **Run Tests** - `python manage.py test`
3. **Check Migrations** - `python manage.py makemigrations`
4. **Apply Migrations** - `python manage.py migrate`
5. **Test API** - Use Swagger UI or Postman
6. **Load Test** - Run performance tests

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support and questions:

1. Check the troubleshooting section above
2. Review the API documentation at `/swagger/`
3. Check system health at `/health/`
4. Review application logs in the `logs/` directory

## 🎉 Acknowledgments

- Django REST Framework for excellent API framework
- Celery for robust task queue system
- PostgreSQL for reliable data storage
- Redis for high-performance caching and messaging
- Docker for containerization and easy deployment

---

**Built with ❤️ using Django, PostgreSQL, Redis, and Celery**