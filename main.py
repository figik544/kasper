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

# Функции проверки прав пользователя
def is_supreme_ruler(user_id):
    """Проверка, является ли пользователь верховным правителем"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return str(user_id) == config['government_structure']['supreme_ruler']
    except:
        return False

def is_chancellor(user_id):
    """Проверка, является ли пользователь канцлером"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return str(user_id) in config['government_structure']['chancellery']
    except:
        return False

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
async def on_message(message):
    if message.author.bot:
        return
    
    # Проверка на слово "сектор"
    if message.content.lower().strip() == 'сектор':
        # Определяем права пользователя
        is_supreme = is_supreme_ruler(message.author.id)
        is_chancellor = is_chancellor(message.author.id)
        is_admin = message.author.guild_permissions.administrator

        # Проверяем, есть ли пользователь в базе
        user_data = await db.get_user_data(message.author.id)
        if not user_data:
            await db.create_user(message.author.id, message.guild.id)
        
        # Формируем доступные команды в зависимости от прав
        if is_supreme:
            # Команды для верховного правителя
            commands_list = """
**Доступные команды для Верховного Правителя:**
- !help - Помощь по командам
- !profile - Ваш профиль
- !balance - Баланс кредитов
- !daily - Ежедневная награда
- !transfer - Перевод кредитов
- !shop - Имперский рынок
- !buy - Покупка предметов
- !inventory - Инвентарь
- !use - Использование предметов
- !trade - Обмен предметами
- !givecredits - Выдача кредитов
- !convert_currency - Конвертация валюты
- !treasury_status - Статус казначейства
- !rankup - Повышение ранга
- !leaderboard - Таблица лидеров
- !setrank - Установка ранга
- !xp_boost - Ускорение опыта
- !level_stats - Статистика уровней
- !ban - Бан пользователя
- !kick - Кик пользователя
- !mute - Мут пользователя
- !warn - Предупреждение
- !unwarn - Снятие предупреждения
- !warnings - Просмотр предупреждений
- !clear - Очистка сообщений
- !set_supreme_ruler - Назначить верховного правителя
- !add_chancellor - Добавить канцлера
- !remove_chancellor - Удалить канцлера
- !set_minister - Назначить министра
- !remove_minister - Удалить министра
- !gov_info - Информация о правительстве
- !change_government - Изменить структуру правительства
- !activate_quarantine - Активировать режим карантина
- !deactivate_quarantine - Деактивировать режим карантина
- !quarantine_status - Проверить статус карантина
- !security_logs - Журнал безопасности
- !declare_emergency - Объявить чрезвычайное положение
- !revoke_emergency - Отменить чрезвычайное положение
- !imperial_decree - Издать императорский указ
            """
        elif is_chancellor or is_admin:
            # Команды для канцлеров и администраторов
            commands_list = """
**Доступные команды для администрации:**
- !help - Помощь по командам
- !profile - Ваш профиль
- !balance - Баланс кредитов
- !daily - Ежедневная награда
- !transfer - Перевод кредитов
- !shop - Имперский рынок
- !buy - Покупка предметов
- !inventory - Инвентарь
- !use - Использование предметов
- !trade - Обмен предметами
- !rankup - Повышение ранга
- !leaderboard - Таблица лидеров
- !setrank - Установка ранга
- !level_stats - Статистика уровней
- !ban - Бан пользователя
- !kick - Кик пользователя
- !mute - Мут пользователя
- !warn - Предупреждение
- !unwarn - Снятие предупреждения
- !warnings - Просмотр предупреждений
- !clear - Очистка сообщений
- !add_chancellor - Добавить канцлера
- !remove_chancellor - Удалить канцлера
- !set_minister - Назначить министра
- !remove_minister - Удалить министра
- !gov_info - Информация о правительстве
- !change_government - Изменить структуру правительства
- !activate_quarantine - Активировать режим карантина
- !deactivate_quarantine - Деактивировать режим карантина
- !quarantine_status - Проверить статус карантина
            """
        else:
            # Команды для обычных пользователей
            commands_list = """
**Доступные команды для пользователей:**
- !help - Помощь по командам
- !profile - Ваш профиль
- !balance - Баланс кредитов
- !daily - Ежедневная награда
- !transfer - Перевод кредитов
- !shop - Имперский рынок
- !buy - Покупка предметов
- !inventory - Инвентарь
- !use - Использование предметов
- !trade - Обмен предметами
- !rankup - Повышение ранга
- !leaderboard - Таблица лидеров
- !level_stats - Статистика уровней
            """

        embed = discord.Embed(
            title="🔒 Сектор - Имперский Центральный Командный Пункт",
            description=f"Доступ ограничен. {'**Верховный Правитель Федерации Галактической Империи**' if is_supreme else ('**Канцлер**' if is_chancellor else '**Пользователь**')} может получить доступ к соответствующим командам." + commands_list,
            color=0xFF0000 if is_supreme else (0x0000FF if is_chancellor or is_admin else 0x00FF00)
        )
        await message.channel.send(embed=embed)
        
    # Обработка остальных сообщений
    await bot.process_commands(message)

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

def start_health_server():
    """Запуск веб-сервера для health check на Render"""
    port = int(os.environ.get('PORT', 10000))
    
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Подавляем логи сервера
            pass
    
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"Health check сервер запущен на порту {port}")
        return server
    except Exception as e:
        print(f"Ошибка при запуске health check сервера: {e}")
        return None


# Функция для запуска бота
def run_bot():
    print("Запуск бота...")
    
    # Запуск веб-сервера для health check
    start_health_server()
    
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