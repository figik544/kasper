import discord
from discord.ext import commands
from discord import app_commands
import random
import json

class StarWarsCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.hybrid_command(name='faction', description='Показывает информацию о фракциях в Галактике')
    async def faction(self, ctx):
        """Показывает информацию о фракциях в Галактике"""
        factions = {
            "Империя": {
                "description": "Авторитарное государство, контролирующее большую часть галактики. Основана на принципах порядка, контроля и подчинения.",
                "leader": "Император Палпатин",
                "colors": ["#000000", "#333333", "#666666"],
                "ships": ["Звёздный Разрушитель", "TIE-истребитель", "Супер Звезда Смерти"]
            },
            "Республика": {
                "description": "Демократическое государство, существовавшее до прихода Империи. Была основана на принципах справедливости и равенства.",
                "leader": "Сенат Галактики",
                "colors": ["#0000FF", "#00FFFF", "#FFFFFF"],
                "ships": ["Корабль-республиканец", "Джедайский истребитель", "Корвет"]
            },
            "Повстанцы": {
                "description": "Альянс, борющийся за свободу галактики от имперской тирании. Ценности: свобода, демократия, справедливость.",
                "leader": "Мон Мотма",
                "colors": ["#FF0000", "#FFD700", "#FFFFFF"],
                "ships": ["X-wing", "Y-wing", "Миллениум Фалкон"]
            },
            "Джедаи": {
                "description": "Древний орден, следящий за балансом Силы. Используют световые мечи и силу для поддержания мира.",
                "leader": "Высший совет Джедаев",
                "colors": ["#0000FF", "#00FF00", "#FFFFFF"],
                "ships": ["Джедайский звездолёт", "Корабль Джедаев", "Истребитель А-кинь"]
            },
            "Ситх": {
                "description": "Темный орден, стремящийся к власти через Силу. Противоположность Джедаев, ценят силу и подчинение.",
                "leader": "Повелитель ситхов",
                "colors": ["#AA0000", "#000000", "#8B0000"],
                "ships": ["Звёздный Разрушитель ситхов", "TIE-истребитель тьмы", "Корабль ситхов"]
            }
        }
        
        embed = discord.Embed(
            title="🌌 Фракции Галактики",
            description="Основные фракции, влияющие на судьбу галактики",
            color=0xFFD700
        )
        
        for name, info in factions.items():
            embed.add_field(
                name=name,
                value=f"**Лидер:** {info['leader']}\n"
                      f"**Описание:** {info['description']}\n"
                      f"**Цвета:** {' '.join(info['colors'])}\n"
                      f"**Корабли:** {', '.join(info['ships'])}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='imperial_motto', description='Показывает имперский лозунг')
    async def imperial_motto(self, ctx):
        """Показывает имперский лозунг"""
        mottos = [
            "«Мир через власть»",
            "«Порядок через контроль»",
            "«Единство через подчинение»",
            "«Сила через дисциплину»",
            "«Безопасность через власть»",
            "«Стабильность через страх»"
        ]
        
        motto = random.choice(mottos)
        
        embed = discord.Embed(
            title=" Imperium 🏛️",
            description=motto,
            color=0x000000
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='imperial_hierarchy', description='Показывает имперскую иерархию')
    async def imperial_hierarchy(self, ctx):
        """Показывает имперскую иерархию"""
        # Загружаем конфиг для получения информации о верховном правителе
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        supreme_ruler = self.bot.get_user(int(supreme_ruler_id)) if supreme_ruler_id else None
        
        hierarchy = [
            ("Император", "Палпатин", "Высшая власть в Галактике"),
        ]
        
        # Добавляем верховного правителя если он назначен
        if supreme_ruler:
            hierarchy.insert(1, (f"Верховный Правитель (Дарт Вейдер)", supreme_ruler.display_name, "Высшая исполнительная власть в Федерации Галактической Империи"))
        else:
            hierarchy.insert(1, ("Верховный Правитель (Дарт Вейдер)", "-", "Высшая исполнительная власть в Федерации Галактической Империи"))
        
        hierarchy.extend([
            ("Лорды ситхов", "Вейдер, Молл", "Темные повелители Силы"),
            ("Гранд-Мафф", "Тиа", "Высшие администраторы Империи"),
            ("Адмиралы", "Тиа, Вейтерс", "Командование флотом"),
            ("Генералы", "Медон, Кенник", "Командование армией"),
            ("Офицеры", "-", "Управление операциями"),
            ("Штурмовики", "-", "Пехота Империи"),
            ("Разведчики", "-", "Специальные операции")
        ])
        
        embed = discord.Embed(
            title="🏛️ Имперская Иерархия",
            description="Структура власти в Галактической Империи",
            color=0x333333
        )
        
        for position, notable_figures, description in hierarchy:
            embed.add_field(
                name=position,
                value=f"**Известные представители:** {notable_figures}\n"
                      f"**Функции:** {description}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='lightsaber_color', description='Определение цвета светового меча по типу персонажа')
    async def lightsaber_color(self, ctx):
        """Определение цвета светового меча по типу персонажа"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        colors = {
            "джедай": ["синий", "зелёный", "фиолетовый", "белый"],
            "ситх": ["красный", "оранжевый", "фиолетовый"],
            "инквизитор": ["красный", "красный с двумя клинками"],
            "мастер джедай": ["синий", "зелёный", "золотой"],
            "лорд ситхов": ["красный", "чёрный", "фиолетовый"]
        }
        
        # Определяем тип персонажа пользователя на основе его ранга
        user_rank = await self.db.get_user_rank(ctx.author.id)
        if not user_rank:
            user_rank = "джедай"  # по умолчанию
        
        user_rank_lower = user_rank.lower()
        available_colors = []
        
        for rank_type, colors_list in colors.items():
            if rank_type in user_rank_lower:
                available_colors.extend(colors_list)
                break
        
        if not available_colors:
            # Если не нашли соответствие, выбираем из всех цветов джедая
            available_colors = colors["джедай"]
        
        # Если пользователь - верховный правитель, он может использовать особый цвет
        if is_supreme_ruler:
            available_colors.append("чёрный")  # Особый цвет для верховного правителя
        
        chosen_color = random.choice(available_colors)
        
        embed = discord.Embed(
            title="⚔️ Цвет светового меча",
            description=f"{ctx.author.mention}, ваш световой меч имеет цвет: **{chosen_color}**",
            color=self.get_color_hex(chosen_color)
        )
        
        if is_supreme_ruler:
            embed.set_footer(text="Как Верховный Правитель, вы имеете доступ к особому цвету светового меча")
        
        await ctx.send(embed=embed)

    def get_color_hex(self, color_name):
        """Возвращает HEX-код цвета по названию"""
        color_map = {
            "синий": 0x0000FF,
            "зелёный": 0x00FF00,
            "красный": 0xFF0000,
            "фиолетовый": 0x800080,
            "белый": 0xFFFFFF,
            "оранжевый": 0xFFA500,
            "чёрный": 0x000000,
            "золотой": 0xFFD700
        }
        return color_map.get(color_name.lower(), 0xFFFFFF)

    @commands.hybrid_command(name='force_ability', description='Показывает случайную способность Силы')
    async def force_ability(self, ctx):
        """Показывает случайную способность Силы"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        abilities = [
            ("Телекинез", "Перемещение объектов с помощью Силы", "Джедаи, Ситх"),
            ("Телепатия", "Общение на расстоянии", "Джедаи"),
            ("Предвидение", "Видение будущего", "Джедаи, Ситх"),
            ("Ментальный контроль", "Влияние на сознание других", "Ситх"),
            ("Целительство", "Лечение ран и болезней", "Джедаи"),
            ("Молния", "Атака электрическими разрядами", "Ситх"),
            ("Удушье", "Атака Силой", "Ситх"),
            ("Щит", "Защита от атак", "Джедаи"),
            ("Прыжок", "Сверхчеловеческие прыжки", "Джедаи, Ситх"),
            ("Скорость", "Сверхчеловеческая скорость", "Джедаи, Ситх")
        ]
        
        ability = random.choice(abilities)
        name, description, users = ability
        
        embed = discord.Embed(
            title="🌟 Способность Силы",
            description=f"**{name}**\n{description}\n*Используется: {users}*",
            color=0x00FFFF
        )
        
        # Если пользователь - верховный правитель, добавляем специальное сообщение
        if is_supreme_ruler:
            embed.set_footer(text="Как Верховный Правитель, вы обладаете особым могуществом в Силе")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='galactic_fact', description='Показывает интересный факт о галактике')
    async def galactic_fact(self, ctx):
        """Показывает интересный факт о галактике"""
        facts = [
            "Галактика состоит из более чем 200 миллиардов звёзд.",
            "Империя контролирует более 1 миллиона планетных систем.",
            "Световой меч требует кристалл силы для своей работы.",
            "Джедаи используют светлую сторону Силы, а ситх - тёмную.",
            "Звёздные Разрушители могут достигать длины до 12 километров.",
            "Имперские штурмовики обучены на планете Камдайн.",
            "Самая быстрая скорость в гиперпространстве - фактор 1.",
            "Силу невозможно измерить стандартными приборами.",
            "Каждый световой меч уникален и создаётся своим владельцем.",
            "Империя затратила более 1 триллиона кредитов на создание Звезды Смерти."
        ]
        
        fact = random.choice(facts)
        
        embed = discord.Embed(
            title="📚 Галактический Факт",
            description=fact,
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='battle_simulator', description='Симуляция битвы между двумя фракциями')
    @app_commands.describe(faction1='Первая фракция', faction2='Вторая фракция')
    async def battle_simulator(self, ctx, faction1: str, faction2: str):
        """Симуляция битвы между двумя фракциями"""
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        factions = {
            "империя": {"strength": 90, "defense": 85, "technology": 95},
            "повстанцы": {"strength": 70, "defense": 75, "technology": 65},
            "джедаи": {"strength": 80, "defense": 85, "force": 100},
            "ситх": {"strength": 85, "defense": 75, "force": 95},
            "республика": {"strength": 75, "defense": 80, "technology": 85}
        }
        
        faction1_lower = faction1.lower()
        faction2_lower = faction2.lower()
        
        if faction1_lower not in factions or faction2_lower not in factions:
            await ctx.send("❌ Одна или обе фракции не найдены! Используйте: Империя, Повстанцы, Джедаи, Ситх, Республика")
            return
        
        # Симуляция битвы
        faction1_stats = factions[faction1_lower]
        faction2_stats = factions[faction2_lower]
        
        # Расчет силы каждой стороны
        faction1_power = (
            faction1_stats["strength"] + 
            faction1_stats["defense"] + 
            faction1_stats.get("technology", 0) + 
            faction1_stats.get("force", 0)
        )
        
        faction2_power = (
            faction2_stats["strength"] + 
            faction2_stats["defense"] + 
            faction2_stats.get("technology", 0) + 
            faction2_stats.get("force", 0)
        )
        
        # Добавляем бонус верховному правителю
        if is_supreme_ruler:
            faction1_power = int(faction1_power * 1.2) if faction1_lower == "империя" or faction1_lower == "ситх" else faction1_power
            faction2_power = int(faction2_power * 1.2) if faction2_lower == "империя" or faction2_lower == "ситх" else faction2_power
        
        # Добавляем немного рандома
        faction1_power += random.randint(-20, 20)
        faction2_power += random.randint(-20, 20)
        
        embed = discord.Embed(
            title="⚔️ Симуляция Битвы",
            description=f"{faction1.capitalize()} против {faction2.capitalize()}",
            color=0xFF0000
        )
        
        embed.add_field(
            name=f"{faction1.capitalize()}",
            value=f"Сила: {faction1_power}",
            inline=True
        )
        
        embed.add_field(
            name=f"{faction2.capitalize()}",
            value=f"Сила: {faction2_power}",
            inline=True
        )
        
        winner = faction1 if faction1_power > faction2_power else faction2
        loser = faction2 if winner == faction1 else faction1
        
        embed.add_field(
            name="🏆 Победитель",
            value=f"{winner.capitalize()}!",
            inline=False
        )
        
        # Если верховный правитель участвует в симуляции, добавляем специальное сообщение
        if is_supreme_ruler and ("империя" in [faction1_lower, faction2_lower] or "ситх" in [faction1_lower, faction2_lower]):
            embed.set_footer(text="Как Верховный Правитель, ваша сила удвоена в битвах за Империю или Ситхов")
        
        await ctx.send(embed=embed)

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(StarWarsCog(bot, db))