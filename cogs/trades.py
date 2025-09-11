import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from typing import Dict, List, Any
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

TRADES_FILE = "data/trades.json"
PROFILE_FILE = "data/profiles.json"

class Trades(commands.Cog):
    """Guild-wide trade board for offers, requests, and wishlist integration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: [ {type, item, price, note} ] }
        self.trades: Dict[str, List[Dict[str, Any]]] = load_json(TRADES_FILE, {})
        self.profiles = load_json(PROFILE_FILE, {})  # For wishlist highlighting

    def _save(self):
        save_json(TRADES_FILE, self.trades)

    # ==================================================
    # Public API
    # ==================================================
    def get_user_trades(self, user_id: int):
        return self.trades.get(str(user_id), [])

    def add_trade(self, user_id: int, ttype: str, item: str, price: str, note: str):
        entry = {"type": ttype, "item": item, "price": price, "note": note}
        self.trades.setdefault(str(user_id), []).append(entry)
        self._save()

        # 🔔 Check for wishlist matches
        self._notify_wishlist_matches(user_id, item, price)
        return entry

    def remove_trade(self, user_id: int, item: str):
        trades = self.trades.get(str(user_id), [])
        self.trades[str(user_id)] = [t for t in trades if t["item"].lower() != item.lower()]
        self._save()

    def get_all_trades(self):
        listings = []
        for uid, posts in self.trades.items():
            for t in posts:
                listings.append((int(uid), t))
        return listings

    def _notify_wishlist_matches(self, poster_id: int, item: str, price: str):
        """Sends mailbox alerts to users if a posted trade matches their wishlist."""
        mail_cog = self.bot.get_cog("Mailbox")
        if not mail_cog:
            return  # Skip silently if mailbox is unavailable

        item_lower = item.lower()
        for uid, profile in self.profiles.items():
            if int(uid) == poster_id:
                continue  # Don't notify the person who posted it

            wishlist = [w.lower() for w in profile.get("wishlist", [])]
            if item_lower in wishlist:
                mail_cog.send_message(
                    from_id=poster_id,
                    to_id=int(uid),
                    subject=f"Wishlist Match: {item}",
                    body=f"✨ Someone just posted **{item}** for {price}!\n"
                         f"Check `/home → Trades` to view it."
                )

    # ==================================================
    # UI — Modals
    # ==================================================
    class PostTradeModal(Modal, title="📦 Post Trade"):
        def __init__(self, cog: "Trades", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.ttype = TextInput(label="Type", placeholder="For Sale / Wanted / Offer", required=True)
            self.item = TextInput(label="Item", placeholder="e.g. Obsidian Dagger", required=True)
            self.price = TextInput(label="Price", placeholder="e.g. 1500g or 'Negotiable'", required=False)
            self.note = TextInput(label="Note", placeholder="Optional: add details here", required=False)
            self.add_item(self.ttype)
            self.add_item(self.item)
            self.add_item(self.price)
            self.add_item(self.note)

        async def on_submit(self, interaction: discord.Interaction):
            self.cog.add_trade(
                self.user_id,
                self.ttype.value.title(),
                self.item.value,
                self.price.value or "—",
                self.note.value or ""
            )
            await refresh_hub(interaction, section="trades")

    # ==================================================
    # UI — Views
    # ==================================================
    class BrowseTradesView(View):
        def __init__(self, cog: "Trades", user_id: int, page: int = 0):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.page = page
            self.per_page = 5
            self.build()

        def build(self):
            self.clear_items()
            listings = self.cog.get_all_trades()
            listings.sort(key=lambda x: x[1]["item"].lower())

            start = self.page * self.per_page
            end = start + self.per_page
            page_list = listings[start:end]

            # Normalize wishlist for highlighting
            wishlist = [w.lower() for w in self.cog.profiles.get(str(self.user_id), {}).get("wishlist", [])]

            for uid, trade in page_list:
                label = f"{trade['type']}: {trade['item']} — {trade['price']}"
                button = self._TradeBtn(self.cog, self.user_id, uid, trade)
                button.label = label[:80]
                button.style = discord.ButtonStyle.success if trade["item"].lower() in wishlist else discord.ButtonStyle.primary
                self.add_item(button)

            # Pagination controls
            if start > 0:
                self.add_item(self._PrevBtn(self.cog, self.user_id, self.page))
            if end < len(listings):
                self.add_item(self._NextBtn(self.cog, self.user_id, self.page))

        class _TradeBtn(Button):
            def __init__(self, cog: "Trades", user_id: int, seller_id: int, trade: dict):
                super().__init__(style=discord.ButtonStyle.primary)
                self.cog = cog
                self.user_id = user_id
                self.seller_id = seller_id
                self.trade = trade

            async def callback(self, interaction: discord.Interaction):
                seller = interaction.guild.get_member(self.seller_id) if interaction.guild else None
                seller_name = seller.display_name if seller else str(self.seller_id)

                e = discord.Embed(
                    title=f"{self.trade['type']}: {self.trade['item']}",
                    description=f"**Price:** {self.trade['price']}\n"
                                f"**Note:** {self.trade['note'] or '—'}\n"
                                f"**Trader:** {seller_name}",
                    color=discord.Color.dark_teal(),
                )

                v = View(timeout=180)
                v.add_item(self._MessageBtn(self.cog, self.user_id, self.seller_id))
                await interaction.response.edit_message(embed=e, view=v)

        class _MessageBtn(Button):
            def __init__(self, cog: "Trades", user_id: int, to_user_id: int):
                super().__init__(label="✉️ Message Trader", style=discord.ButtonStyle.success)
                self.cog = cog
                self.user_id = user_id
                self.to_user_id = to_user_id

            async def callback(self, interaction: discord.Interaction):
                mail_cog = interaction.client.get_cog("Mailbox")
                if mail_cog:
                    modal = mail_cog.ComposeModal(mail_cog, self.user_id, self.to_user_id)
                    return await interaction.response.send_modal(modal)

                await interaction.response.send_message(
                    "📬 Mailbox unavailable. Enable the Mail cog for trader messaging.",
                    ephemeral=True
                )

        class _PrevBtn(Button):
            def __init__(self, cog: "Trades", user_id: int, page: int):
                super().__init__(label="⬅ Prev", style=discord.ButtonStyle.secondary)
                self.cog = cog
                self.user_id = user_id
                self.page = page - 1

            async def callback(self, interaction: discord.Interaction):
                view = Trades.BrowseTradesView(self.cog, self.user_id, self.page)
                await interaction.response.edit_message(view=view)

        class _NextBtn(Button):
            def __init__(self, cog: "Trades", user_id: int, page: int):
                super().__init__(label="Next ➡", style=discord.ButtonStyle.secondary)
                self.cog = cog
                self.user_id = user_id
                self.page = page + 1

            async def callback(self, interaction: discord.Interaction):
                view = Trades.BrowseTradesView(self.cog, self.user_id, self.page)
                await interaction.response.edit_message(view=view)

    class RemoveTradeView(View):
        def __init__(self, cog: "Trades", user_id: int):
            super().__init__(timeout=120)
            self.cog = cog
            self.user_id = user_id

            trades = self.cog.get_user_trades(user_id)
            if not trades:
                self.add_item(Button(label="No trades to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for t in trades:
                    self.add_item(self._RemoveBtn(self.cog, user_id, t["item"]))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Trades", user_id: int, item: str):
                super().__init__(label=item, style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.item = item

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_trade(self.user_id, self.item)
                await refresh_hub(interaction, section="trades")

    # ==================================================
    # Hub Buttons
    # ==================================================
    def build_trades_buttons(self, user_id: int):
        v = View(timeout=180)
        v.add_item(Button(label="📦 Post Trade", style=discord.ButtonStyle.success, custom_id=f"tr_post_{user_id}"))
        v.add_item(Button(label="🔍 Browse Trades", style=discord.ButtonStyle.primary, custom_id=f"tr_browse_{user_id}"))
        v.add_item(Button(label="❌ Remove Trade", style=discord.ButtonStyle.danger, custom_id=f"tr_remove_{user_id}"))
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

        # Post trade
        if cid == f"tr_post_{uid}":
            modal = Trades.PostTradeModal(self, uid)
            return await interaction.response.send_modal(modal)

        # Browse trades
        if cid == f"tr_browse_{uid}":
            e = discord.Embed(title="📦 Trade Board", description="Browse all posted trades.", color=discord.Color.dark_teal())
            v = Trades.BrowseTradesView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        # Remove trade
        if cid == f"tr_remove_{uid}":
            e = discord.Embed(title="❌ Remove Trade", description="Select a trade to remove.", color=discord.Color.red())
            v = Trades.RemoveTradeView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot: commands.Bot):
    await bot.add_cog(Trades(bot))
