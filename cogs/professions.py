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
    async def format_artisan_registry(self, bot: commands.Bot, guild_id: int = None) -> discord.Embed:
        """
        Returns a single embed showing all current professions in columns:
        - Categories are horizontal: Gatherers | Processors | Crafters
        - Each user appears next to their profession: Fishing - Red (*tier*)
        - Uses guild nicknames if available; falls back to global username.
        """
        profession_icons = {
            "Fishing": "🎣", "Herbalism": "🌿", "Hunting": "🏹", "Lumberjacking": "🪓", "Mining": "⛏️",
            "Alchemy": "⚗️", "Animal Husbandry": "🐄", "Cooking": "🍳", "Farming": "🌾", "Lumber Milling": "🪵",
            "Metalworking": "⚒️", "Stonemasonry": "🧱", "Tanning": "🪶", "Weaving": "🧵",
            "Arcane Engineering": "🔮", "Armor Smithing": "🛡️", "Carpentry": "🪑", "Jewelry": "💍",
            "Leatherworking": "👢", "Scribing": "📜", "Tailoring": "🧶", "Weapon Smithing": "⚔️",
        }

        categories = {
            "Gatherers": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
            "Processors": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
                        "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
            "Crafters": ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
                        "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"],
        }

        embed = discord.Embed(title="Current Professions", color=discord.Color.blurple())

        # Fetch the guild if provided
        guild = bot.get_guild(guild_id) if guild_id else None

        # We'll build one "row" per profession line
        # Determine max number of professions in a category
        max_rows = max(len(categories[cat]) for cat in categories)

        for i in range(max_rows):
            line_parts = []
            for cat_name in ["Gatherers", "Processors", "Crafters"]:
                professions = categories[cat_name]
                if i < len(professions):
                    prof = professions[i]
                    members = self.artisan_registry.get(prof, {})

                    if members:
                        member_texts = []
                        for user_id, tier in members.items():
                            display_name = "Unknown"
                            # Try guild nickname first
                            if guild:
                                member = guild.get_member(int(user_id))
                                if member:
                                    display_name = member.display_name
                            # Fallback to global username
                            if display_name == "Unknown":
                                try:
                                    user = await bot.fetch_user(int(user_id))
                                    display_name = user.name
                                except Exception:
                                    pass
                            member_texts.append(f"{display_name} (*{tier}*)")
                        line = f"{profession_icons.get(prof,'')} {prof} - " + ", ".join(member_texts)
                    else:
                        line = f"{profession_icons.get(prof,'')} {prof} - *Empty*"
                else:
                    line = ""
                line_parts.append(line.ljust(40))  # pad for column alignment
            embed.add_field(name="\u200b", value="".join(line_parts), inline=False)

        return embed



# ----- Setup Cog -----
async def setup(bot):
    await bot.add_cog(Professions(bot))
