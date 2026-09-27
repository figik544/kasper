@echo off
echo Starting Galactic Empire Discord Bot...
echo.

python bot.py

if %errorlevel% neq 0 (
    echo The bot failed to start. Please check the error messages above.
    echo Make sure you have configured your bot token in config.json.
    pause
    exit /b %errorlevel%
)

pause