import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime
import aiosqlite
import json

from .database import get_user_data, add_credits, get_user_credits, get_guild_config, update_guild_config

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

class StarWarsCog(commands.Cog, name="Звёздные Войны"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='faction')
    async def show_faction(self, ctx):
        """Показывает информацию о фракциях в Галактике"""
        embed = discord.Embed(
            title="Фракции Галактической Империи",
            color=0x000000
        )
        embed.add_field(
            name="Империя",
            value="Верховная власть в галактике. Основана Палпатином для установления порядка.\n"
                  "Лидеры: Император, Тёмные Лорды, Верховное Командование",
            inline=False
        )
        embed.add_field(
            name="Повстанцы",
            value="Оппозиционная организация, борющаяся за свободу галактики.\n"
                  "Лидеры: Лидеры Альянса, Командиры повстанческих клеток",
            inline=False
        )
        embed.add_field(
            name="Джедаи",
            value="Хранители мира и справедливости в галактике.\n"
                  "Лидеры: Совет Джедаев, Мастера Джедаи",
            inline=False
        )
        embed.add_field(
            name="Ситхи",
            value="Последователи темной стороны Силы.\n"
                  "Лидеры: Тёмные Лорды Ситхов",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='lightsaber_color')
    async def lightsaber_color(self, ctx):
        """Определение цвета светового меча по типу персонажа"""
        colors = {
            "джедай": ["синий", "зелёный", "фиолетовый", "белый"],
            "ситх": ["красный"],
            "инквизитор": ["красный", "красный двойной клинок"],
            "джедай-скрытый": ["жёлтый"]
        }
        
        user_data = await get_user_data(ctx.author.id, ctx.guild.id)
        if user_data and 'rank' in user_data:
            rank = user_data['rank'].lower()
            if 'джедай' in rank:
                color = random.choice(colors['джедай'])
            elif 'ситх' in rank or 'тёмный лорд' in rank:
                color = random.choice(colors['ситх'])
            elif 'инквизитор' in rank:
                color = random.choice(colors['инквизитор'])
            else:
                color = random.choice(colors['джедай'] + colors['ситх'])
        else:
            color = random.choice(colors['джедай'])
        
        embed = discord.Embed(
            title="Цвет светового меча",
            description=f"{ctx.author.mention}, ваш световой меч светится {color} цветом!",
            color=self.get_color_by_name(color)
        )
        await ctx.send(embed=embed)

    def get_color_by_name(self, color_name):
        """Возвращает цвет Discord по названию"""
        colors_map = {
            "синий": 0x0000FF,
            "зелёный": 0x00FF00,
            "красный": 0xFF0000,
            "фиолетовый": 0x800080,
            "белый": 0xFFFFFF,
            "жёлтый": 0xFFFF00,
            "красный двойной клинок": 0xCC0000
        }
        return colors_map.get(color_name.lower(), 0x000000)

    @commands.command(name='imperial_hierarchy')
    async def imperial_hierarchy(self, ctx):
        """Показывает имперскую иерархию"""
        embed = discord.Embed(
            title="Имперская Иерархия",
            description="Структура власти в Галактической Империи",
            color=0x000000
        )
        hierarchy = [
            ("Император", "Верховный правитель всей Империи"),
            ("Тёмный Лорд", "Мощный пользователь темной стороны"),
            ("Адмирал", "Командование флотом"),
            ("Генерал", "Командование армией"),
            ("Полковник", "Командование полком"),
            ("Майор", "Старший офицер"),
            ("Капитан", "Командир роты"),
            ("Лейтенант", "Младший офицер"),
            ("Сержант", "Старшина"),
            ("Корпорал", "Младший сержант"),
            ("Штурмовик", "Базовый солдат"),
            ("Рекрут", "Новичок")
        ]
        
        for rank, description in hierarchy:
            embed.add_field(name=rank, value=description, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='galactic_fact')
    async def galactic_fact(self, ctx):
        """Показывает интересный факт о галактике"""
        facts = [
            "Галактика состоит из более чем 1000 секторов.",
            "Империя контролирует более 1 миллиона планет.",
            "Каждый год в галактике происходит около 10000 звёздных сражений.",
            "Световые мечи используют кристаллы силы для фокусировки энергии.",
            "Имперские штурмовики проходят обучение на планете Камдайн.",
            "Куай-Хен - это форма жизни, способная влиять на Силу.",
            "Гиперпространственные прыжки возможны благодаря навигационным компьютерам.",
            "Самый известный пилот истребителей TIE - Ас Траппера.",
            "Кореллианский бегун - самый быстрый корабль в галактике.",
            "Двуствольные бластеры были изобретены ещё до основания Республики."
        ]
        
        fact = random.choice(facts)
        
        embed = discord.Embed(
            title="Факт о Галактике",
            description=fact,
            color=0x4B0082
        )
        await ctx.send(embed=embed)

    @commands.command(name='battle_simulator')
    async def battle_simulator(self, ctx, faction1: str, faction2: str):
        """Симуляция битвы между двумя фракциями"""
        factions = {
            "империя": {"power": 90, "defense": 85, "speed": 70},
            "повстанцы": {"power": 75, "defense": 70, "speed": 85},
            "джедаи": {"power": 80, "defense": 80, "speed": 80},
            "ситх": {"power": 95, "defense": 70, "speed": 85}
        }
        
        f1 = faction1.lower()
        f2 = faction2.lower()
        
        if f1 not in factions or f2 not in factions:
            embed = discord.Embed(
                title="Неверная фракция",
                description="Доступные фракции: Империя, Повстанцы, Джедаи, Ситх",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return
        
        # Симуляция битвы
        f1_stats = factions[f1]
        f2_stats = factions[f2]
        
        # Расчет результатов
        f1_score = (f1_stats['power'] * 0.4) + (f1_stats['defense'] * 0.3) + (f1_stats['speed'] * 0.3)
        f2_score = (f2_stats['power'] * 0.4) + (f2_stats['defense'] * 0.3) + (f2_stats['speed'] * 0.3)
        
        # Добавляем немного случайности
        f1_score += random.randint(-10, 10)
        f2_score += random.randint(-10, 10)
        
        embed = discord.Embed(
            title=f"Симуляция битвы: {faction1.title()} vs {faction2.title()}",
            color=0xFF4500
        )
        
        if f1_score > f2_score:
            winner = faction1.title()
            loser = faction2.title()
        else:
            winner = faction2.title()
            loser = faction1.title()
        
        embed.add_field(name="Победитель", value=winner, inline=False)
        embed.add_field(name="Результаты", 
                       value=f"{faction1.title()}: {round(f1_score)} очков\n"
                             f"{faction2.title()}: {round(f2_score)} очков", 
                       inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='force_ability')
    async def force_ability(self, ctx):
        """Показывает случайную способность Силы"""
        abilities = [
            ("Телекинез", "Перемещение объектов силой мысли"),
            ("Телепатия", "Общение на расстоянии"),
            ("Предвидение", "Видение будущего"),
            ("Иллюзия", "Создание ложных образов"),
            ("Ментальный контроль", "Влияние на разум других"),
            ("Лечение", "Восстановление здоровья"),
            ("Молния", "Разрушительная атака темной стороны"),
            ("Щит", "Защита от атак"),
            ("Ускорение", "Повышение скорости движений"),
            ("Прозрение", "Видение истинной природы вещей")
        ]
        
        ability, description = random.choice(abilities)
        
        embed = discord.Embed(
            title="Способность Силы",
            description=f"**{ability}**\n{description}",
            color=0x9370DB
        )
        await ctx.send(embed=embed)

    @commands.command(name='imperial_motto')
    async def imperial_motto(self, ctx):
        """Показывает имперский лозунг"""
        mottoes = [
            "Порядок через силу",
            "Единство через контроль", 
            "Стабильность через власть",
            "Мир через господство",
            "Сила через преданность"
        ]
        
        motto = random.choice(mottoes)
        
        embed = discord.Embed(
            title="Имперский Лозунг",
            description=f"\"{motto}\"",
            color=0x2F4F4F
        )
        await ctx.send(embed=embed)

    @commands.command(name='setup_imperial_server')
    @commands.has_permissions(administrator=True)
    async def setup_imperial_server(self, ctx):
        """Настройка сервера в стиле Империи"""
        # Создание тематических ролей
        sw_roles = [
            ("Император", 0x111111),
            ("Тёмный Лорд", 0x222222),
            ("Адмирал", 0x333333),
            ("Генерал", 0x444444),
            ("Полковник", 0x555555),
            ("Майор", 0x666666),
            ("Капитан", 0x777777),
            ("Лейтенант", 0x888888),
            ("Сержант", 0x999999),
            ("Корпорал", 0xAAAAAA),
            ("Штурмовик", 0xCCCCCC),
            ("Рекрут", 0xFFFFFF),
            ("Мофф", 0x4B0082),
            ("Инквизитор", 0x800000),
            ("Пилот ТА", 0x696969),
            ("Имперский Офицер", 0x708090),
            ("Имперский Гвардеец", 0xDC143C),
            ("Королевский Гвардеец", 0xB22222),
            ("Повелитель Ситхов", 0x8B0000),
            ("Охотник за Джедаями", 0x2F4F4F),
            ("Имперский Шпион", 0x228B22)
        ]
        
        created_roles = []
        for role_name, color in sw_roles:
            existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not existing_role:
                role = await ctx.guild.create_role(
                    name=role_name,
                    color=discord.Color(color),
                    reason="Имперская тематическая роль"
                )
                created_roles.append(role_name)
        
        # Создание тематических каналов
        categories = {
            " имперская военная": [
                "центр-командования",
                "развертывание-войск",
                "военный-архив"
            ],
            " галактическая политика": [
                "сенат-империи",
                "бюро-пропаганды",
                "зал-совета"
            ],
            " имперская социальная": [
                "коридор",
                "зал-почёта",
                "голо-театр"
            ],
            " имперская команда": [
                "имперская-команда",
                "журнал-безопасности",
                "тронный-зал-императора"
            ]
        }
        
        created_channels = []
        for cat_name, channels in categories.items():
            category = await ctx.guild.create_category(cat_name)
            for ch_name in channels:
                if "голос" in ch_name or "зал" in ch_name:
                    channel = await ctx.guild.create_voice_channel(ch_name, category=category)
                else:
                    channel = await ctx.guild.create_text_channel(ch_name, category=category)
                created_channels.append(channel.name)
        
        # Обновляем конфигурацию сервера
        await update_guild_config(ctx.guild.id, autorank_enabled=True, economy_enabled=True)
        
        embed = discord.Embed(
            title="Сервер настроен в стиле Империи!",
            description=f"Создано {len(created_roles)} ролей и {len(created_channels)} каналов",
            color=0x000000
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StarWarsCog(bot))