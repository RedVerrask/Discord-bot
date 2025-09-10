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
            with open(self.REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "Fishing": {}, "Herbalism": {}, "Hunting": {}, "Lumberjacking": {}, "Mining": {},
            "Alchemy": {}, "Animal Husbandry": {}, "Cooking": {}, "Farming": {}, "Lumber Milling": {},
            "Metalworking": {}, "Stonemasonry": {}, "Tanning": {}, "Weaving": {},
            "Arcane Engineering": {}, "Armor Smithing": {}, "Carpentry": {}, "Jewelry": {},
            "Leatherworking": {}, "Scribing": {}, "Tailoring": {}, "Weapon Smithing": {},
        }

    def save_registry(self):
        with open(self.REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.artisan_registry, f, indent=4)

    def set_user_profession(self, user_id: int, profession: str, tier: str):
        # Remove user from other professions if you only allow one profession
        for prof, members in self.artisan_registry.items():
            members.pop(str(user_id), None)

        if profession not in self.artisan_registry:
            self.artisan_registry[profession] = {}
        self.artisan_registry[profession][str(user_id)] = tier
        self.save_registry()

    # ----- Get Professions for User -----
    def get_user_professions(self, user_id: int):
        """Return a list of profession names the user currently has."""
        user_id_str = str(user_id)
        professions = [prof for prof, members in self.artisan_registry.items() if user_id_str in members]
        return professions

    # ----- Check if User Has Profession -----
    def has_profession(self, user_id: int):
        return bool(self.get_user_professions(user_id))

    # ----- Format Registry for Display -----
    async def format_artisan_registry(self, bot: commands.Bot, guild_id: int = None) -> list:
        profession_icons = {
            "Fishing": "🎣", "Herbalism": "🌿", "Hunting": "🏹", "Lumberjacking": "🪓", "Mining": "⛏️",
            "Alchemy": "⚗️", "Animal Husbandry": "🐄", "Cooking": "🍳", "Farming": "🌾", "Lumber Milling": "🪵",
            "Metalworking": "⚒️", "Stonemasonry": "🧱", "Tanning": "🪶", "Weaving": "🧵",
            "Arcane Engineering": "🔮", "Armor Smithing": "🛡️", "Carpentry": "🪑", "Jewelry": "💍",
            "Leatherworking": "👢", "Scribing": "📜", "Tailoring": "🧶", "Weapon Smithing": "⚔️",
        }

        tier_colors = {
            "1": "⚪",
            "2": "🟢",
            "3": "🔵",
            "4": "🟣",
            "5": "🟠"
        }

        categories = {
            "Gatherers": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
            "Processors": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
                        "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
            "Crafters": ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
                        "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"],
        }

        filled_embed = discord.Embed(title="Current Professions", color=discord.Color.blurple())
        empty_embed = discord.Embed(title="Vacant Professions", color=discord.Color.greyple())
        guild = bot.get_guild(guild_id) if guild_id else None

        for category_name, professions in categories.items():
            filled_text = ""
            empty_text = ""

            for prof in professions:
                members = self.artisan_registry.get(prof, {})
                if members:
                    member_lines = []
                    for user_id, tier in members.items():
                        display_name = "Unknown"
                        if guild:
                            member = guild.get_member(int(user_id))
                            if member:
                                display_name = member.display_name
                        if display_name == "Unknown":
                            user = await bot.fetch_user(int(user_id))
                            display_name = user.name

                        color = tier_colors.get(str(tier), "⚪")
                        member_lines.append(f"{display_name} - {color} Tier {tier}")
                    filled_text += f"{profession_icons.get(prof,'')} {prof}: " + ", ".join(member_lines) + "\n"
                else:
                    empty_text += f"{profession_icons.get(prof,'')} {prof} - *Empty*\n"

            if filled_text:
                filled_embed.add_field(name=f"**{category_name}**", value=filled_text, inline=False)
            if empty_text:
                empty_embed.add_field(name=f"**{category_name}**", value=empty_text, inline=False)

        return [filled_embed, empty_embed]

# ----- Setup Cog -----
async def setup(bot):
    await bot.add_cog(Professions(bot))
