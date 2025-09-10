import os
import asyncio
import logging
import discord
from discord.ext import commands
from cogs.views import HomeView

# ------------------------------------------------------
# Load Token from Environment (Railway handles this)
# ------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN is missing! "
        "Set it in Railway → Variables before deploying."
    )

# ------------------------------------------------------
# Logging Setup
# ------------------------------------------------------
LOG_LEVEL = logging.INFO
logger = logging.getLogger("AshesBot")
logger.setLevel(LOG_LEVEL)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] [%(levelname)s] | %(message)s",
    "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(console_handler)

# ------------------------------------------------------
# Bot Setup
# ------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class AshesBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Load cogs, add persistent views, and sync commands."""
        await load_cogs(self)

        # Register persistent HomeView
        professions_cog = self.get_cog("Professions")
        recipes_cog = self.get_cog("Recipes")
        if professions_cog and recipes_cog:
            self.add_view(HomeView(professions_cog, recipes_cog))

        # Sync slash commands globally
        synced = await self.tree.sync()
        logger.info(f"🌐 Synced {len(synced)} slash commands globally.")

bot = AshesBot()

# ------------------------------------------------------
# Load Cogs Dynamically
# ------------------------------------------------------
async def load_cogs(bot: AshesBot):
    cogs = ["professions", "recipes"]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            logger.info(f"🔹 Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load cog '{cog}': {e}")

# ------------------------------------------------------
# Slash Commands
# ------------------------------------------------------
@bot.tree.command(name="home", description="Open your guild home menu")
async def home(interaction: discord.Interaction):
    logger.info(f"🏠 /home triggered by {interaction.user}")
    professions_cog = bot.get_cog("Professions")
    recipes_cog = bot.get_cog("Recipes")

    if not professions_cog or not recipes_cog:
        await interaction.response.send_message(
            "⚠️ Required cogs are missing.", ephemeral=True
        )
        return

    try:
        # Send Home Menu via DM
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(
            "🏠 Welcome to your Guild Home!",
            view=HomeView(professions_cog, recipes_cog)
        )
        await interaction.response.send_message(
            "📩 I've sent you a DM with your home menu!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ I can't DM you. Please enable DMs.", ephemeral=True
        )

# ------------------------------------------------------
# Debug Command
# ------------------------------------------------------
if not any(cmd.name == "debug-recipes" for cmd in bot.tree.get_commands()):
    @bot.tree.command(name="debug-recipes", description="Debug the recipes system")
    async def debug_recipes(interaction: discord.Interaction):
        cogs = list(bot.cogs.keys())
        commands_list = [cmd.name for cmd in bot.tree.get_commands()]
        embed = discord.Embed(title="🔍 Debug Info", color=discord.Color.blue())
        embed.add_field(
            name="Loaded Cogs",
            value=", ".join(cogs) or "⚠️ None",
            inline=False
        )
        embed.add_field(
            name="Slash Commands",
            value=", ".join(commands_list) or "⚠️ None",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------------------
# Events
# ------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")
    logger.info(f"🌐 Connected to {len(bot.guilds)} servers.")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"❌ Command Error: {error}")
    await ctx.send(f"⚠️ Something went wrong: `{error}`", delete_after=10)

@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"💥 Unexpected error in event: {event}")

# ------------------------------------------------------
# Run Bot
# ------------------------------------------------------
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
