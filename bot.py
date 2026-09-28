import discord
from discord.ext import commands, tasks
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
import sqlite3

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

# Initialize bot
bot = commands.Bot(command_prefix=config['default_prefix'], intents=intents)
bot.remove_command('help')

# Database setup
def init_db():
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    # Create tables for user profiles
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        guild_id INTEGER,
                        level INTEGER DEFAULT 1,
                        xp INTEGER DEFAULT 0,
                        credits INTEGER DEFAULT 0,
                        rank TEXT DEFAULT 'Recruit',
                        join_date TEXT,
                        last_daily_claim TEXT,
                        warnings INTEGER DEFAULT 0
                    )''')
    
    # Create table for server settings
    cursor.execute('''CREATE TABLE IF NOT EXISTS server_settings (
                        guild_id INTEGER PRIMARY KEY,
                        admin_role_id INTEGER,
                        mod_role_id INTEGER,
                        mute_role_id INTEGER,
                        log_channel_id INTEGER
                    )''')
    
    # Create table for user warnings
    cursor.execute('''CREATE TABLE IF NOT EXISTS warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        guild_id INTEGER,
                        moderator_id INTEGER,
                        reason TEXT,
                        timestamp TEXT
                    )''')
    
    # Create table for shop items
    cursor.execute('''CREATE TABLE IF NOT EXISTS shop_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE,
                        price INTEGER,
                        description TEXT
                    )''')
    
    # Create table for user inventory
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        item_id INTEGER,
                        quantity INTEGER DEFAULT 1
                    )''')
    
    # Insert default shop items
    default_items = [
        ("Imperial Helmet", 200, "A standard Imperial stormtrooper helmet"),
        ("Lightsaber", 500, "A Jedi's weapon of choice"),
        ("Darth Vader Mask", 300, "Intimidate others with this iconic mask"),
        ("TIE Fighter Model", 400, "Collectible TIE fighter model"),
        ("Rebel Alliance Pin", 150, "Show your support for the Rebellion"),
        ("Imperial Credits Token", 100, "Decorative Imperial currency token"),
        ("Sith Holocron", 1000, "A repository of Sith knowledge"),
        ("Jedi Holocron", 1000, "A repository of Jedi knowledge"),
        ("Death Star Pin", 250, "Pin featuring the Death Star"),
        ("Ewok Figure", 120, "Collectible Ewok action figure")
    ]
    
    for item in default_items:
        cursor.execute("INSERT OR IGNORE INTO shop_items (name, price, description) VALUES (?, ?, ?)", item)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Star Wars themed ranks dictionary
STAR_WARS_RANKS = {
    1: {"name": "Recruit", "role_color": 0xCCCCCC, "perm_desc": "Basic member"},
    5: {"name": "Stormtrooper", "role_color": 0xCCCCCC, "perm_desc": "Basic soldier"},
    10: {"name": "Squad Leader", "role_color": 0xBBBBBB, "perm_desc": "Squad leader"},
    15: {"name": "Corporal", "role_color": 0xAAAAAA, "perm_desc": "Junior NCO"},
    20: {"name": "Sergeant", "role_color": 0x999999, "perm_desc": "Non-commissioned officer"},
    30: {"name": "Lieutenant", "role_color": 0x888888, "perm_desc": "Junior commissioned officer"},
    40: {"name": "Captain", "role_color": 0x777777, "perm_desc": "Company-grade officer"},
    50: {"name": "Major", "role_color": 0x666666, "perm_desc": "Field-grade officer"},
    60: {"name": "Colonel", "role_color": 0x555555, "perm_desc": "Senior field-grade officer"},
    70: {"name": "General", "role_color": 0x444444, "perm_desc": "High-ranking officer"},
    80: {"name": "Admiral", "role_color": 0x333333, "perm_desc": "Naval command officer"},
    90: {"name": "Dark Lord", "role_color": 0x222222, "perm_desc": "Powerful dark side user"},
    100: {"name": "Emperor", "role_color": 0x111111, "perm_desc": "Supreme ruler of the Empire"}
}

