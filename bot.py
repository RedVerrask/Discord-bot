import discord
from discord.ext import commands
import sqlite3
import os
import asyncio  # make sure this is at the top of your file
import json

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
        await interaction.response.send_message("Artisan Menu:", view=AddArtisanView(), ephemeral=True)
        
            
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

REGISTRY_FILE = "artisan_registry.json"

# Load registry from file if it exists
def load_registry():
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    else:
        # default empty registry with dicts, not lists
        return {
            "Fishing": {},
            "Herbalism": {},
            "Hunting": {},
            "Lumberjacking": {},
            "Mining": {},
            
            "Alchemy": {},
            "Animal Husbandry": {},
            "Cooking": {},
            "Farming": {},
            "Lumber Milling": {},
            "Metalworking": {},
            "Stonemasonry": {},
            "Tanning": {},
            "Weaving": {},
            
            "Arcane Engineering": {},
            "Armor Smithing": {},
            "Carpentry": {},
            "Jewelry": {},
            "Leatherworking": {},
            "Scribing": {},
            "Tailoring": {},
            "Weapon Smithing": {},
        }


def save_registry():
    with open(REGISTRY_FILE, "w") as f:
        json.dump(artisan_registry, f, indent=4)


artisan_registry = load_registry()


profession_icons = {
    "Fishing": "🎣",
    "Herbalism": "🌿",
    "Hunting": "🏹",
    "Lumberjacking": "🪓",
    "Mining": "⛏️",

    "Alchemy": "⚗️",
    "Animal Husbandry": "🐄",
    "Cooking": "🍳",
    "Farming": "🌾",
    "Lumber Milling": "🪵",
    "Metalworking": "⚒️",
    "Stonemasonry": "🧱",
    "Tanning": "🪶",
    "Weaving": "🧵",

    "Arcane Engineering": "🔮",
    "Armor Smithing": "🛡️",
    "Carpentry": "🪑",
    "Jewlry": "💍",
    "Leatherworking": "👢",
    "Scribing": "📜",
    "Tailoring": "🧶",
    "Weapon Smithing": "⚔️",
}

def set_user_profession(user_id: int, new_profession: str, tier: str):
    # Remove user from any old profession
    for profession, members in artisan_registry.items():
        if str(user_id) in members:  # JSON saves keys as strings
            del members[str(user_id)]

    # Make sure the profession exists
    if new_profession not in artisan_registry:
        artisan_registry[new_profession] = {}

    # Add to new profession with tier
    artisan_registry[new_profession][str(user_id)] = tier

    # Save changes
    save_registry()




class TierSelectView(discord.ui.View):
    def __init__(self, user_id, profession):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.profession = profession

    @discord.ui.select(
        placeholder="Choose your tier...",
        options=[
            discord.SelectOption(label="Novice", description="Just starting out"),
            discord.SelectOption(label="Apprentice", description="Learning the ropes"),
            discord.SelectOption(label="Journeyman", description="Skilled worker"),
            discord.SelectOption(label="Master", description="Expert level"),
            discord.SelectOption(label="Grandmaster", description="The very best"),
        ]
    )
    async def select_tier(self, interaction: discord.Interaction, select: discord.ui.Select):
        tier = select.values[0]
        set_user_profession(self.user_id, self.profession, tier)

        await interaction.response.send_message(f"✅ You are now a **{tier} {self.profession}**!",ephemeral=True)

async def format_artisan_registry(bot: discord.Client):
    embed = discord.Embed(
        title="⚒️ Artisan Registry",
        description="Current professions and their members:",
        color=discord.Color.blurple()
    )

    for profession, members in artisan_registry.items():
        if members:  # only show professions with members
            member_names = []
            for uid, tier in members.items():
                user = bot.get_user(int(uid))  # convert string back to int
                if not user:
                    try:
                        user = await bot.fetch_user(int(uid))
                    except:
                        user = None
                if user:
                    member_names.append(f"• {user.display_name} ({tier})")
                else:
                    member_names.append(f"• Unknown ({uid}) ({tier})")
            
            icon = profession_icons.get(profession, "🎓")
            embed.add_field(name=f"{icon} {profession}", value="\n".join(member_names), inline=False)
    
    if all(len(members) == 0 for members in artisan_registry.values()):
        embed.description = "*No artisans have joined any profession yet.*"
    
    return embed



