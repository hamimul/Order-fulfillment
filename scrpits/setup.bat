@echo off
echo =======================================
echo   Order Fulfillment System Setup
echo =======================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Docker installation
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo Step 1: Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip

echo Step 4: Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Step 5: Starting Docker services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    pause
    exit /b 1
)

echo Step 6: Waiting for database to be ready...
timeout /t 15 /nobreak >nul

echo Step 7: Running database migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Database migration failed
    pause
    exit /b 1
)

echo Step 8: Creating logs directory...
if not exist "logs" mkdir logs

echo Step 9: Creating superuser account...
echo.
echo You will be prompted to create an admin account for Django admin interface.
echo You can skip this by pressing Ctrl+C if you want to create it later.
echo.
python manage.py createsuperuser

echo Step 10: Loading demo data...
python manage.py setup_demo_data --products 50
if %errorlevel% neq 0 (
    echo WARNING: Failed to load demo data, but setup can continue
)

echo.
echo ========================================
echo   Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo   1. Run "scripts\start_services.bat" to start all services
echo   2. Open http://localhost:8000/swagger/ to view API documentation
echo   3. Open http://localhost:5050 to access PgAdmin (admin@example.com / admin123)
echo   4. Open http://localhost:8000/admin/ to access Django admin
echo.
echo Press any key to exit...
pause >nul