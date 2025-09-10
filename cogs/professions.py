import discord
from discord.ext import commands
import os
import json

class Professions(commands.Cog):
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
        # Remove user from other professions
        for prof, members in self.artisan_registry.items():
            members.pop(str(user_id), None)
        if profession not in self.artisan_registry:
            self.artisan_registry[profession] = {}
        self.artisan_registry[profession][str(user_id)] = tier
        self.save_registry()

    # ----- Format Registry -----
    async def format_artisan_registry(self, bot: commands.Bot) -> discord.Embed:
        """Return an embed showing all users and their professions, grouped by type."""
        embed = discord.Embed(title="Current Professions", color=discord.Color.blurple())

        profession_icons = {
            "Fishing": "🎣", "Herbalism": "🌿", "Hunting": "🏹", "Lumberjacking": "🪓", "Mining": "⛏️",
            "Alchemy": "⚗️", "Animal Husbandry": "🐄", "Cooking": "🍳", "Farming": "🌾", "Lumber Milling": "🪵",
            "Metalworking": "⚒️", "Stonemasonry": "🧱", "Tanning": "🪶", "Weaving": "🧵",
            "Arcane Engineering": "🔮", "Armor Smithing": "🛡️", "Carpentry": "🪑", "Jewelry": "💍",
            "Leatherworking": "👢", "Scribing": "📜", "Tailoring": "🧶", "Weapon Smithing": "⚔️",
        }

        # Define categories
        categories = {
            "Gatherers": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
            "Processors": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
                           "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
            "Crafters": ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
                         "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"],
        }

        # Loop through each category
        for category_name, professions in categories.items():
            for profession in professions:
                members = self.artisan_registry.get(profession, {})
                member_list = []

                if not members:
                    member_list.append("- Empty -")
                else:
                    for user_id, tier in members.items():
                        user = bot.get_user(int(user_id))  # no await needed
                        if user:
                            member_list.append(f"{str(user)} ({tier})")
                        else:
                            member_list.append(f"Unknown User ({tier})")

                icon = profession_icons.get(profession, "")
                embed.add_field(
                    name=f"{category_name} — {icon} {profession}",
                    value="\n".join(member_list),
                    inline=False
                )

        return embed

# ----- Setup Cog -----
async def setup(bot):
    await bot.add_cog(Professions(bot))
