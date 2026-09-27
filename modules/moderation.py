import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite
import json

from .database import add_warning, reset_warnings, get_guild_config

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class ModerationCog(commands.Cog, name="Модерация"):
    def __init__(self, bot):
        self.bot = bot
        self.spam_detection = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Проверка на спам
        await self.check_spam(message)

    async def check_spam(self, message):
        """Проверка сообщений на спам"""
        user_id = message.author.id
        channel_id = message.channel.id
        guild_id = message.guild.id

        # Инициализация структуры для пользователя, если её нет
        if guild_id not in self.spam_detection:
            self.spam_detection[guild_id] = {}
        if user_id not in self.spam_detection[guild_id]:
            self.spam_detection[guild_id][user_id] = []

        # Добавляем время сообщения в список
        self.spam_detection[guild_id][user_id].append(datetime.utcnow())

        # Очищаем старые сообщения (старше 10 секунд)
        cutoff_time = datetime.utcnow() - timedelta(seconds=config['spam_threshold']['time_window_seconds'])
        self.spam_detection[guild_id][user_id] = [
            msg_time for msg_time in self.spam_detection[guild_id][user_id] 
            if msg_time > cutoff_time
        ]

        # Проверяем, превышает ли количество сообщений порог
        if len(self.spam_detection[guild_id][user_id]) >= config['spam_threshold']['message_count']:
            await self.moderate_spam(message.author, message.channel)
            # Очищаем историю сообщений пользователя после модерации
            self.spam_detection[guild_id][user_id] = []

    async def moderate_spam(self, user, channel):
        """Модерация спама"""
        # Находим или создаем роль 'Muted'
        muted_role = discord.utils.get(user.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await user.guild.create_role(
                name="Muted",
                permissions=discord.Permissions(send_messages=False, speak=False),
                reason="Автоматически созданная роль для мута"
            )
            # Применяем роль мута ко всем текстовым каналам
            for text_channel in user.guild.text_channels:
                await text_channel.set_permissions(muted_role, send_messages=False)

        # Добавляем роль мута пользователю
        await user.add_roles(muted_role)

        # Логируем действие модерации
        log_channel = discord.utils.get(user.guild.text_channels, name="mod-log")
        if not log_channel:
            log_channel = user.guild.system_channel

        if log_channel:
            embed = discord.Embed(
                title="Обнаружен спам",
                description=f"{user.mention} был замучен за спам в {channel.mention}",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Автоматически размучиваем через 10 минут
        await asyncio.sleep(600)
        await user.remove_roles(muted_role)

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban_user(self, ctx, member: discord.Member, *, reason=None):
        """Блокировка пользователя с сервера"""
        if reason is None:
            reason = "Причина не указана"

        await member.ban(reason=reason)

        embed = discord.Embed(
            title="Пользователь заблокирован",
            description=f"{member.mention} был заблокирован пользователем {ctx.author.mention}\nПричина: {reason}",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick_user(self, ctx, member: discord.Member, *, reason=None):
        """Выгоняет пользователя с сервера"""
        if reason is None:
            reason = "Причина не указана"

        await member.kick(reason=reason)

        embed = discord.Embed(
            title="Пользователь выгнан",
            description=f"{member.mention} был выгнан пользователем {ctx.author.mention}\nПричина: {reason}",
            color=0xFFA500
        )
        await ctx.send(embed=embed)

    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    async def mute_user(self, ctx, member: discord.Member, duration: int = 10):
        """Мутит пользователя на определенное время (в минутах)"""
        # Находим или создаем роль 'Muted'
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(
                name="Muted",
                permissions=discord.Permissions(send_messages=False, speak=False),
                reason="Автоматически созданная роль для мута"
            )
            # Применяем роль мута ко всем текстовым каналам
            for text_channel in ctx.guild.text_channels:
                await text_channel.set_permissions(muted_role, send_messages=False)

        await member.add_roles(muted_role)

        embed = discord.Embed(
            title="Пользователь замучен",
            description=f"{member.mention} был замучен пользователем {ctx.author.mention} на {duration} минут",
            color=0xFFA500
        )
        await ctx.send(embed=embed)

        # Автоматически размучиваем через указанное время
        await asyncio.sleep(duration * 60)
        await member.remove_roles(muted_role)

    @commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason):
        """Выдает предупреждение пользователю"""
        new_warning_count = await add_warning(member.id, ctx.guild.id, ctx.author.id, reason)

        # Проверяем, нужно ли банить пользователя из-за большого количества предупреждений
        if new_warning_count >= config['max_warns_before_ban']:
            await member.ban(reason=f"Превышено максимальное количество предупреждений ({config['max_warns_before_ban']})")
            embed = discord.Embed(
                title="Пользователь заблокирован",
                description=f"{member.mention} был заблокирован за превышение количества предупреждений ({new_warning_count})",
                color=0xFF0000
            )
        else:
            embed = discord.Embed(
                title="Пользователь предупрежден",
                description=f"{member.mention} получил предупреждение от {ctx.author.mention}\nПричина: {reason}\nПредупреждения: {new_warning_count}/{config['max_warns_before_ban']}",
                color=0xFFFF00
            )

        await ctx.send(embed=embed)

    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: int):
        """Удаляет указанное количество сообщений"""
        await ctx.channel.purge(limit=amount + 1)  # +1 чтобы удалить команду тоже
        msg = await ctx.send(f"Удалено {amount} сообщений")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name='unwarn')
    @commands.has_permissions(manage_messages=True)
    async def unwarn_user(self, ctx, member: discord.Member):
        """Сбрасывает предупреждения пользователя"""
        await reset_warnings(member.id, ctx.guild.id)

        embed = discord.Embed(
            title="Предупреждения сброшены",
            description=f"Предупреждения пользователя {member.mention} были сброшены пользователем {ctx.author.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='warnings')
    @commands.has_permissions(manage_messages=True)
    async def show_warnings(self, ctx, member: discord.Member):
        """Показывает количество предупреждений у пользователя"""
        async with aiosqlite.connect('galactic_empire_bot.db') as db:
            async with db.execute("SELECT warnings FROM users WHERE user_id = ? AND guild_id = ?", 
                                 (member.id, ctx.guild.id)) as cursor:
                result = await cursor.fetchone()
                
        warning_count = result[0] if result else 0
        
        embed = discord.Embed(
            title="Предупреждения пользователя",
            description=f"У {member.mention} {warning_count} предупреждений",
            color=0xFFFF00
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))