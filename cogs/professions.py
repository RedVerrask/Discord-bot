import discord
from discord.ext import commands
import json
import os

PROFILES_FILE = "data/profiles.json"
REGISTRY_FILE = "data/artisan_registry.json"

# Profession aliases for syncing with recipes.json
PROFESSION_ALIASES = {
    "Jeweler": "Jewelry",
    "Scribe": "Scribing",
    "Crafting": "Arcane Engineering"
}

TIER_COLORS = {
    "1": "⚪",  # Novice
    "2": "🟢",  # Apprentice
    "3": "🔵",  # Journeyman
    "4": "🟣",  # Master
    "5": "🟠"   # Grandmaster
}


# ======================================================
# Utility: Profiles + Registry Sync
# ======================================================
def load_profiles():
    if not os.path.exists(PROFILES_FILE):
        return {}
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profiles(data):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_registry(data):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ======================================================
# Professions Cog
# ======================================================
class Professions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profiles = load_profiles()
        self.artisan_registry = load_registry()

    # -----------------------------
    # Get Player Profile
    # -----------------------------
    def get_profile(self, user_id):
        user_id = str(user_id)
        if user_id not in self.profiles:
            self.profiles[user_id] = {"professions": []}
            save_profiles(self.profiles)
        return self.profiles[user_id]

    # -----------------------------
    # Assign / Update Profession
    # -----------------------------
    def set_user_profession(self, user_id, profession, tier):
        """Assign or update profession, enforcing 2 max limit."""
        user_id_str = str(user_id)
        profile = self.get_profile(user_id)

        # Alias mapping
        profession = PROFESSION_ALIASES.get(profession, profession)

        # Check if they already have 2 professions
        if profession not in [p["name"] for p in profile["professions"]] and len(profile["professions"]) >= 2:
            return False  # Too many professions selected

        # Update profile data
        profile["professions"] = [
            p for p in profile["professions"] if p["name"] != profession
        ]
        profile["professions"].append({"name": profession, "tier": tier})
        save_profiles(self.profiles)

        # Update global artisan registry
        if profession not in self.artisan_registry:
            self.artisan_registry[profession] = {}
        self.artisan_registry[profession][user_id_str] = tier
        save_registry(self.artisan_registry)
        return True
    
    def remove_user_profession(self, user_id, profession):
        """Remove a profession from user (updates profile + registry)."""
        user_id_str = str(user_id)
        # normalize
        profession = PROFESSION_ALIASES.get(profession, profession)

        # profiles.json
        profile = self.get_profile(user_id)
        before = len(profile.get("professions", []))
        profile["professions"] = [p for p in profile.get("professions", []) if p["name"] != profession]
        if len(profile["professions"]) != before:
            save_profiles(self.profiles)

        # artisan_registry.json
        if profession in self.artisan_registry and user_id_str in self.artisan_registry[profession]:
            del self.artisan_registry[profession][user_id_str]
            if not self.artisan_registry[profession]:
                # Cleanup empty profession bucket (optional)
                self.artisan_registry.pop(profession, None)
            save_registry(self.artisan_registry)
    # -----------------------------
    # Get Player Professions
    # -----------------------------
    def get_user_professions(self, user_id):
        profile = self.get_profile(user_id)
        return profile.get("professions", [])

    # -----------------------------
    # Profession Legend Embed
    # -----------------------------
    def get_tier_legend(self):
        embed = discord.Embed(
            title="📜 Profession Tier Legend",
            description="Color indicators for artisan tiers",
            color=discord.Color.blurple()
        )
        for tier, emoji in TIER_COLORS.items():
            label = {
                "1": "Novice",
                "2": "Apprentice",
                "3": "Journeyman",
                "4": "Master",
                "5": "Grandmaster"
            }[tier]
            embed.add_field(name=f"{emoji} {label}", value=f"Tier {tier}", inline=True)
        return embed

    # -----------------------------
    # View Current Professions (Guild-Wide)
    # -----------------------------
    async def format_artisan_registry(self, bot: commands.Bot, guild_id: int = None):
        """Guild-wide professions overview."""
        guild = bot.get_guild(guild_id) if guild_id else None
        embed = discord.Embed(
            title="🏆 Guild Artisan Registry",
            description="Current artisans & their tiers",
            color=discord.Color.gold()
        )

        for profession, members in self.artisan_registry.items():
            if not members:
                continue
            lines = []
            for user_id, tier in members.items():
                member = guild.get_member(int(user_id)) if guild else None
                name = member.display_name if member else f"User {user_id}"
                color = TIER_COLORS.get(str(tier), "⚪")
                lines.append(f"{color} {name} — Tier {tier}")
            embed.add_field(
                name=f"{profession} ({len(members)} members)",
                value="\n".join(lines),
                inline=False
            )
        return [embed]


# ======================================================
# Cog Setup
# ======================================================
async def setup(bot):
    await bot.add_cog(Professions(bot))
