# cogs/profile.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

PROFILE_FILE = "data/profiles.json"

# Fixed list of classes (Ashes archetypes + combos if you want to expand later)
PRIMARY_CLASSES = [
    "Fighter", "Tank", "Rogue", "Ranger",
    "Mage", "Cleric", "Summoner", "Bard"
]
SECONDARY_CLASSES = PRIMARY_CLASSES  # same set for now


class Profile(commands.Cog):
    """Handles profiles, classes, and wishlists."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.profiles = load_json(PROFILE_FILE, {})  # { user_id: { classes: {primary, secondary}, wishlist: [] } }

    def save(self):
        save_json(PROFILE_FILE, self.profiles)

    # ---------------- Public API ----------------
    def get_profile(self, user_id: int):
        return self.profiles.setdefault(str(user_id), {"classes": {"primary": None, "secondary": None}, "wishlist": []})

    def get_wishlist(self, user_id: int):
        return self.get_profile(user_id).get("wishlist", [])

    def add_to_wishlist(self, user_id: int, item: str):
        profile = self.get_profile(user_id)
        wishlist = profile.setdefault("wishlist", [])
        if item not in wishlist:
            wishlist.append(item)
            self.save()
            return True
        return False

    def remove_from_wishlist(self, user_id: int, item: str):
        profile = self.get_profile(user_id)
        wishlist = profile.setdefault("wishlist", [])
        if item in wishlist:
            wishlist.remove(item)
            self.save()
            return True
        return False

    def set_classes(self, user_id: int, primary: str, secondary: str):
        profile = self.get_profile(user_id)
        profile["classes"] = {"primary": primary, "secondary": secondary}
        self.save()

    # ---------------- UI: Modals ----------------
    class AddWishlistModal(Modal, title="➕ Add Wishlist Item"):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.item = TextInput(label="Item Name", placeholder="e.g. Obsidian Dagger", required=True)
            self.add_item(self.item)

        async def on_submit(self, interaction: discord.Interaction):
            added = self.cog.add_to_wishlist(self.user_id, self.item.value)
            msg = f"✅ Added **{self.item.value}** to your wishlist." if added else f"⚠️ **{self.item.value}** is already in your wishlist."
            e = discord.Embed(title="📌 Wishlist Updated", description=msg, color=discord.Color.green())
            await refresh_hub(interaction, section="profile")

    class RemoveWishlistView(View):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=300)
            self.cog = cog
            self.user_id = user_id
            wishlist = self.cog.get_wishlist(user_id)
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

    # ---------------- UI: Edit Profile ----------------
    class EditProfileView(View):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.add_item(self.PrimarySelect(self.cog, self.user_id))
            self.add_item(self.SecondarySelect(self.cog, self.user_id))

        class PrimarySelect(Select):
            def __init__(self, cog: "Profile", user_id: int):
                opts = [discord.SelectOption(label=cls) for cls in PRIMARY_CLASSES]
                super().__init__(placeholder="Choose Primary Class", options=opts)
                self.cog = cog
                self.user_id = user_id

            async def callback(self, interaction: discord.Interaction):
                primary = self.values[0]
                profile = self.cog.get_profile(self.user_id)
                secondary = profile["classes"].get("secondary")
                self.cog.set_classes(self.user_id, primary, secondary)
                await refresh_hub(interaction, section="profile")

        class SecondarySelect(Select):
            def __init__(self, cog: "Profile", user_id: int):
                opts = [discord.SelectOption(label=cls) for cls in SECONDARY_CLASSES]
                super().__init__(placeholder="Choose Secondary Class", options=opts)
                self.cog = cog
                self.user_id = user_id

            async def callback(self, interaction: discord.Interaction):
                secondary = self.values[0]
                profile = self.cog.get_profile(self.user_id)
                primary = profile["classes"].get("primary")
                self.cog.set_classes(self.user_id, primary, secondary)
                await refresh_hub(interaction, section="profile")

    # ---------------- Hub Buttons ----------------
    def build_profile_buttons(self, user_id: int):
        v = View(timeout=180)
        v.add_item(Button(label="✏️ Edit Profile", style=discord.ButtonStyle.primary, custom_id=f"pf_edit_{user_id}"))
        v.add_item(Button(label="➕ Add Wishlist", style=discord.ButtonStyle.success, custom_id=f"pf_addwl_{user_id}"))
        v.add_item(Button(label="🗑 Remove Wishlist", style=discord.ButtonStyle.danger, custom_id=f"pf_remwl_{user_id}"))
        return v

    # ---------------- Interaction Handling ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        # Edit profile
        if cid == f"pf_edit_{uid}":
            e = discord.Embed(title="✏️ Edit Profile", description="Select your Primary and Secondary classes.", color=discord.Color.blue())
            v = Profile.EditProfileView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        # Add to wishlist
        if cid == f"pf_addwl_{uid}":
            modal = Profile.AddWishlistModal(self, uid)
            return await interaction.response.send_modal(modal)

        # Remove from wishlist
        if cid == f"pf_remwl_{uid}":
            e = discord.Embed(title="🗑 Remove Wishlist Item", description="Select an item to remove.", color=discord.Color.red())
            v = Profile.RemoveWishlistView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

    # ---------------- Profile Embed ----------------
    def build_profile_embed(self, user: discord.User):
        profile = self.get_profile(user.id)
        classes = profile.get("classes", {})
        wishlist = profile.get("wishlist", [])

        e = discord.Embed(title=f"👤 {user.display_name}'s Profile", color=discord.Color.blue())
        e.add_field(name="🎭 Classes", value=f"Primary: {classes.get('primary') or '—'}\nSecondary: {classes.get('secondary') or '—'}", inline=False)
        e.add_field(name="📌 Wishlist", value="\n".join(wishlist) if wishlist else "*Empty*", inline=False)
        e.set_footer(text="Use the buttons below to manage your profile.")
        return e


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
