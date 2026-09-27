@echo off
echo Запуск системы Галактической Империи...
echo.

echo Запуск админ-панели...
start "Admin Panel" cmd /k "cd /d "%~dp0" && python admin_panel.py"

timeout /t 5 /nobreak >nul

echo Запуск Discord бота...
python main.py

if %errorlevel% neq 0 (
    echo Произошла ошибка при запуске бота. Проверьте ошибки выше.
    pause
    exit /b %errorlevel%
)

pause