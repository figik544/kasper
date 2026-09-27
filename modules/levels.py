import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime
import aiosqlite
import json

from .database import update_user_xp, get_top_users, get_user_data, create_user

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Тематические ранги Звёздных войн
STAR_WARS_RANKS = {
    1: {"name": "Рекрут", "role_color": 0xCCCCCC, "perm_desc": "Базовый член"},
    5: {"name": "Штурмовик", "role_color": 0xCCCCCC, "perm_desc": "Базовый солдат"},
    10: {"name": "Лейтенант", "role_color": 0x888888, "perm_desc": "Младший офицер"},
    15: {"name": "Капитан", "role_color": 0x777777, "perm_desc": "Офицер роты"},
    20: {"name": "Майор", "role_color": 0x666666, "perm_desc": "Офицер полевого уровня"},
    30: {"name": "Полковник", "role_color": 0x555555, "perm_desc": "Старший офицер полевого уровня"},
    40: {"name": "Генерал", "role_color": 0x444444, "perm_desc": "Высокопоставленный офицер"},
    50: {"name": "Адмирал", "role_color": 0x333333, "perm_desc": "Офицер флота"},
    60: {"name": "Тёмный Лорд", "role_color": 0x222222, "perm_desc": "Мощный пользователь темной стороны"},
    70: {"name": "Император", "role_color": 0x111111, "perm_desc": "Верховный правитель Империи"}
}

