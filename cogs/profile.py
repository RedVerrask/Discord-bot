import discord
from discord.ext import commands
import json, os
from cogs.professions import TIER_COLORS
from cogs.professions import TIER_COLORS
from cogs.professions_menu import ProfessionsMenu
from cogs.market import MarketMenu

PROFILES_FILE = "data/profiles.json"

def load_profiles():
    if not os.path.exists(PROFILES_FILE):
        return {}
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profiles(data):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profiles = load_profiles()

    def get_profile(self, user_id):
        user_id = str(user_id)
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                "class": None,
                "bio": None,
                "professions": [],   # professions actually read from Professions cog for display
                "wishlist": [],
                "market_posts": []
            }
            save_profiles(self.profiles)
        return self.profiles[user_id]

    def build_profile_embed(self, user: discord.User):
        profile = self.get_profile(user.id)
        professions_cog = self.bot.get_cog("Professions")
        professions = professions_cog.get_user_professions(user.id) if professions_cog else []

        embed = discord.Embed(title=f"👤 {user.display_name}'s Profile", color=discord.Color.blurple())
        embed.add_field(name="Class", value=profile["class"] or "*Not set*", inline=True)

        if professions:
            prof_list = []
            for p in professions:
                tier = str(p.get("tier", "1"))
                emoji = TIER_COLORS.get(tier, "⚪")
                prof_list.append(f"{emoji} **{p['name']}** (Tier {tier})")
            professions_text = "\n".join(prof_list)
        else:
            professions_text = "*None selected*"
        embed.add_field(name="Professions", value=professions_text, inline=False)

        wishlist = profile["wishlist"]
        embed.add_field(name="Wishlist", value=("\n".join([f"• {i}" for i in wishlist]) or "*Empty*"), inline=False)

        market = profile["market_posts"]
        embed.add_field(name="Market Listings", value=("\n".join([f"• {i}" for i in market]) or "*No active listings*"), inline=False)

        embed.set_footer(text="Manage your profile using the buttons below.")
        return embed

    async def open_profile(self, interaction: discord.Interaction):
        embed = self.build_profile_embed(interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=ProfileMenuView(self, interaction.user),
            ephemeral=True
        )

# --------- UI ----------
from cogs.market import MarketMenu

class ProfileMenuView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=None)
        self.cog = cog
        self.user = user

    @discord.ui.button(label="🎭 Set Class", style=discord.ButtonStyle.primary)
    async def set_class(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("⚠️ This menu isn't yours!", ephemeral=True)
        await interaction.response.send_modal(ClassModal(self.cog, self.user))

    @discord.ui.button(label="🛠️ Manage Professions", style=discord.ButtonStyle.secondary)
    async def manage_professions(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("⚠️ This menu isn't yours!", ephemeral=True)
        from cogs.professions_menu import ProfessionsMenu
        professions_cog = self.cog.bot.get_cog("Professions")
        await interaction.response.send_message(
            "🛠️ **Manage Your Professions**",
            view=ProfessionsMenu(professions_cog, self.user),
            ephemeral=True
        )

    @discord.ui.button(label="📜 Manage Wishlist", style=discord.ButtonStyle.success)
    async def manage_wishlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("⚠️ This menu isn't yours!", ephemeral=True)
        await interaction.response.send_modal(WishlistModal(self.cog, self.user))

    @discord.ui.button(label="💰 My Market Posts", style=discord.ButtonStyle.success)
    async def market_posts(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("⚠️ This menu isn't yours!", ephemeral=True)
        market_cog = self.cog.bot.get_cog("Market")
        user_listings = market_cog.get_user_listings(interaction.user.id)
        if not user_listings:
            return await interaction.response.send_message("⚠️ You don’t have any active market listings.", ephemeral=True)

        embed = discord.Embed(title=f"💰 {self.user.display_name}'s Market Posts", color=discord.Color.green())
        for entry in user_listings:
            embed.add_field(
                name=f"🛒 {entry['item']} — {entry['price']}g",
                value=f"📍 Village: {entry['village']}\n[🔗 Ashes Codex]({entry['link']})",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --------- Modals ---------
class ClassModal(discord.ui.Modal, title="Set Your Class"):
    def __init__(self, cog, user):
        super().__init__()
        self.cog, self.user = cog, user
        self.class_input = discord.ui.TextInput(label="Enter your class", placeholder="Rogue, Bard, Mage...", required=True)
        self.add_item(self.class_input)

    async def on_submit(self, interaction: discord.Interaction):
        profile = self.cog.get_profile(self.user.id)
        profile["class"] = self.class_input.value.strip()
        save_profiles(self.cog.profiles)
        # Show refreshed profile
        await self.cog.open_profile(interaction)

class WishlistModal(discord.ui.Modal, title="Manage Wishlist"):
    def __init__(self, cog, user):
        super().__init__()
        self.cog, self.user = cog, user
        self.wishlist_input = discord.ui.TextInput(
            label="Items (comma-separated)",
            placeholder="Obsidian Dagger, Phoenix Cloak...",
            required=True
        )
        self.add_item(self.wishlist_input)

    async def on_submit(self, interaction: discord.Interaction):
        items = [s.strip() for s in self.wishlist_input.value.split(",") if s.strip()]
        profile = self.cog.get_profile(self.user.id)
        profile["wishlist"] = items
        save_profiles(self.cog.profiles)
        await self.cog.open_profile(interaction)

async def setup(bot):
    await bot.add_cog(Profile(bot))

