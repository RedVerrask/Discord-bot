import discord
from discord.ext import commands
import os
import json

class Professions(commands.Cog):
    # ... your other methods ...

    async def format_artisan_registry(self, bot: commands.Bot) -> discord.Embed:
        """Return an embed showing all users and their professions."""
        embed = discord.Embed(title="Current Professions", color=discord.Color.blurple())

        # Profession icons
        profession_icons = {"Fishing": "🎣", "Herbalism": "🌿", "Hunting": "🏹", "Lumberjacking": "🪓", "Mining": "⛏️",
        "Alchemy": "⚗️", "Animal Husbandry": "🐄", "Cooking": "🍳", "Farming": "🌾", "Lumber Milling": "🪵",
        "Metalworking": "⚒️", "Stonemasonry": "🧱", "Tanning": "🪶", "Weaving": "🧵",
        "Arcane Engineering": "🔮", "Armor Smithing": "🛡️", "Carpentry": "🪑", "Jewelry": "💍",
        "Leatherworking": "👢", "Scribing": "📜", "Tailoring": "🧶", "Weapon Smithing": "⚔️",}

        for profession, members in self.artisan_registry.items():
            member_list = []
            if not members:
                member_list.append("- Empty -")
            else:
                for user_id, tier in members.items():
                    try:
                        user = await bot.fetch_user(int(user_id))
                        member_list.append(f"{str(user)} ({tier})")  # Shows unique username
                    except discord.NotFound:
                        member_list.append(f"Unknown User ({tier})")
        
            icon = profession_icons.get(profession, "")
            embed.add_field(name=f"{icon} {profession}", value="\n".join(member_list), inline=False)

        return embed



    def __init__(self, bot):
        self.bot = bot
        self.REGISTRY_FILE = "artisan_registry.json"
        self.artisan_registry = self.load_registry()

    # ----- Registry Functions -----
    def load_registry(self):
        if os.path.exists(self.REGISTRY_FILE):
            with open(self.REGISTRY_FILE, "r") as f:
                return json.load(f)
        return {
            "Fishing": {}, "Herbalism": {}, "Hunting": {}, "Lumberjacking": {}, "Mining": {},
            "Alchemy": {}, "Animal Husbandry": {}, "Cooking": {}, "Farming": {}, "Lumber Milling": {},
            "Metalworking": {}, "Stonemasonry": {}, "Tanning": {}, "Weaving": {},
            "Arcane Engineering": {}, "Armor Smithing": {}, "Carpentry": {}, "Jewelry": {},
            "Leatherworking": {}, "Scribing": {}, "Tailoring": {}, "Weapon Smithing": {},
        }

    def save_registry(self):
        with open(self.REGISTRY_FILE, "w") as f:
            json.dump(self.artisan_registry, f, indent=4)

    def set_user_profession(self, user_id: int, profession: str, tier: str):
        for prof, members in self.artisan_registry.items():
            members.pop(str(user_id), None)
        if profession not in self.artisan_registry:
            self.artisan_registry[profession] = {}
        self.artisan_registry[profession][str(user_id)] = tier
        self.save_registry()

# ----- Setup Cog -----
async def setup(bot):
    await bot.add_cog(Professions(bot))
