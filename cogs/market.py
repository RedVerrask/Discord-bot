import os
import json
import logging
import discord
from discord.ext import commands

log = logging.getLogger("AshesBot")

DATA_DIR = "data"
MARKET_FILE = os.path.join(DATA_DIR, "market.json")


# ---------- utils ----------
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_market() -> list[dict]:
    ensure_data_dir()
    if not os.path.exists(MARKET_FILE):
        return []
    with open(MARKET_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def save_market(data: list[dict]):
    ensure_data_dir()
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def to_copper(gold: int, silver: int, copper: int) -> int:
    return max(0, int(gold)) * 10_000 + max(0, int(silver)) * 100 + max(0, int(copper))


def format_price(copper_total: int) -> str:
    g = copper_total // 10_000
    rem = copper_total % 10_000
    s = rem // 100
    c = rem % 100
    parts = []
    if g: parts.append(f"{g}g")
    if s: parts.append(f"{s}s")
    if c or not parts: parts.append(f"{c}c")
    return " ".join(parts)


def codex_search_link(item_name: str) -> str:
    from urllib.parse import quote_plus
    return f"https://ashescodex.com/search?query={quote_plus(item_name)}"


# ======================================================
# Market Cog
# ======================================================
class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market: list[dict] = load_market()  # [{item, price_copper, price_str, village, seller, seller_id, link}]

    # ---------- data ops ----------
    def get_user_listings(self, user_id: int) -> list[dict]:
        return [item for item in self.market if item["seller_id"] == str(user_id)]

    def get_all_listings(self) -> list[dict]:
        # Sort by price ascending for browsing
        return sorted(self.market, key=lambda x: x.get("price_copper", 0))

    def add_listing(self, item_name: str, price_copper: int, village: str, seller_id: int, seller_name: str):
        entry = {
            "item": item_name,
            "price_copper": price_copper,
            "price_str": format_price(price_copper),
            "village": village,
            "seller": seller_name,
            "seller_id": str(seller_id),
            "link": codex_search_link(item_name),
        }
        self.market.append(entry)
        save_market(self.market)
        log.info(f"[market] + {item_name} @ {entry['price_str']} ({village}) by {seller_name}")

    def remove_listing(self, seller_id: int, item_name: str) -> bool:
        before = len(self.market)
        self.market = [
            item for item in self.market
            if not (item["seller_id"] == str(seller_id) and item["item"] == item_name)
        ]
        changed = len(self.market) != before
        if changed:
            save_market(self.market)
            log.info(f"[market] - {item_name} by {seller_id}")
        return changed

    # Wishlist matching: case-insensitive substring
    def find_matches_for_wishlist(self, wishlist_items: list[str]) -> list[dict]:
        terms = [t.lower() for t in wishlist_items if t.strip()]
        if not terms:
            return []
        out = []
        for entry in self.get_all_listings():
            name_l = entry["item"].lower()
            if any(term in name_l for term in terms):
                out.append(entry)
        return out

    # ---------- UI entry ----------
    async def open_market(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "💰 **Market**",
            view=MarketMenu(self, interaction.user),
            ephemeral=True
        )


# ======================================================
# Market Menu View
# ======================================================
class MarketMenu(discord.ui.View):
    def __init__(self, market_cog: Market, user: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.market_cog = market_cog
        self.user = user

    # 📜 Browse Market (paginated + quick add to wishlist)
    @discord.ui.button(label="📜 Browse Market", style=discord.ButtonStyle.primary, custom_id="market_browse")
    async def browse_market(self, interaction: discord.Interaction, _: discord.ui.Button):
        listings = self.market_cog.get_all_listings()
        if not listings:
            return await interaction.response.send_message("⚠️ There are no active market listings.", ephemeral=True)

        per_page = 5

        async def send_page(page_idx: int):
            total_pages = (len(listings) - 1) // per_page + 1
            start = page_idx * per_page
            end = start + per_page
            current = listings[start:end]

            embed = discord.Embed(
                title=f"💰 Market Listings (Page {page_idx + 1}/{total_pages})",
                description="Current player-submitted prices",
                color=discord.Color.gold()
            )

            # Build a select to Add-to-Wishlist for items on this page
            add_options: list[discord.SelectOption] = []
            for entry in current:
                embed.add_field(
                    name=f"🛒 {entry['item']} — {entry['price_str']}",
                    value=f"📍 **Village**: {entry['village']}\n"
                          f"👤 **Seller**: {entry['seller']}\n"
                          f"[🔗 Ashes Codex]({entry['link']})",
                    inline=False
                )
                add_options.append(discord.SelectOption(
                    label=entry["item"],
                    value=entry["item"][:100]  # custom_id value cap
                ))

            view = discord.ui.View(timeout=None)

            # Select: Add selected item to wishlist
            if add_options:
                add_select = discord.ui.Select(
                    placeholder="➕ Add a listed item to your wishlist…",
                    options=add_options[:25],
                    min_values=1,
                    max_values=1,
                    custom_id=f"market_add_wishlist_{page_idx}"
                )

                async def add_cb(sel_itx: discord.Interaction):
                    item_name = add_select.values[0]
                    prof = self.market_cog.bot.get_cog("Profile")
                    if not prof:
                        return await sel_itx.response.send_message("⚠️ Profiles cog unavailable.", ephemeral=True)
                    added = prof.add_wishlist_item(sel_itx.user.id, item_name)
                    msg = f"✅ Added **{item_name}** to your wishlist." if added else "⚠️ That item is already on your wishlist."
                    await sel_itx.response.send_message(msg, ephemeral=True)

                add_select.callback = add_cb
                view.add_item(add_select)

            # Pagination
            if page_idx > 0:
                prev_btn = discord.ui.Button(label="⬅ Prev", style=discord.ButtonStyle.secondary, custom_id=f"market_prev_{page_idx}")
                async def prev_cb(i): await i.response.edit_message(embed=None, view=None); await send_page(page_idx - 1)
                prev_btn.callback = prev_cb
                view.add_item(prev_btn)

            if end < len(listings):
                next_btn = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.secondary, custom_id=f"market_next_{page_idx}")
                async def next_cb(i): await i.response.edit_message(embed=None, view=None); await send_page(page_idx + 1)
                next_btn.callback = next_cb
                view.add_item(next_btn)

            close_btn = discord.ui.Button(label="❌ Close", style=discord.ButtonStyle.danger, custom_id=f"market_close_{page_idx}")
            async def close_cb(i): await i.response.edit_message(content="Menu closed.", embed=None, view=None)
            close_btn.callback = close_cb
            view.add_item(close_btn)

            # First response vs follow-up edit handling:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        await send_page(0)

    # ➕ Add Listing
    @discord.ui.button(label="➕ Add Listing", style=discord.ButtonStyle.success, custom_id="market_add")
    async def add_listing_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(AddListingModal(self.market_cog, self.user))

    # ❌ Remove Listing
    @discord.ui.button(label="❌ Remove Listing", style=discord.ButtonStyle.danger, custom_id="market_remove")
    async def remove_listing_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        user_listings = self.market_cog.get_user_listings(interaction.user.id)
        if not user_listings:
            return await interaction.response.send_message("⚠️ You don’t have any active listings to remove.", ephemeral=True)

        options = [
            discord.SelectOption(label=entry["item"], value=entry["item"])
            for entry in user_listings
        ]

        dropdown = discord.ui.Select(
            placeholder="Select a listing to remove…",
            options=options[:25],
            min_values=1,
            max_values=1,
            custom_id="market_remove_dropdown"
        )

        view = discord.ui.View(timeout=None)

        async def dropdown_callback(select_interaction: discord.Interaction):
            item_name = dropdown.values[0]
            removed = self.market_cog.remove_listing(select_interaction.user.id, item_name)
            msg = f"✅ Removed **{item_name}**." if removed else "⚠️ Not found."
            await select_interaction.response.send_message(msg, ephemeral=True)

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
    def __init__(self, market_cog: Market, user: discord.User | discord.Member):
        super().__init__()
        self.market_cog = market_cog
        self.user = user

        self.item_name = discord.ui.TextInput(
            label="Item Name",
            placeholder="Example: Ironwood Plank",
            required=True,
            max_length=80
        )
        self.gold = discord.ui.TextInput(label="Gold", placeholder="0", required=False, max_length=6)
        self.silver = discord.ui.TextInput(label="Silver", placeholder="0", required=False, max_length=6)
        self.copper = discord.ui.TextInput(label="Copper", placeholder="0", required=False, max_length=6)
        self.village = discord.ui.TextInput(
            label="Village Name",
            placeholder="Example: Riverlands",
            required=True,
            max_length=64
        )

        self.add_item(self.item_name)
        self.add_item(self.gold)
        self.add_item(self.silver)
        self.add_item(self.copper)
        self.add_item(self.village)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            g = int(self.gold.value or 0)
            s = int(self.silver.value or 0)
            c = int(self.copper.value or 0)
            if g < 0 or s < 0 or c < 0 or s >= 100 or c >= 100:
                raise ValueError
        except Exception:
            return await interaction.response.send_message(
                "⚠️ Invalid price. Use non-negative numbers; 0 ≤ silver,copper < 100.",
                ephemeral=True
            )

        price_copper = to_copper(g, s, c)
        self.market_cog.add_listing(
            self.item_name.value.strip(),
            price_copper,
            self.village.value.strip(),
            self.user.id,
            getattr(self.user, "display_name", self.user.name)
        )

        embed = discord.Embed(
            title="✅ Listing Added",
            description=f"**{self.item_name.value}** listed for **{format_price(price_copper)}**\n"
                        f"📍 Village: **{self.village.value}**\n"
                        f"[🔗 Ashes Codex]({codex_search_link(self.item_name.value)})",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Market(bot))
