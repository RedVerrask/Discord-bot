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
            self.add_view(HubView(cog=None, user_id=0))  # registers buttons persistently
        except Exception as e:
            logger.warning(f"⚠️ Could not register HubView: {e}")


        # Sync slash commands
        synced = await self.tree.sync()
        logger.info(f"🌐 Synced {len(synced)} app commands.")

async def load_cogs(bot: commands.Bot):
    """Load all cogs safely, skipping missing ones."""
    cogs = [
    "cogs.profile",
    "cogs.professions",
    "cogs.recipes",
    "cogs.market",
    "cogs.mailbox",
    "cogs.trades",
    "cogs.hub",
    "utils.debug",   # <-- add this
]


    for ext in cogs:
        try:
            await bot.load_extension(ext)
            logger.info(f"🔹 Loaded cog: {ext}")
        except Exception as e:
            logger.exception(f"❌ Failed to load {ext}: {e}")

def debug_log(message: str, logger=None, bot=None, **extra):
    """
    Lightweight debug logger used globally.
    Falls back to print if logger is missing.
    """
    if logger:
        logger.info(f"[DEBUG] {message} | {extra}")
    else:
        print(f"[DEBUG] {message} | {extra}")

bot = AshesBot()


# =========================
# Minimal Global Commands
# =========================



# =========================
# Events
# =========================
@bot.event
async def on_ready():
    guild = discord.Object(id=1064785222576644137)  # put your server ID here
    await bot.tree.sync(guild=guild)
    # In on_ready()
    await bot.tree.sync()   # sync globally

    print("🌐 Slash commands synced instantly!")


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
