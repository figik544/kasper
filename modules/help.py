import discord
from discord.ext import commands
from discord import app_commands
import json

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.categories = {
            'moderation': ['ban', 'kick', 'mute', 'warn', 'unwarn', 'warnings', 'clear'],
            'economy': ['balance', 'daily', 'transfer', 'shop', 'buy', 'inventory', 'use', 'trade', 'givecredits'],
            'levels': ['profile', 'leaderboard', 'rankup', 'setrank'],
            'rpg': ['duel', 'quest', 'char_create'],
            'star_wars': ['faction', 'imperial_motto', 'imperial_hierarchy', 'lightsaber_color', 'force_ability', 'galactic_fact', 'battle_simulator'],
            'government': ['set_supreme_ruler', 'add_chancellor', 'remove_chancellor', 'set_minister', 'remove_minister', 'gov_info', 'change_government'],
            'advertising': ['enable_ads', 'disable_ads', 'set_ad_message', 'ad_info'],
            'other': ['about', 'setup_imperial_server']
        }

    @commands.hybrid_command(name='help', description='Показывает список команд или информацию о конкретном модуле')
    @app_commands.describe(module_name='Название модуля для получения информации')
    async def help(self, ctx, module_name: str = None):
        """Показывает список команд или информацию о конкретном модуле"""
        if module_name:
            await self.show_module_help(ctx, module_name.lower())
        else:
            await self.show_all_help(ctx)

    async def show_all_help(self, ctx):
        # Загружаем конфиг для проверки, является ли пользователь верховным правителем
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        is_supreme_ruler = ctx.author.id == int(supreme_ruler_id)
        
        embed = discord.Embed(
            title="📚 Помощь - Галактический Имперский Бот",
            description="Команды бота сгруппированы по категориям:" + 
                       ("\n\n👑 Вы являетесь Верховным Правителем Федерации Галактической Империи!" if is_supreme_ruler else ""),
            color=0xFFD700
        )

        for category, commands_list in self.categories.items():
            if commands_list:
                commands_str = ", ".join([f"`{cmd}`" for cmd in commands_list])
                embed.add_field(
                    name=f"{category.title()}",
                    value=commands_str,
                    inline=False
                )

        embed.set_footer(text="Используйте !help <название_модуля> для получения информации о конкретной категории")
        await ctx.send(embed=embed)

    async def show_module_help(self, ctx, module_name):
        if module_name in self.categories:
            commands_list = self.categories[module_name]
            commands_str = ", ".join([f"`{cmd}`" for cmd in commands_list])
            
            embed = discord.Embed(
                title=f"📚 {module_name.title()} команды",
                description=f"Команды в категории {module_name}: {commands_str}",
                color=0xFFD700
            )
            
            # Добавляем информацию о правах доступа для government команд
            if module_name == 'government':
                embed.add_field(
                    name="Права доступа",
                    value="Команды правительства доступны:\n"
                          "- Владельцу бота\n"
                          "- Верховному правителю (yochin0837)\n"
                          "- Администраторам сервера\n"
                          "- Канцлерам правительства",
                    inline=False
                )
            elif module_name == 'moderation':
                embed.add_field(
                    name="Права доступа",
                    value="Команды модерации доступны:\n"
                          "- Администраторам сервера\n"
                          "- Верховному правителю (yochin0837)",
                    inline=False
                )
            elif module_name == 'economy':
                embed.add_field(
                    name="Особенности для Верховного Правителя",
                    value="Верховный правитель получает:\n"
                          "- Двойную ежедневную награду\n"
                          "- Возможность бесплатных покупок\n"
                          "- Увеличенные награды за задания\n"
                          "- Специальные транзакции",
                    inline=False
                )
            elif module_name == 'levels':
                embed.add_field(
                    name="Особенности для Верховного Правителя",
                    value="Верховный правитель получает:\n"
                          "- Двойной опыт за сообщения\n"
                          "- Ускоренное повышение рангов\n"
                          "- Специальные награды",
                    inline=False
                )
            elif module_name == 'rpg':
                embed.add_field(
                    name="Особенности для Верховного Правителя",
                    value="Верховный правитель получает:\n"
                          "- Усиленные характеристики персонажа\n"
                          "- Повышенные шансы на победу в дуэлях\n"
                          "- Увеличенные награды за задания",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Категория `{module_name}` не найдена. Используйте `!help` для просмотра всех категорий.")

    @commands.hybrid_command(name='about', description='Информация о боте')
    async def about(self, ctx):
        """Информация о боте"""
        # Загружаем конфиг для получения информации о верховном правителе
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        supreme_ruler = self.bot.get_user(int(supreme_ruler_id)) if supreme_ruler_id else None
        
        embed = discord.Embed(
            title="🤖 Галактический Имперский Бот",
            description="Комплексный Discord бот с тематикой Звёздных Войн, авторитарной политикой, РП-элементами, экономической системой и системой уровней.",
            color=0xFFD700
        )
        embed.add_field(name="_creators_", value="Создатель: yochin0837", inline=False)
        if supreme_ruler:
            embed.add_field(name="верховный правитель", value=f"{supreme_ruler.mention} (Дарт Вейдер)", inline=True)
        embed.add_field(name="version", value="1.0", inline=True)
        embed.add_field(name="server_count", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="user_count", value=len(self.bot.users), inline=True)
        embed.set_footer(text="Служим Империи с 2026 года")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='setup_imperial_server', description='Настройка сервера в стиле Империи')
    async def setup_imperial_server(self, ctx):
        """Настройка сервера в стиле Империи"""
        guild = ctx.guild
        
        # Создание ролей Империи
        imperial_roles = [
            ("Император", 0x000000),
            ("Лорд ситхов", 0xAA0000),
            ("Генерал Империи", 0x333333),
            ("Офицер Империи", 0x666666),
            ("Штурмовик", 0x999999),
            ("Рекрут", 0xCCCCCC)
        ]
        
        for role_name, color in imperial_roles:
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                await guild.create_role(name=role_name, color=discord.Color(color))
        
        # Создание каналов
        imperial_categories = [
            "Имперская Команда",
            "Общий Штаб",
            "Штурмовые Батальоны",
            "Гражданские Дела"
        ]
        
        for cat_name in imperial_categories:
            existing_cat = discord.utils.get(guild.categories, name=cat_name)
            if not existing_cat:
                await guild.create_category(cat_name)
        
        await ctx.send("✅ Настройка сервера в стиле Империи завершена!")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))