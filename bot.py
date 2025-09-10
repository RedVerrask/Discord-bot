import discord
from discord.ext import commands
import os
import asyncio
from cogs.views import HomeView

# ----- Bot Intents -----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----- Load Cogs -----
async def load_cogs():
    cogs_to_load = ["professions", "recipes", "views"]
    for cog in cogs_to_load:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"🔹 Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

# ----- on_ready Event -----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        # Persistent views registration
        professions_cog = bot.get_cog("Professions")
        recipes_cog = bot.get_cog("Recipes")
        if professions_cog and recipes_cog:
            bot.add_view(HomeView(professions_cog, recipes_cog))

        # Global slash sync
        await bot.tree.sync()
        print("🌐 Slash commands synced globally!")
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}")

# ----- Home Slash Command -----
@bot.tree.command(name="home", description="Open your guild home menu")
async def home(interaction: discord.Interaction):
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

# ----- Run Bot -----
async def main():
    async with bot:
        await load_cogs()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError("❌ DISCORD_TOKEN is missing in Railway variables!")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
