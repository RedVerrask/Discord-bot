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
        # Ensure data dir exists
        os.makedirs("data", exist_ok=True)

        # Load cogs
        await load_cogs(self)

        # Register persistent HomeView
        self.add_view(HomeView())  # fetch cogs on-demand inside the view

        # (you can keep slash-sync for now, or remove if you want no slash cmds at all)
        synced = await self.tree.sync()
        logger.info(f"🌐 Synced {len(synced)} slash commands globally.")

async def load_cogs(bot):
    cogs = ["professions", "recipes", "profile", "market"]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            logger.info(f"🔹 Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load cog '{cog}': {e}")

bot = AshesBot()

# ------------------------------------------------------
# Load Cogs Dynamically
# ------------------------------------------------------
async def load_cogs(bot):
        cogs = ["professions", "recipes", "profile", "market"]  # ⬅ Added market + profile
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
    professions_cog = bot.get_cog("Professions")
    recipes_cog = bot.get_cog("Recipes")

    if not professions_cog or not recipes_cog:
        await interaction.response.send_message(
            "⚠️ Required cogs are missing.", ephemeral=True
        )
        return

    # Create embed with banner
    embed = discord.Embed(
        title="🏰 Guild Codex",
        description="Your guide to artisans, recipes, and knowledge.",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/691099716657741864/1415440284111863903/ChatGPT_Image_Sep_10_2025_02_54_03_PM.png?ex=68c336fd&is=68c1e57d&hm=a5c30c34a2aa5eaed7d712cd916fbdf4d51feb7adf1a9409571d080d13498d9a&")
    embed.set_footer(text="Ashes of Creation - Guild Codex")

    await interaction.response.send_message(
        embed=embed,
        view=HomeView(professions_cog, recipes_cog),
        ephemeral=True
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
