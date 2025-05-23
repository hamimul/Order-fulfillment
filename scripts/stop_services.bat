@echo off
echo ====================================
echo   Stopping Order Fulfillment System
echo ====================================
echo.

echo Stopping Docker services...
docker-compose down

echo Stopping Django server...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo Killing process %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Celery processes...
taskkill /F /IM celery.exe >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Celery*" >nul 2>&1

echo.
echo ====================================
echo   All services stopped successfully!
echo ====================================
echo.
echo Press any key to exit...
pause >nul