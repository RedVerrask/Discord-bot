import discord
from discord.ext import commands
import os
import asyncio
from cogs.views import HomeView  # type: ignore

# ----- Bot Intents -----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ----- Load Cogs -----
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename not in ("views.py",):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"🔹 Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")


# ----- on_ready Event -----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    GUILD_ID = 1064785222576644137  # replace with your guild ID
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("🌐 Slash commands synced!")


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
        await load_cogs()  # load cogs before starting
        await bot.start(os.environ['DISCORD_TOKEN'])


if __name__ == "__main__":
    asyncio.run(main())
