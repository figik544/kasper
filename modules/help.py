import discord
from discord.ext import commands
import asyncio
import json

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class HelpCog(commands.Cog, name="Помощь"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_command(self, ctx, module_name: str = None):
        """Показывает список команд или информацию о конкретном модуле"""
        if module_name is None:
            # Показываем общую помощь
            embed = discord.Embed(
                title="Помощь - Галактический Имперский Бот",
                description="Команды, доступные для служения Империи",
                color=0x000000
            )
            
            embed.add_field(name="!profile [@user]", value="Просмотр профиля пользователя с его статистикой", inline=False)
            embed.add_field(name="!leaderboard", value="Просмотр топа Имперских офицеров", inline=False)
            embed.add_field(name="!daily", value="Получить ежедневную награду", inline=False)
            embed.add_field(name="!balance [@user]", value="Проверить баланс кредитов", inline=False)
            embed.add_field(name="!rankup", value="Попытаться получить более высокий ранг", inline=False)
            embed.add_field(name="!shop", value="Просмотреть имперский рынок", inline=False)
            embed.add_field(name="!buy [item]", value="Купить предметы за кредиты", inline=False)
            embed.add_field(name="!inventory [@user]", value="Просмотреть инвентарь", inline=False)
            embed.add_field(name="!faction", value="Информация о фракциях в галактике", inline=False)
            embed.add_field(name="!lightsaber_color", value="Определить цвет светового меча", inline=False)
            embed.add_field(name="!imperial_hierarchy", value="Показать имперскую иерархию", inline=False)
            embed.add_field(name="!galactic_fact", value="Интересный факт о галактике", inline=False)
            
            if ctx.author.guild_permissions.administrator:
                embed.add_field(name="АДМИН КОМАНДЫ:", value=" ", inline=False)
                embed.add_field(name="!ban @user [reason]", value="Заблокировать пользователя", inline=False)
                embed.add_field(name="!kick @user [reason]", value="Выгнать пользователя", inline=False)
                embed.add_field(name="!mute @user [time]", value="Замутить пользователя", inline=False)
                embed.add_field(name="!warn @user [reason]", value="Выдать предупреждение", inline=False)
                embed.add_field(name="!clear [num]", value="Очистить сообщения", inline=False)
                embed.add_field(name="!setrank @user [rank]", value="Установить ранг пользователю", inline=False)
                embed.add_field(name="!givecredits @user [amount]", value="Выдать кредиты", inline=False)
                embed.add_field(name="!setup_imperial_server", value="Настроить сервер в стиле Империи", inline=False)
            
            embed.add_field(name="!help [module]", value="Показать помощь по конкретному модулю", inline=False)
            
            await ctx.send(embed=embed)
        else:
            # Показываем помощь по конкретному модулю
            modules_help = {
                'moderation': {
                    'title': 'Модуль модерации',
                    'description': 'Инструменты для поддержания порядка на сервере',
                    'commands': [
                        ('!ban @user [reason]', 'Заблокировать пользователя'),
                        ('!kick @user [reason]', 'Выгнать пользователя'),
                        ('!mute @user [time]', 'Замутить пользователя на время'),
                        ('!warn @user [reason]', 'Выдать предупреждение'),
                        ('!clear [num]', 'Очистить указанное количество сообщений'),
                        ('!warnings @user', 'Показать количество предупреждений пользователя'),
                        ('!unwarn @user', 'Сбросить предупреждения пользователя')
                    ]
                },
                'economy': {
                    'title': 'Экономический модуль',
                    'description': 'Система кредитов и магазин',
                    'commands': [
                        ('!balance [@user]', 'Проверить баланс кредитов'),
                        ('!daily', 'Получить ежедневную награду'),
                        ('!shop', 'Просмотреть имперский рынок'),
                        ('!buy [item]', 'Купить предмет'),
                        ('!inventory [@user]', 'Просмотреть инвентарь'),
                        ('!transfer @user [amount]', 'Перевести кредиты другому пользователю'),
                        ('!givecredits @user [amount]', 'Выдать кредиты (админ)')
                    ]
                },
                'levels': {
                    'title': 'Модуль уровней',
                    'description': 'Система опыта, уровней и рангов',
                    'commands': [
                        ('!profile [@user]', 'Просмотр профиля с XP и рангом'),
                        ('!leaderboard', 'Таблица лидеров по уровню'),
                        ('!rankup', 'Попытаться получить более высокий ранг'),
                        ('!setrank @user [rank]', 'Установить ранг пользователю (админ)')
                    ]
                },
                'rpg': {
                    'title': 'РП модуль',
                    'description': 'Ролевые элементы и мини-игры',
                    'commands': [
                        ('!char_create [class]', 'Создать персонажа с классом'),
                        ('!duel @user', 'Вызвать пользователя на дуэль'),
                        ('!quest', 'Получить задание'),
                        ('!trade @user [item] [quantity]', 'Предложить обмен пользователю'),
                        ('!use [item]', 'Использовать предмет из инвентаря')
                    ]
                },
                'star_wars': {
                    'title': 'Звёздные Войны модуль',
                    'description': 'Тематические элементы вселенной Звёздных Войн',
                    'commands': [
                        ('!faction', 'Информация о фракциях'),
                        ('!lightsaber_color', 'Цвет светового меча'),
                        ('!imperial_hierarchy', 'Имперская иерархия'),
                        ('!galactic_fact', 'Факт о галактике'),
                        ('!battle_simulator [faction1] [faction2]', 'Симуляция битвы'),
                        ('!force_ability', 'Способность Силы'),
                        ('!imperial_motto', 'Имперский лозунг'),
                        ('!setup_imperial_server', 'Настроить сервер в стиле Империи')
                    ]
                }
            }
            
            if module_name.lower() in modules_help:
                module_info = modules_help[module_name.lower()]
                
                embed = discord.Embed(
                    title=module_info['title'],
                    description=module_info['description'],
                    color=0x0000FF
                )
                
                for cmd, desc in module_info['commands']:
                    embed.add_field(name=cmd, value=desc, inline=False)
                
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Модуль не найден",
                    description=f"Модуль '{module_name}' не существует. Используйте !help для просмотра всех модулей.",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)

    @commands.command(name='about')
    async def about_command(self, ctx):
        """Информация о боте"""
        embed = discord.Embed(
            title="О Галактическом Имперском Боте",
            description="Комплексный бот для сервера в тематике Звёздных Войн с элементами авторитарной политики",
            color=0x8B0000
        )
        embed.add_field(name="Владелец", value="Галактическая Империя", inline=True)
        embed.add_field(name="Тематика", value="Звёздные Войны + Авторитаризм", inline=True)
        embed.add_field(name="Функции", value="Модерация, РП, Экономика, Уровни", inline=True)
        embed.add_field(
            name="Описание", 
            value="Этот бот обеспечивает порядок на сервере, следит за спамом, "
                  "предлагает РП-элементы, экономическую систему и продвинутую "
                  "систему уровней с тематикой Звёздных Войн.",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))