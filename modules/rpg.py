import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime, timedelta

class RPGCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.hybrid_command(name='duel', description='Вызов на дуэль другого участника')
    @app_commands.describe(opponent='Оппонент для дуэли')
    async def duel(self, ctx, opponent: discord.Member):
        """Вызов на дуэль другого участника"""
        if opponent.id == ctx.author.id:
            await ctx.send("❌ Вы не можете дуэлиться с самим собой!")
            return
        
        # Загружаем конфиг для проверки, является ли кто-то из участников верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_attacker_supreme = ctx.author.id == int(supreme_ruler_id)
        is_defender_supreme = opponent.id == int(supreme_ruler_id)
        
        # Проверяем, есть ли оба игрока в базе
        for user_id in [ctx.author.id, opponent.id]:
            user_data = await self.db.get_user_data(user_id)
            if not user_data:
                await self.db.create_user(user_id, ctx.guild.id)
        
        # Простая механика дуэли
        attacker_power = random.randint(1, 100) + await self.db.get_user_level(ctx.author.id)
        defender_power = random.randint(1, 100) + await self.db.get_user_level(opponent.id)
        
        # Если один из участников - верховный правитель, он получает бонус
        if is_attacker_supreme:
            attacker_power = int(attacker_power * 1.5)  # 50% бонус для верховного правителя
        if is_defender_supreme:
            defender_power = int(defender_power * 1.5)  # 50% бонус для верховного правителя
        
        embed = discord.Embed(
            title="⚔️ Дуэль",
            description=f"{ctx.author.mention} вызвал на дуэль {opponent.mention}!",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        
        await ctx.send("⏳ Подготовка к дуэли...")
        await ctx.send("💥 Дуэль началась!")
        
        # Симуляция боя
        await ctx.send(f"{ctx.author.display_name} атакует с силой {attacker_power}!" + (" (Сила Верховного Правителя!)" if is_attacker_supreme else ""))
        await ctx.send(f"{opponent.display_name} защищается с силой {defender_power}!" + (" (Сила Верховного Правителя!)" if is_defender_supreme else ""))
        
        winner = ctx.author if attacker_power > defender_power else opponent
        loser = opponent if winner == ctx.author else ctx.author
        
        # Определяем победителя с учетом статуса верховного правителя
        if is_attacker_supreme and is_defender_supreme:
            # Если оба - верховные правители, побеждает тот, у кого больше сила
            winner = ctx.author if attacker_power > defender_power else opponent
        elif is_attacker_supreme and not is_defender_supreme:
            # Если атакующий - верховный правитель, он получает преимущество
            if abs(attacker_power - defender_power) < 20:  # Если разница небольшая
                winner = ctx.author
        elif is_defender_supreme and not is_attacker_supreme:
            # Если защищающийся - верховный правитель, он получает преимущество
            if abs(attacker_power - defender_power) < 20:  # Если разница небольшая
                winner = opponent
        
        # Награда победителю
        reward = random.randint(50, 200)
        await self.db.add_credits(winner.id, reward)
        
        embed = discord.Embed(
            title="🏆 Результат дуэли",
            description=f"{winner.mention} побеждает над {loser.mention}!\n"
                       f"Победитель получает {reward} кредитов!",
            color=0x00FF00
        )
        
        # Если победитель - верховный правитель, добавляем специальное сообщение
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_winner_supreme = winner.id == int(supreme_ruler_id)
        
        if is_winner_supreme:
            embed.add_field(
                name="Специальная победа",
                value="Как Верховный Правитель, вы получаете усиленную награду!",
                inline=False
            )
            reward = int(reward * 1.5)  # Увеличенная награда
            await self.db.add_credits(winner.id, int(reward * 0.5))  # Дополнительно начисляем разницу
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='quest', description='Выполнение задания для получения награды')
    async def quest(self, ctx):
        """Выполнение задания для получения награды"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        user_id = ctx.author.id
        last_quest = await self.db.get_last_quest(user_id)
        
        if last_quest:
            last_quest_time = datetime.fromisoformat(last_quest)
            time_diff = datetime.now() - last_quest_time
            
            if time_diff.days < 1:
                remaining_time = timedelta(days=1) - time_diff
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏳ Задание",
                    description=f"Вы уже выполняли задание сегодня!\nСледующее задание через: {hours}ч {minutes}м",
                    color=0xFFA500
                )
                await ctx.send(embed=embed)
                return
        
        # Список возможных заданий
        quests = [
            ("Патрулирование системы", 150, "Проверить все каналы на наличие нарушений"),
            ("Сбор ресурсов", 200, "Собрать ресурсы для Империи"),
            ("Обучение новобранцев", 100, "Провести тренировку для новых рекрутов"),
            ("Разведка", 175, "Собрать информацию о противнике"),
            ("Поддержка порядка", 125, "Помочь в модерации сервера")
        ]
        
        quest = random.choice(quests)
        quest_name, base_reward, description = quest
        
        # Если пользователь - верховный правитель, он получает увеличенную награду
        reward = int(base_reward * 1.5) if is_supreme_ruler else base_reward
        
        embed = discord.Embed(
            title="🎯 Новое задание",
            description=f"**{quest_name}**\n{description}",
            color=0x00FFFF
        )
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.add_field(
                name="Специальное задание",
                value="Как Верховный Правитель, вы получаете повышенную награду!",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # Подтверждение выполнения задания
        await self.db.set_last_quest(user_id)
        await self.db.add_credits(user_id, reward)
        
        embed = discord.Embed(
            title="✅ Задание выполнено",
            description=f"Вы успешно выполнили задание '{quest_name}' и получили {reward} кредитов!" + 
                       (" (Бонус для Верховного Правителя!)" if is_supreme_ruler else ""),
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='char_create', description='Создание персонажа с определённым классом')
    @app_commands.describe(char_class='Класс персонажа')
    async def char_create(self, ctx, char_class: str):
        """Создание персонажа с определённым классом"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        user_id = ctx.author.id
        
        # Проверяем, есть ли уже персонаж у пользователя
        existing_char = await self.db.get_character(user_id)
        if existing_char:
            await ctx.send("❌ У вас уже есть персонаж!")
            return
        
        # Определяем характеристики на основе класса
        class_stats = {
            "джедай": {"сила": random.randint(60, 80), "ловкость": random.randint(70, 90), "интеллект": random.randint(80, 100)},
            "ситх": {"сила": random.randint(80, 100), "ловкость": random.randint(60, 80), "интеллект": random.randint(70, 90)},
            "штурмовик": {"сила": random.randint(50, 70), "ловкость": random.randint(50, 70), "интеллект": random.randint(40, 60)},
            "офицер": {"сила": random.randint(40, 60), "ловкость": random.randint(50, 70), "интеллект": random.randint(70, 90)},
            "техник": {"сила": random.randint(40, 60), "ловкость": random.randint(60, 80), "интеллект": random.randint(80, 100)}
        }
        
        char_class_lower = char_class.lower()
        if char_class_lower not in class_stats:
            await ctx.send(f"❌ Неверный класс персонажа! Доступные классы: {', '.join(class_stats.keys())}")
            return
        
        stats = class_stats[char_class_lower]
        
        # Если пользователь - верховный правитель, он получает усиленные характеристики
        if is_supreme_ruler:
            stats = {key: value + 20 for key, value in stats.items()}  # Увеличиваем все характеристики на 20
        
        # Создаем персонажа в базе данных
        await self.db.create_character(user_id, char_class, stats["сила"], stats["ловкость"], stats["интеллект"])
        
        embed = discord.Embed(
            title="👤 Создание персонажа",
            description=f"Персонаж успешно создан!",
            color=0x00FF00
        )
        embed.add_field(name="Класс", value=char_class.capitalize(), inline=False)
        embed.add_field(name="Сила", value=stats["сила"], inline=True)
        embed.add_field(name="Ловкость", value=stats["ловкость"], inline=True)
        embed.add_field(name="Интеллект", value=stats["интеллект"], inline=True)
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.add_field(
                name="Специальные способности",
                value="Как Верховный Правитель, ваш персонаж имеет усиленные характеристики!",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(RPGCog(bot, db))