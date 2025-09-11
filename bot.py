import os
import asyncio
import logging
import discord
from discord.ext import commands
from utils.debug import debug_log

# =========================
# Logging
# =========================
LOG_LEVEL = logging.INFO
logger = logging.getLogger("AshesBot")
logger.setLevel(LOG_LEVEL)
_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(_console)

# =========================
# Bot Setup
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN is missing! Set it in Railway → Variables.")

# Set your Discord ID for dev-only debug access
DEV_USER_ID = int(os.getenv("DEV_USER_ID", "0"))

class AshesBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.debug_mode: bool = False  # toggled by /debug

    async def setup_hook(self):
        os.makedirs("data", exist_ok=True)
        await load_cogs(self)

        # Register persistent views
        try:
            from cogs.hub import HubView
            self.add_view(HubView(cog=None, user_id=0))  # Register base view for all users
            debug_log("🔄 Registered persistent HubView", logger, self)
        except Exception as e:
            logger.warning(f"⚠️ Could not register HubView: {e}")

        # Sync slash commands
        synced = await self.tree.sync()
        logger.info(f"🌐 Synced {len(synced)} app commands.")

async def load_cogs(bot: commands.Bot):
    """Load all cogs safely, skipping missing ones."""
    cogs = [
        "cogs.professions",
        "cogs.recipes",
        "cogs.profile",
        "cogs.market",
        "cogs.hub",
        # "cogs.mail",     # ⬅ coming in Phase 3
        # "cogs.registry", # ⬅ coming in Phase 3
    ]
    for ext in cogs:
        try:
            await bot.load_extension(ext)
            logger.info(f"🔹 Loaded cog: {ext}")
        except Exception as e:
            logger.exception(f"❌ Failed to load {ext}: {e}")

bot = AshesBot()

# =========================
# Minimal Global Commands
# =========================
@bot.tree.command(name="debug", description="Toggle debug mode (developer only).")
async def debug_cmd(interaction: discord.Interaction):
    if DEV_USER_ID and interaction.user.id != DEV_USER_ID:
        return await interaction.response.send_message("⛔ You are not authorized to use this.", ephemeral=True)

    bot.debug_mode = not bot.debug_mode
    status = "ON ✅" if bot.debug_mode else "OFF ❌"

    debug_log("Toggled debug mode", bot=bot, user=interaction.user.id, status=status)
    await interaction.response.send_message(f"🐞 Debug mode is now **{status}**", ephemeral=True)


# =========================
# Events
# =========================
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")
    logger.info(f"🌐 Connected to {len(bot.guilds)} servers.")
    logger.info("📌 Slash Commands: %s", [cmd.name for cmd in bot.tree.get_commands()])

@bot.event
async def on_command_error(ctx, error):
    logger.error("❌ Command Error: %s", error)
    try:
        await ctx.send(f"⚠️ Error: `{error}`", delete_after=10)
    except Exception:
        pass

@bot.event
async def on_error(event_method, *args, **kwargs):
    logger.exception(f"💥 Unexpected error in event: {event_method}")

# =========================
# Run
# =========================
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
