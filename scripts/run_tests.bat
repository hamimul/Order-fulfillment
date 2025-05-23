@echo off
echo ====================================
echo   Order Fulfillment System Testing
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Available test options:
echo   1. Validate settings configuration
echo   2. Run Django unit tests
echo   3. Run load test (50 orders, 5 threads)
echo   4. Run load test (100 orders, 10 threads)
echo   5. Run custom load test
echo   6. Reset database and reload demo data
echo   7. Check system health
echo   8. Run all tests (comprehensive)
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto validate_settings
if "%choice%"=="2" goto django_tests
if "%choice%"=="3" goto load_test_small
if "%choice%"=="4" goto load_test_medium
if "%choice%"=="5" goto load_test_custom
if "%choice%"=="6" goto reset_data
if "%choice%"=="7" goto health_check
if "%choice%"=="8" goto run_all_tests

echo Invalid choice. Exiting...
pause
exit /b 1

:validate_settings
echo.
echo Validating settings configuration...
python scripts\validate_settings.py
goto end

:django_tests
echo.
echo Running Django unit tests...
python manage.py test
goto end

:load_test_small
echo.
echo Running load test: 50 orders with 5 threads...
python manage.py load_test --orders 50 --threads 5
goto end

:load_test_medium
echo.
echo Running load test: 100 orders with 10 threads...
python manage.py load_test --orders 100 --threads 10
goto end

:load_test_custom
echo.
set /p orders="Enter number of orders to create: "
set /p threads="Enter number of threads to use: "
set /p delay="Enter delay between orders in seconds (e.g., 0.1): "
echo.
echo Running custom load test: %orders% orders with %threads% threads...
python manage.py load_test --orders %orders% --threads %threads% --delay %delay%
goto end

:reset_data
echo.
echo WARNING: This will delete all existing data!
set /p confirm="Are you sure? (y/N): "
if /i not "%confirm%"=="y" goto end

echo Applying fresh migrations...
python manage.py migrate

echo Loading fresh demo data...
python manage.py setup_demo_data --clear --products 50
goto end

:health_check
echo.
echo Checking system health...
echo.
echo Django server status:
curl -s http://localhost:8000/health/ | python -m json.tool
echo.
echo Database connectivity:
python manage.py dbshell --command="SELECT version();" 2>nul && echo Database: OK || echo Database: ERROR
echo.
echo Celery workers:
celery -A order_fulfillment inspect active
goto end

:run_all_tests
echo.
echo Running comprehensive test suite...
echo.

echo 1/5: Validating settings...
python scripts\validate_settings.py
if %errorlevel% neq 0 (
    echo Settings validation failed!
    goto end
)

echo.
echo 2/5: Running Django unit tests...
python manage.py test
if %errorlevel% neq 0 (
    echo Unit tests failed!
    goto end
)

echo.
echo 3/5: Running system health check...
python manage.py check_system
if %errorlevel% neq 0 (
    echo System health check failed!
    goto end
)

echo.
echo 4/5: Running small load test...
python manage.py load_test --orders 25 --threads 3
if %errorlevel% neq 0 (
    echo Load test failed!
    goto end
)

echo.
echo 5/5: Checking API endpoints...
timeout /t 2 /nobreak >nul
curl -f http://localhost:8000/health/ >nul 2>&1 && echo API: OK || echo API: ERROR

echo.
echo ====================================
echo   All tests completed successfully!
echo ====================================
goto end

:end
echo.
echo Test completed!
echo Press any key to exit...
pause >nul