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
        await interaction.response.send_message("Artisan Menu:", view=ArtisanView(), ephemeral=True)
        
            
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

class AddGathererView(discord.ui.View):
    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary)
    async def add_Miner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Miner Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Lumberjacking", style=discord.ButtonStyle.secondary)
    async def add_LumberJacking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("LumberJacker Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary)
    async def add_Fisher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fishing Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Herbalism", style=discord.ButtonStyle.secondary)
    async def add_Herbing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Herber Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Hunting", style=discord.ButtonStyle.secondary)
    async def add_Hunter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Hunter Selected!", view=AddGathererView(), ephemeral=True)
        
class AddProcessing(discord.ui.View):

    @discord.ui.button(label="Stonemasonry", style=discord.ButtonStyle.secondary)
    async def add_Stonemasonry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Stoney Masey Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Tanning", style=discord.ButtonStyle.secondary)
    async def add_Tanner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Tanner Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Weaving", style=discord.ButtonStyle.secondary)
    async def add_Weaver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Weaver Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Metalworking", style=discord.ButtonStyle.secondary)
    async def add_Metalworker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Metalworker Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Farming", style=discord.ButtonStyle.secondary)
    async def add_Farmer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Farmer Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Lumber Milling", style=discord.ButtonStyle.secondary)
    async def add_LumberMilling(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Lumber Miller Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Alchemy", style=discord.ButtonStyle.secondary)
    async def add_Alchemy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Alchemy Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Animal Husbandry", style=discord.ButtonStyle.secondary)
    async def add_Anm_Hus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Animal Breeder Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Cooking", style=discord.ButtonStyle.secondary)
    async def add_Cook(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Your Cooked!", view=AddGathererView(), ephemeral=True)

class AddCraftingProfessionView(discord.ui.View):
    @discord.ui.button(label="Arcane Engineering", style=discord.ButtonStyle.secondary)
    async def add_ArcaneEngineer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Arcane Engi Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Armor Smithing", style=discord.ButtonStyle.secondary)
    async def add_ArmorSmithing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Armor Smithy Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Carpentry", style=discord.ButtonStyle.secondary)
    async def add_Carpenter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Carpenter Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Jewelry", style=discord.ButtonStyle.secondary)
    async def add_Jeweler(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Jeweler Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Leatherworking", style=discord.ButtonStyle.secondary)
    async def add_Leatherworker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("LeatherWorking Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Scribing", style=discord.ButtonStyle.secondary)
    async def add_Scriber(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Scriber Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Tailoring", style=discord.ButtonStyle.secondary)
    async def add_Tailoring(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Tailor Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Weapon Smithing", style=discord.ButtonStyle.secondary)
    async def add_WeaponSmithy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Weapon Smith Selected!", view=AddGathererView(), ephemeral=True)

class AddArtisanView(discord.ui.View):
    @discord.ui.button(label="Gathering Profession", style=discord.ButtonStyle.secondary)
    async def add_GatherProfession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Weaver Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Processing Profession", style=discord.ButtonStyle.secondary)
    async def add_Gatherer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Weaver Selected!", view=AddGathererView(), ephemeral=True)
    
    @discord.ui.button(label="Crafting Profession", style=discord.ButtonStyle.secondary)
    async def add_Gatherer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Weaver Selected!", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def add_Crafter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Crafter Selected!", ephemeral=True)
        

class ArtisanView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Artisan", style=discord.ButtonStyle.secondary)
    async def add_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to add an artisan!", view=AddArtisanView(), ephemeral=True)


    @discord.ui.button(label="Change Artisan", style=discord.ButtonStyle.secondary)
    async def change_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to Change an artisan!", ephemeral=True)

    @discord.ui.button(label="View Artisans", style=discord.ButtonStyle.secondary)
    async def view_artisans(self, interaction: discord.Interaction, button: discord.ui.Button):
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

bot.run(os.environ['DISCORD_TOKEN'])