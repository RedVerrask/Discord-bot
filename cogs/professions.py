import discord
from discord.ext import commands
import os
import json

class Professions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.REGISTRY_FILE = "artisan_registry.json"
        self.artisan_registry = self.load_registry()

    # ------------------------------------------------------
    # Registry Loader / Saver
    # ------------------------------------------------------
    def load_registry(self):
        """Loads the artisan registry from file or initializes defaults."""
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
        """Saves the artisan registry to file."""
        with open(self.REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.artisan_registry, f, indent=4)

    # ------------------------------------------------------
    # Profession Assignment
    # ------------------------------------------------------
    def set_user_profession(self, user_id: int, profession: str, tier: str):
        """
        Assigns or updates a user's profession and tier.
        Now allows MULTIPLE professions instead of removing previous ones.
        """
        if profession not in self.artisan_registry:
            self.artisan_registry[profession] = {}
        self.artisan_registry[profession][str(user_id)] = tier
        self.save_registry()

    # ------------------------------------------------------
    # Profession Retrieval
    # ------------------------------------------------------
    def get_user_professions(self, user_id: int):
        """Returns a list of professions the user currently has."""
        user_id_str = str(user_id)
        return [prof for prof, members in self.artisan_registry.items() if user_id_str in members]

    def get_user_tier(self, user_id: int, profession: str):
        """Returns the user's tier for a given profession, or None."""
        return self.artisan_registry.get(profession, {}).get(str(user_id))

    def has_profession(self, user_id: int):
        """Checks if a user has at least one profession."""
        return bool(self.get_user_professions(user_id))

    def can_learn_recipe(self, user_id: int, profession: str, required_level: int):
        """
        Returns True if the user has the profession and meets the tier requirement.
        Recipes can use this to restrict access.
        """
        tier = self.get_user_tier(user_id, profession)
        if tier is None:
            return False  # Doesn't have the profession at all
        try:
            return int(tier) >= int(required_level)
        except ValueError:
            return False

    # ------------------------------------------------------
    # Profession Registry Formatting (Embeds)
    # ------------------------------------------------------
    async def format_artisan_registry(self, bot: commands.Bot, guild_id: int = None) -> list:
        """Creates two embeds — filled & empty professions for the guild."""
        profession_icons = {
            "Fishing": "🎣", "Herbalism": "🌿", "Hunting": "🏹", "Lumberjacking": "🪓", "Mining": "⛏️",
            "Alchemy": "⚗️", "Animal Husbandry": "🐄", "Cooking": "🍳", "Farming": "🌾", "Lumber Milling": "🪵",
            "Metalworking": "⚒️", "Stonemasonry": "🧱", "Tanning": "🪶", "Weaving": "🧵",
            "Arcane Engineering": "🔮", "Armor Smithing": "🛡️", "Carpentry": "🪑", "Jewelry": "💍",
            "Leatherworking": "👢", "Scribing": "📜", "Tailoring": "🧶", "Weapon Smithing": "⚔️",
        }

        tier_colors = {
            "1": "⚪",  # Novice
            "2": "🟢",  # Apprentice
            "3": "🔵",  # Journeyman
            "4": "🟣",  # Master
            "5": "🟠"   # Grandmaster
        }

        categories = {
            "Gatherers": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
            "Processors": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
                           "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
            "Crafters": ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
                         "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"],
        }

        filled_embed = discord.Embed(
            title="📜 Current Professions",
            description="Here are the currently registered professions:",
            color=discord.Color.blurple()
        )

        empty_embed = discord.Embed(
            title="📭 Vacant Professions",
            description="Professions with no registered members:",
            color=discord.Color.greyple()
        )

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
                            try:
                                user = await bot.fetch_user(int(user_id))
                                display_name = getattr(user, "display_name", None) or getattr(user, "name", f"User {user_id}")
                            except Exception:
                                display_name = f"User {user_id}"

                        color = tier_colors.get(str(tier), "⚪")
                        member_lines.append(f"{display_name} — {color} Tier {tier}")
                    filled_text += f"{profession_icons.get(prof,'')} **{prof}**: " + ", ".join(member_lines) + "\n"
                else:
                    empty_text += f"{profession_icons.get(prof,'')} {prof} — *Empty*\n"

            if filled_text:
                filled_embed.add_field(name=f"**{category_name}**", value=filled_text, inline=False)
            if empty_text:
                empty_embed.add_field(name=f"**{category_name}**", value=empty_text, inline=False)

        embeds = []
        if filled_embed.fields:
            embeds.append(filled_embed)
        if empty_embed.fields:
            embeds.append(empty_embed)

        if not embeds:
            embeds.append(discord.Embed(
                title="📭 No Professions Found",
                description="Nobody has registered any professions yet.",
                color=discord.Color.greyple()
            ))

        return embeds


# ------------------------------------------------------
# Setup Cog
# ------------------------------------------------------
async def setup(bot):
    await bot.add_cog(Professions(bot))
