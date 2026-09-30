import discord
from discord.ext import commands
from discord import app_commands
import random
import math
from datetime import datetime
import json

class LevelsCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        # Словарь для отслеживания последнего времени получения опыта пользователем
        self.last_message_time = {}

    @commands.hybrid_command(name='profile', description='Показывает профиль пользователя с его статистикой')
    @app_commands.describe(member='Пользователь для просмотра профиля')
    async def profile(self, ctx, member: discord.Member = None):
        """Показывает профиль пользователя с его статистикой"""
        if not member:
            member = ctx.author
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = member.id == int(supreme_ruler_id)
        
        user_data = await self.db.get_user_data(member.id)
        if not user_data:
            await self.db.create_user(member.id, member.guild.id)
            user_data = await self.db.get_user_data(member.id)
        
        level = user_data[3]
        xp = user_data[4]
        xp_needed = int((level + 1) ** 2 * 10)
        balance = await self.db.get_balance(member.id)
        
        # Получаем текущую роль пользователя
        current_rank = await self.db.get_user_rank(member.id)
        
        embed = discord.Embed(
            title=f"👤 Профиль {member.display_name}",
            color=0x00FFFF
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Уровень", value=level, inline=True)
        embed.add_field(name="Опыт", value=f"{xp}/{xp_needed}", inline=True)
        embed.add_field(name="Кредиты", value=balance, inline=True)
        embed.add_field(name="Ранг", value=current_rank if current_rank else "Новичок", inline=False)
        embed.add_field(name="Присоединился", value=member.joined_at.strftime("%d.%m.%Y"), inline=True)
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        
        # Если пользователь - верховный правитель, добавляем специальное поле
        if is_supreme_ruler:
            embed.add_field(name="Статус", value="👑 **Верховный Правитель Федерации Галактической Империи**", inline=False)
            embed.color = 0xFFFF00  # Жёлтый цвет для верховного правителя
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='leaderboard', description='Показывает топ игроков по уровню')
    async def leaderboard(self, ctx):
        """Показывает топ игроков по уровню"""
        top_users = await self.db.get_top_users()
        
        if not top_users:
            await ctx.send("📊 Список лидеров пуст!")
            return
        
        embed = discord.Embed(
            title="🏆 Таблица Лидеров",
            description="Топ игроков по уровню:",
            color=0xFFD700
        )
        
        for i, user_data in enumerate(top_users[:10], 1):
            user_id, guild_id, user_level, user_xp = user_data
            user = self.bot.get_user(user_id)
            if user:
                # Проверяем, является ли пользователь верховным правителем
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                supreme_ruler_id = config['government_structure']['supreme_ruler']
                is_supreme_ruler = user_id == int(supreme_ruler_id)
                
                rank_display = f"{i}. {user.display_name}"
                if is_supreme_ruler:
                    rank_display = f"👑 {rank_display}"
                
                embed.add_field(
                    name=rank_display,
                    value=f"Уровень: {user_level}, Опыт: {user_xp}",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='rankup', description='Попытка получить более высокий ранг через испытания')
    async def rankup(self, ctx):
        """Попытка получить более высокий ранг через испытания"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        user_data = await self.db.get_user_data(ctx.author.id)
        if not user_data:
            await self.db.create_user(ctx.author.id, ctx.guild.id)
            user_data = await self.db.get_user_data(ctx.author.id)
        
        current_level = user_data[3]
        current_rank = await self.db.get_user_rank(ctx.author.id)
        
        # Если пользователь - верховный правитель, он всегда может повышаться
        if is_supreme_ruler:
            # Определяем следующий возможный ранг
            rank_order = [
                "Новичок", "Рекрут", "Штурмовик", "Офицер", "Капитан", 
                "Майор", "Подполковник", "Полковник", "Генерал", "Маршал", "Император"
            ]
            
            if not current_rank or current_rank not in rank_order:
                next_rank = "Рекрут"
            else:
                current_index = rank_order.index(current_rank)
                if current_index < len(rank_order) - 1:
                    next_rank = rank_order[current_index + 1]
                else:
                    await ctx.send("🎉 Вы достигли максимального ранга!")
                    return
            
            await self.db.set_user_rank(ctx.author.id, next_rank)
            
            embed = discord.Embed(
                title="🎖️ Повышение!",
                description=f"@{ctx.author.display_name}, как **Верховный Правитель**, вы были произведены в **{next_rank}**!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            
            # Награда за повышение
            reward = random.randint(100, 300)
            await self.db.add_credits(ctx.author.id, reward)
            
            reward_embed = discord.Embed(
                title="💰 Награда за повышение",
                description=f"Вы получили **{reward}** кредитов за продвижение до **{next_rank}**!",
                color=0x00FF00
            )
            await ctx.send(embed=reward_embed)
            
            return
        
        # Определяем следующий возможный ранг
        rank_order = [
            "Новичок", "Рекрут", "Штурмовик", "Офицер", "Капитан", 
            "Майор", "Подполковник", "Полковник", "Генерал", "Маршал", "Император"
        ]
        
        if not current_rank or current_rank not in rank_order:
            next_rank = "Рекрут"
        else:
            current_index = rank_order.index(current_rank)
            if current_index < len(rank_order) - 1:
                next_rank = rank_order[current_index + 1]
            else:
                await ctx.send("🎉 Вы достигли максимального ранга!")
                return
        
        # Проверяем, достаточно ли уровня для повышения
        required_level = rank_order.index(next_rank) * 5  # каждые 5 уровней - новый ранг
        
        if current_level >= required_level:
            await self.db.set_user_rank(ctx.author.id, next_rank)
            
            embed = discord.Embed(
                title="🎖️ Повышение!",
                description=f"@{ctx.author.display_name}, ваша **преданность** была отмечена. Вы были произведены в **{next_rank}**!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            
            # Награда за повышение
            reward = random.randint(100, 300)
            await self.db.add_credits(ctx.author.id, reward)
            
            reward_embed = discord.Embed(
                title="💰 Награда за повышение",
                description=f"Вы получили **{reward}** кредитов за продвижение до **{next_rank}**!",
                color=0x00FF00
            )
            await ctx.send(embed=reward_embed)
        else:
            required_xp = required_level * 20  # примерный расчет
            current_xp = user_data[4]
            
            embed = discord.Embed(
                title="⏳ Повышение",
                description=f"Для получения ранга **{next_rank}** требуется уровень **{required_level}**.\n"
                           f"Ваш текущий уровень: **{current_level}**\n"
                           f"Необходимо опыта: **{required_xp - current_xp}**",
                color=0xFFA500
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='setrank', description='Ручная установка ранга пользователю (только для администраторов)')
    @app_commands.describe(member='Пользователь для установки ранга', rank_name='Название ранга')
    @commands.has_permissions(administrator=True)
    async def setrank(self, ctx, member: discord.Member, rank_name: str):
        """Ручная установка ранга пользователю (только для администраторов)"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        # Если пользователь - верховный правитель, он может устанавливать ранги
        if not (ctx.author.guild_permissions.administrator or is_supreme_ruler):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        await self.db.set_user_rank(member.id, rank_name)
        
        embed = discord.Embed(
            title="⚙️ Установка ранга",
            description=f"{ctx.author.mention} установил ранг '**{rank_name}**' пользователю {member.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Обработка получения опыта за сообщения"""
        if message.author.bot:
            return
        
        if message.guild is None:  # не в приватных сообщениях
            return
        
        # Проверяем, является ли сообщение командой
        if message.content.startswith(tuple(self.bot.command_prefix)):
            return
        
        # Проверяем, является ли сообщение словом "сектор"
        if message.content.lower().strip() == 'сектор':
            return  # Не начисляем опыт за команду "сектор"
        
        # Проверяем время последнего сообщения от пользователя
        current_time = datetime.now()
        if message.author.id in self.last_message_time:
            time_since_last_message = current_time - self.last_message_time[message.author.id]
            # Если прошло меньше 30 секунд, не начисляем опыт
            if time_since_last_message.total_seconds() < 30:
                return
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = message.author.id == int(supreme_ruler_id)
        
        # Проверяем, есть ли пользователь в базе
        user_data = await self.db.get_user_data(message.author.id)
        if not user_data:
            await self.db.create_user(message.author.id, message.guild.id)
        
        # Добавляем опыт за сообщение
        base_xp = random.randint(
            self.bot.config.get('xp_rewards', {}).get('message_range_min', 15),
            self.bot.config.get('xp_rewards', {}).get('message_range_max', 25)
        )
        
        # Если пользователь - верховный правитель, он получает бонус к опыту
        xp_gain = base_xp * 2 if is_supreme_ruler else base_xp
        
        await self.db.add_xp(message.author.id, xp_gain)
        
        # Обновляем время последнего сообщения
        self.last_message_time[message.author.id] = current_time
        
        # Проверяем, повысился ли уровень
        user_data = await self.db.get_user_data(message.author.id)
        level = user_data[3]
        xp = user_data[4]
        
        xp_needed = int((level + 1) ** 2 * 10)
        
        if xp >= xp_needed:
            # Повышение уровня
            await self.db.level_up(message.author.id)
            
            # Уведомление о повышении уровня
            new_level_data = await self.db.get_user_data(message.author.id)
            new_level = new_level_data[3]
            
            embed = discord.Embed(
                title="📈 Повышение уровня!",
                description=f"{message.author.mention}, поздравляем! Вы достигли **уровня {new_level}**!",
                color=0x00FF00
            )
            
            # Если пользователь - верховный правитель, добавляем специальное сообщение
            if is_supreme_ruler:
                embed.add_field(
                    name="Специальная награда",
                    value="Как **Верховный Правитель**, вы получаете двойной опыт!",
                    inline=False
                )
            
            # Проверяем, нужно ли обновить роль
            if self.bot.config.get('autorank_enabled', True):
                rank_order = [
                    "Новичок", "Рекрут", "Штурмовик", "Офицер", "Капитан", 
                    "Майор", "Подполковник", "Полковник", "Генерал", "Маршал", "Император"
                ]
                
                current_rank = await self.db.get_user_rank(message.author.id)
                if not current_rank:
                    current_rank = "Новичок"
                
                if current_rank != "Император":  # не повышаем выше максимального ранга
                    current_index = rank_order.index(current_rank) if current_rank in rank_order else 0
                    target_index = min(len(rank_order) - 1, new_level // 5)  # каждые 5 уровней - новый ранг
                    
                    if target_index > current_index:
                        new_rank = rank_order[target_index]
                        await self.db.set_user_rank(message.author.id, new_rank)
                        
                        embed.add_field(
                            name="🎖️ Новый ранг",
                            value=f"Вы были произведены в звание: **{new_rank}**",
                            inline=False
                        )
            
            await message.channel.send(embed=embed)

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(LevelsCog(bot, db))