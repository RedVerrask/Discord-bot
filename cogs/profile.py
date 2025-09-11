# cogs/profile.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, Any

from utils.data import load_json, save_json
from cogs.hub import refresh_hub

PROFILE_FILE = "data/profiles.json"

# Restricted list of archetypes/classes
CLASS_OPTIONS = [
    "Fighter", "Tank", "Rogue", "Ranger",
    "Mage", "Summoner", "Cleric", "Bard"
]

class Profile(commands.Cog):
    """Handles profiles, character info, and wishlists."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: { "character_name": str, "primary_class": str, "secondary_class": str, "wishlist": [] } }
        self.profiles: Dict[str, Dict[str, Any]] = load_json(PROFILE_FILE, {})

    def save(self):
        save_json(PROFILE_FILE, self.profiles)

    # ==================================================
    # Public API
    # ==================================================
    def get_profile(self, user_id: int) -> Dict[str, Any]:
        return self.profiles.setdefault(str(user_id), {
            "character_name": "",
            "primary_class": "",
            "secondary_class": "",
            "wishlist": []
        })

    def add_to_wishlist(self, user_id: int, item: str) -> bool:
        profile = self.get_profile(user_id)
        wishlist = profile.setdefault("wishlist", [])
        if item not in wishlist:
            wishlist.append(item)
            self.save()
            return True
        return False

    def remove_from_wishlist(self, user_id: int, item: str) -> bool:
        profile = self.get_profile(user_id)
        wishlist = profile.setdefault("wishlist", [])
        if item in wishlist:
            wishlist.remove(item)
            self.save()
            return True
        return False

    def set_character_name(self, user_id: int, name: str):
        profile = self.get_profile(user_id)
        profile["character_name"] = name
        self.save()

    def set_classes(self, user_id: int, primary: str, secondary: str):
        profile = self.get_profile(user_id)
        profile["primary_class"] = primary
        profile["secondary_class"] = secondary
        self.save()

    # ==================================================
    # UI — Modals & Selects
    # ==================================================
    class EditNameModal(Modal, title="✏️ Edit Character Name"):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.name = TextInput(label="Character Name", placeholder="e.g. Kael", required=True)
            self.add_item(self.name)

        async def on_submit(self, interaction: discord.Interaction):
            self.cog.set_character_name(self.user_id, self.name.value)
            await refresh_hub(interaction, section="profile")

    class ChooseClassesView(View):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.add_item(self._ClassSelect(self.cog, self.user_id, "Primary Class", "primary_class"))
            self.add_item(self._ClassSelect(self.cog, self.user_id, "Secondary Class", "secondary_class"))

        class _ClassSelect(Select):
            def __init__(self, cog: "Profile", user_id: int, placeholder: str, key: str):
                options = [discord.SelectOption(label=c) for c in CLASS_OPTIONS]
                super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)
                self.cog = cog
                self.user_id = user_id
                self.key = key

            async def callback(self, interaction: discord.Interaction):
                val = self.values[0]
                profile = self.cog.get_profile(self.user_id)
                profile[self.key] = val
                self.cog.save()
                await refresh_hub(interaction, section="profile")

    class AddWishlistModal(Modal, title="➕ Add Wishlist Item"):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.item = TextInput(label="Item Name", placeholder="e.g. Obsidian Dagger", required=True)
            self.add_item(self.item)

        async def on_submit(self, interaction: discord.Interaction):
            added = self.cog.add_to_wishlist(self.user_id, self.item.value)
            msg = f"✅ Added **{self.item.value}**." if added else f"⚠️ Already in wishlist."
            e = discord.Embed(title="📌 Wishlist Updated", description=msg, color=discord.Color.green())
            await refresh_hub(interaction, section="profile")

    class RemoveWishlistView(View):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=300)
            self.cog = cog
            self.user_id = user_id
            wishlist = self.cog.get_profile(user_id).get("wishlist", [])
            if not wishlist:
                self.add_item(Button(label="No items to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for item in wishlist:
                    self.add_item(self._RemoveBtn(self.cog, self.user_id, item))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Profile", user_id: int, item: str):
                super().__init__(label=item, style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.item = item

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_from_wishlist(self.user_id, self.item)
                await refresh_hub(interaction, section="profile")

    # ==================================================
    # Hub Buttons
    # ==================================================
    def build_profile_buttons(self, user_id: int):
        v = View(timeout=180)
        v.add_item(Button(label="✏️ Edit Name", style=discord.ButtonStyle.secondary, custom_id=f"pf_name_{user_id}"))
        v.add_item(Button(label="🎭 Set Classes", style=discord.ButtonStyle.primary, custom_id=f"pf_classes_{user_id}"))
        v.add_item(Button(label="➕ Add Wishlist", style=discord.ButtonStyle.success, custom_id=f"pf_addwl_{user_id}"))
        v.add_item(Button(label="🗑 Remove Wishlist", style=discord.ButtonStyle.danger, custom_id=f"pf_remwl_{user_id}"))
        return v

    # ==================================================
    # Interaction Handling
    # ==================================================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type or not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return
        uid = interaction.user.id

        if cid == f"pf_name_{uid}":
            modal = Profile.EditNameModal(self, uid)
            return await interaction.response.send_modal(modal)

        if cid == f"pf_classes_{uid}":
            e = discord.Embed(title="🎭 Choose Classes", description="Pick your primary and secondary classes.", color=discord.Color.blurple())
            v = Profile.ChooseClassesView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"pf_addwl_{uid}":
            modal = Profile.AddWishlistModal(self, uid)
            return await interaction.response.send_modal(modal)

        if cid == f"pf_remwl_{uid}":
            e = discord.Embed(title="🗑 Remove Wishlist Item", description="Select an item to remove.", color=discord.Color.red())
            v = Profile.RemoveWishlistView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

    # ==================================================
    # Profile Embed
    # ==================================================
    def build_profile_embed(self, user: discord.User):
        profile = self.get_profile(user.id)
        e = discord.Embed(title=f"👤 {user.display_name}'s Profile", color=discord.Color.blue())

        # Character info
        e.add_field(name="🎭 Character", value=f"**Name:** {profile.get('character_name','—')}\n"
                                               f"**Classes:** {profile.get('primary_class','—')} / {profile.get('secondary_class','—')}", inline=False)

        # Professions (from Professions cog)
        profs_cog = self.bot.get_cog("Professions")
        if profs_cog:
            profs = profs_cog.get_user_professions(user.id)
            if profs:
                lines = [f"• {p} — {tier}" for p, tier in profs.items()]
                e.add_field(name="🛠️ Professions", value="\n".join(lines), inline=False)

        # Wishlist
        wishlist = profile.get("wishlist", [])
        e.add_field(name="📌 Wishlist", value="\n".join(wishlist) if wishlist else "*Empty*", inline=False)

        # Learned recipes (from Recipes cog)
        rec_cog = self.bot.get_cog("Recipes")
        if rec_cog:
            learned = rec_cog.get_user_recipes(user.id)
            total = sum(len(v) for v in learned.values())
            e.add_field(name="📘 Learned Recipes", value=f"{total} total", inline=False)

        e.set_footer(text="Manage your character and wishlist with the buttons below.")
        return e


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
