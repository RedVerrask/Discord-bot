import discord
from discord.ext import commands
import os
import asyncio
import logging
from cogs.views import HomeView

# ------------------------------------------------------
# Logging Setup
# ------------------------------------------------------
LOG_LEVEL = logging.INFO
logger = logging.getLogger("AshesBot")
logger.setLevel(LOG_LEVEL)

console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ------------------------------------------------------
# Bot Setup
# ------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------------------------------
# Load Cogs
# ------------------------------------------------------
async def load_cogs():
    cogs_to_load = ["professions", "recipes"]
    for cog in cogs_to_load:
        try:
            await bot.load_extension(f"cogs.{cog}")
            logger.info(f"🔹 Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}")

# ------------------------------------------------------
# Bot Ready Event
# ------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    try:
        professions_cog = bot.get_cog("Professions")
        recipes_cog = bot.get_cog("Recipes")

        # Register persistent home view
        if professions_cog and recipes_cog:
            bot.add_view(HomeView(professions_cog, recipes_cog))

        await bot.tree.sync()
        logger.info("🌐 Slash commands synced globally!")
    except Exception as e:
        logger.error(f"⚠️ Failed to sync slash commands: {e}")

# ------------------------------------------------------
# Home Slash Command
# ------------------------------------------------------
@bot.tree.command(name="home", description="Open your guild home menu")
async def home(interaction: discord.Interaction):
    logger.info(f"🏠 Home Menu Opened | User: {interaction.user}")
    professions_cog = bot.get_cog("Professions")
    recipes_cog = bot.get_cog("Recipes")

    if professions_cog is None or recipes_cog is None:
        await interaction.response.send_message(
            "⚠️ Required cogs are not loaded yet.", ephemeral=True
        )
        return

    try:
        await interaction.response.send_message(
            "Welcome to your Guild Home!",
            view=HomeView(professions_cog, recipes_cog),
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I couldn't open your home menu. Please enable DMs.", ephemeral=True
        )

# ------------------------------------------------------
# Debug Command (Admin Only)
# ------------------------------------------------------
from discord import app_commands

@bot.tree.command(name="debug", description="Debug bot status")
@app_commands.checks.has_permissions(administrator=True)
async def debug(interaction: discord.Interaction):
    """Shows debug info about the bot, cogs, and views."""
    professions_cog = bot.get_cog("Professions")
    recipes_cog = bot.get_cog("Recipes")

    views_info = []
    if hasattr(bot, "_views"):
        for view in bot._views.values():
            if isinstance(view, discord.ui.View):
                views_info.append(f"✅ {view.__class__.__name__}")
    else:
        views_info.append("⚠️ No views registered")

    embed = discord.Embed(
        title="🔍 Bot Debug Information",
        color=discord.Color.blue()
    )
    embed.add_field(name="Bot Status", value="✅ Online", inline=False)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=False)
    embed.add_field(
        name="Loaded Cogs",
        value="\n".join(bot.cogs.keys()) or "⚠️ No cogs loaded",
        inline=False
    )
    embed.add_field(
        name="Persistent Views",
        value="\n".join(views_info) or "⚠️ No persistent views registered",
        inline=False
    )
    embed.add_field(
        name="Professions Cog",
        value="✅ Loaded" if professions_cog else "⚠️ Missing",
        inline=True
    )
    embed.add_field(
        name="Recipes Cog",
        value="✅ Loaded" if recipes_cog else "⚠️ Missing",
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------------------
# Run Bot
# ------------------------------------------------------
async def main():
    async with bot:
        await load_cogs()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.critical("❌ DISCORD_TOKEN missing! Add it to Railway variables.")
            raise RuntimeError("DISCORD_TOKEN is required!")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
