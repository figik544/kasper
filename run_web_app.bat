@echo off
echo Запуск веб-приложения Галактической Империи...
echo.

python web_app.py

if %errorlevel% neq 0 (
    echo Веб-приложение не запустилось. Проверьте ошибки выше.
    pause
    exit /b %errorlevel%
)

pause