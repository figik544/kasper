import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime, timedelta

class EconomyCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.hybrid_command(name='balance', description='Проверка баланса кредитов')
    @app_commands.describe(member='Пользователь для проверки баланса')
    async def balance(self, ctx, member: discord.Member = None):
        """Проверка баланса кредитов"""
        if not member:
            member = ctx.author
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = member.id == int(supreme_ruler_id)
        
        balance = await self.db.get_balance(member.id)
        
        embed = discord.Embed(
            title=f"💰 Баланс {member.display_name}",
            description=f"Кредитов: **{balance}**",
            color=0x00FF00
        )
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.add_field(
                name="Статус",
                value="👑 **Верховный Правитель Федерации Галактической Империи**",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='daily', description='Ежедневная награда')
    async def daily(self, ctx):
        """Ежедневная награда"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        user_id = ctx.author.id
        last_daily = await self.db.get_last_daily(user_id)
        
        if last_daily:
            last_daily_time = datetime.fromisoformat(last_daily)
            time_diff = datetime.now() - last_daily_time
            
            if time_diff.days < 1:
                remaining_time = timedelta(days=1) - time_diff
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏳ Ежедневная награда",
                    description=f"Вы уже получали ежедневную награду!\nСледующая награда через: **{hours}ч {minutes}м**",
                    color=0xFFA500
                )
                await ctx.send(embed=embed)
                return
        
        # Награда за ежедневный вход
        min_credits = self.bot.config.get('daily_rewards', {}).get('min_credits', 50)
        max_credits = self.bot.config.get('daily_rewards', {}).get('max_credits', 150)
        reward = random.randint(min_credits, max_credits)
        
        # Если пользователь - верховный правитель, он получает бонус к награде
        if is_supreme_ruler:
            reward = int(reward * 2)  # Двойная награда для верховного правителя
        
        await self.db.add_credits(user_id, reward)
        await self.db.set_last_daily(user_id)
        
        embed = discord.Embed(
            title="🎁 Ежедневная награда",
            description=f"Вы получили **{reward}** кредитов!" + (" (Бонус для **Верховного Правителя**!)" if is_supreme_ruler else ""),
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='transfer', description='Перевод кредитов другому пользователю')
    @app_commands.describe(member='Пользователь для перевода', amount='Количество кредитов')
    async def transfer(self, ctx, member: discord.Member, amount: int):
        """Перевод кредитов другому пользователю"""
        if member.id == ctx.author.id:
            await ctx.send("❌ Вы не можете переводить кредиты самому себе!")
            return
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        sender_balance = await self.db.get_balance(ctx.author.id)
        
        # Если пользователь - верховный правитель, он может переводить больше, чем у него есть
        if is_supreme_ruler:
            # Верховный правитель может создавать кредиты для перевода
            await self.db.add_credits(ctx.author.id, amount)
            await self.db.add_credits(ctx.author.id, -amount)  # компенсируем для корректного баланса
            await self.db.add_credits(member.id, amount)
            
            embed = discord.Embed(
                title="💸 Специальный перевод",
                description=f"**Верховный Правитель** {ctx.author.mention} перевел **{amount}** кредитов {member.mention}",
                color=0xFFD700
            )
            await ctx.send(embed=embed)
            return
        
        if sender_balance < amount:
            await ctx.send("❌ У вас недостаточно кредитов для перевода!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Количество кредитов должно быть больше 0!")
            return
        
        await self.db.add_credits(ctx.author.id, -amount)
        await self.db.add_credits(member.id, amount)
        
        embed = discord.Embed(
            title="💸 Перевод",
            description=f"{ctx.author.mention} перевел **{amount}** кредитов {member.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='shop', description='Отображение имперского рынка')
    async def shop(self, ctx):
        """Отображение имперского рынка"""
        items = await self.db.get_shop_items()
        
        if not items:
            # Добавляем стандартные товары в магазин
            default_items = [
                ("🔫 Имперский Бластер", 500, "Стандартное оружие Империи"),
                ("⚔️ Элитный Меч", 1000, "Особое оружие для элитных войск"),
                ("🛡️ Имперский Щит", 750, "Защитное оборудование"),
                ("🔋 Энергетический Щит", 300, "Дополнительная защита"),
                ("🎯 Прицел Снайпера", 400, "Улучшает точность стрельбы"),
                ("⚡ Турбо-Заряд", 200, "Ускоряет перезарядку оружия"),
                ("🎭 Маска Дарта Вейдера", 1500, "Легендарная маска"),
                ("🔮 Сфера Предсказаний", 2000, "Помогает предвидеть будущее"),
                ("📜 Карта Галактики", 600, "Показывает расположение планет"),
                ("👑 Имперская Корона", 3000, "Символ высшей власти")
            ]
            
            for item_name, price, description in default_items:
                await self.db.add_item_to_shop(item_name, price, description)
            
            items = await self.db.get_shop_items()
        
        embed = discord.Embed(
            title="🛒 Имперский Рынок",
            description="Добро пожаловать на **Имперский Рынок**! Здесь вы можете приобрести различные товары за кредиты.",
            color=0xFFD700
        )
        
        for item in items:
            embed.add_field(
                name=f"{item[1]} - **{item[2]}** кредитов",
                value=item[3],
                inline=False
            )
        
        embed.set_footer(text="Используйте команду !buy <название_предмета> для покупки")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='buy', description='Покупка предмета из магазина')
    @app_commands.describe(item_name='Название предмета для покупки')
    async def buy(self, ctx, *, item_name: str):
        """Покупка предмета из магазина"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        item = await self.db.get_item_by_name(item_name)
        if not item:
            await ctx.send(f"❌ Предмет '{item_name}' не найден в магазине!")
            return
        
        price = item[2]
        
        # Если пользователь - верховный правитель, он может купить любой предмет бесплатно
        if is_supreme_ruler:
            await self.db.add_item_to_inventory(ctx.author.id, item[0])  # item[0] - это id предмета
            
            embed = discord.Embed(
                title="👑 Специальная покупка",
                description=f"**Верховный Правитель** {ctx.author.mention} получил **{item[1]}** бесплатно!",
                color=0xFFFF00
            )
            await ctx.send(embed=embed)
            return
        
        user_balance = await self.db.get_balance(ctx.author.id)
        
        if user_balance < price:
            await ctx.send(f"❌ У вас недостаточно кредитов! Необходимо **{price}**, у вас **{user_balance}**")
            return
        
        await self.db.add_credits(ctx.author.id, -price)
        await self.db.add_item_to_inventory(ctx.author.id, item[0])  # item[0] - это id предмета
        
        embed = discord.Embed(
            title="✅ Покупка успешна",
            description=f"Вы купили **{item[1]}** за **{price}** кредитов!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='inventory', description='Просмотр инвентаря пользователя')
    @app_commands.describe(member='Пользователь для просмотра инвентаря')
    async def inventory(self, ctx, member: discord.Member = None):
        """Просмотр инвентаря пользователя"""
        if not member:
            member = ctx.author
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = member.id == int(supreme_ruler_id)
        
        inventory = await self.db.get_inventory(member.id)
        
        if not inventory:
            embed = discord.Embed(
                title=f"🎒 Инвентарь {member.display_name}",
                description="Инвентарь пуст",
                color=0xFFA500
            )
        else:
            embed = discord.Embed(
                title=f"🎒 Инвентарь {member.display_name}",
                description="Ваши предметы:",
                color=0x00FF00
            )
            
            for item in inventory:
                item_details = await self.db.get_item_by_id(item[1])  # item[1] - это item_id
                if item_details:
                    embed.add_field(
                        name=f"**{item_details[1]}**",  # название предмета
                        value=item_details[3],  # описание предмета
                        inline=False
                    )
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.add_field(
                name="Статус",
                value="👑 **Верховный Правитель Федерации Галактической Империи**",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='use', description='Использование предмета из инвентаря')
    @app_commands.describe(item_name='Название предмета для использования')
    async def use(self, ctx, *, item_name: str):
        """Использование предмета из инвентаря"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        item = await self.db.get_item_by_name(item_name)
        if not item:
            await ctx.send(f"❌ Предмет '{item_name}' не найден!")
            return
        
        user_inventory = await self.db.get_inventory(ctx.author.id)
        item_exists = any(inv_item[1] == item[0] for inv_item in user_inventory)  # item[0] - это id предмета
        
        # Если пользователь - верховный правитель, он может использовать любой предмет
        if is_supreme_ruler or item_exists:
            # В зависимости от типа предмета выполняем разные действия
            item_effects = {
                "🔫 Имперский Бластер": "💥 Вы использовали **Имперский Бластер**!",
                "⚔️ Элитный Меч": "⚔️ Вы взмахнули **Элитным Мечом**!",
                "🛡️ Имперский Щит": "🛡️ Вы активировали **Имперский Щит**!",
                "🎭 Маска Дарта Вейдера": "~-~- Вы надели **Маску Дарта Вейдера**!"
            }
            
            effect = item_effects.get(item[1], f"✨ Вы использовали **{item[1]}**!")
            
            embed = discord.Embed(
                title="✨ Использование предмета",
                description=effect,
                color=0x00FF00
            )
            
            # Если пользователь - верховный правитель, добавляем специальное сообщение
            if is_supreme_ruler:
                embed.add_field(
                    name="Специальное использование",
                    value="Как **Верховный Правитель**, вы можете использовать любой предмет!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ У вас нет предмета '{item_name}' в инвентаре!")

    @commands.hybrid_command(name='trade', description='Обмен предметами с другим участником')
    @app_commands.describe(member='Пользователь для обмена', item_name='Название предмета для передачи', quantity='Количество предметов')
    async def trade(self, ctx, member: discord.Member, *, item_name: str, quantity: int = 1):
        """Обмен предметами с другим участником"""
        if member.id == ctx.author.id:
            await ctx.send("❌ Вы не можете обмениваться с самим собой!")
            return
        
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        item = await self.db.get_item_by_name(item_name)
        if not item:
            await ctx.send(f"❌ Предмет '{item_name}' не найден!")
            return
        
        user_inventory = await self.db.get_inventory(ctx.author.id)
        user_item_count = sum(1 for inv_item in user_inventory if inv_item[1] == item[0])
        
        # Если пользователь - верховный правитель, он может торговать любым количеством предметов
        if is_supreme_ruler:
            # Верховный правитель может создавать предметы для торговли
            for _ in range(quantity):
                await self.db.add_item_to_inventory(member.id, item[0])
            
            embed = discord.Embed(
                title="🔄 Специальный обмен",
                description=f"**Верховный Правитель** {ctx.author.mention} передал **{quantity} шт.** {item[1]} пользователю {member.mention}",
                color=0xFFD700
            )
            await ctx.send(embed=embed)
            return
        
        if user_item_count < quantity:
            await ctx.send(f"❌ У вас недостаточно предметов '{item_name}'! У вас **{user_item_count}**, нужно **{quantity}**")
            return
        
        # Удаляем предметы у отправителя и добавляем получателю
        for _ in range(quantity):
            await self.db.remove_item_from_inventory(ctx.author.id, item[0])
            await self.db.add_item_to_inventory(member.id, item[0])
        
        embed = discord.Embed(
            title="🔄 Обмен",
            description=f"{ctx.author.mention} передал **{quantity} шт.** {item[1]} пользователю {member.mention}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='givecredits', description='Выдача кредитов пользователю (только для администраторов)')
    @app_commands.describe(member='Пользователь для выдачи кредитов', amount='Количество кредитов')
    @commands.check(lambda ctx: ctx.author.guild_permissions.administrator or 
                   ctx.author.id == int(json.load(open('config.json', 'r', encoding='utf-8'))['government_structure']['supreme_ruler']))
    async def givecredits(self, ctx, member: discord.Member, amount: int):
        """Выдача кредитов пользователю (только для администраторов)"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        # Проверяем права
        if not (ctx.author.guild_permissions.administrator or is_supreme_ruler):
            await ctx.send("❌ У вас нет прав для выполнения этой команды!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Количество кредитов должно быть больше 0!")
            return
        
        await self.db.add_credits(member.id, amount)
        
        embed = discord.Embed(
            title="💳 Выдача кредитов",
            description=f"{ctx.author.mention} выдал **{amount}** кредитов пользователю {member.mention}",
            color=0x00FF00
        )
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.set_footer(text="Выделено Верховным Правителем Федерации Галактической Империи")
        
        await ctx.send(embed=embed)

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(EconomyCog(bot, db))