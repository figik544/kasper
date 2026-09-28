@echo off
echo Installing Galactic Empire Discord Bot dependencies...

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install dependencies. Please make sure you have Python and pip installed.
    pause
    exit /b %errorlevel%
)

echo Dependencies installed successfully!
echo.
echo Please configure your bot token in config.json before running the bot.
echo.
echo To run the bot, execute: python main.py
echo.
pause