# Political ranks (authoritarian theme)
POLITICAL_RANKS = {
    "Supreme Leader": 95,
    "High Inquisitor": 90,
    "Grand Moff": 85,
    "Regional Governor": 80,
    "Sector Commander": 75,
    "Imperial Officer": 70,
    "Security Chief": 65,
    "Enforcer": 60,
    "Agent": 50
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers and serving {len(bot.users)} users')
    await bot.change_presence(activity=discord.Game(name="Galactic Empire Command"))
    
    # Start background tasks
    await setup_server_roles()

@bot.event
async def on_member_join(member):
    # Add user to database
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, guild_id, join_date, warnings) VALUES (?, ?, ?, ?)",
                   (member.id, member.guild.id, datetime.now().isoformat(), 0))
    
    conn.commit()
    conn.close()
    
    # Send welcome message
    welcome_channels = [channel for channel in member.guild.text_channels if 'general' in channel.name.lower() or 'welcome' in channel.name.lower()]
    if welcome_channels:
        embed = discord.Embed(
            title=" imperial greeting",
            description=f"Greetings, {member.mention}! Welcome to the Galactic Empire. Your loyalty shall determine your place in our hierarchy.",
            color=0x000000
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await welcome_channels[0].send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # XP system - give XP for messages
    await add_xp(message.author, message.guild, random.randint(config['xp_rewards']['message_range_min'], config['xp_rewards']['message_range_max']))
    
    # Check for spam (more than 5 messages in 10 seconds)
    recent_messages = [
        msg for msg in (await message.channel.history(limit=config['spam_threshold']['message_count']).flatten())
        if msg.author == message.author and (datetime.utcnow() - msg.created_at).seconds < config['spam_threshold']['time_window_seconds']
    ]
    
    if len(recent_messages) >= config['spam_threshold']['message_count']:
        await moderate_spam(message.author, message.channel)
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Command Not Found",
            description="That command does not exist in the Galactic Empire database.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Insufficient Permissions",
            description="You lack the authority to execute this command. Only Imperials with proper clearance may proceed.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)

async def add_xp(user, guild, xp_amount):
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    # Get current XP and level
    cursor.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (user.id, guild.id))
    result = cursor.fetchone()
    
    if result:
        current_xp, current_level = result
        new_xp = current_xp + xp_amount
        
        # Calculate new level based on XP threshold (every 100 XP = 1 level)
        new_level = (new_xp // 100) + 1
        
        cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                       (new_xp, new_level, user.id, guild.id))
        
        # Check if user leveled up
        if new_level > current_level:
            await handle_level_up(user, new_level, guild)
    else:
        # User doesn't exist in DB, create entry
        cursor.execute("INSERT INTO users (user_id, guild_id, xp, level, join_date, warnings) VALUES (?, ?, ?, 1, ?, ?)",
                       (user.id, guild.id, xp_amount, datetime.now().isoformat(), 0))
    
    conn.commit()
    conn.close()

async def handle_level_up(user, new_level, guild):
    # Check if user qualifies for a new rank
    if new_level in STAR_WARS_RANKS:
        rank_info = STAR_WARS_RANKS[new_level]
        
        # Create or update role
        existing_role = discord.utils.get(guild.roles, name=rank_info["name"])
        if not existing_role:
            role = await guild.create_role(
                name=rank_info["name"],
                color=discord.Color(rank_info["role_color"]),
                reason="Level up rank"
            )
        else:
            role = existing_role
        
        # Assign role to user
        await user.add_roles(role)
        
        # Remove previous rank roles if they exist
        for level_check, info in STAR_WARS_RANKS.items():
            if level_check < new_level and level_check != new_level:
                old_role = discord.utils.get(guild.roles, name=info["name"])
                if old_role and old_role in user.roles:
                    await user.remove_roles(old_role)
        
        # Send level up message
        embed = discord.Embed(
            title="Promotion!",
            description=f"{user.mention}, your loyalty has been noted. You have been promoted to {rank_info['name']}!",
            color=rank_info["role_color"]
        )
        await guild.system_channel.send(embed=embed)

