import os
import asyncio
import logging
import discord
from discord.ext import commands

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
LOG_LEVEL = logging.INFO
logger = logging.getLogger("AshesBot")
logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] | %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

# ------------------------------------------------------
# Discord
# ------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN is missing! Set it in Railway → Variables before deploying.")

# Your Discord user ID for dev-only commands
DEV_USER_ID = 1064785222576644137


class AshesBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.debug_mode = False  # toggled via /debugtoggle

    async def setup_hook(self):
        os.makedirs("data", exist_ok=True)
        await load_cogs(self)
        synced = await self.tree.sync()
        logger.info(f"🌐 Synced {len(synced)} slash commands.")


async def load_cogs(bot: commands.Bot):
    # Load data cogs first, hub last
    for name in ["professions", "recipes", "profile", "market", "hub"]:
        try:
            await bot.load_extension(f"cogs.{name}")
            logger.info(f"🔹 Loaded cog: {name}")
        except Exception as e:
            logger.exception(f"❌ Failed to load cog '{name}': {e}")


bot = AshesBot()

# ------------------------------------------------------
# Dev utilities
# ------------------------------------------------------
@bot.tree.command(name="debugtoggle", description="Toggle developer debug mode")
async def debugtoggle(interaction: discord.Interaction):
    if interaction.user.id != DEV_USER_ID:
        return await interaction.response.send_message("⚠️ Unauthorized.", ephemeral=True)
    bot.debug_mode = not bot.debug_mode
    await interaction.response.send_message(f"✅ Debug mode: **{'ON' if bot.debug_mode else 'OFF'}**", ephemeral=True)


@bot.tree.command(name="dumprecipes", description="DM raw learned_recipes.json")
async def dumprecipes(interaction: discord.Interaction):
    if interaction.user.id != DEV_USER_ID:
        return await interaction.response.send_message("⚠️ Unauthorized.", ephemeral=True)
    try:
        path = "data/learned_recipes.json"
        data = "{}"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        if len(data) < 1800:
            await interaction.user.send(f"```json\n{data}\n```")
        else:
            await interaction.user.send(file=discord.File(path))
        await interaction.response.send_message("✅ Sent via DM.", ephemeral=True)
    except Exception as e:
        logger.exception("dumprecipes failed")
        await interaction.response.send_message(f"⚠️ Failed: {e}", ephemeral=True)


@bot.tree.command(name="dumpmarket", description="DM raw market.json")
async def dumpmarket(interaction: discord.Interaction):
    if interaction.user.id != DEV_USER_ID:
        return await interaction.response.send_message("⚠️ Unauthorized.", ephemeral=True)
    try:
        path = "data/market.json"
        data = "{}"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        if len(data) < 1800:
            await interaction.user.send(f"```json\n{data}\n```")
        else:
            await interaction.user.send(file=discord.File(path))
        await interaction.response.send_message("✅ Sent via DM.", ephemeral=True)
    except Exception as e:
        logger.exception("dumpmarket failed")
        await interaction.response.send_message(f"⚠️ Failed: {e}", ephemeral=True)


# ------------------------------------------------------
# Events
# ------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} ({bot.user.id})")
    logger.info(f"🌐 Guilds: {len(bot.guilds)}")
    logger.info("📌 Slash Commands: %s", [cmd.name for cmd in bot.tree.get_commands()])


@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.send(f"⚠️ {error}", delete_after=10)
    except Exception:
        pass
    finally:
        logger.error("❌ Command Error", exc_info=error)


@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"💥 Unexpected error in event: {event}")


# ------------------------------------------------------
# Run
# ------------------------------------------------------
async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
