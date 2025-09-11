import discord
from discord.ext import commands
import json
import os
import logging
from typing import Dict, List, Any
from cogs.hub import refresh_hub  # live hub refresh

logger = logging.getLogger("AshesBot")
PROFILES_FILE = "data/profiles.json"
REGISTRY_FILE = "data/artisan_registry.json"

# Profession aliases for syncing with recipes.json and UI
PROFESSION_ALIASES: Dict[str, str] = {
    "Jeweler": "Jewelry",
    "Scribe": "Scribing",
    "Crafting": "Arcane Engineering",
    "Armorsmithing": "Armor Smithing",
    "Weaponsmithing": "Weapon Smithing",
}

TIER_COLORS = {
    "1": "⚪",  # Novice
    "2": "🟢",  # Apprentice
    "3": "🔵",  # Journeyman
    "4": "🟣",  # Master
    "5": "🟠",  # Grandmaster
}

# -------------------- JSON HELPERS --------------------
def _load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_profiles():
    return _load_json(PROFILES_FILE, {})

def save_profiles(data):
    _save_json(PROFILES_FILE, data)

def load_registry():
    return _load_json(REGISTRY_FILE, {})

def save_registry(data):
    _save_json(REGISTRY_FILE, data)


# ================================ Cog ================================
class Professions(commands.Cog):
    """Track each player's professions (max 2), tiers, and a guild registry."""
    def __init__(self, bot):
        self.bot = bot
        self.profiles: Dict[str, Dict[str, Any]] = load_profiles()
        self.artisan_registry: Dict[str, Dict[str, str]] = load_registry()

    # ---------- core helpers ----------
    def _norm(self, name: str) -> str:
        return PROFESSION_ALIASES.get(name, name)

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        uid = str(user_id)
        if uid not in self.profiles:
            self.profiles[uid] = {"professions": []}
            save_profiles(self.profiles)
        return self.profiles[uid]

    def get_user_professions(self, user_id: int) -> List[Dict[str, str]]:
        return self.get_profile(user_id).get("professions", [])

    # ---------- embeds ----------
    def build_user_professions_embed(self, member: discord.Member | discord.User):
        profs = self.get_user_professions(member.id)
        if not profs:
            desc = "*You haven’t selected any professions yet.*"
        else:
            lines = []
            for p in profs:
                tier = str(p.get("tier", "1"))
                lines.append(f"{TIER_COLORS.get(tier, '⚪')} **{p['name']}** — Tier {tier}")
            desc = "\n".join(lines)
        return discord.Embed(
            title=f"🛠️ {getattr(member, 'display_name', member.id)} — Current Professions",
            description=desc,
            color=discord.Color.blurple()
        )

    # ---------- mutations ----------
    def set_user_profession(self, user_id: int, profession: str, tier: str) -> bool:
        """Assign/update profession; max 2 per user. Returns True if set."""
        uid = str(user_id)
        profile = self.get_profile(user_id)
        profession = self._norm(profession)

        # Enforce 2 profession limit
        names = [p["name"] for p in profile["professions"]]
        if profession not in names and len(names) >= 2:
            return False

        # Replace if exists, otherwise add
        profile["professions"] = [p for p in profile["professions"] if p["name"] != profession]
        profile["professions"].append({"name": profession, "tier": str(max(1, min(int(tier), 5)))})
        save_profiles(self.profiles)

        # Update registry
        self.artisan_registry.setdefault(profession, {})[uid] = str(tier)
        save_registry(self.artisan_registry)
        return True

    def remove_user_profession(self, user_id: int, profession: str) -> bool:
        uid = str(user_id)
        profession = self._norm(profession)

        profile = self.get_profile(user_id)
        before = len(profile.get("professions", []))
        profile["professions"] = [p for p in profile.get("professions", []) if p["name"] != profession]
        changed = len(profile["professions"]) != before
        if changed:
            save_profiles(self.profiles)

        if profession in self.artisan_registry and uid in self.artisan_registry[profession]:
            del self.artisan_registry[profession][uid]
            if not self.artisan_registry[profession]:
                self.artisan_registry.pop(profession, None)
            save_registry(self.artisan_registry)
        return changed

    # ---------- commands ----------
    @commands.hybrid_command(name="professions", description="View your current professions.")
    async def professions_cmd(self, ctx: commands.Context):
        embed = self.build_user_professions_embed(ctx.author)
        await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="setprofession", description="Set or update your profession and tier.")
    async def set_profession_cmd(self, ctx: commands.Context, profession: str, tier: int):
        ok = self.set_user_profession(ctx.author.id, profession, str(tier))
        if ok:
            await ctx.reply(f"✅ Set **{self._norm(profession)}** to **Tier {max(1,min(tier,5))}**.", ephemeral=True)
            # refresh hub panels
            if getattr(ctx, "interaction", None):
                await refresh_hub(ctx.interaction, ctx.author.id, section="professions")
                await refresh_hub(ctx.interaction, ctx.author.id, section="profile")
        else:
            await ctx.reply("⚠️ You can only have up to **2 professions**.", ephemeral=True)

    @commands.hybrid_command(name="removeprofession", description="Remove one of your professions.")
    async def remove_profession_cmd(self, ctx: commands.Context, profession: str):
        changed = self.remove_user_profession(ctx.author.id, profession)
        if changed:
            await ctx.reply(f"🗑️ Removed **{self._norm(profession)}**.", ephemeral=True)
            if getattr(ctx, "interaction", None):
                await refresh_hub(ctx.interaction, ctx.author.id, section="professions")
                await refresh_hub(ctx.interaction, ctx.author.id, section="profile")
        else:
            await ctx.reply("⚠️ You don't have that profession.", ephemeral=True)

    @commands.hybrid_command(name="tiers", description="Show profession tier legend.")
    async def tiers_cmd(self, ctx: commands.Context):
        embed = discord.Embed(title="📜 Profession Tier Legend", color=discord.Color.blurple())
        labels = {"1": "Novice", "2": "Apprentice", "3": "Journeyman", "4": "Master", "5": "Grandmaster"}
        for t, emoji in TIER_COLORS.items():
            embed.add_field(name=f"{emoji} {labels[t]}", value=f"**Tier {t}**", inline=True)
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Professions(bot))