async def moderate_spam(user, channel):
    # Find or create muted role
    muted_role = discord.utils.get(user.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await user.guild.create_role(
            name="Muted",
            permissions=discord.Permissions(send_messages=False, speak=False),
            reason="Auto-created muted role"
        )
        # Apply muted role to all text channels
        for text_channel in user.guild.text_channels:
            await text_channel.set_permissions(muted_role, send_messages=False)
    
    # Add muted role to user
    await user.add_roles(muted_role)
    
    # Log the moderation action
    log_channel = discord.utils.get(user.guild.text_channels, name="mod-log")
    if not log_channel:
        log_channel = user.guild.system_channel
    
    embed = discord.Embed(
        title="Spam Detected",
        description=f"{user.mention} was muted for spamming in {channel.mention}",
        color=0xFF0000,
        timestamp=datetime.utcnow()
    )
    await log_channel.send(embed=embed)
    
    # Auto-unmute after 10 minutes
    await asyncio.sleep(600)
    await user.remove_roles(muted_role)

async def setup_server_roles():
    """Setup default roles for servers the bot joins"""
    for guild in bot.guilds:
        # Create Star Wars themed roles
        sw_roles = [
            ("Emperor", 0x111111),
            ("Dark Lord", 0x222222),
            ("Admiral", 0x333333),
            ("General", 0x444444),
            ("Colonel", 0x555555),
            ("Major", 0x666666),
            ("Captain", 0x777777),
            ("Sergeant", 0x999999),
            ("Corporal", 0xAAAAAA),
            ("Stormtrooper", 0xCCCCCC),
            ("Recruit", 0xFFFFFF),
            ("Moff", 0x4B0082),
            ("Inquisitor", 0x800000),
            ("TIE Pilot", 0x696969),
            ("Imperial Officer", 0x708090),
            ("Imperial Guard", 0xDC143C),
            ("Royal Guard", 0xB22222),
            ("Sith Lord", 0x8B0000),
            ("Jedi Hunter", 0x2F4F4F),
            ("Imperial Spy", 0x228B22)
        ]
        
        for role_name, color in sw_roles:
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                await guild.create_role(
                    name=role_name,
                    color=discord.Color(color),
                    reason="Star Wars themed role"
                )
        
        # Create political/authoritarian roles
        political_roles = [
            ("Supreme Leader", 0x000000),
            ("High Command", 0x2F4F4F),
            ("Security Chief", 0x708090),
            ("Enforcer", 0x8B0000),
            ("Agent", 0x696969),
            ("Propaganda Officer", 0xDC143C),
            ("Loyalist", 0x228B22)
        ]
        
        for role_name, color in political_roles:
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                await guild.create_role(
                    name=role_name,
                    color=discord.Color(color),
                    reason="Political/Autoritarian themed role"
                )
        
        # Create channel categories for organization
        try:
            # Create military channels
            military_cat = await guild.create_category(" imperial military")
            await guild.create_text_channel("command-center", category=military_cat)
            await guild.create_text_channel("troop-deployments", category=military_cat)
            await guild.create_voice_channel("war-room", category=military_cat)
            
            # Create political channels
            politics_cat = await guild.create_category(" galactic politics")
            await guild.create_text_channel("senate-hall", category=politics_cat)
            await guild.create_text_channel("propaganda-bureau", category=politics_cat)
            await guild.create_voice_channel("council-chamber", category=politics_cat)
            
            # Create social channels
            social_cat = await guild.create_category(" imperial social")
            await guild.create_text_channel("cantina", category=social_cat)
            await guild.create_text_channel("trophy-hall", category=social_cat)
            await guild.create_voice_channel("holo-theater", category=social_cat)
            
            # Create admin channels
            admin_cat = await guild.create_category(" imperial command")
            await guild.create_text_channel("imperial-command", category=admin_cat)
            await guild.create_text_channel("security-logs", category=admin_cat)
            await guild.create_voice_channel("emperor-s-throne-room", category=admin_cat, overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                discord.utils.get(guild.roles, name="Emperor"): discord.PermissionOverwrite(view_channel=True, connect=True)
            })
        except discord.Forbidden:
            # If bot doesn't have permissions to create channels, skip
            pass

