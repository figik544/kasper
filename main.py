import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
import asyncio
import aiosqlite
import logging
from enum import Enum
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import threading

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "bot_token": "",
    "admin_user_ids": [],
    "default_prefix": "!",
    "max_warns_before_ban": 5,
    "spam_threshold": {
        "message_count": 5,
        "time_window_seconds": 10,
    },
    "xp_rewards": {
        "message_range_min": 15,
        "message_range_max": 25,
        "command_bonus": 10,
    },
    "daily_rewards": {
        "min_credits": 50,
        "max_credits": 150,
    },
    "star_wars_themed": True,
    "autorank_enabled": True,
    "advertising_enabled": False,
    "ad_message": "Присоединяйся к Федерации Галактической Империи!",
    "ad_frequency_hours": 6,
    "government_structure": {
        "supreme_ruler": "0",
        "chancellery": [],
        "ministries": {},
        "elections_enabled": False,
        "election_cycle_days": 30,
    },
}


def _deep_merge(base, override):
    """Глубоко объединяет словари, сохраняя значения override при наличии."""
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path='config.json'):
    """Загружает конфиг, создавая дефолтный файл при отсутствии/битой структуре."""
    config_path = path
    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        return json.loads(json.dumps(DEFAULT_CONFIG))

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, OSError):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        return json.loads(json.dumps(DEFAULT_CONFIG))

    if not isinstance(loaded, dict):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        return json.loads(json.dumps(DEFAULT_CONFIG))

    merged = _deep_merge(DEFAULT_CONFIG, loaded)
    if merged != loaded:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


def resolve_bot_token(environment_token, config_token):
    return (environment_token or '').strip() or (config_token or '').strip()


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        return


def start_health_server():
    port = os.getenv('PORT')
    if not port:
        return None

    server = HTTPServer(('0.0.0.0', int(port)), HealthCheckHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


config = load_config()

# Получение токена из переменной окружения или файла конфигурации
environment_token = os.getenv('DISCORD_BOT_TOKEN')
BOT_TOKEN = resolve_bot_token(environment_token, config.get('bot_token', ''))
token_source = 'DISCORD_BOT_TOKEN' if environment_token and environment_token.strip() else 'config.json'

if not BOT_TOKEN:
    print("Ошибка: Токен бота не найден! Установите переменную окружения DISCORD_BOT_TOKEN или укажите токен в config.json.")
    exit(1)
else:
    print(f"Токен загружен из {token_source} ({len(BOT_TOKEN)} символов). Значение скрыто.")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Инициализация бота с поддержкой слэш-команд
bot = commands.Bot(command_prefix=config['default_prefix'], intents=intents, owner_id=int(config['government_structure']['supreme_ruler']), help_command=None)
bot.remove_command('help')

# Глобальные переменные
advertising_task = None
current_government = config['government_structure']
bot.config = config  # Добавляем конфигурацию как атрибут бота

# Импорт модулей
from modules.database import Database
from modules.moderation import ModerationCog
from modules.economy import EconomyCog
from modules.levels import LevelsCog
from modules.rpg import RPGCog
from modules.star_wars import StarWarsCog
from modules.help import HelpCog
from modules.government import GovernmentCog

# Глобальная переменная для базы данных
db = Database()

# Загрузка модулей
async def load_cogs():
    await bot.add_cog(ModerationCog(bot, db))
    await bot.add_cog(EconomyCog(bot, db))
    await bot.add_cog(LevelsCog(bot, db))
    await bot.add_cog(RPGCog(bot, db))
    await bot.add_cog(StarWarsCog(bot, db))
    await bot.add_cog(HelpCog(bot))
    await bot.add_cog(GovernmentCog(bot))

@bot.event
async def on_ready():
    print(f'{bot.user} подключен к Discord!')
    print(f'Бот подключен к {len(bot.guilds)} серверам')
    print(f'Служит {len(bot.users)} пользователям')
    
    # Синхронизация слэш-команд
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"Ошибка при синхронизации слэш-команд: {e}")

    # Загрузка модулей
    await load_cogs()
    
    # Запуск задач
    from modules.moderation import start_advertising_task
    start_advertising_task(bot)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Команда не найдена",
            description="Эта команда не существует в базе данных Галактической Империи.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Недостаточно прав",
            description="У вас нет полномочий для выполнения этой команды. Только Имперские офицеры с соответствующим допуском могут продолжить.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

# Удалены дублирующиеся команды правительства
# Они определены в модуле government.py как гибридные команды:
# set_supreme_ruler, add_chancellor, remove_chancellor, set_minister, remove_minister, gov_info, change_government

# Функция для запуска бота
def run_bot():
    print("Запуск бота...")
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("Ошибка: Неверный токен бота. Пожалуйста, проверьте значение токена в config.json или переменной окружения DISCORD_BOT_TOKEN.")
        exit(1)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        exit(1)

if __name__ == "__main__":
    # Запуск бота с токеном
    try:
        print("Попытка запуска бота...")
        run_bot()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
