import discord
from discord.ext import commands
import os
import asyncio
import logging
from cogs.views import HomeView

# ------------------------------------------------------
# Logging Setup
# ------------------------------------------------------
LOG_LEVEL = logging.DEBUG  # Change to logging.INFO in production
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
# Slash Command Logging
# ------------------------------------------------------
@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    logger.info(
        f"✅ Slash Command | User: {interaction.user} | Command: /{command.name}"
    )

# ------------------------------------------------------
# Button & Select Interaction Logging
# ------------------------------------------------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.type == discord.InteractionType.component:
            component_type = "Select" if isinstance(interaction.data, dict) and interaction.data.get("component_type") == 3 else "Button"
            logger.info(
                f"🔘 {component_type} Clicked | User: {interaction.user} | ID: {interaction.data.get('custom_id', 'N/A')}"
            )
        elif interaction.type == discord.InteractionType.modal_submit:
            logger.info(f"📝 Modal Submitted | User: {interaction.user}")
    except Exception as e:
        logger.error(f"⚠️ Interaction logging failed: {e}")

# ------------------------------------------------------
# Error Handling
# ------------------------------------------------------
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"❌ Command Error | User: {ctx.author} | Error: {error}")
    await ctx.send(f"⚠️ Something went wrong: `{error}`", delete_after=10)

@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"💥 Unexpected error in event: {event}")

# ------------------------------------------------------
# Bot Ready Event
# ------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    try:
        professions_cog = bot.get_cog("Professions")
        recipes_cog = bot.get_cog("Recipes")
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
            "Required cogs are not loaded yet.", ephemeral=True
        )
        return

    try:
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(
            "Welcome to your Guild Home!",
            view=HomeView(professions_cog, recipes_cog)
        )
        await interaction.response.send_message(
            "I've sent you a DM with your home menu!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I couldn't DM you. Please enable DMs.", ephemeral=True
        )

# ------------------------------------------------------
# Run Bot
# ------------------------------------------------------
from discord import app_commands

# ------------------------------------------------------
# Hidden Debug Command
# ------------------------------------------------------
@bot.tree.command(name="debug", description="Debug bot status")
@app_commands.checks.has_permissions(administrator=True)
async def debug(interaction: discord.Interaction):
    """Shows debug info about the bot, cogs, and views."""
    professions_cog = bot.get_cog("Professions")
    recipes_cog = bot.get_cog("Recipes")

    # Check persistent views
    views_info = []
    if hasattr(bot, "_views"):
        for view in bot._views.values():
            if isinstance(view, discord.ui.View):
                views_info.append(f"✅ {view.__class__.__name__}")
    else:
        views_info.append("⚠️ No views registered")

    # Check buttons/selects missing custom_id
    invalid_items = []
    for view in getattr(bot, "_views", {}).values():
        if isinstance(view, discord.ui.View):
            for item in view.children:
                if hasattr(item, "custom_id") and not item.custom_id:
                    invalid_items.append(f"{item.label or 'Unnamed Item'} ({view.__class__.__name__})")

    # Build debug embed
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
        name="Missing custom_id",
        value="\n".join(invalid_items) if invalid_items else "✅ All items have custom IDs",
        inline=False
    )

    # Professions & Recipes cog status
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
