import aiosqlite
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.db_path = 'database.db'
        # Инициализируем базу данных при создании экземпляра класса
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Если цикл уже запущен, создаем задачу
            loop.create_task(self.init_db())
        except RuntimeError:
            # Если цикл не запущен, можно безопасно использовать run
            asyncio.run(self.init_db())

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Создание таблицы пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    credits INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    rank TEXT DEFAULT 'Новичок',
                    last_daily TEXT,
                    last_quest TEXT
                )
            ''')
            
            # Создание таблицы предупреждений
            await db.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    moderator_id INTEGER,
                    date TEXT,
                    reason TEXT
                )
            ''')
            
            # Создание таблицы магазина
            await db.execute('''
                CREATE TABLE IF NOT EXISTS shop (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    price INTEGER,
                    description TEXT
                )
            ''')
            
            # Создание таблицы инвентаря
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id INTEGER,
                    FOREIGN KEY (item_id) REFERENCES shop (id)
                )
            ''')
            
            # Создание таблицы персонажей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    class TEXT,
                    strength INTEGER,
                    agility INTEGER,
                    intelligence INTEGER
                )
            ''')
            
            # Создание таблицы политических партий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS political_parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    name TEXT UNIQUE,
                    description TEXT,
                    creation_date TEXT,
                    leader_id INTEGER
                )
            ''')
            
            # Создание таблицы участников партий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS party_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    party_id INTEGER,
                    joined_date TEXT,
                    FOREIGN KEY (party_id) REFERENCES political_parties (id)
                )
            ''')
            
            # Создание таблицы выборов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS elections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    election_type TEXT,
                    scheduled_date TEXT,
                    completed BOOLEAN DEFAULT 0
                )
            ''')
            
            # Создание таблицы форм правления
            await db.execute('''
                CREATE TABLE IF NOT EXISTS government_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER UNIQUE,
                    gov_type TEXT
                )
            ''')
            
            await db.commit()

    async def create_user(self, user_id, guild_id):
        """Создание нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO users (id, guild_id, credits, level, xp) VALUES (?, ?, 0, 1, 0)', 
                           (user_id, guild_id))
            await db.commit()

    async def get_user_data(self, user_id):
        """Получение данных пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return await cursor.fetchone()

    async def get_balance(self, user_id):
        """Получение баланса пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT credits FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def add_credits(self, user_id, amount):
        """Добавление/удаление кредитов у пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET credits = credits + ? WHERE id = ?', (amount, user_id))
            await db.commit()

    async def get_user_level(self, user_id):
        """Получение уровня пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT level FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else 1

    async def add_xp(self, user_id, xp_amount):
        """Добавление опыта пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (xp_amount, user_id))
            await db.commit()

    async def level_up(self, user_id):
        """Повышение уровня пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем текущий уровень и опыт
            cursor = await db.execute('SELECT level, xp FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            
            if result:
                current_level, current_xp = result
                xp_needed = int((current_level + 1) ** 2 * 10)
                
                # Обновляем уровень и сбрасываем XP сверх нужного
                new_level = current_level + 1
                remaining_xp = current_xp - xp_needed
                
                await db.execute('UPDATE users SET level = ?, xp = ? WHERE id = ?', 
                               (new_level, remaining_xp, user_id))
                await db.commit()

    async def get_top_users(self):
        """Получение топ пользователей по уровню"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id, guild_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 10')
            return await cursor.fetchall()

    async def add_warning(self, user_id, guild_id, moderator_id, reason):
        """Добавление предупреждения пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT INTO warnings (user_id, guild_id, moderator_id, date, reason) VALUES (?, ?, ?, ?, ?)',
                           (user_id, guild_id, moderator_id, datetime.now().isoformat(), reason))
            await db.commit()

    async def get_warnings(self, user_id, guild_id):
        """Получение предупреждений пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
            return await cursor.fetchall()

    async def clear_warnings(self, user_id, guild_id):
        """Очистка предупреждений пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM warnings WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
            await db.commit()

    async def get_last_daily(self, user_id):
        """Получение времени последней ежедневной награды"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT last_daily FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def set_last_daily(self, user_id):
        """Установка времени последней ежедневной награды"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET last_daily = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
            await db.commit()

    async def get_last_quest(self, user_id):
        """Получение времени последнего задания"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT last_quest FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def set_last_quest(self, user_id):
        """Установка времени последнего задания"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET last_quest = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
            await db.commit()

    async def get_shop_items(self):
        """Получение всех товаров в магазине"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM shop')
            return await cursor.fetchall()

    async def add_item_to_shop(self, name, price, description):
        """Добавление товара в магазин"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR IGNORE INTO shop (name, price, description) VALUES (?, ?, ?)',
                           (name, price, description))
            await db.commit()

    async def get_item_by_name(self, name):
        """Получение товара по имени"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM shop WHERE name = ?', (name,))
            return await cursor.fetchone()

    async def get_item_by_id(self, item_id):
        """Получение товара по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM shop WHERE id = ?', (item_id,))
            return await cursor.fetchone()

    async def add_item_to_inventory(self, user_id, item_id):
        """Добавление товара в инвентарь пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT INTO inventory (user_id, item_id) VALUES (?, ?)', (user_id, item_id))
            await db.commit()

    async def get_inventory(self, user_id):
        """Получение инвентаря пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM inventory WHERE user_id = ?', (user_id,))
            return await cursor.fetchall()

    async def remove_item_from_inventory(self, user_id, item_id):
        """Удаление товара из инвентаря пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1', (user_id, item_id))
            result = await cursor.fetchone()
            if result:
                await db.execute('DELETE FROM inventory WHERE id = ?', (result[0],))
                await db.commit()

    async def set_user_rank(self, user_id, rank):
        """Установка ранга пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET rank = ? WHERE id = ?', (rank, user_id))
            await db.commit()

    async def get_user_rank(self, user_id):
        """Получение ранга пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT rank FROM users WHERE id = ?', (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else None


    async def set_government_type(self, guild_id, gov_type):
        """Установка формы правления для гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO government_types (guild_id, gov_type) VALUES (?, ?)',
                (guild_id, gov_type)
            )
            await db.commit()
    
    async def get_government_type(self, guild_id):
        """Получение формы правления гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT gov_type FROM government_types WHERE guild_id = ?', (guild_id,))
            result = await cursor.fetchone()
            return result[0] if result else None
    
    async def create_political_party(self, guild_id, name, description, leader_id):
        """Создание политической партии"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO political_parties (guild_id, name, description, creation_date, leader_id) VALUES (?, ?, ?, ?, ?)',
                (guild_id, name, description, datetime.now().isoformat(), leader_id)
            )
            party_id = (await db.execute('SELECT last_insert_rowid()')).fetchone()[0]
                
            # Добавляем лидера как первого участника партии
            await db.execute(
                'INSERT INTO party_members (user_id, party_id, joined_date) VALUES (?, ?, ?)',
                (leader_id, party_id, datetime.now().isoformat())
            )
                
            await db.commit()
    
    async def get_party_by_name(self, guild_id, name):
        """Получение политической партии по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT * FROM political_parties WHERE guild_id = ? AND name = ?',
                (guild_id, name)
            )
            return await cursor.fetchone()
    
    async def get_user_party(self, user_id, guild_id):
        """Получение партии, в которой состоит пользователь"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT pp.* FROM political_parties pp
                JOIN party_members pm ON pp.id = pm.party_id
                WHERE pm.user_id = ? AND pp.guild_id = ?
            ''', (user_id, guild_id))
            return await cursor.fetchone()
    
    async def add_user_to_party(self, user_id, party_id):
        """Добавление пользователя в партию"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO party_members (user_id, party_id, joined_date) VALUES (?, ?, ?)',
                (user_id, party_id, datetime.now().isoformat())
            )
            await db.commit()
    
    async def remove_user_from_party(self, user_id, party_id):
        """Удаление пользователя из партии"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM party_members WHERE user_id = ? AND party_id = ?', (user_id, party_id))
            await db.commit()
    
    async def get_server_parties(self, guild_id):
        """Получение всех партий на сервере"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT * FROM political_parties WHERE guild_id = ?', (guild_id,))
            return await cursor.fetchall()
    
    async def get_parties_count(self, guild_id):
        """Получение количества партий на сервере"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM political_parties WHERE guild_id = ?', (guild_id,))
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_party_members_count(self, party_id):
        """Получение количества участников партии"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM party_members WHERE party_id = ?', (party_id,))
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def delete_party(self, party_id):
        """Удаление политической партии"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM party_members WHERE party_id = ?', (party_id,))
            await db.execute('DELETE FROM political_parties WHERE id = ?', (party_id,))
            await db.commit()
    
    async def schedule_election(self, guild_id, election_type, scheduled_date):
        """Назначение выборов"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO elections (guild_id, election_type, scheduled_date) VALUES (?, ?, ?)',
                (guild_id, election_type, scheduled_date)
            )
            await db.commit()
    
    async def get_scheduled_elections(self, guild_id):
        """Получение запланированных выборов"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT * FROM elections WHERE guild_id = ? AND completed = 0',
                (guild_id,)
            )
            return await cursor.fetchall()
    
    async def get_top_users_by_credits(self, guild_id, limit=99):
        """Получение топ пользователей по кредитам"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT id, credits FROM users WHERE guild_id = ? ORDER BY credits DESC LIMIT ?',
                (guild_id, limit)
            )
            return await cursor.fetchall()
    
    async def get_total_server_credits(self, guild_id):
        """Получение общего количества кредитов на сервере"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT SUM(credits) FROM users WHERE guild_id = ?', (guild_id,))
            result = await cursor.fetchone()
            return result[0] if result[0] else 0
    
    async def get_average_server_level(self, guild_id):
        """Получение среднего уровня пользователей на сервере"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT AVG(level) FROM users WHERE guild_id = ?', (guild_id,))
            result = await cursor.fetchone()
            return result[0] if result[0] else 0
    
    def is_supreme_ruler(self, user_id):
        """Проверка, является ли пользователь верховным правителем"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            supreme_ruler_id = config['government_structure']['supreme_ruler']
            return str(user_id) == supreme_ruler_id
        except:
            return False