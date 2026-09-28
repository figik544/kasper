import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import sqlite3
from datetime import datetime, timedelta
import aiosqlite
import json

# Глобальная переменная для задачи рекламы
advertising_task = None

class ModerationCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.spam_detection = {}
        self.warn_counts = {}
        self.advertising_enabled = False
        self.ad_message = ""
        self.ad_frequency_hours = 6
        self.load_ad_config()

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

    def is_supreme_ruler_or_admin():
        """Проверка, является ли пользователь верховным правителем или администратором"""
        async def predicate(ctx):
            # Загружаем текущую конфигурацию
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            supreme_ruler_id = config['government_structure']['supreme_ruler']
            return ctx.author.id == int(supreme_ruler_id) or ctx.author.guild_permissions.administrator
        return commands.check(predicate)

    @commands.hybrid_command(name='ban', description='Блокировка пользователя с сервера')
    @app_commands.describe(member='Пользователь для бана', reason='Причина бана')
    @is_supreme_ruler_or_admin()
    async def ban(self, ctx, member: discord.Member, reason: str = "Причина не указана"):
        """Блокировка пользователя с сервера"""
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="🔨 Бан",
                description=f"{member.mention} был заблокирован\nПричина: {reason}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Ошибка при бане: {e}")

    @commands.hybrid_command(name='kick', description='Выгоняет пользователя с сервера')
    @app_commands.describe(member='Пользователь для кика', reason='Причина кика')
    @is_supreme_ruler_or_admin()
    async def kick(self, ctx, member: discord.Member, reason: str = "Причина не указана"):
        """Выгоняет пользователя с сервера"""
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="👢 Кик",
                description=f"{member.mention} был выгнан\nПричина: {reason}",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Ошибка при кике: {e}")

    @commands.hybrid_command(name='mute', description='Мутит пользователя на определенное время')
    @app_commands.describe(member='Пользователь для мута', duration='Длительность в минутах', reason='Причина мута')
    @is_supreme_ruler_or_admin()
    async def mute(self, ctx, member: discord.Member, duration: int = 10, reason: str = "Причина не указана"):
        """Мутит пользователя на определенное время (в минутах)"""
        try:
            # Создаем роль мута если её нет
            mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await ctx.guild.create_role(name="Muted")
                # Настраиваем права для роли мута
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, speak=False, send_messages=False)
            
            await member.add_roles(mute_role, reason=reason)
            
            embed = discord.Embed(
                title="🔇 Мут",
                description=f"{member.mention} получил мут на {duration} минут\nПричина: {reason}",
                color=0xFFFF00
            )
            await ctx.send(embed=embed)
            
            # Автоматически снимаем мут через указанное время
            await asyncio.sleep(duration * 60)
            await member.remove_roles(mute_role)
            await ctx.send(f"⏰ Мут для {member.mention} снят автоматически")
        except Exception as e:
            await ctx.send(f"Ошибка при муте: {e}")

    @commands.hybrid_command(name='warn', description='Выдает предупреждение пользователю')
    @app_commands.describe(member='Пользователь для предупреждения', reason='Причина предупреждения')
    @is_supreme_ruler_or_admin()
    async def warn(self, ctx, member: discord.Member, reason: str = "Причина не указана"):
        """Выдает предупреждение пользователю"""
        try:
            # Сохраняем предупреждение в базе данных
            await self.db.add_warning(member.id, ctx.guild.id, ctx.author.id, reason)
            
            # Проверяем количество предупреждений
            warnings = await self.db.get_warnings(member.id, ctx.guild.id)
            max_warns = self.bot.config.get('max_warns_before_ban', 5)
            
            embed = discord.Embed(
                title="⚠️ Предупреждение",
                description=f"{member.mention} получил предупреждение\nПричина: {reason}\nКоличество предупреждений: {len(warnings)}/{max_warns}",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
            
            # Если достигнут лимит предупреждений - бан
            if len(warnings) >= max_warns:
                await member.ban(reason=f"Превышено количество предупреждений ({max_warns})")
                await ctx.send(f"🔨 {member.mention} был заблокирован за превышение количества предупреждений")
        except Exception as e:
            await ctx.send(f"Ошибка при выдаче предупреждения: {e}")

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

    @commands.hybrid_command(name='unwarn', description='Сбрасывает предупреждения пользователя')
    @app_commands.describe(member='Пользователь для сброса предупреждений')
    @is_supreme_ruler_or_admin()
    async def unwarn(self, ctx, member: discord.Member):
        """Сбрасывает предупреждения пользователя"""
        try:
            await self.db.clear_warnings(member.id, ctx.guild.id)
            embed = discord.Embed(
                title="✅ Сброс предупреждений",
                description=f"Предупреждения для {member.mention} были сброшены",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Ошибка при сбросе предупреждений: {e}")

    @commands.hybrid_command(name='clear', description='Удаляет указанное количество сообщений')
    @app_commands.describe(amount='Количество сообщений для удаления')
    @is_supreme_ruler_or_admin()
    async def clear(self, ctx, amount: int):
        """Удаляет указанное количество сообщений"""
        try:
            await ctx.channel.purge(limit=amount + 1)  # +1 для удаления команды тоже
            msg = await ctx.send(f"🗑️ Удалено {amount} сообщений")
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            await ctx.send(f"Ошибка при очистке сообщений: {e}")

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
    global advertising_task
    # Импортируем здесь, чтобы избежать циклических импортов
    from modules.moderation import ModerationCog
    
    # Находим cog модерации
    mod_cog = None
    for cog in bot.cogs.values():
        if isinstance(cog, ModerationCog):
            mod_cog = cog
            break
    
    if mod_cog and mod_cog.advertising_enabled:
        @tasks.loop(hours=mod_cog.ad_frequency_hours)
        async def advertise():
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            await channel.send(mod_cog.ad_message)
                            break  # Отправляем только в первый доступный канал
                        except:
                            continue
        
        advertising_task = advertise
        advertise.start()

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(ModerationCog(bot, db))