# ADMIN COMMANDS
@commands.has_permissions(administrator=True)
@bot.command(name='admin')
async def admin_panel(ctx):
    """Admin panel for server management"""
    embed = discord.Embed(
        title="Imperial Command Center",
        description="Administrative tools for managing the Galactic Empire server",
        color=0x000000
    )
    embed.add_field(name="!ban @user [reason]", value="Ban a user from the server", inline=False)
    embed.add_field(name="!kick @user [reason]", value="Kick a user from the server", inline=False)
    embed.add_field(name="!mute @user [duration]", value="Mute a user for a specified time", inline=False)
    embed.add_field(name="!warn @user [reason]", value="Issue a warning to a user", inline=False)
    embed.add_field(name="!clear [number]", value="Clear messages from a channel", inline=False)
    embed.add_field(name="!setrank @user [rank]", value="Manually assign a rank to a user", inline=False)
    embed.add_field(name="!givexp @user [amount]", value="Give XP to a user", inline=False)
    embed.add_field(name="!givecredits @user [amount]", value="Give credits to a user", inline=False)
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command(name='ban')
async def ban_user(ctx, member: discord.Member, *, reason=None):
    """Ban a user from the server"""
    if reason is None:
        reason = "No reason provided"
    
    await member.ban(reason=reason)
    
    embed = discord.Embed(
        title="User Banned",
        description=f"{member.mention} has been banned by {ctx.author.mention}\nReason: {reason}",
        color=0xFF0000
    )
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command(name='kick')
async def kick_user(ctx, member: discord.Member, *, reason=None):
    """Kick a user from the server"""
    if reason is None:
        reason = "No reason provided"
    
    await member.kick(reason=reason)
    
    embed = discord.Embed(
        title="User Kicked",
        description=f"{member.mention} has been kicked by {ctx.author.mention}\nReason: {reason}",
        color=0xFFA500
    )
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command(name='mute')
async def mute_user(ctx, member: discord.Member, duration: int = 10):
    """Mute a user for a specified duration (minutes)"""
    # Find or create muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(
            name="Muted",
            permissions=discord.Permissions(send_messages=False, speak=False),
            reason="Auto-created muted role"
        )
        # Apply muted role to all text channels
        for text_channel in ctx.guild.text_channels:
            await text_channel.set_permissions(muted_role, send_messages=False)
    
    await member.add_roles(muted_role)
    
    embed = discord.Embed(
        title="User Muted",
        description=f"{member.mention} has been muted by {ctx.author.mention} for {duration} minutes",
        color=0xFFA500
    )
    await ctx.send(embed=embed)
    
    # Auto-unmute after duration
    await asyncio.sleep(duration * 60)
    await member.remove_roles(muted_role)

