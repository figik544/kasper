@echo off
echo Запуск Галактического Имперского Бота...
python main.py
pause

if %errorlevel% neq 0 (
    echo The bot failed to start. Please check the error messages above.
    echo Configure DISCORD_BOT_TOKEN or the bot_token value in config.json.
    pause
    exit /b %errorlevel%
)

pause