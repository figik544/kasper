import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
from datetime import datetime, timedelta
import aiosqlite
import random

class PoliticsCog(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.max_parties_per_server = 9
        self.max_party_members = 50
        self.max_level = 999
        self.voting_channel_name = "выборы"
        self.parliament_voice_channel_name = "парламент"
        self.parliament_text_channel_name = "голосование"
        self.supreme_ruler_id = "1551842724418822149"
        
        # Загрузка конфига
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.config = {}
    
    def is_supreme_ruler(self, user_id):
        """Проверка, является ли пользователь верховным правителем"""
        return str(user_id) == self.supreme_ruler_id
    
    def is_president(self, ctx):
        """Проверка, является ли пользователь президентом"""
        president_role = discord.utils.get(ctx.guild.roles, name="Президент")
        return president_role in ctx.author.roles if president_role else False
    
    def is_parliament_member(self, ctx):
        """Проверка, является ли пользователь членом парламента"""
        parliament_role = discord.utils.get(ctx.guild.roles, name="Член Парламента")
        return parliament_role in ctx.author.roles if parliament_role else False
    
    @commands.hybrid_command(name='setup_government', description='Настройка формы правления для сервера')
    @app_commands.describe(gov_type='Тип правительства (democracy/monarchy)')
    @commands.has_permissions(administrator=True)
    async def setup_government(self, ctx, gov_type: str):
        """Настройка формы правления для сервера"""
        if gov_type.lower() not in ['democracy', 'monarchy', 'authoritarian']:
            await ctx.send("❌ Неверный тип правительства! Используйте: democracy, monarchy, authoritarian")
            return
        
        # Сохраняем тип правительства для сервера
        await self.db.set_government_type(ctx.guild.id, gov_type.lower())
        
        embed = discord.Embed(
            title="🏛️ Форма правления установлена",
            description=f"Сервер теперь использует форму правления: **{gov_type.lower()}**\n"
                       f"Все последующие выборы будут проходить согласно этой системе.",
            color=0xFFD700
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='create_political_party', description='Создать политическую партию')
    @app_commands.describe(party_name='Название партии', party_description='Описание партии')
    async def create_political_party(self, ctx, party_name: str, party_description: str = ""):
        """Создать политическую партию (только для пользователей с высоким уровнем)"""
        user_data = await self.db.get_user_data(ctx.author.id)
        if not user_data:
            await self.db.create_user(ctx.author.id, ctx.guild.id)
            user_data = await self.db.get_user_data(ctx.author.id)
        
        level = user_data[3]
        
        # Проверяем уровень пользователя
        if level < 99 and not self.is_supreme_ruler(ctx.author.id):
            await ctx.send(f"❌ Для создания политической партии требуется уровень 99+. У вас уровень: {level}")
            return
        
        # Проверяем, не является ли пользователь уже лидером партии
        existing_party = await self.db.get_user_party(ctx.author.id, ctx.guild.id)
        if existing_party:
            await ctx.send("❌ Вы уже являетесь лидером политической партии!")
            return
        
        # Проверяем количество партий на сервере
        parties_count = await self.db.get_parties_count(ctx.guild.id)
        if parties_count >= self.max_parties_per_server:
            await ctx.send(f"❌ На сервере уже существует максимальное количество партий: {self.max_parties_per_server}")
            return
        
        # Создаем партию
        await self.db.create_political_party(ctx.guild.id, party_name, party_description, ctx.author.id)
        
        embed = discord.Embed(
            title="🏛️ Политическая партия создана",
            description=f"Партия **{party_name}** успешно создана!\n"
                       f"Лидер: {ctx.author.mention}\n"
                       f"Участники: 1/50",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='join_party', description='Присоединиться к политической партии')
    @app_commands.describe(party_name='Название партии')
    async def join_party(self, ctx, party_name: str):
        """Присоединиться к политической партии"""
        party = await self.db.get_party_by_name(ctx.guild.id, party_name)
        if not party:
            await ctx.send(f"❌ Партия '{party_name}' не найдена!")
            return
        
        # Проверяем, не является ли пользователь уже членом партии
        user_party = await self.db.get_user_party(ctx.author.id, ctx.guild.id)
        if user_party:
            await ctx.send("❌ Вы уже состоите в политической партии!")
            return
        
        # Проверяем количество участников в партии
        members_count = await self.db.get_party_members_count(party[0])  # party[0] - id партии
        if members_count >= self.max_party_members:
            await ctx.send(f"❌ Партия '{party_name}' уже набрала максимальное количество участников: {self.max_party_members}")
            return
        
        # Присоединяем пользователя к партии
        await self.db.add_user_to_party(ctx.author.id, party[0])
        
        embed = discord.Embed(
            title="🏛️ Присоединение к партии",
            description=f"{ctx.author.mention} присоединился к партии **{party_name}**!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='leave_party', description='Покинуть политическую партию')
    async def leave_party(self, ctx):
        """Покинуть политическую партию"""
        user_party = await self.db.get_user_party(ctx.author.id, ctx.guild.id)
        if not user_party:
            await ctx.send("❌ Вы не состоите ни в одной политической партии!")
            return
        
        # Проверяем, является ли пользователь лидером партии
        if user_party[4] == ctx.author.id:  # user_party[4] - leader_id
            members_count = await self.db.get_party_members_count(user_party[0])
            if members_count > 1:
                await ctx.send("❌ Вы являетесь лидером партии. Сначала передайте лидерство или покиньте партию как лидер.")
                return
            else:
                # Если лидер единственный член партии, удаляем партию
                await self.db.delete_party(user_party[0])
                embed = discord.Embed(
                    title="🏛️ Партия распущена",
                    description=f"Партия **{user_party[1]}** была распущена, так как лидер покинул её.",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
                return
        
        # Удаляем пользователя из партии
        await self.db.remove_user_from_party(ctx.author.id, user_party[0])
        
        embed = discord.Embed(
            title="🏛️ Выход из партии",
            description=f"{ctx.author.mention} покинул партию **{user_party[1]}**.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='parties_list', description='Список всех политических партий на сервере')
    async def parties_list(self, ctx):
        """Список всех политических партий на сервере"""
        parties = await self.db.get_server_parties(ctx.guild.id)
        
        if not parties:
            await ctx.send("📋 На сервере пока нет политических партий.")
            return
        
        embed = discord.Embed(
            title="🏛️ Политические партии сервера",
            color=0xFFD700
        )
        
        for party in parties:
            members_count = await self.db.get_party_members_count(party[0])  # party[0] - id партии
            embed.add_field(
                name=f"{party[1]} (ID: {party[0]})",
                value=f"Описание: {party[2]}\n"
                     f"Лидер: <@{party[4]}>\n"
                     f"Участников: {members_count}/50",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='election_campaign', description='Начать предвыборную кампанию')
    @app_commands.describe(election_type='Тип выборов (presidential/parliamentary)', start_date='Дата начала кампании (YYYY-MM-DD)', end_date='Дата окончания кампании (YYYY-MM-DD)')
    @commands.has_permissions(administrator=True)
    async def election_campaign(self, ctx, election_type: str, start_date: str, end_date: str):
        """Начать предвыборную кампанию до назначенной даты выборов"""
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Неверный формат даты! Используйте формат YYYY-MM-DD")
            return
        
        if election_type.lower() not in ['presidential', 'parliamentary']:
            await ctx.send("❌ Неверный тип выборов! Используйте: presidential, parliamentary")
            return
        
        if end_datetime <= start_datetime:
            await ctx.send("❌ Дата окончания кампании должна быть позже даты начала!")
            return
        
        # Сохраняем данные о предвыборной кампании
        await self.db.schedule_election_campaign(ctx.guild.id, election_type.lower(), start_datetime.isoformat(), end_datetime.isoformat())
        
        # Создаем канал для предвыборной кампании, если его нет
        campaign_channel_name = f"предвыборная-кампания-{election_type.lower()}"
        campaign_channel = discord.utils.get(ctx.guild.text_channels, name=campaign_channel_name)
        
        if not campaign_channel:
            campaign_channel = await ctx.guild.create_text_channel(
                campaign_channel_name,
                topic=f"Канал для предвыборной кампании по {election_type.lower()} выборам"
            )
        
        embed = discord.Embed(
            title="선거️ Предвыборная кампания объявлена",
            description=f"Предвыборная кампания по **{election_type.lower()}** выборам начата!\n"
                       f"Дата начала: **{start_date}**\n"
                       f"Дата окончания: **{end_date}**\n"
                       f"Канал кампании: {campaign_channel.mention}\n\n"
                       f"Кандидаты могут рекламировать себя, публиковать программы и взаимодействовать с избирателями до дня выборов.",
            color=0xFFD700
        )
        await ctx.send(embed=embed)
        
        # Отправляем сообщение в канал кампании
        campaign_message = (
            f"**선거️ Предвыборная кампания по {election_type.lower()} выборам**\n"
            f"Кампания началась! Кандидаты могут публиковать свои программы, проводить дебаты и взаимодействовать с избирателями.\n"
            f"Дата начала: **{start_date}**\n"
            f"Дата окончания: **{end_date}**\n\n"
            f"Публикации, не связанные с выборами, будут удаляться."
        )
        
        await campaign_channel.send(campaign_message)

    @commands.hybrid_command(name='schedule_elections', description='Назначить дату выборов')
    @app_commands.describe(election_type='Тип выборов (presidential/parliamentary)', election_date='Дата выборов (YYYY-MM-DD)')
    @commands.has_permissions(administrator=True)
    async def schedule_elections(self, ctx, election_type: str, election_date: str):
        """Назначить дату выборов"""
        try:
            election_datetime = datetime.strptime(election_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("❌ Неверный формат даты! Используйте формат YYYY-MM-DD")
            return
        
        if election_type.lower() not in ['presidential', 'parliamentary']:
            await ctx.send("❌ Неверный тип выборов! Используйте: presidential, parliamentary")
            return
        
        # Сохраняем дату выборов
        await self.db.schedule_election(ctx.guild.id, election_type.lower(), election_datetime.isoformat())
        
        embed = discord.Embed(
            title="📅 Выборы назначены",
            description=f"Выборы типа **{election_type.lower()}** запланированы на **{election_date}**\n"
                       f"Система подготовит необходимые каналы в день выборов.\n\n"
                       f"До этой даты участники могут проводить предвыборную кампанию.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='setup_political_infrastructure', description='Настроить политическую инфраструктуру сервера')
    @commands.has_permissions(administrator=True)
    async def setup_political_infrastructure(self, ctx):
        """Настроить политическую инфраструктуру сервера"""
        # Создаем необходимые роли, если они не существуют
        roles_to_create = ["Президент", "Член Парламента", "Гражданин", "Политик"]
        
        created_roles = []
        for role_name in roles_to_create:
            existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not existing_role:
                new_role = await ctx.guild.create_role(name=role_name, mentionable=True)
                created_roles.append(role_name)
        
        # Создаем необходимые каналы, если они не существуют
        text_channels_to_create = [self.voting_channel_name, self.parliament_text_channel_name]
        voice_channels_to_create = [self.parliament_voice_channel_name]
        
        created_channels = []
        
        # Создаем текстовые каналы
        for channel_name in text_channels_to_create:
            existing_channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
            if not existing_channel:
                new_channel = await ctx.guild.create_text_channel(channel_name)
                created_channels.append(f"Текстовый: #{channel_name}")
        
        # Создаем голосовые каналы
        for channel_name in voice_channels_to_create:
            existing_channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
            if not existing_channel:
                new_channel = await ctx.guild.create_voice_channel(channel_name)
                created_channels.append(f"Голосовой: {channel_name}")
        
        embed = discord.Embed(
            title="🏛️ Политическая инфраструктура настроена",
            description="Создана следующая инфраструктура:",
            color=0x00FF00
        )
        
        if created_roles:
            embed.add_field(name="Созданные роли", value="\n".join(created_roles), inline=False)
        
        if created_channels:
            embed.add_field(name="Созданные каналы", value="\n".join(created_channels), inline=False)
        
        if not created_roles and not created_channels:
            embed.add_field(name="Информация", value="Вся политическая инфраструктура уже существует!", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='presidential_election', description='Запустить президентские выборы')
    @commands.has_permissions(administrator=True)
    async def presidential_election(self, ctx):
        """Запустить президентские выборы"""
        gov_type = await self.db.get_government_type(ctx.guild.id)
        if not gov_type:
            await ctx.send("❌ Сначала установите форму правления с помощью команды `!setup_government`")
            return
        
        if gov_type == "monarchy" or gov_type == "authoritarian":
            # В монархии/авторитаризме президент назначается
            embed = discord.Embed(
                title="👑 Назначение президента",
                description="В соответствии с формой правления, президент назначается Верховным Правителем или владельцем сервера.",
                color=0xFFD700
            )
            await ctx.send(embed=embed)
            return
        
        # В демократии проводим выборы
        parties = await self.db.get_server_parties(ctx.guild.id)
        if not parties:
            await ctx.send("❌ Для проведения президентских выборов должны существовать политические партии!")
            return
        
        embed = discord.Embed(
            title="🗳️ Президентские выборы",
            description="Президентские выборы начаты! Участники могут голосовать за партии в канале #выборы",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
        
        # Создаем канал для голосования, если его нет
        voting_channel = discord.utils.get(ctx.guild.text_channels, name=self.voting_channel_name)
        if not voting_channel:
            voting_channel = await ctx.guild.create_text_channel(self.voting_channel_name)
        
        # Отправляем сообщение с инструкциями для голосования
        instructions = (
            "**🗳️ Президентские выборы**\n"
            "Напишите название партии, за которую хотите проголосовать.\n"
            "Другие сообщения будут удалены!\n"
            "Голосование продлится 24 часа."
        )
        
        await voting_channel.send(instructions)
        
        # Запускаем процесс подсчета голосов через 24 часа
        await asyncio.sleep(86400)  # 24 часа
        await self.count_presidential_votes(ctx.guild, voting_channel)
    
    async def count_presidential_votes(self, guild, voting_channel):
        """Подсчет голосов на президентских выборах"""
        # Получаем все сообщения в канале голосования
        messages = []
        async for message in voting_channel.history(limit=9999):
            if not message.author.bot:  # Исключаем сообщения ботов
                messages.append(message)
        
        # Подсчет голосов
        votes = {}
        parties = await self.db.get_server_parties(guild.id)
        party_names = {party[1].lower(): party for party in parties}  # party[1] - name
        
        valid_votes = 0
        for message in messages:
            content = message.content.strip().lower()
            if content in party_names:
                if content not in votes:
                    votes[content] = 0
                votes[content] += 1
                valid_votes += 1
        
        # Удаляем сообщения после подсчета
        await voting_channel.purge(limit=9999)
        
        # Определяем победителя
        if votes:
            winner_name = max(votes, key=votes.get)
            winner_party = party_names[winner_name]
            
            # Назначаем роль президента лидеру партии-победителя
            president_role = discord.utils.get(guild.roles, name="Президент")
            if not president_role:
                president_role = await guild.create_role(name="Президент")
            
            # Убираем роль президента у старого президента
            for member in guild.members:
                if president_role in member.roles:
                    await member.remove_roles(president_role)
            
            # Назначаем новому президенту роль
            new_president = guild.get_member(int(winner_party[4]))  # winner_party[4] - leader_id
            if new_president:
                await new_president.add_roles(president_role)
            
            # Отправляем результаты
            results_message = (
                "**ания завершены!**\n"
                f"Победила партия: **{winner_name}**\n"
                f"Количество голосов: **{votes[winner_name]}** из **{valid_votes}**\n"
                f"Новый президент: {new_president.mention if new_president else 'Неизвестен'}"
            )
            
            await voting_channel.send(results_message)
        else:
            await voting_channel.send("**Выборы завершены!**\nНикто не проголосовал.")
    
    @commands.hybrid_command(name='parliamentary_election', description='Запустить парламентские выборы')
    @commands.has_permissions(administrator=True)
    async def parliamentary_election(self, ctx):
        """Запустить парламентские выборы"""
        gov_type = await self.db.get_government_type(ctx.guild.id)
        if not gov_type:
            await ctx.send("❌ Сначала установите форму правления с помощью команды `!setup_government`")
            return
        
        embed = discord.Embed(
            title="🏛️ Парламентские выборы",
            description="Парламентские выборы начаты! Желающие участвовать должны иметь высокий уровень и достаточное количество кредитов.",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
        
        # Создаем каналы для парламента, если их нет
        parliament_voice = discord.utils.get(ctx.guild.voice_channels, name=self.parliament_voice_channel_name)
        parliament_text = discord.utils.get(ctx.guild.text_channels, name=self.parliament_text_channel_name)
        
        if not parliament_voice:
            parliament_voice = await ctx.guild.create_voice_channel(self.parliament_voice_channel_name)
        
        if not parliament_text:
            parliament_text = await ctx.guild.create_text_channel(self.parliament_text_channel_name)
        
        # Отправляем сообщение с инструкциями
        instructions = (
            "**🏛️ Парламентские выборы**\n"
            "Желающие участвовать в парламенте должны иметь высокий уровень и достаточное количество кредитов.\n"
            "Выбор происходит по количеству кредитов - топ 99 участников становятся членами парламента.\n"
            "После выборов в этом канале будут доступны функции голосования и принятия решений."
        )
        
        await parliament_text.send(instructions)
        
        # Получаем топ 99 пользователей по кредитам
        top_users = await self.db.get_top_users_by_credits(ctx.guild.id, limit=99)
        
        # Назначаем роль члена парламента топ пользователям
        parliament_role = discord.utils.get(ctx.guild.roles, name="Член Парламента")
        if not parliament_role:
            parliament_role = await ctx.guild.create_role(name="Член Парламента")
        
        # Убираем роль у старых членов парламента
        for member in ctx.guild.members:
            if parliament_role in member.roles:
                await member.remove_roles(parliament_role)
        
        # Назначаем роль новым членам парламента
        for user_data in top_users:
            user_id = user_data[0]  # user_data[0] - id
            user = ctx.guild.get_member(user_id)
            if user:
                await user.add_roles(parliament_role)
        
        embed = discord.Embed(
            title="🏛️ Парламент сформирован",
            description=f"Парламент сформирован из топ {len(top_users)} пользователей по количеству кредитов!",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='server_stats', description='Статистика сервера как государства')
    async def server_stats(self, ctx):
        """Статистика сервера как государства"""
        # Подсчет ВВП (общее количество кредитов на сервере)
        total_credits = await self.db.get_total_server_credits(ctx.guild.id)
        
        # Подсчет населения (количество пользователей на сервере)
        total_members = len(ctx.guild.members)
        
        # Подсчет уровня активности (средний уровень пользователей)
        avg_level = await self.db.get_average_server_level(ctx.guild.id)
        
        embed = discord.Embed(
            title="🏛️ Статистика сервера-государства",
            color=0xFFD700
        )
        embed.add_field(name="ВВП (в кредитах)", value=f"{total_credits:,}", inline=True)
        embed.add_field(name="Население", value=total_members, inline=True)
        embed.add_field(name="Средний уровень", value=f"{avg_level:.2f}" if avg_level else "0.00", inline=True)
        
        # Подсчет политических данных
        parties_count = await self.db.get_parties_count(ctx.guild.id)
        gov_type = await self.db.get_government_type(ctx.guild.id)
        
        embed.add_field(name="Политические партии", value=parties_count, inline=True)
        embed.add_field(name="Форма правления", value=gov_type or "Не установлена", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Обработка сообщений в канале выборов"""
        if message.author.bot:
            return
        
        # Проверяем, находится ли сообщение в канале выборов
        if message.channel.name == self.voting_channel_name:
            # Проверяем, является ли сообщение голосованием за партию
            gov_type = await self.db.get_government_type(message.guild.id)
            if gov_type and gov_type != "democracy":
                return  # В других формах правления голосование неактуально
            
            # Проверяем, является ли сообщение названием существующей партии
            parties = await self.db.get_server_parties(message.guild.id)
            party_names = [party[1].lower() for party in parties]  # party[1] - name
            
            if message.content.strip().lower() in party_names:
                # Это действительный голос, оставляем сообщение
                pass
            else:
                # Это недействительное сообщение, удаляем его
                try:
                    await message.delete()
                    # Отправляем предупреждение пользователю
                    await message.author.send("❌ В канале выборов можно отправлять только названия политических партий!")
                except:
                    pass

async def setup(bot):
    db = bot.db  # используем общую базу данных
    await bot.add_cog(PoliticsCog(bot, db))