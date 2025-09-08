import discord
from discord.ext import commands
import sqlite3
import os
import asyncio  # make sure this is at the top of your file


intents = discord.Intents.default()
intents.message_content = True # Needed to read messages
intents.members = True # usefule for guild bots
bot = commands.Bot(command_prefix="!", intents=intents)
ADMIN_USER_IDS = [359521236663009293]  # Replace with your actual Discord user ID




class HomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # no timeout

    #artisan menu
    @discord.ui.button(label="Artisan", style=discord.ButtonStyle.secondary)
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Artisan Menu:", ephemeral=True)
            
    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Recipe Menu:", view=RecipeView(), ephemeral=True)

    

class RecipeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Recipe", style=discord.ButtonStyle.success)
    async def add_recipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please type your recipe:", ephemeral=True)

    @discord.ui.button(label="List Recipes", style=discord.ButtonStyle.primary)
    async def list_recipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        # For now, just a placeholder
        await interaction.response.send_message("Here are your recipes:\n- Example Recipe 1\n- Example Recipe 2", ephemeral=True)

class ArtisanView(discord.ui.View):
    def __innit__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Artisan", style=discord.ButtonStyle.secondary)
    async def add_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to add an artisan!", ephemeral=True)

    @discord.ui.button(label="Change Artisan", style=discord.ButtonStyle.secondary)
    async def add_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to Change an artisan!", ephemeral=True)

    @discord.ui.button(label="View Artisans", style=discord.ButtonStyle.secondary)
    async def add_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to View an artisan!", ephemeral=True)

@bot.tree.command(name="home", description="Open your guild home menu")
async def home(interaction: discord.Interaction):
    try:
        # DM the user first
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send("Welcome to your Guild Home!", view=HomeView())

        # Respond to the slash command so Discord doesn’t timeout
        await interaction.response.send_message(
            "I've sent you a DM with your home menu!", ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I couldn't DM you. Please enable DMs.", ephemeral=True
        )





@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(os.environ('DISCORD_TOKEN'))