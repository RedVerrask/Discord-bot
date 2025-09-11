# cogs/professions.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from typing import Dict, List

from utils.data import load_json, save_json
from cogs.hub import refresh_hub

PROFESSIONS_FILE = "data/professions.json"

ALL_PROFESSIONS = [
    "Blacksmithing", "Leatherworking", "Alchemy", "Cooking",
    "Fishing", "Hunting", "Herbalism", "Lumberjacking",
    "Mining", "Weaving", "Scribing", "Jewelry"
]

TIERS = ["Novice", "Apprentice", "Journeyman", "Master", "Grandmaster"]


class Professions(commands.Cog):
    """Handles profession selection and tier progression."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: { "professions": { name: tier } } }
        self.data: Dict[str, Dict[str, Dict[str, str]]] = load_json(PROFESSIONS_FILE, {})

    def save(self):
        save_json(PROFESSIONS_FILE, self.data)

    # ---------------- Public API ----------------
    def get_user_professions(self, user_id: int) -> Dict[str, str]:
        return self.data.get(str(user_id), {}).get("professions", {})

    def add_profession(self, user_id: int, profession: str):
        user = self.data.setdefault(str(user_id), {"professions": {}})
        if profession not in user["professions"]:
            user["professions"][profession] = TIERS[0]  # start at Novice
            self.save()

    def remove_profession(self, user_id: int, profession: str):
        user = self.data.get(str(user_id), {}).get("professions", {})
        if profession in user:
            del user[profession]
            self.save()

    def set_tier(self, user_id: int, profession: str, tier: str):
        user = self.data.setdefault(str(user_id), {"professions": {}})
        if profession in user["professions"]:
            user["professions"][profession] = tier
            self.save()

    # ---------------- Views ----------------
    class AddProfessionView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            current = self.cog.get_user_professions(user_id)
            available = [p for p in ALL_PROFESSIONS if p not in current]

            if not available:
                self.add_item(Button(label="All professions selected", style=discord.ButtonStyle.secondary, disabled=True))
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
                self.cog.add_profession(self.user_id, profession)
                await refresh_hub(interaction, section="professions")

    class RemoveProfessionView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            current = self.cog.get_user_professions(user_id)

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
        def __init__(self, cog: "Professions", user_id: int, profs: Dict[str, str]):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            for p in profs:
                self.add_item(self._ProfBtn(self.cog, self.user_id, p))

        class _ProfBtn(Button):
            def __init__(self, cog: "Professions", user_id: int, prof_name: str):
                super().__init__(label=f"Change {prof_name}", style=discord.ButtonStyle.primary)
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
                self.cog.set_tier(self.user_id, self.prof_name, new_tier)
                await refresh_hub(interaction, section="professions")

    # ---------------- Hub Buttons ----------------
    def build_professions_buttons(self, user_id: int) -> discord.ui.View:
        v = View(timeout=240)
        v.add_item(Button(label="➕ Add Profession", style=discord.ButtonStyle.success, custom_id=f"prof_add_{user_id}"))
        v.add_item(Button(label="🛠 Change Tier", style=discord.ButtonStyle.primary, custom_id=f"prof_tier_{user_id}"))
        v.add_item(Button(label="❌ Remove Profession", style=discord.ButtonStyle.danger, custom_id=f"prof_rem_{user_id}"))
        return v

    # ---------------- Interaction Listener ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        if cid == f"prof_add_{uid}":
            e = discord.Embed(title="➕ Add Profession", description="Pick from available professions.", color=discord.Color.green())
            v = Professions.AddProfessionView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"prof_rem_{uid}":
            e = discord.Embed(title="❌ Remove Profession", description="Select a profession to remove.", color=discord.Color.red())
            v = Professions.RemoveProfessionView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"prof_tier_{uid}":
            profs = self.get_user_professions(uid)
            if not profs:
                return await interaction.response.send_message("⚠️ You have no professions to change.", ephemeral=True)

            e = discord.Embed(
                title="🛠 Change Tier",
                description="Select a profession below to update its tier.",
                color=discord.Color.blurple()
            )
            v = self.ChangeTierView(self, uid, profs)
            return await interaction.response.edit_message(embed=e, view=v)

    # ---------------- Embed ----------------
    def build_professions_embed(self, user: discord.User) -> discord.Embed:
        profs = self.get_user_professions(user.id)
        e = discord.Embed(title=f"🛠️ {user.display_name}'s Professions", color=discord.Color.orange())

        if not profs:
            e.description = "No professions selected yet."
        else:
            for p, tier in profs.items():
                e.add_field(name=p, value=f"Tier: {tier}", inline=False)

        e.set_footer(text="Use the buttons below to manage professions.")
        return e


async def setup(bot: commands.Bot):
    await bot.add_cog(Professions(bot))
