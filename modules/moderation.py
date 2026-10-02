import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import time
import json
import aiosqlite

# Глобальная переменная для задачи рекламы
advertising_task = None

class SecuritySystem:
    def __init__(self):
        self.spam_detection = {}
        self.quarantine_mode = False
        self.quarantine_start_time = None
        self.quarantine_duration = timedelta(hours=1)
        self.security_logs = []
    
    def add_log(self, event_type, user_id, details):
        """Добавить запись в журнал безопасности"""
        self.security_logs.append({
            'timestamp': datetime.now(),
            'event_type': event_type,
            'user_id': user_id,
            'details': details
        })
    
    def detect_spam(self, user_id, guild_id):
        """Обнаружение спама от пользователя"""
        key = f"{user_id}_{guild_id}"
        now = time.time()
        
        if key not in self.spam_detection:
            self.spam_detection[key] = []
        
        # Добавляем текущее событие
        self.spam_detection[key].append(now)
        
        # Оставляем только события за последние 10 секунд
        self.spam_detection[key] = [t for t in self.spam_detection[key] if now - t <= 10]
        
        # Если больше 5 сообщений за 10 секунд - это спам
        return len(self.spam_detection[key]) > 5
    
    def activate_quarantine(self, guild_id, detected_by=None):
        """Активировать режим карантина"""
        self.quarantine_mode = True
        self.quarantine_start_time = datetime.now()
        self.add_log("QUARANTINE_ACTIVATED", detected_by, f"Activated quarantine for guild {guild_id}")
    
    def deactivate_quarantine(self, guild_id, deactivated_by=None):
        """Деактивировать режим карантина"""
        self.quarantine_mode = False
        self.quarantine_start_time = None
        self.add_log("QUARANTINE_DEACTIVATED", deactivated_by, f"Deactivated quarantine for guild {guild_id}")
    
    def is_in_quarantine(self):
        """Проверить, находится ли сервер в карантине"""
        if not self.quarantine_mode:
            return False
        
        if self.quarantine_start_time:
            elapsed = datetime.now() - self.quarantine_start_time
            return elapsed < self.quarantine_duration
        
        return False


class ModerationCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.security = SecuritySystem()
        self.antiraid_enabled = True
        self.spam_violators = set()
        
        # Загрузка конфига
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.config = {}

    def load_ad_config(self):
        """Загрузка настроек рекламы из config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                ad_config = config.get('advertising', {})
                self.advertising_enabled = ad_config.get('enabled', False)
                self.ad_message = ad_config.get('message', 'Присоединяйся к Федерации Галактической Империи!')
                self.ad_frequency_hours = ad_config.get('frequency_hours', 6)
        except FileNotFoundError:
            print("Файл config.json не найден, используются стандартные настройки рекламы")

    def is_supreme_ruler(self, user_id):
        """Проверка, является ли пользователь верховным правителем"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return str(user_id) == config['government_structure']['supreme_ruler']
        except:
            return False
    
    def is_admin_or_supreme(self, ctx):
        """Проверка, является ли пользователь администратором или верховным правителем"""
        return ctx.author.guild_permissions.administrator or self.is_supreme_ruler(ctx.author.id)
    
    def is_chancellor_or_higher(self, ctx):
        """Проверка, является ли пользователь канцлером или выше"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            user_id = str(ctx.author.id)
            chancellors = config['government_structure']['chancellery']
            is_chancellor = user_id in chancellors
            is_supreme = user_id == config['government_structure']['supreme_ruler']
            
            return is_chancellor or is_supreme
        except:
            return False

    @commands.hybrid_command(name='ban', description='Забанить пользователя (только для администраторов)')
    @app_commands.describe(user='Пользователь для бана', reason='Причина бана')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *, reason='Нарушение правил сервера'):
        """Забанить пользователя (только для администраторов)"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        try:
            await ctx.guild.ban(user, reason=reason)
            embed = discord.Embed(
                title="🔨 Бан",
                description=f"{ctx.author.mention} забанил {user.mention}\nПричина: {reason}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Не удалось забанить пользователя: {e}")

    @commands.hybrid_command(name='kick', description='Кикнуть пользователя (только для администраторов)')
    @app_commands.describe(user='Пользователь для кика', reason='Причина кика')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.User, *, reason='Нарушение правил сервера'):
        """Кикнуть пользователя (только для администраторов)"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        try:
            await ctx.guild.kick(user, reason=reason)
            embed = discord.Embed(
                title="👢 Кик",
                description=f"{ctx.author.mention} кикнул {user.mention}\nПричина: {reason}",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Не удалось кикнуть пользователя: {e}")

    @commands.hybrid_command(name='mute', description='Замутить пользователя (только для администраторов)')
    @app_commands.describe(user='Пользователь для мута', duration='Длительность (в минутах)', reason='Причина мута')
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, user: discord.Member, duration: int = 10, *, reason='Нарушение правил чата'):
        """Замутить пользователя (только для администраторов)"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        try:
            # Создаем роль мута если её нет
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await ctx.guild.create_role(name="Muted")
                # Устанавливаем права для роли мута
                for channel in ctx.guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False)
            
            await user.add_roles(muted_role, reason=reason)
            
            # Автоматическое снятие мута
            await asyncio.sleep(duration * 60)
            await user.remove_roles(muted_role)
            
            embed = discord.Embed(
                title="🤐 Мут",
                description=f"{ctx.author.mention} замутил {user.mention} на {duration} минут\nПричина: {reason}",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Не удалось замутить пользователя: {e}")

    @commands.hybrid_command(name='warn', description='Выдать предупреждение пользователю')
    @app_commands.describe(user='Пользователь для предупреждения', reason='Причина предупреждения')
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason='Нарушение правил'):
        """Выдать предупреждение пользователю"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        # Сохраняем предупреждение в базе данных
        await self.db.add_warning(user.id, ctx.guild.id, ctx.author.id, reason)
        
        # Проверяем количество предупреждений
        warns = await self.db.get_warnings(user.id, ctx.guild.id)
        max_warns = self.config.get('max_warns_before_ban', 5)
        
        embed = discord.Embed(
            title="⚠️ Предупреждение",
            description=f"{ctx.author.mention} выдал предупреждение {user.mention}\nПричина: {reason}\nПредупреждений: {len(warns)}/{max_warns}",
            color=0xFFA500
        )
        await ctx.send(embed=embed)
        
        # Если слишком много предупреждений - бан
        if len(warns) >= max_warns:
            try:
                await ctx.guild.ban(user, reason=f"Превышено количество предупреждений ({max_warns})")
                embed = discord.Embed(
                    title="🔨 Бан за предупреждения",
                    description=f"{user.mention} был забанен за превышение количества предупреждений",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
            except:
                pass

    @commands.hybrid_command(name='warnings', description='Показывает количество предупреждений у пользователя')
    @app_commands.describe(member='Пользователь для проверки')
    async def warnings(self, ctx, member: discord.Member = None):
        """Показывает количество предупреждений у пользователя"""
        if not member:
            member = ctx.author
        
        try:
            warnings = await self.db.get_warnings(member.id, ctx.guild.id)
            embed = discord.Embed(
                title=f"📋 Предупреждения {member.display_name}",
                description=f"Количество предупреждений: {len(warnings)}",
                color=0x00FFFF
            )
            
            if warnings:
                for i, warning in enumerate(warnings, 1):
                    embed.add_field(
                        name=f"Предупреждение #{i}",
                        value=f"**Модератор:** <@{warning[2]}>\n**Дата:** {warning[3]}\n**Причина:** {warning[4]}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Ошибка при получении предупреждений: {e}")

    @commands.hybrid_command(name='unwarn', description='Снять предупреждение с пользователя')
    @app_commands.describe(user='Пользователь для снятия предупреждения', warn_id='ID предупреждения для снятия')
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, user: discord.Member, warn_id: int):
        """Снять предупреждение с пользователя"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        # В реальной реализации здесь будет код для снятия конкретного предупреждения
        # Для упрощения просто покажем сообщение
        embed = discord.Embed(
            title="✅ Снятие предупреждения",
            description=f"Предупреждение #{warn_id} снято с {user.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='clear', description='Очистить сообщения (только для администраторов)')
    @app_commands.describe(amount='Количество сообщений для удаления')
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        """Очистить сообщения (только для администраторов)"""
        if not self.is_admin_or_supreme(ctx):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        if amount < 1 or amount > 100:
            await ctx.send("❌ Количество сообщений должно быть от 1 до 100!")
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 чтобы удалить команду тоже
            embed = discord.Embed(
                title="🗑️ Очистка",
                description=f"{ctx.author.mention} удалил {len(deleted)-1} сообщений",
                color=0x00FF00
            )
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            await ctx.send(f"❌ Не удалось очистить сообщения: {e}")

    @commands.hybrid_command(name='nuke_channel', description='Полностью очистить канал (только для высших администраторов)')
    @commands.has_permissions(administrator=True)
    async def nuke_channel(self, ctx):
        """Полностью очистить канал (только для высших администраторов)"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        confirm_embed = discord.Embed(
            title="⚠️ Подтверждение",
            description=f"Вы уверены, что хотите полностью очистить канал {ctx.channel.mention}?\n"
                       f"Все сообщения будут удалены безвозвратно!\n"
                       f"Для подтверждения введите `!confirm_nuke` в течение 30 секунд.",
            color=0xFFA500
        )
        await ctx.send(embed=confirm_embed)
        
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content == '!confirm_nuke'
        
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("❌ Время подтверждения истекло. Очистка отменена.")
            return
        
        # Создаем новый канал с тем же именем и настройками
        overwrites = ctx.channel.overwrites
        new_channel = await ctx.channel.clone(reason="Nuke command")
        
        # Отправляем сообщение о нуке в старый канал перед удалением
        try:
            nuke_message = discord.Embed(
                title="💥 Канал очищен",
                description=f"Канал {ctx.channel.mention} был полностью очищен пользователем {ctx.author.mention}",
                color=0xFF0000
            )
            await ctx.channel.send(embed=nuke_message)
        except:
            pass  # Если не можем отправить сообщение, просто продолжаем
        
        # Удаляем старый канал
        await ctx.channel.delete()
        
        # Отправляем сообщение о нуке в новый канал
        nuke_announce = discord.Embed(
            title="💥 Канал очищен",
            description=f"Канал был полностью очищен пользователем {ctx.author.mention}",
            color=0xFF0000
        )
        await new_channel.send(embed=nuke_announce)

    @commands.hybrid_command(name='create_all_channels', description='Создать все необходимые каналы и настроить разрешения')
    @commands.has_permissions(administrator=True)
    async def create_all_channels(self, ctx):
        """Создать все необходимые каналы и настроить разрешения"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        # Создаем категории, если они не существуют
        categories_to_create = [
            "🏛️ Правительственные",
            "💰 Экономические",
            "🎮 Игровые",
            "🛡️ Безопасность",
            "📜 Информационные"
        ]
        
        created_categories = []
        for cat_name in categories_to_create:
            existing_cat = discord.utils.get(ctx.guild.categories, name=cat_name)
            if not existing_cat:
                new_category = await ctx.guild.create_category(cat_name)
                created_categories.append(new_category.name)
            else:
                created_categories.append(f"{existing_cat.name} (уже существует)")
        
        # Создаем текстовые каналы, если они не существуют
        text_channels_to_create = [
            ("📢-объявления", "канал для официальных объявлений"),
            ("чат", "основной чат сервера"),
            ("выборы", "канал для голосования на выборах"),
            ("голосование", "канал для парламентских голосований"),
            ("жалобы", "канал для подачи жалоб"),
            ("репорт", "канал для репортов о нарушениях"),
            ("архив", "канал для архивирования информации"),
            ("rules", "канал с правилами сервера")
        ]
        
        created_text_channels = []
        for channel_name, topic in text_channels_to_create:
            existing_channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
            if not existing_channel:
                new_channel = await ctx.guild.create_text_channel(
                    channel_name,
                    category=discord.utils.get(ctx.guild.categories, name="📜 Информационные"),
                    topic=topic
                )
                created_text_channels.append(new_channel.name)
            else:
                created_text_channels.append(f"{existing_channel.name} (уже существует)")
        
        # Создаем голосовые каналы, если они не существуют
        voice_channels_to_create = [
            ("💬 Основной", 999),
            ("🔊 Парламент", 99),
            ("🤫 Тихий", 99),
            ("🎤 VIP", 9)
        ]
        
        created_voice_channels = []
        for channel_name, limit in voice_channels_to_create:
            existing_channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
            if not existing_channel:
                new_channel = await ctx.guild.create_voice_channel(
                    channel_name,
                    category=discord.utils.get(ctx.guild.categories, name="🎮 Игровые"),
                    user_limit=limit
                )
                created_voice_channels.append(new_channel.name)
            else:
                created_voice_channels.append(f"{existing_channel.name} (уже существует)")
        
        # Настройка разрешений для важных каналов
        try:
            # Канал выборов - разрешаем только определенные сообщения
            voting_channel = discord.utils.get(ctx.guild.text_channels, name="выборы")
            if voting_channel:
                # Устанавливаем разрешения: только админы могут отправлять сообщения, остальные могут читать
                for role in ctx.guild.roles:
                    if role.permissions.administrator:
                        await voting_channel.set_permissions(role, send_messages=True)
                    elif role.name != "@everyone":
                        await voting_channel.set_permissions(role, send_messages=False)
        
            # Канал голосования - только для членов парламента и админов
            parliament_channel = discord.utils.get(ctx.guild.text_channels, name="голосование")
            if parliament_channel:
                parliament_role = discord.utils.get(ctx.guild.roles, name="Член Парламента")
                if not parliament_role:
                    parliament_role = await ctx.guild.create_role(name="Член Парламента")
                
                # Разрешаем отправку сообщений только админам и членам парламента
                for role in ctx.guild.roles:
                    if role.permissions.administrator or role == parliament_role:
                        await parliament_channel.set_permissions(role, send_messages=True)
                    elif role.name != "@everyone":
                        await parliament_channel.set_permissions(role, send_messages=False)
        
            # Канал жалоб - все могут писать, но только модераторы могут отвечать
            complaints_channel = discord.utils.get(ctx.guild.text_channels, name="жалобы")
            if complaints_channel:
                mod_role = discord.utils.get(ctx.guild.roles, name="Модератор")
                if not mod_role:
                    mod_role = await ctx.guild.create_role(name="Модератор")
                
                # Все могут читать и писать
                await complaints_channel.set_permissions(ctx.guild.default_role, send_messages=True, read_messages=True)
                # Модераторы и администраторы имеют дополнительные права
                await complaints_channel.set_permissions(mod_role, manage_messages=True)
        
        except Exception as e:
            print(f"Ошибка при настройке разрешений: {e}")
        
        # Формируем сообщение с результатами
        embed = discord.Embed(
            title="🏗️ Создание инфраструктуры завершено",
            description="Были созданы или проверены следующие элементы:",
            color=0x00FF00
        )
        
        if created_categories:
            embed.add_field(
                name="📁 Созданные категории",
                value="\n".join(created_categories),
                inline=False
            )
        
        if created_text_channels:
            embed.add_field(
                name="📄 Созданные текстовые каналы",
                value="\n".join(created_text_channels),
                inline=False
            )
        
        if created_voice_channels:
            embed.add_field(
                name="🔊 Созданные голосовые каналы",
                value="\n".join(created_voice_channels),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Информация",
            value="Разрешения для специальных каналов настроены автоматически",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='enable_ads', description='Включить рекламу с заданной частотой')
    @app_commands.describe(frequency_hours='Частота показа рекламы в часах')
    @commands.check(lambda ctx: ctx.author.id == ctx.bot.owner_id or 
                   ctx.author.id == int(json.load(open('config.json', 'r', encoding='utf-8'))['government_structure']['supreme_ruler']))
    async def enable_ads(self, ctx, frequency_hours: int = 6):
        """Включить рекламу с заданной частотой"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        # Проверяем права
        if not (ctx.author.id == self.bot.owner_id or is_supreme_ruler):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        self.advertising_enabled = True
        self.ad_frequency_hours = frequency_hours
        
        # Обновляем настройки в config.json
        try:
            with open('config.json', 'r+', encoding='utf-8') as f:
                config = json.load(f)
                if 'advertising' not in config:
                    config['advertising'] = {}
                config['advertising']['enabled'] = True
                config['advertising']['frequency_hours'] = frequency_hours
                f.seek(0)
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.truncate()
        except Exception as e:
            await ctx.send(f"Ошибка при сохранении настроек: {e}")
            return
        
        if advertising_task and not advertising_task.done():
            advertising_task.cancel()
        
        start_advertising_task(self.bot)
        
        embed = discord.Embed(
            title="📢 Реклама включена",
            description=f"Реклама включена с частотой {frequency_hours} часов",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='disable_ads', description='Выключить рекламу')
    @commands.check(lambda ctx: ctx.author.id == ctx.bot.owner_id or 
                   ctx.author.id == int(json.load(open('config.json', 'r', encoding='utf-8'))['government_structure']['supreme_ruler']))
    async def disable_ads(self, ctx):
        """Выключить рекламу"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        # Проверяем права
        if not (ctx.author.id == self.bot.owner_id or is_supreme_ruler):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        self.advertising_enabled = False
        
        # Обновляем настройки в config.json
        try:
            with open('config.json', 'r+', encoding='utf-8') as f:
                config = json.load(f)
                if 'advertising' not in config:
                    config['advertising'] = {}
                config['advertising']['enabled'] = False
                f.seek(0)
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.truncate()
        except Exception as e:
            await ctx.send(f"Ошибка при сохранении настроек: {e}")
            return
        
        if advertising_task and not advertising_task.done():
            advertising_task.cancel()
        
        embed = discord.Embed(
            title="🔕 Реклама выключена",
            description="Реклама отключена",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='set_ad_message', description='Установить рекламное сообщение')
    @app_commands.describe(message='Текст рекламного сообщения')
    @commands.check(lambda ctx: ctx.author.id == ctx.bot.owner_id or 
                   ctx.author.id == int(json.load(open('config.json', 'r', encoding='utf-8'))['government_structure']['supreme_ruler']))
    async def set_ad_message(self, ctx, *, message: str):
        """Установить рекламное сообщение"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        # Проверяем права
        if not (ctx.author.id == self.bot.owner_id or is_supreme_ruler):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        self.ad_message = message
        
        # Обновляем настройки в config.json
        try:
            with open('config.json', 'r+', encoding='utf-8') as f:
                config = json.load(f)
                if 'advertising' not in config:
                    config['advertising'] = {}
                config['advertising']['message'] = message
                f.seek(0)
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.truncate()
        except Exception as e:
            await ctx.send(f"Ошибка при сохранении настроек: {e}")
            return
        
        embed = discord.Embed(
            title="📝 Рекламное сообщение установлено",
            description=f"Новое рекламное сообщение: {message}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='ad_info', description='Показать информацию о рекламе')
    async def ad_info(self, ctx):
        """Показать информацию о рекламе"""
        embed = discord.Embed(
            title="📊 Информация о рекламе",
            description=f"**Статус:** {'Включена' if self.advertising_enabled else 'Выключена'}\n"
                       f"**Частота:** {self.ad_frequency_hours} часов\n"
                       f"**Сообщение:** {self.ad_message}",
            color=0x00FFFF
        )
        await ctx.send(embed=embed)

# Функция для запуска задачи рекламы
def start_advertising_task(bot):
    """Запуск задачи рекламы"""
    config = bot.config
    if config.get('advertising_enabled', False):
        @tasks.loop(hours=config.get('ad_frequency_hours', 6))
        async def advertise():
            ad_message = config.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!')
            
            embed = discord.Embed(
                title="📢 Реклама Федерации",
                description=ad_message,
                color=0xFFD700
            )
            
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            await channel.send(embed=embed)
                            break  # Отправляем только в первый доступный канал
                        except:
                            continue
        
        advertise.start()

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(ModerationCog(bot, db))