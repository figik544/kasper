import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
import asyncio
import aiosqlite
import logging
from enum import Enum

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
BOT_TOKEN = resolve_bot_token(os.getenv('DISCORD_BOT_TOKEN'), config.get('bot_token', ''))

if not BOT_TOKEN:
    print("Ошибка: Токен бота не найден! Установите переменную окружения DISCORD_BOT_TOKEN или укажите токен в config.json.")
    exit(1)

# Настройка интентов
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

# Инициализация бота
bot = commands.Bot(command_prefix=config['default_prefix'], intents=intents, owner_id=int(config['government_structure']['supreme_ruler']))
bot.remove_command('help')

# Глобальные переменные
advertising_task = None
current_government = config['government_structure']

# Загрузка расширений (модулей)
async def load_extensions():
    extensions = [
        'modules.moderation',
        'modules.economy',
        'modules.levels',
        'modules.rpg',
        'modules.star_wars',
        'modules.database',
        'modules.help'
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f"Загружено расширение: {extension}")
        except Exception as e:
            print(f"Ошибка при загрузке расширения {extension}: {e}")

@bot.event
async def on_ready():
    global advertising_task
    print(f'{bot.user} подключен к Discord!')
    print(f'Бот находится в {len(bot.guilds)} серверах и обслуживает {len(bot.users)} пользователей')
    
    # Инициализация базы данных
    from modules.database import init_db
    await init_db()
    
    # Установка активности
    await bot.change_presence(activity=discord.Game(name="Galactic Empire Command"))
    
    # Запуск рекламной задачи если включена
    if config.get('advertising_enabled', False):
        start_advertising_task()

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

# Команды управления правительством
@commands.is_owner()
@bot.command(name='set_supreme_ruler')
async def set_supreme_ruler(ctx, user: discord.User):
    """Установить верховного правителя (только для владельца бота)"""
    global current_government
    current_government['supreme_ruler'] = str(user.id)
    
    # Обновляем конфиг
    config['government_structure']['supreme_ruler'] = str(user.id)
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    embed = discord.Embed(
        title="Верховный правитель изменен",
        description=f"Новый Верховный правитель: {user.mention}",
        color=0x8B0000
    )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='add_chancellor')
async def add_chancellor(ctx, user: discord.User):
    """Добавить канцлера в правительство"""
    global current_government
    if str(user.id) not in current_government['chancellery']:
        current_government['chancellery'].append(str(user.id))
        
        # Обновляем конфиг
        config['government_structure']['chancellery'] = current_government['chancellery']
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="Канцлер добавлен",
            description=f"{user.mention} назначен(а) канцлером",
            color=0x006400
        )
    else:
        embed = discord.Embed(
            title="Ошибка",
            description=f"{user.mention} уже является канцлером",
            color=0xFF0000
        )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='remove_chancellor')
async def remove_chancellor(ctx, user: discord.User):
    """Удалить канцлера из правительства"""
    global current_government
    if str(user.id) in current_government['chancellery']:
        current_government['chancellery'].remove(str(user.id))
        
        # Обновляем конфиг
        config['government_structure']['chancellery'] = current_government['chancellery']
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="Канцлер удален",
            description=f"{user.mention} удален(а) из должности канцлера",
            color=0x006400
        )
    else:
        embed = discord.Embed(
            title="Ошибка",
            description=f"{user.mention} не является канцлером",
            color=0xFF0000
        )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='set_minister')
async def set_minister(ctx, ministry: str, user: discord.User):
    """Назначить министра в ведомство"""
    global current_government
    current_government['ministries'][ministry] = str(user.id)
    
    # Обновляем конфиг
    config['government_structure']['ministries'][ministry] = str(user.id)
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    embed = discord.Embed(
        title="Министр назначен",
        description=f"{user.mention} назначен(а) министром {ministry}",
        color=0x006400
    )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='remove_minister')
