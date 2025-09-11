import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from utils.data import load_json, save_json
from cogs.hub import refresh_hub
from utils.debug import debug_log

debug_log("Set classes", bot=self.bot, user=interaction.user.id, primary=primary_class, secondary=secondary_class)
debug_log("Wishlist updated", bot=self.bot, user=interaction.user.id, item=item, action="added")


PROFILE_FILE = "profiles.json"

class Profile(commands.Cog):
    """Handles player profiles: classes, wishlist, and learned recipes summary."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.profiles = load_json(PROFILE_FILE, {})

    def save_profiles(self):
        save_json(PROFILE_FILE, self.profiles)

    # ==============================
    # Public API
    # ==============================
    def get_user_profile(self, user_id: int):
        return self.profiles.get(str(user_id), {
            "classes": {"primary": None, "secondary": None},
            "wishlist": []
        })

    def set_user_profile(self, user_id: int, data: dict):
        self.profiles[str(user_id)] = data
        self.save_profiles()

    def build_profile_embed(self, user: discord.User) -> discord.Embed:
        profile = self.get_user_profile(user.id)
        wishlist = profile.get("wishlist", [])
        classes = profile.get("classes", {})

        embed = discord.Embed(
            title=f"👤 {user.display_name}'s Profile",
            color=discord.Color.blue(),
        )

        # Classes
        embed.add_field(
            name="🎭 Classes",
            value=f"Primary: **{classes.get('primary') or 'Unset'}**\nSecondary: **{classes.get('secondary') or 'Unset'}**",
            inline=False
        )

        # Wishlist
        if wishlist:
            embed.add_field(
                name="🧾 Wishlist",
                value="\n".join([f"• {item}" for item in wishlist])[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🧾 Wishlist",
                value="*No wishlist items yet.*",
                inline=False
            )

        # Learned Recipes (summary only)
        recipes_cog = self.bot.get_cog("Recipes")
        if recipes_cog and hasattr(recipes_cog, "get_user_recipes"):
            learned = recipes_cog.get_user_recipes(user.id)
            total = sum(len(r) for r in learned.values()) if isinstance(learned, dict) else 0
            embed.add_field(
                name="📘 Learned Recipes",
                value=f"Total learned: **{total}**",
                inline=False
            )

        return embed

    # ==============================
    # UI Buttons & Modals
    # ==============================
    class EditClassesModal(Modal, title="🎭 Edit Classes"):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.primary = TextInput(label="Primary Class", required=True, placeholder="e.g. Bard")
            self.secondary = TextInput(label="Secondary Class", required=True, placeholder="e.g. Rogue")
            self.add_item(self.primary)
            self.add_item(self.secondary)

        async def on_submit(self, interaction: discord.Interaction):
            profile = self.cog.get_user_profile(self.user_id)
            profile["classes"]["primary"] = self.primary.value
            profile["classes"]["secondary"] = self.secondary.value
            self.cog.set_user_profile(self.user_id, profile)
            await refresh_hub(interaction, section="profile")

    class AddWishlistModal(Modal, title="🧾 Add Wishlist Item"):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=180)
            self.cog = cog
            self.user_id = user_id
            self.item = TextInput(label="Item Name", required=True, placeholder="e.g. Obsidian Dagger")
            self.add_item(self.item)

        async def on_submit(self, interaction: discord.Interaction):
            profile = self.cog.get_user_profile(self.user_id)
            wishlist = profile.setdefault("wishlist", [])
            if self.item.value not in wishlist:
                wishlist.append(self.item.value)
                self.cog.set_user_profile(self.user_id, profile)
            await refresh_hub(interaction, section="profile")

    class RemoveWishlistView(View):
        def __init__(self, cog: "Profile", user_id: int):
            super().__init__(timeout=120)
            self.cog = cog
            self.user_id = user_id
            profile = self.cog.get_user_profile(user_id)
            wishlist = profile.get("wishlist", [])

            for item in wishlist:
                self.add_item(self._RemoveBtn(self.cog, user_id, item))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Profile", user_id: int, item: str):
                super().__init__(label=item, style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.item = item

            async def callback(self, interaction: discord.Interaction):
                profile = self.cog.get_user_profile(self.user_id)
                wishlist = profile.get("wishlist", [])
                if self.item in wishlist:
                    wishlist.remove(self.item)
                    self.cog.set_user_profile(self.user_id, profile)
                await refresh_hub(interaction, section="profile")

    # ==============================
    # Hub Buttons
    # ==============================
    def build_profile_buttons(self, user_id: int):
        view = View(timeout=120)
        view.add_item(Button(label="🎭 Edit Classes", style=discord.ButtonStyle.primary,
                             custom_id=f"edit_classes_{user_id}"))
        view.add_item(Button(label="🧾 Add Wishlist", style=discord.ButtonStyle.success,
                             custom_id=f"add_wishlist_{user_id}"))
        view.add_item(Button(label="❌ Remove Wishlist", style=discord.ButtonStyle.danger,
                             custom_id=f"remove_wishlist_{user_id}"))
        return view

async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
