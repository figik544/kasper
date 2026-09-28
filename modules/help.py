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

    def command_listing(self):
        prefix = config.get('default_prefix', '!')
        lines = []
        for command in sorted(self.bot.commands, key=lambda item: item.name):
            if command.hidden:
                continue
            usage = f"{prefix}{command.qualified_name}"
            if command.signature:
                usage = f"{usage} {command.signature}"
            description = command.short_doc or "Команда бота"
            lines.append(f"`{usage}` — {description}")
        return "\n".join(lines)

    @commands.command(name='help')
    async def help_command(self, ctx, module_name: str = None):
        """Показывает список команд или информацию о конкретном модуле"""
        if module_name is None:
            # Показываем общую помощь
            embed = discord.Embed(
                title="Помощь - Галактический Имперский Бот",
                description=self.command_listing(),
                color=0x000000
            )
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