@commands.has_permissions(administrator=True)
@bot.command(name='warn')
async def warn_user(ctx, member: discord.Member, *, reason):
    """Warn a user and record the warning"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    # Get current warning count
    cursor.execute("SELECT warnings FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if result:
        current_warnings = result[0]
        new_warnings = current_warnings + 1
        
        # Update user's warning count
        cursor.execute("UPDATE users SET warnings = ? WHERE user_id = ? AND guild_id = ?",
                       (new_warnings, member.id, ctx.guild.id))
    else:
        new_warnings = 1
        cursor.execute("INSERT INTO users (user_id, guild_id, warnings, join_date) VALUES (?, ?, ?, ?)",
                       (member.id, ctx.guild.id, 1, datetime.now().isoformat()))
    
    # Record the warning
    cursor.execute("INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (member.id, ctx.guild.id, ctx.author.id, reason, datetime.now().isoformat()))
    
    # Check if user should be banned
    if new_warnings >= config['max_warns_before_ban']:
        await member.ban(reason=f"Exceeded max warnings ({config['max_warns_before_ban']})")
        embed = discord.Embed(
            title="User Banned",
            description=f"{member.mention} was banned for accumulating {new_warnings} warnings",
            color=0xFF0000
        )
    else:
        embed = discord.Embed(
            title="User Warned",
            description=f"{member.mention} has been warned by {ctx.author.mention}\nReason: {reason}\nWarnings: {new_warnings}/{config['max_warns_before_ban']}",
            color=0xFFFF00
        )
    
    conn.commit()
    conn.close()
    await ctx.send(embed=embed)

@commands.has_permissions(manage_messages=True)
@bot.command(name='clear')
async def clear_messages(ctx, amount: int):
    """Clear a specified number of messages"""
    await ctx.channel.purge(limit=amount + 1)  # +1 to remove the command message too
    msg = await ctx.send(f"Cleared {amount} messages")
    await asyncio.sleep(3)
    await msg.delete()

@commands.has_permissions(administrator=True)
@bot.command(name='setrank')
async def set_rank(ctx, member: discord.Member, *, rank_name):
    """Manually assign a rank to a user"""
    # Find the role by name
    role = discord.utils.get(ctx.guild.roles, name=rank_name)
    if not role:
        embed = discord.Embed(
            title="Rank Not Found",
            description=f"The rank '{rank_name}' does not exist on this server.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return
    
    # Remove all rank roles first
    for r in ctx.guild.roles:
        if r.name in [info["name"] for level, info in STAR_WARS_RANKS.items()]:
            if r in member.roles:
                await member.remove_roles(r)
    
    # Add the new rank
    await member.add_roles(role)
    
    # Update user's rank in DB
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET rank = ? WHERE user_id = ? AND guild_id = ?",
                   (rank_name, member.id, ctx.guild.id))
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="Rank Assigned",
        description=f"{member.mention} has been assigned the rank of {rank_name}",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command(name='givexp')
async def give_xp(ctx, member: discord.Member, amount: int):
    """Give XP to a user"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if result:
        current_xp, current_level = result
        new_xp = current_xp + amount
        new_level = (new_xp // 100) + 1
        
        cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
                       (new_xp, new_level, member.id, ctx.guild.id))
    else:
        new_xp = amount
        new_level = (new_xp // 100) + 1
        cursor.execute("INSERT INTO users (user_id, guild_id, xp, level, join_date, warnings) VALUES (?, ?, ?, ?, ?, ?)",
                       (member.id, ctx.guild.id, new_xp, new_level, datetime.now().isoformat(), 0))
    
    conn.commit()
    conn.close()
    
    await handle_level_up(member, new_level, ctx.guild)
    
    embed = discord.Embed(
        title="XP Given",
        description=f"{amount} XP given to {member.mention}. New level: {new_level}",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command(name='givecredits')
async def give_credits(ctx, member: discord.Member, amount: int):
    """Give credits to a user"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if result:
        current_credits = result[0]
        new_credits = current_credits + amount
        cursor.execute("UPDATE users SET credits = ? WHERE user_id = ? AND guild_id = ?",
                       (new_credits, member.id, ctx.guild.id))
    else:
        new_credits = amount
        cursor.execute("INSERT INTO users (user_id, guild_id, credits, join_date, warnings) VALUES (?, ?, ?, ?, ?)",
                       (member.id, ctx.guild.id, new_credits, datetime.now().isoformat(), 0))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="Credits Given",
        description=f"{amount} credits given to {member.mention}. New balance: {new_credits}",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

# PUBLIC COMMANDS
@bot.command(name='profile')
async def profile(ctx, member: discord.Member = None):
    """Show user profile with stats"""
    if member is None:
        member = ctx.author
    
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT level, xp, credits, rank, warnings FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if not result:
        level, xp, credits, rank, warnings = 1, 0, 0, "Recruit", 0
    else:
        level, xp, credits, rank, warnings = result
    
    conn.close()
    
    # Calculate XP progress to next level
    xp_to_next = ((level * 100) - xp) % 100
    if xp_to_next == 0:
        xp_to_next = 100
    
    embed = discord.Embed(
        title=f"Profile: {member.display_name}",
        color=0x0000FF
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=level, inline=True)
    embed.add_field(name="XP", value=f"{xp}/{level * 100}", inline=True)
    embed.add_field(name="Credits", value=credits, inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Warnings", value=warnings, inline=True)
    embed.add_field(name="XP to Next Level", value=xp_to_next, inline=True)
    embed.add_field(name="Join Date", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """Show top players by level"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, level, xp FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (ctx.guild.id,))
    results = cursor.fetchall()
    
    conn.close()
    
    embed = discord.Embed(
        title="Galactic Empire Leaderboard",
        description="Top Imperials by rank",
        color=0x000000
    )
    
    for i, (user_id, level, xp) in enumerate(results, 1):
        user = bot.get_user(user_id)
        if user:
            embed.add_field(
                name=f"#{i}: {user.display_name}",
                value=f"Level {level} (XP: {xp})",
                inline=False
            )
        else:
            embed.add_field(
                name=f"#{i}: Unknown User",
                value=f"Level {level} (XP: {xp})",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily_reward(ctx):
    """Claim daily reward"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT last_daily_claim FROM users WHERE user_id = ? AND guild_id = ?", (ctx.author.id, ctx.guild.id))
    result = cursor.fetchone()
    
    now = datetime.now()
    if result and result[0]:
        last_claim = datetime.fromisoformat(result[0])
        if (now - last_claim).days < 1:
            hours_left = 24 - (now - last_claim).seconds // 3600
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've already claimed your daily reward. Try again in {hours_left} hours.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            conn.close()
            return
    
    # Give daily reward
    reward = random.randint(config['daily_rewards']['min_credits'], config['daily_rewards']['max_credits'])
    cursor.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (ctx.author.id, ctx.guild.id))
    credit_result = cursor.fetchone()
    
    if credit_result:
        new_credits = credit_result[0] + reward
        cursor.execute("UPDATE users SET credits = ?, last_daily_claim = ? WHERE user_id = ? AND guild_id = ?",
                       (new_credits, now.isoformat(), ctx.author.id, ctx.guild.id))
    else:
        cursor.execute("INSERT INTO users (user_id, guild_id, credits, last_daily_claim, join_date, warnings) VALUES (?, ?, ?, ?, ?, ?)",
                       (ctx.author.id, ctx.guild.id, reward, now.isoformat(), now.isoformat(), 0))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="Daily Reward Claimed",
        description=f"You received {reward} credits as your daily loyalty bonus!",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@bot.command(name='balance')
async def balance(ctx, member: discord.Member = None):
    """Check credits balance"""
    if member is None:
        member = ctx.author
    
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if result:
        credits = result[0]
    else:
        credits = 0
    
    conn.close()
    
    embed = discord.Embed(
        title=f"Credit Balance",
        description=f"{member.display_name} has {credits} credits",
        color=0x00FFFF
    )
    await ctx.send(embed=embed)

@bot.command(name='rankup')
async def rankup(ctx):
    """Attempt to gain a higher rank through challenges"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT level, xp, credits FROM users WHERE user_id = ? AND guild_id = ?", (ctx.author.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if not result:
        embed = discord.Embed(
            title="Cannot Rank Up",
            description="You need to participate more to gain experience.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        conn.close()
        return
    
    level, xp, credits = result
    conn.close()
    
    # Cost to rank up increases with level
    cost = level * 50
    
    if credits < cost:
        embed = discord.Embed(
            title="Insufficient Funds",
            description=f"You need {cost} credits to attempt a rank up, but you only have {credits}.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        return
    
    # Deduct cost
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    new_credits = credits - cost
    cursor.execute("UPDATE users SET credits = ? WHERE user_id = ? AND guild_id = ?", 
                   (new_credits, ctx.author.id, ctx.guild.id))
    conn.commit()
    conn.close()
    
    # Random chance to succeed based on level
    success_chance = min(70 + level, 95)  # Chance increases with level, max 95%
    
    if random.randint(1, 100) <= success_chance:
        # Add XP for successful rank up
        xp_gain = random.randint(50, 100)
        await add_xp(ctx.author, ctx.guild, xp_gain)
        
        embed = discord.Embed(
            title="Rank Up Successful!",
            description=f"Your loyalty has been recognized! You gained {xp_gain} XP.",
            color=0x00FF00
        )
    else:
        embed = discord.Embed(
            title="Rank Up Failed",
            description="Your attempt to rise in rank was unsuccessful. Continue proving your loyalty.",
            color=0xFFA500
        )
    
    await ctx.send(embed=embed)

@bot.command(name='shop')
async def shop(ctx):
    """Display the Imperial marketplace"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, price, description FROM shop_items")
    items = cursor.fetchall()
    
    conn.close()
    
    embed = discord.Embed(
        title=" imperial marketplace",
        description="Items available for purchase with Imperial credits",
        color=0x8B0000
    )
    
    for name, price, desc in items:
        embed.add_field(
            name=f"{name} - {price} credits",
            value=desc,
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='buy')
async def buy_item(ctx, *, item_name):
    """Buy an item from the shop"""
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    # Get item info
    cursor.execute("SELECT id, name, price FROM shop_items WHERE name LIKE ?", (f'%{item_name}%',))
    item = cursor.fetchone()
    
    if not item:
        embed = discord.Embed(
            title="Item Not Found",
            description=f"No item matching '{item_name}' was found in the shop.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        conn.close()
        return
    
    item_id, item_name, price = item
    
    # Get user credits
    cursor.execute("SELECT credits FROM users WHERE user_id = ? AND guild_id = ?", (ctx.author.id, ctx.guild.id))
    result = cursor.fetchone()
    
    if not result:
        embed = discord.Embed(
            title="Cannot Purchase",
            description="You don't have an account yet. Participate in chat to earn credits.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        conn.close()
        return
    
    credits = result[0]
    
    if credits < price:
        embed = discord.Embed(
            title="Insufficient Funds",
            description=f"This item costs {price} credits, but you only have {credits}.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
        conn.close()
        return
    
    # Process purchase
    new_credits = credits - price
    cursor.execute("UPDATE users SET credits = ? WHERE user_id = ? AND guild_id = ?", 
                   (new_credits, ctx.author.id, ctx.guild.id))
    
    # Add item to inventory
    cursor.execute("INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (?, ?, 1)", 
                   (ctx.author.id, item_id))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="Purchase Successful!",
        description=f"You bought {item_name} for {price} credits. Remaining balance: {new_credits}",
        color=0x00FF00
    )
    await ctx.send(embed=embed)

@bot.command(name='inventory')
async def inventory(ctx, member: discord.Member = None):
    """Show user's inventory"""
    if member is None:
        member = ctx.author
    
    conn = sqlite3.connect('galactic_empire_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT si.name, ui.quantity 
        FROM user_inventory ui
        JOIN shop_items si ON ui.item_id = si.id
        WHERE ui.user_id = ?
    """, (member.id,))
    
    items = cursor.fetchall()
    
    conn.close()
    
    if not items:
        embed = discord.Embed(
            title=f"{member.display_name}'s Inventory",
            description="No items in inventory",
            color=0xFFFF00
        )
    else:
        embed = discord.Embed(
            title=f"{member.display_name}'s Inventory",
            color=0xFFFF00
        )
        for item_name, quantity in items:
            embed.add_field(
                name=item_name,
                value=f"Quantity: {quantity}",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="Galactic Empire Bot Commands",
        description="Commands available to serve the Empire",
        color=0x000000
    )
    
    embed.add_field(name="!profile [@user]", value="View user profile with stats", inline=False)
    embed.add_field(name="!leaderboard", value="View top ranked Imperials", inline=False)
    embed.add_field(name="!daily", value="Claim daily loyalty bonus", inline=False)
    embed.add_field(name="!balance [@user]", value="Check credit balance", inline=False)
    embed.add_field(name="!rankup", value="Attempt to gain a higher rank", inline=False)
    embed.add_field(name="!shop", value="Browse the Imperial marketplace", inline=False)
    embed.add_field(name="!buy [item]", value="Purchase items with credits", inline=False)
    embed.add_field(name="!inventory [@user]", value="View your inventory", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="ADMIN COMMANDS:", value=" ", inline=False)
        embed.add_field(name="!admin", value="View admin panel", inline=False)
        embed.add_field(name="!ban @user [reason]", value="Ban a user", inline=False)
        embed.add_field(name="!kick @user [reason]", value="Kick a user", inline=False)
        embed.add_field(name="!mute @user [time]", value="Mute a user", inline=False)
        embed.add_field(name="!warn @user [reason]", value="Warn a user", inline=False)
        embed.add_field(name="!clear [num]", value="Clear messages", inline=False)
        embed.add_field(name="!setrank @user [rank]", value="Set user rank", inline=False)
        embed.add_field(name="!givexp @user [amount]", value="Give XP", inline=False)
        embed.add_field(name="!givecredits @user [amount]", value="Give credits", inline=False)
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    environment_token = os.getenv('DISCORD_BOT_TOKEN')
    token = (environment_token or config.get('bot_token') or '').strip()
    if not token:
        raise SystemExit("Set DISCORD_BOT_TOKEN or bot_token in config.json before starting the bot.")
    bot.run(token)