class LevelsCog(commands.Cog, name="Уровни"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Добавляем XP за сообщения
        xp_amount = random.randint(config['xp_rewards']['message_range_min'], config['xp_rewards']['message_range_max'])
        
        # Создаем пользователя, если его нет
        await create_user(message.author.id, message.guild.id)
        
        new_level = await update_user_xp(message.author.id, message.guild.id, xp_amount)
        
        # Проверяем, нужно ли обновить роль пользователя
        await self.update_user_rank(message.author, new_level, message.guild)

    async def update_user_rank(self, user, new_level, guild):
        """Обновление роли пользователя при повышении уровня"""
        if new_level in STAR_WARS_RANKS:
            rank_info = STAR_WARS_RANKS[new_level]

            # Создаем или получаем роль
            existing_role = discord.utils.get(guild.roles, name=rank_info["name"])
            if not existing_role:
                role = await guild.create_role(
                    name=rank_info["name"],
                    color=discord.Color(rank_info["role_color"]),
                    reason="Повышение уровня"
                )
            else:
                role = existing_role

            # Добавляем роль пользователю
            await user.add_roles(role)

            # Удаляем предыдущие роли ранга, если они есть
            for level_check, info in STAR_WARS_RANKS.items():
                if level_check < new_level and level_check != new_level:
                    old_role = discord.utils.get(guild.roles, name=info["name"])
                    if old_role and old_role in user.roles:
                        await user.remove_roles(old_role)

            # Отправляем сообщение о повышении
            embed = discord.Embed(
                title="Повышение!",
                description=f"{user.mention}, ваша преданность была отмечена. Вы были произведены в {rank_info['name']}!",
                color=rank_info["role_color"]
            )
            # Пытаемся найти системный канал для отправки сообщения
            system_channel = guild.system_channel or guild.text_channels[0]
            await system_channel.send(embed=embed)

    @commands.command(name='profile')
    async def profile(self, ctx, member: discord.Member = None):
        """Показывает профиль пользователя с его статистикой"""
        if member is None:
            member = ctx.author

        user_data = await get_user_data(member.id, ctx.guild.id)
        
        if not user_data:
            await create_user(member.id, ctx.guild.id)
            user_data = await get_user_data(member.id, ctx.guild.id)

        if not user_data:
            embed = discord.Embed(
                title="Профиль не найден",
                description=f"У {member.mention} нет профиля. Активность на сервере создаст профиль.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Рассчитываем прогресс до следующего уровня
        xp_to_next = ((user_data['level'] * 100) - user_data['xp']) % 100
        if xp_to_next == 0:
            xp_to_next = 100

        embed = discord.Embed(
            title=f"Профиль: {member.display_name}",
            color=0x0000FF
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Уровень", value=user_data['level'], inline=True)
        embed.add_field(name="XP", value=f"{user_data['xp']}/{user_data['level'] * 100}", inline=True)
        embed.add_field(name="Кредиты", value=user_data['credits'], inline=True)
        embed.add_field(name="Ранг", value=user_data['rank'], inline=True)
        embed.add_field(name="Предупреждения", value=user_data['warnings'], inline=True)
        embed.add_field(name="XP до следующего уровня", value=xp_to_next, inline=True)
        
        if user_data['join_date']:
            join_date = datetime.fromisoformat(user_data['join_date'].replace('Z', '+00:00'))
            embed.add_field(name="Дата присоединения", value=join_date.strftime("%Y-%m-%d"), inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='leaderboard')
    async def leaderboard(self, ctx):
        """Показывает топ игроков по уровню"""
        top_users = await get_top_users(ctx.guild.id, 10)

        embed = discord.Embed(
            title="Лидерборд Галактической Империи",
            description="Топ Имперских офицеров по рангу",
            color=0x000000
        )

        for i, (user_id, level, xp) in enumerate(top_users, 1):
            user = self.bot.get_user(user_id)
            if user:
                embed.add_field(
                    name=f"#{i}: {user.display_name}",
                    value=f"Уровень {level} (XP: {xp})",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"#{i}: Неизвестный пользователь (ID: {user_id})",
                    value=f"Уровень {level} (XP: {xp})",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.command(name='rankup')
    async def rankup(self, ctx):
        """Попытка получить более высокий ранг через испытания"""
        user_data = await get_user_data(ctx.author.id, ctx.guild.id)
        
        if not user_data:
            embed = discord.Embed(
                title="Невозможно повысить ранг",
                description="Вы должны больше участвовать, чтобы получить опыт.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        level, xp, credits = user_data['level'], user_data['xp'], user_data['credits']
        
        # Стоимость повышения увеличивается с уровнем
        cost = level * 50
        
        if credits < cost:
            embed = discord.Embed(
                title="Недостаточно средств",
                description=f"Вам нужно {cost} кредитов для попытки повышения, но у вас только {credits}.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Списываем стоимость
        await add_credits(ctx.author.id, ctx.guild.id, -cost)
        
        # Шанс успеха зависит от уровня
        success_chance = min(70 + level, 95)  # Шанс увеличивается с уровнем, максимум 95%
        
        if random.randint(1, 100) <= success_chance:
            # Добавляем XP за успешное повышение
            xp_gain = random.randint(50, 100)
            new_level = await update_user_xp(ctx.author.id, ctx.guild.id, xp_gain)
            
            embed = discord.Embed(
                title="Повышение успешно!",
                description=f"Ваша преданность была отмечена! Вы получили {xp_gain} XP.",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="Повышение не удалось",
                description="Ваша попытка подняться в ранге была безуспешной. Продолжайте доказывать свою преданность.",
                color=0xFFA500
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='setrank')
    @commands.has_permissions(administrator=True)
    async def set_rank(self, ctx, member: discord.Member, *, rank_name):
        """Ручная установка ранга пользователю (только для администраторов)"""
        # Находим роль по имени
        role = discord.utils.get(ctx.guild.roles, name=rank_name)
        if not role:
            embed = discord.Embed(
                title="Ранг не найден",
                description=f"Ранг '{rank_name}' не существует на этом сервере.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Удаляем все роли рангов сначала
        for r in ctx.guild.roles:
            if r.name in [info["name"] for level, info in STAR_WARS_RANKS.items()]:
                if r in member.roles:
                    await member.remove_roles(r)

        # Добавляем новый ранг
        await member.add_roles(role)

        # Обновляем ранг пользователя в БД
        async with aiosqlite.connect('galactic_empire_bot.db') as db:
            await db.execute("UPDATE users SET rank = ? WHERE user_id = ? AND guild_id = ?",
                           (rank_name, member.id, ctx.guild.id))
            await db.commit()

        embed = discord.Embed(
            title="Ранг назначен",
            description=f"{member.mention} получил назначение на ранг {rank_name}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LevelsCog(bot))