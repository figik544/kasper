import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime
import aiosqlite
import json

from .database import add_credits, get_user_credits, get_shop_items, buy_item, get_user_inventory

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class EconomyCog(commands.Cog, name="Экономика"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='balance')
    async def balance(self, ctx, member: discord.Member = None):
        """Проверка баланса кредитов"""
        if member is None:
            member = ctx.author

        credits = await get_user_credits(member.id, ctx.guild.id)

        embed = discord.Embed(
            title="Баланс кредитов",
            description=f"{member.display_name} имеет {credits} кредитов",
            color=0x00FFFF
        )
        await ctx.send(embed=embed)

    @commands.command(name='daily')
    async def daily_reward(self, ctx):
        """Ежедневная награда"""
        async with aiosqlite.connect('galactic_empire_bot.db') as db:
            async with db.execute("SELECT last_daily_claim FROM users WHERE user_id = ? AND guild_id = ?", 
                                 (ctx.author.id, ctx.guild.id)) as cursor:
                result = await cursor.fetchone()

        now = datetime.now()
        if result and result[0]:
            try:
                last_claim = datetime.fromisoformat(result[0])
                if (now - last_claim).days < 1:
                    hours_left = 24 - (now - last_claim).seconds // 3600
                    embed = discord.Embed(
                        title="Ежедневная награда",
                        description=f"Вы уже получили ежедневную награду. Попробуйте снова через {hours_left} часов.",
                        color=0xFF0000
                    )
                    await ctx.send(embed=embed)
                    return
            except ValueError:
                # Если формат даты неверный, продолжаем
                pass

        # Выдаем ежедневную награду
        reward = random.randint(config['daily_rewards']['min_credits'], config['daily_rewards']['max_credits'])
        new_balance = await add_credits(ctx.author.id, ctx.guild.id, reward)

        embed = discord.Embed(
            title="Ежедневная награда получена",
            description=f"Вы получили {reward} кредитов в качестве ежедневной лояльности!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='givecredits')
    @commands.has_permissions(administrator=True)
    async def give_credits(self, ctx, member: discord.Member, amount: int):
        """Выдача кредитов пользователю (только для администраторов)"""
        new_balance = await add_credits(member.id, ctx.guild.id, amount)

        embed = discord.Embed(
            title="Кредиты выданы",
            description=f"{amount} кредитов выдано пользователю {member.mention}. Новый баланс: {new_balance}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.command(name='shop')
    async def shop(self, ctx):
        """Отображение имперского рынка"""
        items = await get_shop_items()

        embed = discord.Embed(
            title=" имперский рынок",
            description="Предметы, доступные для покупки за Имперские кредиты",
            color=0x8B0000
        )

        for item_id, name, price, desc in items:
            embed.add_field(
                name=f"{name} - {price} кредитов",
                value=desc,
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='buy')
    async def buy_item_cmd(self, ctx, *, item_name):
        """Покупка предмета из магазина"""
        # Получаем все предметы из магазина
        items = await get_shop_items()
        
        # Находим совпадающий предмет
        target_item = None
        for item_id, name, price, desc in items:
            if item_name.lower() in name.lower():
                target_item = (item_id, name, price)
                break
        
        if not target_item:
            embed = discord.Embed(
                title="Предмет не найден",
                description=f"Не найдено предметов, соответствующих '{item_name}' в магазине.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        item_id, item_name, price = target_item
        
        success, message = await buy_item(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="Результат покупки" if success else "Ошибка покупки",
            description=message,
            color=0x00FF00 if success else 0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.command(name='inventory')
    async def inventory(self, ctx, member: discord.Member = None):
        """Просмотр инвентаря пользователя"""
        if member is None:
            member = ctx.author

        user_inventory = await get_user_inventory(member.id)

        if not user_inventory:
            embed = discord.Embed(
                title=f"Инвентарь {member.display_name}",
                description="Инвентарь пуст",
                color=0xFFFF00
            )
        else:
            embed = discord.Embed(
                title=f"Инвентарь {member.display_name}",
                color=0xFFFF00
            )
            for item_name, quantity in user_inventory:
                embed.add_field(
                    name=item_name,
                    value=f"Количество: {quantity}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.command(name='transfer')
    async def transfer_credits(self, ctx, member: discord.Member, amount: int):
        """Перевод кредитов другому пользователю"""
        if member.id == ctx.author.id:
            embed = discord.Embed(
                title="Невозможно перевести",
                description="Вы не можете перевести кредиты самому себе.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if amount <= 0:
            embed = discord.Embed(
                title="Неверная сумма",
                description="Сумма перевода должна быть больше 0.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        sender_credits = await get_user_credits(ctx.author.id, ctx.guild.id)

        if sender_credits < amount:
            embed = discord.Embed(
                title="Недостаточно средств",
                description=f"У вас недостаточно кредитов для перевода. Ваш баланс: {sender_credits}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        # Снимаем кредиты с отправителя
        await add_credits(ctx.author.id, ctx.guild.id, -amount)
        # Добавляем кредиты получателю
        recipient_new_balance = await add_credits(member.id, ctx.guild.id, amount)

        embed = discord.Embed(
            title="Перевод выполнен",
            description=f"{ctx.author.mention} перевел {amount} кредитов пользователю {member.mention}\nБаланс получателя: {recipient_new_balance}",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))