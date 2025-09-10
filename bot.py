from dotenv import load_dotenv
load_dotenv()
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

logger.info("🚀 Bot is starting... Loading commands...")

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
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")

    try:
        # Force global sync
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

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        # Log basic interaction info
        logger.info(
            f"[INTERACTION] User: {interaction.user} | "
            f"Type: {interaction.type} | "
            f"Custom ID: {interaction.data.get('custom_id', 'N/A') if interaction.data else 'N/A'} | "
            f"Values: {interaction.data.get('values', 'N/A') if interaction.data else 'N/A'}"
        )

        # Check if it's a component interaction (buttons or dropdowns)
        if interaction.type == discord.InteractionType.component:
            logger.debug(f"[COMPONENT] Component data: {interaction.data}")

        # Check if it's a modal submit
        elif interaction.type == discord.InteractionType.modal_submit:
            logger.debug(f"[MODAL SUBMIT] Modal data: {interaction.data}")

        # Pass the event to the default Discord handler
        await bot.process_application_commands(interaction)
    except Exception as e:
        logger.error(f"⚠️ Interaction error: {e}", exc_info=True)
        try:
            await interaction.response.send_message(
                f"⚠️ Something went wrong: `{e}`",
                ephemeral=True
            )
        except:
            pass
@bot.tree.command(name="debug-recipes", description="Debug the recipes system")
async def debug_recipes(interaction: discord.Interaction):
    logger.info(f"🔍 Running recipes debug for {interaction.user}")

    recipes_cog = bot.get_cog("Recipes")
    professions_cog = bot.get_cog("Professions")

    if not recipes_cog:
        await interaction.response.send_message("⚠️ Recipes cog not loaded!", ephemeral=True)
        return

    if not professions_cog:
        await interaction.response.send_message("⚠️ Professions cog not loaded!", ephemeral=True)
        return

    total_recipes = len(recipes_cog.get_all_recipes())
    user_professions = professions_cog.get_user_professions(interaction.user.id)

    embed = discord.Embed(
        title="🛠 Recipes System Debug",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Total Recipes Loaded", value=str(total_recipes), inline=True)
    embed.add_field(name="Your Professions", value=", ".join(user_professions) or "None", inline=True)
    embed.add_field(name="Portfolio Entries", value=str(len(recipes_cog.user_portfolios)), inline=True)

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
