# cogs/professions.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from typing import Dict, List, Optional

from utils.data import load_json, save_json
from cogs.hub import refresh_hub

PROFESSIONS_FILE = "data/professions.json"

# Expand as needed
ALL_PROFESSIONS = [
    "Blacksmithing", "Leatherworking", "Alchemy", "Cooking",
    "Fishing", "Hunting", "Herbalism", "Lumberjacking",
    "Mining", "Weaving", "Scribing", "Jewelry"
]

TIERS = ["Novice", "Apprentice", "Journeyman", "Master", "Grandmaster"]

# Enforce your “2 only” logic
MAX_PROFESSIONS = 2


class Professions(commands.Cog):
    """Handles profession selection and tier changes with guardrails."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Storage shape on disk:
        # { "<user_id>": { "professions": { "<name>": "<tier>" } } }
        self._data: Dict[str, Dict[str, Dict[str, str]]] = load_json(PROFESSIONS_FILE, {})

    # ---------------- persistence ----------------
    def _save(self):
        save_json(PROFESSIONS_FILE, self._data)

    # ---------------- internal helpers ----------------
    def _store_for(self, user_id: int) -> Dict[str, Dict[str, str]]:
        return self._data.setdefault(str(user_id), {"professions": {}})

    @staticmethod
    def _valid_tier(tier: str) -> bool:
        return tier in TIERS

    # ---------------- public API (what other cogs use) ----------------
    def get_user_profession_map(self, user_id: int) -> Dict[str, str]:
        """Return { profession_name: tier }."""
        return self._store_for(user_id)["professions"]

    def get_user_professions(self, user_id: int) -> List[Dict[str, str]]:
        """Return list of {name, tier} to match Hub’s rendering."""
        profs = self.get_user_profession_map(user_id)
        return [{"name": n, "tier": t} for n, t in profs.items()]

    def add_profession(self, user_id: int, profession: str) -> (bool, str):
        """Add a profession at Novice. Returns (ok, message)."""
        profs = self.get_user_profession_map(user_id)

        if profession not in ALL_PROFESSIONS:
            return False, "⚠️ Invalid profession."

        if profession in profs:
            return False, f"⚠️ You already have **{profession}**."

        if len(profs) >= MAX_PROFESSIONS:
            return False, f"⚠️ You can only have **{MAX_PROFESSIONS}** professions."

        profs[profession] = TIERS[0]  # Novice
        self._save()
        return True, f"✅ Added **{profession}** (Novice)."

    def remove_profession(self, user_id: int, profession: str) -> bool:
        profs = self.get_user_profession_map(user_id)
        if profession in profs:
            del profs[profession]
            self._save()
            return True
        return False

    def set_profession_tier(self, user_id: int, profession: str, tier: str) -> (bool, str):
        """Change tier with validation. Returns (ok, msg)."""
        profs = self.get_user_profession_map(user_id)
        if profession not in profs:
            return False, "⚠️ You don’t have that profession."
        if not self._valid_tier(tier):
            return False, "⚠️ Invalid tier."
        profs[profession] = tier
        self._save()
        return True, f"✅ Set **{profession}** → **{tier}**."

    # ---------------- Views ----------------
    class AddProfessionView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id

            current = set(self.cog.get_user_profession_map(user_id).keys())
            available = [p for p in ALL_PROFESSIONS if p not in current]

            if len(current) >= MAX_PROFESSIONS:
                self.add_item(Button(label="Max professions reached", style=discord.ButtonStyle.secondary, disabled=True))
            elif not available:
                self.add_item(Button(label="No available professions", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                self.add_item(self._ProfSelect(self.cog, self.user_id, available))

        class _ProfSelect(Select):
            def __init__(self, cog: "Professions", user_id: int, available: List[str]):
                options = [discord.SelectOption(label=p) for p in available]
                super().__init__(placeholder="Select a profession…", options=options, min_values=1, max_values=1)
                self.cog = cog
                self.user_id = user_id

            async def callback(self, interaction: discord.Interaction):
                profession = self.values[0]
                ok, msg = self.cog.add_profession(self.user_id, profession)
                if not ok:
                    await interaction.response.send_message(msg, ephemeral=True)
                    return
                await refresh_hub(interaction, section="professions")

    class RemoveProfessionView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            current = list(self.cog.get_user_profession_map(user_id).keys())

            if not current:
                self.add_item(Button(label="No professions to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for p in current:
                    self.add_item(self._RemoveBtn(self.cog, self.user_id, p))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Professions", user_id: int, profession: str):
                super().__init__(label=f"Remove {profession}", style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.profession = profession

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_profession(self.user_id, self.profession)
                await refresh_hub(interaction, section="professions")

    class ChangeTierView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            profs = list(self.cog.get_user_profession_map(user_id).keys())
            if not profs:
                self.add_item(Button(label="No professions to change", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                # One button per profession; clicking opens the tier dropdown
                for p in profs:
                    self.add_item(self._ProfBtn(self.cog, self.user_id, p))

        class _ProfBtn(Button):
            def __init__(self, cog: "Professions", user_id: int, prof_name: str):
                super().__init__(label=prof_name, style=discord.ButtonStyle.primary)
                self.cog = cog
                self.user_id = user_id
                self.prof_name = prof_name

            async def callback(self, interaction: discord.Interaction):
                e = discord.Embed(
                    title=f"🛠 Change Tier — {self.prof_name}",
                    description="Select the new tier below.",
                    color=discord.Color.orange()
                )
                v = Professions.ChooseTierView(self.cog, self.user_id, self.prof_name)
                await interaction.response.edit_message(embed=e, view=v)

    class ChooseTierView(View):
        def __init__(self, cog: "Professions", user_id: int, prof_name: str):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.prof_name = prof_name
            self.add_item(self._TierSelect(self.cog, self.user_id, self.prof_name))

        class _TierSelect(Select):
            def __init__(self, cog: "Professions", user_id: int, prof_name: str):
                options = [discord.SelectOption(label=t) for t in TIERS]
                super().__init__(placeholder="Choose new tier…", options=options, min_values=1, max_values=1)
                self.cog = cog
                self.user_id = user_id
                self.prof_name = prof_name

            async def callback(self, interaction: discord.Interaction):
                new_tier = self.values[0]
                ok, msg = self.cog.set_profession_tier(self.user_id, self.prof_name, new_tier)
                if not ok:
                    return await interaction.response.send_message(msg, ephemeral=True)
                await refresh_hub(interaction, section="professions")

    # ---------------- Hub buttons provider ----------------
    def build_professions_buttons(self, user_id: int) -> discord.ui.View:
        v = View(timeout=240)
        v.add_item(Button(
            label="➕ Add Profession",
            style=discord.ButtonStyle.success,
            custom_id=f"prof_add_{user_id}"
        ))
        v.add_item(Button(
            label="🛠 Change Tier",
            style=discord.ButtonStyle.primary,
            custom_id=f"prof_tier_{user_id}"
        ))
        v.add_item(Button(
            label="❌ Remove Profession",
            style=discord.ButtonStyle.danger,
            custom_id=f"prof_remove_{user_id}"
        ))
        return v

    # ---------------- Interaction Listener ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")  # type: ignore
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        # Add Profession
        if cid == f"prof_add_{uid}":
            e = discord.Embed(
                title="➕ Add Profession",
                description=f"Pick a profession (max **{MAX_PROFESSIONS}**).",
                color=discord.Color.green()
            )
            v = Professions.AddProfessionView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        # Change Tier (choose profession first)
        if cid == f"prof_tier_{uid}":
            e = discord.Embed(
                title="🛠 Change Tier",
                description="Select a profession to update its tier.",
                color=discord.Color.blurple()
            )
            v = Professions.ChangeTierView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        # Remove Profession
        if cid == f"prof_remove_{uid}":
            e = discord.Embed(
                title="❌ Remove Profession",
                description="Select a profession to remove.",
                color=discord.Color.red()
            )
            v = Professions.RemoveProfessionView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

    # ---------------- Profile/Hub helper (optional, used by Hub in some versions) ----------------
    def build_professions_embed(self, user: discord.User) -> discord.Embed:
        e = discord.Embed(title=f"🛠️ {user.display_name}'s Professions", color=discord.Color.orange())
        profs = self.get_user_profession_map(user.id)

        if not profs:
            e.description = "No professions selected yet."
        else:
            # Show nice bullets; add emoji flavor if you want later
            for name, tier in profs.items():
                e.add_field(name=name, value=f"Tier: {tier}", inline=False)

        e.set_footer(text="Use the buttons below to manage professions.")
        return e


async def setup(bot: commands.Bot):
    await bot.add_cog(Professions(bot))