class AddGathererView(discord.ui.View):
    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary)
    async def add_Miner(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        await interaction.response.send_message("Select your Mining tier:",view=TierSelectView(user_id, "Mining"),ephemeral=True)




    
    
    @discord.ui.button(label="Lumberjacking", style=discord.ButtonStyle.secondary)
    async def add_LumberJacking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("LumberJacker Selected!", view=HomeView(), ephemeral=True)
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary)
    async def add_Fisher(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)
    
    @discord.ui.button(label="Herbalism", style=discord.ButtonStyle.secondary)
    async def add_Herbing(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Hunting", style=discord.ButtonStyle.secondary)
    async def add_Hunter(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="back?", style=discord.ButtonStyle.secondary)
    async def add_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("back?", view=HomeView(), ephemeral=True)
        
class AddProcessingView(discord.ui.View):

    @discord.ui.button(label="Stonemasonry", style=discord.ButtonStyle.secondary)
    async def add_Stonemasonry(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Tanning", style=discord.ButtonStyle.secondary)
    async def add_Tanner(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Weaving", style=discord.ButtonStyle.secondary)
    async def add_Weaver(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Metalworking", style=discord.ButtonStyle.secondary)
    async def add_Metalworker(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Farming", style=discord.ButtonStyle.secondary)
    async def add_Farmer(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)
    
    @discord.ui.button(label="Lumber Milling", style=discord.ButtonStyle.secondary)
    async def add_LumberMilling(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Alchemy", style=discord.ButtonStyle.secondary)
    async def add_Alchemy(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Animal Husbandry", style=discord.ButtonStyle.secondary)
    async def add_Anm_Hus(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Cooking", style=discord.ButtonStyle.secondary)
    async def add_Cook(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="back?", style=discord.ButtonStyle.secondary)
    async def add_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("back?", view=HomeView(), ephemeral=True)

class AddCraftingProfessionView(discord.ui.View):
    @discord.ui.button(label="Arcane Engineering", style=discord.ButtonStyle.secondary)
    async def add_ArcaneEngineer(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)
    
    @discord.ui.button(label="Armor Smithing", style=discord.ButtonStyle.secondary)
    async def add_ArmorSmithing(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Carpentry", style=discord.ButtonStyle.secondary)
    async def add_Carpenter(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Jewelry", style=discord.ButtonStyle.secondary)
    async def add_Jeweler(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Leatherworking", style=discord.ButtonStyle.secondary)
    async def add_Leatherworker(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Scribing", style=discord.ButtonStyle.secondary)
    async def add_Scriber(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)

    @discord.ui.button(label="Tailoring", style=discord.ButtonStyle.secondary)
    async def add_Tailoring(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)
    
    @discord.ui.button(label="Weapon Smithing", style=discord.ButtonStyle.secondary)
    async def add_WeaponSmithy(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        set_user_profession(user_id, button.label)
        #Add user to profession if not already added
        await interaction.response.send_message(" You are now in the **"+ button.label +"** profession!", view=HomeView(), ephemeral=True)
    
    @discord.ui.button(label="back?", style=discord.ButtonStyle.secondary)
    async def add_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("back?", view=HomeView(), ephemeral=True)

class AddArtisanView(discord.ui.View):
    @discord.ui.button(label="Gathering Profession", style=discord.ButtonStyle.secondary)
    async def add_GatherProfession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Gathering: ", view=AddGathererView(), ephemeral=True)

    @discord.ui.button(label="Processing Profession", style=discord.ButtonStyle.secondary)
    async def add_ProcessingProfession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Processing: ", view=AddProcessingView(), ephemeral=True)
    
    @discord.ui.button(label="Crafting Profession", style=discord.ButtonStyle.secondary)
    async def add_CraftingProfession(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(" Crafting: ", view=AddCraftingProfessionView(), ephemeral=True)

    @discord.ui.button(label="View Current Professions", style=discord.ButtonStyle.secondary)
    async def view_artisans(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await format_artisan_registry(interaction.client)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def add_Back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("what can I do for ya Scrub?", view=HomeView(), ephemeral=True)
        

class ArtisanView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Artisan", style=discord.ButtonStyle.secondary)
    async def add_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to add an artisan!", view=AddArtisanView(), ephemeral=True)


    @discord.ui.button(label="Change Artisan", style=discord.ButtonStyle.secondary)
    async def change_artisan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to Change an artisan!", view=AddArtisanView(), ephemeral=True)

    @discord.ui.button(label="View Artisans", style=discord.ButtonStyle.secondary)
    async def view_artisans(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You chose to View artisans!", ephemeral=True)

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