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
        Return an embed showing all users and their professions:
        - Filled professions first
        - Empty professions below
        - Grouped by category, column-aligned for cleaner view
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
        max_columns = 4  # Users per line

        guild = bot.get_guild(guild_id) if guild_id else None

        for category_name, professions in categories.items():
            embed.add_field(name=f"**{category_name}**", value="\u200b", inline=False)

            # --- First: filled professions ---
            for profession in professions:
                members = self.artisan_registry.get(profession, {})
                if not members:
                    continue  # skip empty for now

                username_line = ""
                tier_line = ""
                col_count = 0
                table_lines = []

                for user_id, tier in members.items():
                    display_name = "Unknown"

                    # Try fetching member from guild first
                    member = guild.get_member(int(user_id)) if guild else None
                    if member:
                        display_name = member.display_name
                    else:
                        try:
                            user = await bot.fetch_user(int(user_id))
                            display_name = user.name
                        except Exception:
                            display_name = "Unknown"

                    display_name_padded = display_name.ljust(15)
                    tier_padded = tier.ljust(15)
                    username_line += display_name_padded
                    tier_line += f"*{tier_padded}*"
                    col_count += 1

                    if col_count >= max_columns:
                        table_lines.append(username_line)
                        table_lines.append(tier_line)
                        username_line = ""
                        tier_line = ""
                        col_count = 0

                if username_line:
                    table_lines.append(username_line)
                    table_lines.append(tier_line)

                embed.add_field(
                    name=f"{profession_icons.get(profession,'')} {profession}",
                    value=f"```{chr(10).join(table_lines)}```",
                    inline=False
                )

            # --- Second: empty professions ---
            for profession in professions:
                members = self.artisan_registry.get(profession, {})
                if members:
                    continue  # skip filled

                embed.add_field(
                    name=f"{profession_icons.get(profession,'')} {profession}",
                    value="- Empty -",
                    inline=False
                )

        return embed


# ----- Setup Cog -----
async def setup(bot):
    await bot.add_cog(Professions(bot))
