@echo off
echo ====================================
echo   Order Fulfillment System Startup
echo ====================================
echo.

REM Change to project root directory
cd /d "%~dp0\.."

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and make sure it's running
    pause
    exit /b 1
)

REM Start Docker services
echo Starting Docker services (PostgreSQL, Redis, PgAdmin)...
docker-compose up -d

REM Wait for services to be ready
echo Waiting for database to be ready...
timeout /t 10 /nobreak >nul

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run scripts\setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Create migrations if they don't exist
echo Creating migrations...
python manage.py makemigrations products --noinput
python manage.py makemigrations inventory --noinput
python manage.py makemigrations orders --noinput
python manage.py makemigrations core --noinput

REM Run database migrations
echo Running database migrations...
python manage.py migrate

REM Start Django development server
echo Starting Django development server...
start "Django Server" cmd /k "cd /d "%CD%" && venv\Scripts\activate.bat && python manage.py runserver"

REM Wait a moment for Django to start
timeout /t 3 /nobreak >nul

REM Start Celery worker
echo Starting Celery worker...
start "Celery Worker" cmd /k "cd /d "%CD%" && venv\Scripts\activate.bat && celery -A order_fulfillment worker -l info"

REM Wait a moment for Celery worker to start
timeout /t 3 /nobreak >nul

REM Start Celery beat scheduler
echo Starting Celery beat scheduler...
start "Celery Beat" cmd /k "cd /d "%CD%" && venv\Scripts\activate.bat && celery -A order_fulfillment beat -l info"

echo.
echo ====================================
echo   All services started successfully!
echo ====================================
echo.
echo Services running:
echo   - Django Server: http://localhost:8000
echo   - API Documentation: http://localhost:8000/swagger/
echo   - PostgreSQL: localhost:5432
echo   - PgAdmin: http://localhost:5050 (admin@example.com / admin123)
echo   - Redis: localhost:6379
echo.
echo Press any key to open the API documentation in your browser...
pause >nul

REM Open browser to API documentation
start http://localhost:8000/swagger/

echo.
echo System is ready! Press any key to exit this window...
pause >nul