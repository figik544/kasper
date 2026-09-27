import sqlite3
import os
from datetime import datetime
import aiosqlite

DATABASE_PATH = 'galactic_empire_bot.db'

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Создание таблиц для профилей пользователей
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            guild_id INTEGER,
                            level INTEGER DEFAULT 1,
                            xp INTEGER DEFAULT 0,
                            credits INTEGER DEFAULT 0,
                            rank TEXT DEFAULT 'Recruit',
                            join_date TEXT,
                            last_daily_claim TEXT,
                            warnings INTEGER DEFAULT 0,
                            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
                        )''')
        
        # Создание таблицы для настроек сервера
        await db.execute('''CREATE TABLE IF NOT EXISTS guilds (
                            guild_id INTEGER PRIMARY KEY,
                            admin_role_id INTEGER,
                            mod_role_id INTEGER,
                            mute_role_id INTEGER,
                            log_channel_id INTEGER,
                            autorank_enabled BOOLEAN DEFAULT 1,
                            economy_enabled BOOLEAN DEFAULT 1
                        )''')
        
        # Создание таблицы для предупреждений
        await db.execute('''CREATE TABLE IF NOT EXISTS warnings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            guild_id INTEGER,
                            moderator_id INTEGER,
                            reason TEXT,
                            timestamp TEXT
                        )''')
        
        # Создание таблицы для предметов магазина
        await db.execute('''CREATE TABLE IF NOT EXISTS shop_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT UNIQUE,
                            price INTEGER,
                            description TEXT
                        )''')
        
        # Создание таблицы для инвентаря пользователя
        await db.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            item_id INTEGER,
                            quantity INTEGER DEFAULT 1,
                            FOREIGN KEY (item_id) REFERENCES shop_items(id)
                        )''')
        
        # Создание таблицы для пользовательских настроек
        await db.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                            user_id INTEGER PRIMARY KEY,
                            guild_id INTEGER,
                            notifications_enabled BOOLEAN DEFAULT 1,
                            private_messages_enabled BOOLEAN DEFAULT 1
                        )''')
        
        # Вставка стандартных предметов магазина
        default_items = [
            ("Имперский шлем", 200, "Стандартный шлем штурмовика Империи"),
            ("Меч джедая", 500, "Оружие выбора Джедая"),
            ("Маска Дарта Вейдера", 300, "Из intimidating маска Ситхов"),
            ("Модель истребителя ТА", 400, "Коллекционная модель истребителя ТА"),
            ("Значок Альянса повстанцев", 150, "Покажите свою поддержку Повстанцам"),
            ("Монета Имперских кредитов", 100, "Декоративная монета Имперской валюты"),
            ("Голокрон Ситхов", 1000, "Хранилище знаний Ситхов"),
            ("Голокрон Джедаев", 1000, "Хранилище знаний Джедаев"),
            ("Значок Звёздного флота", 250, "Значок с изображением Звёздного флота"),
            ("Фигурка Эвоков", 120, "Коллекционная фигурка Эвоков")
        ]
        
        for item in default_items:
            await db.execute("INSERT OR IGNORE INTO shop_items (name, price, description) VALUES (?, ?, ?)", item)
        
        await db.commit()

async def get_user_data(user_id, guild_id):
    """Получение данных пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            result = await cursor.fetchone()
            if result:
                columns = ['user_id', 'guild_id', 'level', 'xp', 'credits', 'rank', 'join_date', 'last_daily_claim', 'warnings']
                return dict(zip(columns, result))
            return None

async def create_user(user_id, guild_id):
    """Создание нового пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, guild_id, join_date, warnings) VALUES (?, ?, ?, ?)",
                         (user_id, guild_id, datetime.now().isoformat(), 0))
        await db.commit()

async def update_user_xp(user_id, guild_id, xp_amount):
    """Обновление XP пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем текущие XP и уровень
        async with db.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            result = await cursor.fetchone()
        
        if result:
            current_xp, current_level = result
            new_xp = current_xp + xp_amount
            new_level = (new_xp // 100) + 1
            
            await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                           (new_xp, new_level, user_id, guild_id))
        else:
            new_xp = xp_amount
            new_level = (new_xp // 100) + 1
            await db.execute("INSERT INTO users (user_id, guild_id, xp, level, join_date, warnings) VALUES (?, ?, ?, ?, ?, ?)",
                           (user_id, guild_id, new_xp, new_level, datetime.now().isoformat(), 0))
        
        await db.commit()
        return new_level

async def get_top_users(guild_id, limit=10):
    """Получение топ пользователей по уровню"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id, level, xp FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?", 
                             (guild_id, limit)) as cursor:
            return await cursor.fetchall()

async def add_warning(user_id, guild_id, moderator_id, reason):
    """Добавление предупреждения пользователю"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Обновляем счетчик предупреждений пользователя
        await db.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ? AND guild_id = ?", 
                        (user_id, guild_id))
        
        # Добавляем запись о предупреждении
        await db.execute("INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (user_id, guild_id, moderator_id, reason, datetime.now().isoformat()))
        
        # Получаем количество предупреждений
        async with db.execute("SELECT warnings FROM users WHERE user_id = ? AND guild_id = ?", 
                             (user_id, guild_id)) as cursor:
            result = await cursor.fetchone()
        
        await db.commit()
        return result[0] if result else 0

async def reset_warnings(user_id, guild_id):
    """Сброс предупреждений пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET warnings = 0 WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        await db.commit()

async def add_credits(user_id, guild_id, amount):
    """Добавление кредитов пользователю"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            result = await cursor.fetchone()
        
        if result:
            current_credits = result[0]
            new_credits = current_credits + amount
            await db.execute("UPDATE users SET credits = ? WHERE user_id = ? AND guild_id = ?", 
                           (new_credits, user_id, guild_id))
        else:
            new_credits = amount
            await db.execute("INSERT INTO users (user_id, guild_id, credits, join_date, warnings) VALUES (?, ?, ?, ?, ?)",
                           (user_id, guild_id, new_credits, datetime.now().isoformat(), 0))
        
        await db.commit()
        return new_credits

async def get_user_credits(user_id, guild_id):
    """Получение количества кредитов пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_shop_items():
    """Получение всех предметов магазина"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id, name, price, description FROM shop_items") as cursor:
            return await cursor.fetchall()

async def buy_item(user_id, item_id):
    """Покупка предмета пользователем"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем цену предмета
        async with db.execute("SELECT price FROM shop_items WHERE id = ?", (item_id,)) as cursor:
            result = await cursor.fetchone()
        
        if not result:
            return False, "Предмет не найден"
        
        price = result[0]
        
        # Проверяем, достаточно ли кредитов у пользователя
        async with db.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        
        if not result or result[0] < price:
            return False, "Недостаточно кредитов"
        
        # Списываем кредиты
        await db.execute("UPDATE users SET credits = credits - ? WHERE user_id = ?", (price, user_id))
        
        # Добавляем предмет в инвентарь
        await db.execute("INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (?, ?, 1)", (user_id, item_id))
        
        await db.commit()
        return True, f"Покупка успешно завершена! Списано {price} кредитов."

async def get_user_inventory(user_id):
    """Получение инвентаря пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("""
            SELECT si.name, ui.quantity 
            FROM user_inventory ui
            JOIN shop_items si ON ui.item_id = si.id
            WHERE ui.user_id = ?
        """, (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_guild_config(guild_id):
    """Получение конфигурации сервера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                columns = ['guild_id', 'admin_role_id', 'mod_role_id', 'mute_role_id', 'log_channel_id', 'autorank_enabled', 'economy_enabled']
                return dict(zip(columns, result))
            return None

async def update_guild_config(guild_id, **kwargs):
    """Обновление конфигурации сервера"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Формируем SQL запрос динамически
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [guild_id]
        
        await db.execute(f"INSERT OR REPLACE INTO guilds (guild_id, {', '.join(kwargs.keys())}) VALUES (?{', ?' * len(kwargs)})", values)
        await db.commit()

async def setup(bot):
    """Функция setup для загрузки модуля"""
    pass