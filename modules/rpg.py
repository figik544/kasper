import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime
import aiosqlite
import json

from .database import get_user_data, add_credits, get_user_credits, get_user_inventory

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class RPGRolesCog(commands.Cog, name="РП и Роли"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='char_create')
    async def create_character(self, ctx, *, char_class):
        """Создание персонажа с определённым классом"""
        user_data = await get_user_data(ctx.author.id, ctx.guild.id)
        
        if not user_data:
            embed = discord.Embed(
                title="Создание персонажа",
                description="Сначала необходимо создать профиль. Отправьте любое сообщение на сервере.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Здесь можно реализовать систему классов персонажей
        available_classes = ["джедай", "ситх", "штурмовик", "офицер", "повстанец", "дипломат"]
        
        if char_class.lower() not in available_classes:
            embed = discord.Embed(
                title="Неверный класс персонажа",
                description=f"Доступные классы: {', '.join(available_classes)}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Пример: начисление бонусных кредитов за создание персонажа
        bonus_credits = 100
        new_balance = await add_credits(ctx.author.id, ctx.guild.id, bonus_credits)

        embed = discord.Embed(
            title="Персонаж создан!",
            description=f"{ctx.author.mention}, вы стали {char_class.lower()}ом! Получено {bonus_credits} бонусных кредитов.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='duel')
    async def duel(self, ctx, opponent: discord.Member):
        """Вызов на дуэль другого участника"""
        if opponent.id == ctx.author.id:
            embed = discord.Embed(
                title="Невозможно вызвать на дуэль",
                description="Вы не можете вызвать на дуэль самого себя.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Вызов на дуэль",
            description=f"{ctx.author.mention} вызывает на дуэль {opponent.mention}! Реагируйте командой `!accept_duel`, чтобы принять вызов.",
            color=0xFFFF00
        )
        await ctx.send(embed=embed)

        # Ждем реакцию противника
        def check(m):
            return m.author.id == opponent.id and m.content.lower() == '!accept_duel' and m.channel.id == ctx.channel.id

        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Дуэль отменена",
                description=f"{opponent.mention} не ответил в течение 30 секунд. Дуэль отменена.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Начинаем дуэль
        embed = discord.Embed(
            title="Дуэль началась!",
            description=f"Дуэль между {ctx.author.mention} и {opponent.mention} начинается!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

        # Имитация дуэли
        player1_hp = 100
        player2_hp = 100

        while player1_hp > 0 and player2_hp > 0:
            # Атака первого игрока
            damage1 = random.randint(10, 30)
            player2_hp -= damage1
            player2_hp = max(0, player2_hp)  # Не меньше 0

            embed = discord.Embed(
                title="Ход дуэли",
                description=f"{ctx.author.display_name} атакует {opponent.display_name} и наносит {damage1} урона!\n"
                           f"{ctx.author.display_name}: {player1_hp}/100 HP\n{opponent.display_name}: {player2_hp}/100 HP",
                color=0xFFA500
            )
            await ctx.send(embed=embed)

            if player2_hp <= 0:
                winner = ctx.author
                loser = opponent
                break

            await asyncio.sleep(2)

            # Атака второго игрока
            damage2 = random.randint(10, 30)
            player1_hp -= damage2
            player1_hp = max(0, player1_hp)  # Не меньше 0

            embed = discord.Embed(
                title="Ход дуэли",
                description=f"{opponent.display_name} атакует {ctx.author.display_name} и наносит {damage2} урона!\n"
                           f"{ctx.author.display_name}: {player1_hp}/100 HP\n{opponent.display_name}: {player2_hp}/100 HP",
                color=0xFFA500
            )
            await ctx.send(embed=embed)

            if player1_hp <= 0:
                winner = opponent
                loser = ctx.author
                break

            await asyncio.sleep(2)

        # Определение победителя
        reward = random.randint(50, 150)
        new_balance = await add_credits(winner.id, ctx.guild.id, reward)

        embed = discord.Embed(
            title="Дуэль окончена!",
            description=f"{winner.mention} побеждает в дуэли против {loser.mention} и получает {reward} кредитов!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='quest')
    async def quest(self, ctx):
        """Выполнение задания для получения награды"""
        quests = [
            {"name": "Разведка вражеского флота", "difficulty": "лёгкое", "reward": 25},
            {"name": "Поиск древнего артефакта", "difficulty": "среднее", "reward": 50},
            {"name": "Спасти повстанческий корабль", "difficulty": "трудное", "reward": 100},
            {"name": "Уничтожить базу повстанцев", "difficulty": "очень трудное", "reward": 200}
        ]

        quest = random.choice(quests)
        difficulty_multiplier = {"лёгкое": 0.5, "среднее": 1, "трудное": 1.5, "очень трудное": 2}[quest["difficulty"]]
        success_chance = int(70 / difficulty_multiplier)  # Чем сложнее, тем меньше шанс успеха

        embed = discord.Embed(
            title="Получено задание",
            description=f"Задание: {quest['name']} (уровень сложности: {quest['difficulty']})\n"
                       f"Награда: {quest['reward']} кредитов\n"
                       f"Шанс успеха: {min(success_chance, 95)}%",
            color=0x00FFFF
        )
        await ctx.send(embed=embed)

        # Симуляция выполнения задания
        await asyncio.sleep(2)

        if random.randint(1, 100) <= min(success_chance, 95):
            reward = quest['reward']
            new_balance = await add_credits(ctx.author.id, ctx.guild.id, reward)

            embed = discord.Embed(
                title="Задание выполнено!",
                description=f"Вы успешно выполнили задание '{quest['name']}' и получили {reward} кредитов!",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="Задание провалено",
                description=f"Вам не удалось выполнить задание '{quest['name']}'. Попробуйте снова.",
                color=0xFF0000
            )

        await ctx.send(embed=embed)

    @commands.command(name='trade')
    async def trade_items(self, ctx, member: discord.Member, item_name: str, quantity: int = 1):
        """Обмен предметами с другим участником"""
        if member.id == ctx.author.id:
            embed = discord.Embed(
                title="Невозможно обменять",
                description="Вы не можете обменять предметы сами с собой.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if quantity <= 0:
            embed = discord.Embed(
                title="Неверное количество",
                description="Количество предметов должно быть больше 0.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Получаем инвентарь обоих участников
        author_inventory = await get_user_inventory(ctx.author.id)
        member_inventory = await get_user_inventory(member.id)

        # Проверяем, есть ли предмет у отправителя
        item_found = False
        for inv_item, inv_quantity in author_inventory:
            if item_name.lower() in inv_item.lower():
                if inv_quantity >= quantity:
                    item_found = True
                    item_actual_name = inv_item
                break

        if not item_found:
            embed = discord.Embed(
                title="Предмет не найден",
                description=f"У вас нет {quantity} шт. '{item_name}' для обмена.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Подтверждение обмена
        embed = discord.Embed(
            title="Запрос на обмен",
            description=f"{ctx.author.mention} предлагает {member.mention} обмен:\n"
                       f"{quantity} шт. '{item_actual_name}'",
            color=0xFFFF00
        )
        await ctx.send(embed=embed)

        # Ждем подтверждение
        def check(m):
            return m.author.id == member.id and m.content.lower() == '!accept_trade' and m.channel.id == ctx.channel.id

        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Обмен отменен",
                description=f"{member.mention} не ответил в течение 30 секунд. Обмен отменен.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Выполняем обмен
        # TODO: В реальной системе нужно реализовать логику перемещения предметов между инвентарями
        embed = discord.Embed(
            title="Обмен завершен!",
            description=f"Обмен между {ctx.author.mention} и {member.mention} завершен успешно!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='use')
    async def use_item(self, ctx, *, item_name):
        """Использование предмета из инвентаря"""
        user_inventory = await get_user_inventory(ctx.author.id)

        # Находим предмет в инвентаре
        item_found = False
        for inv_item, quantity in user_inventory:
            if item_name.lower() in inv_item.lower():
                item_found = True
                item_actual_name = inv_item
                break

        if not item_found:
            embed = discord.Embed(
                title="Предмет не найден",
                description=f"У вас нет '{item_name}' в инвентаре.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Эффекты использования предметов
        effects = {
            "меч джедая": f"{ctx.author.mention} использует Меч Джедая! Вы чувствуете прилив сил Светлой стороны.",
            "маска дарта вейдера": f"{ctx.author.mention} надевает Маску Дарта Вейдера! Вы излучаете ауру темной стороны.",
            "имперский шлем": f"{ctx.author.mention} надевает Имперский шлем! Вы чувствуете себя частью Империи.",
            "голокрон джедаев": f"{ctx.author.mention} активирует Голокрон Джедаев! Вы получаете мудрость древних.",
            "голокрон ситхов": f"{ctx.author.mention} активирует Голокрон Ситхов! Вы овладеваете новыми темными знаниями."
        }

        effect_message = effects.get(item_actual_name.lower(), f"{ctx.author.mention} использует {item_actual_name}!")

        embed = discord.Embed(
            title="Предмет использован",
            description=effect_message,
            color=0x9370DB
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RPGRolesCog(bot))