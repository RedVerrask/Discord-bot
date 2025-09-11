# cogs/professions.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

PROFESSIONS_FILE = "data/professions.json"

# Standard tiers in Ashes of Creation
TIERS = ["Novice", "Apprentice", "Journeyman", "Master", "Grandmaster"]

class Professions(commands.Cog):
    """Handles user professions and tiers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: [ { "name": str, "tier": str } ] }
        self.professions: Dict[str, List[Dict[str, str]]] = load_json(PROFESSIONS_FILE, {})

    def _save(self):
        save_json(PROFESSIONS_FILE, self.professions)

    # ---------------- Public API ----------------
    def get_user_professions(self, user_id: int) -> List[Dict[str, str]]:
        return self.professions.get(str(user_id), [])

    def add_profession(self, user_id: int, name: str, tier: str = "Novice") -> bool:
        profs = self.professions.setdefault(str(user_id), [])
        if any(p["name"].lower() == name.lower() for p in profs):
            return False
        profs.append({"name": name, "tier": tier})
        self._save()
        return True

    def set_tier(self, user_id: int, name: str, tier: str) -> bool:
        profs = self.professions.get(str(user_id), [])
        for p in profs:
            if p["name"].lower() == name.lower():
                p["tier"] = tier
                self._save()
                return True
        return False

    def remove_profession(self, user_id: int, name: str) -> bool:
        before = len(self.professions.get(str(user_id), []))
        self.professions[str(user_id)] = [p for p in self.professions.get(str(user_id), []) if p["name"].lower() != name.lower()]
        after = len(self.professions[str(user_id)])
        if after < before:
            self._save()
            return True
        return False

    # ---------------- UI Modals ----------------
    class AddProfessionModal(Modal, title="➕ Add Profession"):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.name = TextInput(label="Profession Name", placeholder="e.g. Blacksmith", required=True)
            self.add_item(self.name)

        async def on_submit(self, interaction: discord.Interaction):
            added = self.cog.add_profession(self.user_id, self.name.value)
            msg = f"✅ Added **{self.name.value}** as Novice." if added else f"⚠️ Already have profession **{self.name.value}**."
            e = discord.Embed(title="Professions Updated", description=msg, color=discord.Color.orange())
            await refresh_hub(interaction, section="professions")

    # ---------------- UI Views ----------------
    class TierSelectView(View):
        def __init__(self, cog: "Professions", user_id: int, prof_name: str):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.prof_name = prof_name
            self.add_item(self._TierSelect(self.cog, self.user_id, self.prof_name))

        class _TierSelect(Select):
            def __init__(self, cog: "Professions", user_id: int, prof_name: str):
                opts = [discord.SelectOption(label=t) for t in TIERS]
                super().__init__(placeholder="Select new tier", options=opts, min_values=1, max_values=1)
                self.cog = cog
                self.user_id = user_id
                self.prof_name = prof_name

            async def callback(self, interaction: discord.Interaction):
                new_tier = self.values[0]
                self.cog.set_tier(self.user_id, self.prof_name, new_tier)
                e = discord.Embed(title="Tier Updated", description=f"✅ {self.prof_name} → **{new_tier}**", color=discord.Color.orange())
                await refresh_hub(interaction, section="professions")

    class RemoveProfessionView(View):
        def __init__(self, cog: "Professions", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            profs = self.cog.get_user_professions(user_id)
            if not profs:
                self.add_item(Button(label="No professions to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for p in profs:
                    self.add_item(self._RemoveBtn(self.cog, self.user_id, p["name"]))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Professions", user_id: int, name: str):
                super().__init__(label=f"Remove {name}", style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.name = name

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_profession(self.user_id, self.name)
                await refresh_hub(interaction, section="professions")

    # ---------------- Hub Buttons ----------------
    def build_professions_buttons(self, user_id: int) -> discord.ui.View:
        v = View(timeout=240)
        v.add_item(Button(label="➕ Add Profession", style=discord.ButtonStyle.success, custom_id=f"prof_add_{user_id}"))
        v.add_item(Button(label="⬆️ Change Tier", style=discord.ButtonStyle.primary, custom_id=f"prof_tier_{user_id}"))
        v.add_item(Button(label="🗑 Remove Profession", style=discord.ButtonStyle.danger, custom_id=f"prof_remove_{user_id}"))
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
            modal = Professions.AddProfessionModal(self, uid)
            return await interaction.response.send_modal(modal)

        if cid == f"prof_tier_{uid}":
            profs = self.get_user_professions(uid)
            if not profs:
                return await interaction.response.send_message("⚠️ You have no professions to change.", ephemeral=True)
            # If multiple, ask to pick
            opts = [discord.SelectOption(label=p["name"], description=f"Current: {p['tier']}") for p in profs]
            select = Select(placeholder="Select profession", options=opts, min_values=1, max_values=1)

            async def select_cb(inter: discord.Interaction):
                prof_name = select.values[0]
                v = Professions.TierSelectView(self, uid, prof_name)
                e = discord.Embed(title="Change Tier", description=f"Select new tier for **{prof_name}**", color=discord.Color.orange())
                await inter.response.edit_message(embed=e, view=v)

            select.callback = select_cb
            v = View(timeout=180)
            v.add_item(select)
            e = discord.Embed(title="Choose Profession", description="Which profession’s tier do you want to change?", color=discord.Color.orange())
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"prof_remove_{uid}":
            e = discord.Embed(title="🗑 Remove Profession", description="Choose which to remove.", color=discord.Color.red())
            v = Professions.RemoveProfessionView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot: commands.Bot):
    await bot.add_cog(Professions(bot))
