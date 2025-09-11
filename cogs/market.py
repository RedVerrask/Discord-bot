import discord
from discord.ext import commands
import json
import os

MARKET_FILE = "data/market.json"

def load_market():
    if not os.path.exists(MARKET_FILE):
        return []
    with open(MARKET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_market(data):
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ======================================================
# Market Cog (Data Management)
# ======================================================
class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market = load_market()

    def get_user_listings(self, user_id):
        return [item for item in self.market if item["seller_id"] == str(user_id)]

    def add_listing(self, item_name, price, village, seller_id, seller_name):
        entry = {
            "item": item_name,
            "price": price,
            "village": village,
            "seller": seller_name,
            "seller_id": str(seller_id),
            "link": f"https://ashescodex.com/search?query={item_name.replace(' ', '+')}"
        }
        self.market.append(entry)
        save_market(self.market)

    def remove_listing(self, seller_id, item_name):
        self.market = [
            item for item in self.market
            if not (item["seller_id"] == str(seller_id) and item["item"] == item_name)
        ]
        save_market(self.market)

    def get_all_listings(self):
        return self.market

# ======================================================
# Market Menu UI
# ======================================================
class MarketMenu(discord.ui.View):  # <-- ✅ MUST EXIST
    def __init__(self, market_cog, user):
        super().__init__(timeout=None)
        self.market_cog = market_cog
        self.user = user

    # 📜 Browse Market Listings
    @discord.ui.button(label="📜 Browse Market", style=discord.ButtonStyle.primary, custom_id="market_browse")
    async def browse_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        listings = self.market_cog.get_all_listings()
        if not listings:
            await interaction.response.send_message(
                "⚠️ There are no active market listings.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💰 Market Listings",
            description="Current player-submitted prices",
            color=discord.Color.gold()
        )

        for entry in listings[:10]:
            embed.add_field(
                name=f"🛒 {entry['item']} — {entry['price']}g",
                value=f"📍 **Village**: {entry['village']}\n"
                      f"👤 **Seller**: {entry['seller']}\n"
                      f"[🔗 View on Ashes Codex]({entry['link']})",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ➕ Add Listing
    @discord.ui.button(label="➕ Add Listing", style=discord.ButtonStyle.success, custom_id="market_add")
    async def add_listing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddListingModal(self.market_cog, self.user)
        await interaction.response.send_modal(modal)

    # ❌ Remove Listing
    @discord.ui.button(label="❌ Remove Listing", style=discord.ButtonStyle.danger, custom_id="market_remove")
    async def remove_listing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_listings = self.market_cog.get_user_listings(interaction.user.id)
        if not user_listings:
            await interaction.response.send_message(
                "⚠️ You don’t have any active listings to remove.",
                ephemeral=True
            )
            return

        options = [
            discord.SelectOption(label=entry["item"], value=entry["item"])
            for entry in user_listings
        ]

        dropdown = discord.ui.Select(
            placeholder="Select a listing to remove...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="market_remove_dropdown"
        )

        view = discord.ui.View(timeout=None)

        async def dropdown_callback(select_interaction: discord.Interaction):
            item_name = dropdown.values[0]
            self.market_cog.remove_listing(select_interaction.user.id, item_name)
            embed = discord.Embed(
                title="✅ Listing Removed",
                description=f"You removed **{item_name}** from the market.",
                color=discord.Color.red()
            )
            await select_interaction.response.send_message(embed=embed, ephemeral=True)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        await interaction.response.send_message(
            content="Select a listing to remove:",
            view=view,
            ephemeral=True
        )

# ======================================================
# Add Listing Modal
# ======================================================
class AddListingModal(discord.ui.Modal, title="➕ Add Market Listing"):
    def __init__(self, market_cog, user):
        super().__init__()
        self.market_cog = market_cog
        self.user = user

        self.item_name = discord.ui.TextInput(label="Item Name", placeholder="Example: Ironwood Plank", required=True)
        self.price = discord.ui.TextInput(label="Sale Price (gold)", placeholder="Example: 175", required=True)
        self.village = discord.ui.TextInput(label="Village Name", placeholder="Example: Riverlands", required=True)

        self.add_item(self.item_name)
        self.add_item(self.price)
        self.add_item(self.village)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Invalid price format. Please enter a number.",
                ephemeral=True
            )
            return

        self.market_cog.add_listing(
            self.item_name.value,
            price,
            self.village.value,
            self.user.id,
            self.user.display_name
        )

        embed = discord.Embed(
            title="✅ Listing Added",
            description=f"**{self.item_name.value}** added for **{price}g**.\n📍 Village: **{self.village.value}**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================================================
# Cog Setup
# ======================================================
async def setup(bot):
    await bot.add_cog(Market(bot))