async def remove_minister(ctx, ministry: str):
    """Удалить министра из ведомства"""
    global current_government
    if ministry in current_government['ministries']:
        del current_government['ministries'][ministry]
        
        # Обновляем конфиг
        if ministry in config['government_structure']['ministries']:
            del config['government_structure']['ministries'][ministry]
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="Министр удален",
            description=f"Должность министра {ministry} освобождена",
            color=0x006400
        )
    else:
        embed = discord.Embed(
            title="Ошибка",
            description=f"Ведомство {ministry} не существует или не имеет министра",
            color=0xFF0000
        )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='gov_info')
async def government_info(ctx):
    """Показать структуру правительства"""
    global current_government
    embed = discord.Embed(
        title="Структура Правительства Галактической Империи",
        color=0x8B0000
    )
    
    # Получаем верховного правителя
    supreme_ruler = bot.get_user(int(current_government['supreme_ruler']))
    embed.add_field(
        name="Верховный правитель",
        value=supreme_ruler.mention if supreme_ruler else f"ID: {current_government['supreme_ruler']}",
        inline=False
    )
    
    # Канцелярия
    if current_government['chancellery']:
        chancellor_mentions = []
        for user_id in current_government['chancellery']:
            user = bot.get_user(int(user_id))
            chancellor_mentions.append(user.mention if user else f"ID: {user_id}")
        embed.add_field(
            name="Канцелярия",
            value=", ".join(chancellor_mentions),
            inline=False
        )
    else:
        embed.add_field(
            name="Канцелярия",
            value="Пусто",
            inline=False
        )
    
    # Министерства
    if current_government['ministries']:
        for ministry, user_id in current_government['ministries'].items():
            user = bot.get_user(int(user_id))
            embed.add_field(
                name=ministry,
                value=user.mention if user else f"ID: {user_id}",
                inline=True
            )
    else:
        embed.add_field(
            name="Министерства",
            value="Пусто",
            inline=False
        )
    
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='enable_ads')
async def enable_ads(ctx, frequency_hours: int = 6):
    """Включить рекламу с заданной частотой"""
    global advertising_task
    config['advertising_enabled'] = True
    config['ad_frequency_hours'] = frequency_hours
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    if advertising_task:
        advertising_task.cancel()
    
    start_advertising_task()
    
    embed = discord.Embed(
        title="Реклама включена",
        description=f"Реклама будет показываться каждые {frequency_hours} часов",
        color=0x006400
    )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='disable_ads')
async def disable_ads(ctx):
    """Выключить рекламу"""
    global advertising_task
    config['advertising_enabled'] = False
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    if advertising_task:
        advertising_task.cancel()
        advertising_task = None
    
    embed = discord.Embed(
        title="Реклама выключена",
        description="Реклама больше не будет показываться",
        color=0x006400
    )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='set_ad_message')
async def set_ad_message(ctx, *, message):
    """Установить рекламное сообщение"""
    config['ad_message'] = message
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    embed = discord.Embed(
        title="Рекламное сообщение установлено",
        description=f"Новое рекламное сообщение: {message}",
        color=0x006400
    )
    await ctx.send(embed=embed)

@commands.is_owner()
@bot.command(name='ad_info')
async def ad_info(ctx):
    """Показать информацию о рекламе"""
    ad_enabled = config.get('advertising_enabled', False)
    ad_message = config.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!')
    ad_frequency = config.get('ad_frequency_hours', 6)
    
    embed = discord.Embed(
        title="Информация о рекламе",
        color=0x8B0000
    )
    embed.add_field(name="Статус", value="Включена" if ad_enabled else "Выключена", inline=False)
    embed.add_field(name="Сообщение", value=ad_message, inline=False)
    embed.add_field(name="Частота", value=f"Каждые {ad_frequency} часов", inline=False)
    
    await ctx.send(embed=embed)

