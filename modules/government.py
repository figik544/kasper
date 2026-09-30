import discord
from discord.ext import commands
from discord import app_commands
import json

class GovernmentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_supreme_ruler(self, user_id):
        """Проверка, является ли пользователь верховным правителем"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return str(user_id) == config['government_structure']['supreme_ruler']
        except:
            return False

    def is_supreme_ruler_or_admin(self, ctx):
        """Проверка, является ли пользователь верховным правителем или администратором"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        chancellors = config['government_structure']['chancellery']
        
        is_supreme = ctx.author.id == int(supreme_ruler_id)
        is_chancellor = str(ctx.author.id) in chancellors
        is_admin = ctx.author.guild_permissions.administrator
        
        return is_supreme or is_admin or is_chancellor

    @commands.hybrid_command(name='set_supreme_ruler', description='Установить верховного правителя (только для владельца бота)')
    @app_commands.describe(user='Пользователь для назначения верховным правителем')
    @commands.is_owner()
    async def set_supreme_ruler(self, ctx, user: discord.User):
        """Установить верховного правителя (только для владельца бота)"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Обновляем верховного правителя
        config['government_structure']['supreme_ruler'] = str(user.id)
        
        # Сохраняем изменения
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="👑 Назначение Верховного Правителя",
            description=f"{user.mention} назначен Верховным Правителем Федерации Галактической Империи!",
            color=0xFFFF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='add_chancellor', description='Добавить канцлера в правительство')
    @app_commands.describe(user='Пользователь для назначения канцлером')
    async def add_chancellor(self, ctx, user: discord.User):
        """Добавить канцлера в правительство"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Проверяем, не является ли пользователь уже канцлером
        chancellors = config['government_structure']['chancellery']
        if str(user.id) in chancellors:
            await ctx.send(f"{user.mention} уже является канцлером!")
            return
        
        # Добавляем пользователя в список канцлеров
        chancellors.append(str(user.id))
        
        # Сохраняем изменения
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="🏛️ Назначение Канцлера",
            description=f"{user.mention} назначен Канцлером Федерации Галактической Империи!",
            color=0x00FFFF
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='remove_chancellor', description='Удалить канцлера из правительства')
    @app_commands.describe(user='Пользователь для удаления из канцлеров')
    async def remove_chancellor(self, ctx, user: discord.User):
        """Удалить канцлера из правительства"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Удаляем пользователя из списка канцлеров
        chancellors = config['government_structure']['chancellery']
        if str(user.id) not in chancellors:
            await ctx.send(f"{user.mention} не является канцлером!")
            return
        
        chancellors.remove(str(user.id))
        
        # Сохраняем изменения
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="❌ Удаление Канцлера",
            description=f"{user.mention} удален из Канцлеров Федерации Галактической Империи!",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='set_minister', description='Назначить министра в ведомство')
    @app_commands.describe(ministry='Название ведомства', user='Пользователь для назначения министром')
    async def set_minister(self, ctx, ministry: str, user: discord.User):
        """Назначить министра в ведомство"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Обновляем структуру министерств
        ministries = config['government_structure']['ministries']
        ministries[ministry] = str(user.id)
        
        # Сохраняем изменения
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="🏛️ Назначение Министра",
            description=f"{user.mention} назначен Министром {ministry} Федерации Галактической Империи!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='remove_minister', description='Удалить министра из ведомства')
    @app_commands.describe(ministry='Название ведомства')
    async def remove_minister(self, ctx, ministry: str):
        """Удалить министра из ведомства"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Удаляем министерство
        ministries = config['government_structure']['ministries']
        if ministry not in ministries:
            await ctx.send(f"Министерство '{ministry}' не найдено!")
            return
        
        del ministries[ministry]
        
        # Сохраняем изменения
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="❌ Удаление Министра",
            description=f"Министерство {ministry} удалено из Правительства Федерации Галактической Империи!",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='gov_info', description='Показать структуру правительства')
    async def gov_info(self, ctx):
        """Показать структуру правительства"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        gov_struct = config['government_structure']
        
        supreme_ruler_id = gov_struct['supreme_ruler']
        supreme_ruler = self.bot.get_user(int(supreme_ruler_id)) if supreme_ruler_id else None
        
        chancellors = []
        for chancellor_id in gov_struct['chancellery']:
            chancellor = self.bot.get_user(int(chancellor_id))
            if chancellor:
                chancellors.append(chancellor.mention)
        
        ministries = []
        for ministry, minister_id in gov_struct['ministries'].items():
            minister = self.bot.get_user(int(minister_id))
            minister_mention = minister.mention if minister else f"<@{minister_id}>"
            ministries.append(f"{ministry}: {minister_mention}")
        
        embed = discord.Embed(
            title="🏛️ Структура Правительства Федерации Галактической Империи",
            color=0xFFD700
        )
        
        if supreme_ruler:
            embed.add_field(
                name="👑 Верховный Правитель",
                value=supreme_ruler.mention,
                inline=False
            )
        else:
            embed.add_field(
                name="👑 Верховный Правитель",
                value="Не назначен",
                inline=False
            )
        
        if chancellors:
            embed.add_field(
                name="🏛️ Канцелярия",
                value="\n".join(chancellors),
                inline=False
            )
        
        if ministries:
            embed.add_field(
                name="🏢 Министерства",
                value="\n".join(ministries),
                inline=False
            )
        
        if not chancellors and not ministries:
            embed.add_field(
                name="ℹ️ Информация",
                value="Правительство пока не сформировано",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='change_government', description='Команда для изменения структуры правительства')
    @app_commands.describe(action='Действие с правительством', target='Цель действия', user='Пользователь')
    async def change_government(self, ctx, action: str, target: str = None, user: discord.User = None):
        """Команда для изменения структуры правительства (владелец, верховный правитель и канцлеры)"""
        # Загружаем текущую конфигурацию
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        chancellors = config['government_structure']['chancellery']
        
        # Проверяем права
        is_authorized = (ctx.author.id == self.bot.owner_id or 
                         ctx.author.id == int(supreme_ruler_id) or 
                         str(ctx.author.id) in chancellors or
                         ctx.author.guild_permissions.administrator)
        
        if not is_authorized:
            await ctx.send("❌ У вас нет прав для изменения структуры правительства!")
            return
        
        if action.lower() == 'add_chancellor':
            if not user:
                await ctx.send("❌ Укажите пользователя для назначения канцлером!")
                return
            
            if str(user.id) in chancellors:
                await ctx.send(f"{user.mention} уже является канцлером!")
                return
            
            chancellors.append(str(user.id))
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="🏛️ Назначение Канцлера",
                description=f"{user.mention} назначен Канцлером Федерации Галактической Империи!",
                color=0x00FFFF
            )
            await ctx.send(embed=embed)
        
        elif action.lower() == 'remove_chancellor':
            if not user:
                await ctx.send("❌ Укажите пользователя для удаления из канцлеров!")
                return
            
            if str(user.id) not in chancellors:
                await ctx.send(f"{user.mention} не является канцлером!")
                return
            
            chancellors.remove(str(user.id))
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="❌ Удаление Канцлера",
                description=f"{user.mention} удален из Канцлеров Федерации Галактической Империи!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
        
        elif action.lower() == 'set_minister':
            if not target or not user:
                await ctx.send("❌ Укажите ведомство и пользователя для назначения министром!")
                return
            
            ministries = config['government_structure']['ministries']
            ministries[target] = str(user.id)
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="🏛️ Назначение Министра",
                description=f"{user.mention} назначен Министром {target} Федерации Галактической Империи!",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
        
        elif action.lower() == 'remove_minister':
            if not target:
                await ctx.send("❌ Укажите ведомство для удаления министра!")
                return
            
            ministries = config['government_structure']['ministries']
            if target not in ministries:
                await ctx.send(f"Министерство '{target}' не найдено!")
                return
            
            del ministries[target]
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            embed = discord.Embed(
                title="❌ Удаление Министра",
                description=f"Министерство {target} удалено из Правительства Федерации Галактической Империи!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
        
        else:
            await ctx.send("❌ Недопустимое действие! Используйте: add_chancellor, remove_chancellor, set_minister, remove_minister")

    @commands.hybrid_command(name='declare_emergency', description='Объявить чрезвычайное положение (только для верховного правителя)')
    async def declare_emergency(self, ctx):
        """Объявить чрезвычайное положение (только для верховного правителя)"""
        if not self.is_supreme_ruler(ctx.author.id):
            await ctx.send("❌ Только **Верховный Правитель Федерации Галактической Империи** может объявить чрезвычайное положение!")
            return
        
        embed = discord.Embed(
            title="🚨 ЧРЕЗВЫЧАЙНОЕ ПОЛОЖЕНИЕ ОБЪЯВЛЕНО!",
            description=f"**Верховный Правитель** {ctx.author.mention} объявил чрезвычайное положение на территории Федерации Галактической Империи!\n\n"
                       f"Все обычные ограничения на сервере временно отменены для обеспечения безопасности Империи.",
            color=0xFF0000
        )
        embed.set_footer(text="Чрезвычайное положение будет действовать до отмены Верховным Правителем")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='revoke_emergency', description='Отменить чрезвычайное положение (только для верховного правителя)')
    async def revoke_emergency(self, ctx):
        """Отменить чрезвычайное положение (только для верховного правителя)"""
        if not self.is_supreme_ruler(ctx.author.id):
            await ctx.send("❌ Только **Верховный Правитель Федерации Галактической Империи** может отменить чрезвычайное положение!")
            return
        
        embed = discord.Embed(
            title="✅ ЧРЕЗВЫЧАЙНОЕ ПОЛОЖЕНИЕ ОТМЕНЕНО",
            description=f"**Верховный Правитель** {ctx.author.mention} отменил чрезвычайное положение на территории Федерации Галактической Империи!",
            color=0x00FF00
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='imperial_decree', description='Издать императорский указ (только для верховного правителя)')
    @app_commands.describe(decree_text='Текст указа')
    async def imperial_decree(self, ctx, decree_text: str):
        """Издать императорский указ (только для верховного правителя)"""
        if not self.is_supreme_ruler(ctx.author.id):
            await ctx.send("❌ Только **Верховный Правитель Федерации Галактической Империи** может издавать императорские указы!")
            return
        
        embed = discord.Embed(
            title="📜 ИМПЕРАТОРСКИЙ УКАЗ",
            description=f"**Верховный Правитель** {ctx.author.mention} издал императорский указ:\n\n**{decree_text}**",
            color=0x800080
        )
        embed.set_footer(text="Императорский указ вступает в силу немедленно")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GovernmentCog(bot))