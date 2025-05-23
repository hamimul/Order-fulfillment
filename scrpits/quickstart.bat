@echo off
echo =======================================
echo   Order Fulfillment Quick Start
echo =======================================
echo.
echo This script will set up and start the entire system.
echo Make sure Docker Desktop is running before continuing.
echo.
pause

REM Run setup
echo Running setup...
call scripts\setup.bat
if %errorlevel% neq 0 (
    echo Setup failed!
    pause
    exit /b 1
)

echo.
echo Setup completed! Starting services...
timeout /t 3 /nobreak >nul

REM Start services
call scripts\start_services.bat

echo.
echo =======================================
echo   Quick Start Complete!
echo =======================================
echo.
echo The system is now ready to use:
echo   • API: http://localhost:8000/swagger/
echo   • Admin: http://localhost:8000/admin/
echo   • Health: http://localhost:8000/health/
echo.
echo You can now test the API or run load tests:
echo   • Run scripts\run_tests.bat for testing options
echo   • Check logs\ directory for application logs
echo.
echo Press any key to exit...
pause >nul