def start_advertising_task():
    """Запуск задачи рекламы"""
    global advertising_task
    if advertising_task:
        advertising_task.cancel()
    
    @tasks.loop(hours=config.get('ad_frequency_hours', 6))
    async def advertise():
        ad_message = config.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!')
        for guild in bot.guilds:
            try:
                # Пытаемся найти главный канал
                general_channel = None
                for channel in guild.text_channels:
                    if 'general' in channel.name.lower() or 'основной' in channel.name.lower() or 'главный' in channel.name.lower():
                        general_channel = channel
                        break
                
                if not general_channel:
                    # Если не найден, берем первый текстовый канал
                    if guild.text_channels:
                        general_channel = guild.text_channels[0]
                
                if general_channel:
                    embed = discord.Embed(
                        title="Реклама Федерации",
                        description=ad_message,
                        color=0xFFD700
                    )
                    await general_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Ошибка при отправке рекламы в {guild.name}: {e}")
    
    advertising_task = advertise
    advertising_task.start()

# Добавляем новые команды для управления правительством и рекламой
@commands.has_permissions(administrator=True)
@bot.command(name='change_government')
async def change_government(ctx, action: str, target: str = None, user: discord.User = None):
    """
    Команда для изменения структуры правительства
    Использование: !change_government [add_chancellor|remove_chancellor|set_minister|remove_minister] [target] [user]
    """
    if str(ctx.author.id) != config['government_structure']['supreme_ruler'] and str(ctx.author.id) not in config['government_structure']['chancellery']:
        embed = discord.Embed(
            title="Недостаточно прав",
            description="Только Верховный правитель или канцлеры могут изменять структуру правительства",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return
    
    if action == 'add_chancellor' and user:
        if str(user.id) not in current_government['chancellery']:
            current_government['chancellery'].append(str(user.id))
            config['government_structure']['chancellery'] = current_government['chancellery']
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="Канцлер добавлен",
                description=f"{user.mention} назначен(а) канцлером",
                color=0x006400
            )
        else:
            embed = discord.Embed(
                title="Ошибка",
                description=f"{user.mention} уже является канцлером",
                color=0xFF0000
            )
    
    elif action == 'remove_chancellor' and user:
        if str(user.id) in current_government['chancellery']:
            current_government['chancellery'].remove(str(user.id))
            config['government_structure']['chancellery'] = current_government['chancellery']
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="Канцлер удален",
                description=f"{user.mention} удален(а) из должности канцлера",
                color=0x006400
            )
        else:
            embed = discord.Embed(
                title="Ошибка",
                description=f"{user.mention} не является канцлером",
                color=0xFF0000
            )
    
    elif action == 'set_minister' and target and user:
        current_government['ministries'][target] = str(user.id)
        config['government_structure']['ministries'][target] = str(user.id)
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="Министр назначен",
            description=f"{user.mention} назначен(а) министром {target}",
            color=0x006400
        )
    
    elif action == 'remove_minister' and target:
        if target in current_government['ministries']:
            del current_government['ministries'][target]
            if target in config['government_structure']['ministries']:
                del config['government_structure']['ministries'][target]
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="Министр удален",
                description=f"Должность министра {target} освобождена",
                color=0x006400
            )
        else:
            embed = discord.Embed(
                title="Ошибка",
                description=f"Ведомство {target} не существует или не имеет министра",
                color=0xFF0000
            )
    
    else:
        embed = discord.Embed(
            title="Неверные параметры",
            description="Используйте: !change_government [add_chancellor|remove_chancellor|set_minister|remove_minister] [target] [user]",
            color=0xFF0000
        )
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    # Запуск бота с токеном
    try:
        print("Попытка запуска бота...")
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("Ошибка входа в Discord: токен отклонён. Укажите Bot Token из раздела Bot в Developer Portal, обновите DISCORD_BOT_TOKEN в Render и перезапустите сервис.")
        exit(1)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        exit(1)
