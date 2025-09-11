# cogs/trades.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

TRADES_FILE = "data/trades.json"
PROFILE_FILE = "data/profiles.json"


class Trades(commands.Cog):
    """Guild-wide trade board for offers, requests, and wishlist integration."""

    def __init__(self, bot):
        self.bot = bot
        self.trades: Dict[str, List[Dict[str, Any]]] = load_json(TRADES_FILE, {})
        self.profiles: Dict[str, Dict[str, Any]] = load_json(PROFILE_FILE, {})

    def _save(self):
        save_json(TRADES_FILE, self.trades)

    # ---------------- Public API ----------------
    def get_user_trades(self, user_id: int) -> List[Dict[str, Any]]:
        return self.trades.get(str(user_id), [])

    def add_trade(self, user_id: int, ttype: str, item: str, price: str, note: str) -> Dict[str, Any]:
        entry = {"type": ttype, "item": item, "price": price, "note": note}
        self.trades.setdefault(str(user_id), []).append(entry)
        self._save()
        return entry

    def remove_trade(self, user_id: int, item: str):
        self.trades[str(user_id)] = [
            t for t in self.trades.get(str(user_id), []) if t["item"].lower() != item.lower()
        ]
        self._save()

    def get_all_trades(self) -> List[tuple]:
        """Return all trades across the guild: (user_id, trade_dict)."""
        return [(int(uid), t) for uid, posts in self.trades.items() for t in posts]

    # ---------------- UI ----------------
    class PostTradeModal(Modal, title="📦 Post Trade"):
        def __init__(self, cog, user_id: int):
            super().__init__(timeout=240)
            self.cog, self.user_id = cog, user_id
            self.ttype = Select(
                placeholder="Trade Type",
                options=[
                    discord.SelectOption(label="For Sale"),
                    discord.SelectOption(label="Wanted")
                ],
                min_values=1, max_values=1
            )
            self.item = TextInput(label="Item", required=True)
            self.price = TextInput(label="Price", placeholder="e.g. 100g", required=False)
            self.note = TextInput(label="Note", required=False)

            self.add_item(self.ttype)
            self.add_item(self.item)
            self.add_item(self.price)
            self.add_item(self.note)

        async def on_submit(self, interaction):
            self.cog.add_trade(
                self.user_id,
                self.ttype.values[0],
                self.item.value,
                self.price.value or "—",
                self.note.value or ""
            )
            await refresh_hub(interaction, "trades")

    class RemoveTradeView(View):
        def __init__(self, cog, user_id: int):
            super().__init__(timeout=120)
            trades = cog.get_user_trades(user_id)
            if not trades:
                self.add_item(Button(label="No trades to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for t in trades:
                    self.add_item(Trades._RemoveBtn(cog, user_id, t["item"]))

        class _RemoveBtn(Button):
            def __init__(self, cog, user_id: int, item: str):
                super().__init__(label=f"Remove {item}", style=discord.ButtonStyle.danger)
                self.cog, self.user_id, self.item = cog, user_id, item

            async def callback(self, interaction):
                self.cog.remove_trade(self.user_id, self.item)
                await refresh_hub(interaction, "trades")

    class ViewAllTradesView(View):
        def __init__(self, cog):
            super().__init__(timeout=180)
            trades = cog.get_all_trades()
            if not trades:
                self.add_item(Button(label="No trades available", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for uid, t in trades[:10]:  # show first 10
                    label = f"{t['type']}: {t['item']} ({t['price']})"
                    self.add_item(Trades._TradeBtn(cog, uid, t, label))

        class _TradeBtn(Button):
            def __init__(self, cog, user_id: int, trade: Dict[str, Any], label: str):
                super().__init__(label=label[:80], style=discord.ButtonStyle.primary)
                self.cog, self.user_id, self.trade = cog, user_id, trade

            async def callback(self, interaction: discord.Interaction):
                user = interaction.guild.get_member(self.user_id) if interaction.guild else None
                poster = user.display_name if user else str(self.user_id)
                e = discord.Embed(
                    title=f"{self.trade['type']} — {self.trade['item']}",
                    description=f"💰 {self.trade['price']}\n📝 {self.trade['note'] or '—'}",
                    color=discord.Color.orange()
                )
                e.set_footer(text=f"Posted by {poster}")
                await interaction.response.edit_message(embed=e, view=None)

    # ---------------- Hub ----------------
    def build_trades_buttons(self, user_id: int) -> View:
        v = View(timeout=180)
        v.add_item(Button(label="📦 Post Trade", style=discord.ButtonStyle.success, custom_id=f"tr_post_{user_id}"))
        v.add_item(Button(label="❌ Remove Trade", style=discord.ButtonStyle.danger, custom_id=f"tr_remove_{user_id}"))
        v.add_item(Button(label="📋 View All Trades", style=discord.ButtonStyle.primary, custom_id=f"tr_all_{user_id}"))
        return v

    # ---------------- Interaction Listener ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        cid = interaction.data.get("custom_id") if getattr(interaction, "data", None) else None
        if not cid:
            return
        uid = interaction.user.id

        if cid == f"tr_post_{uid}":
            return await interaction.response.send_modal(Trades.PostTradeModal(self, uid))

        if cid == f"tr_remove_{uid}":
            e = discord.Embed(title="❌ Remove Trade", description="Pick one to remove.", color=discord.Color.red())
            return await interaction.response.edit_message(embed=e, view=Trades.RemoveTradeView(self, uid))

        if cid == f"tr_all_{uid}":
            e = discord.Embed(title="📋 All Trades", description="Browse the guild's trade board.", color=discord.Color.orange())
            v = Trades.ViewAllTradesView(self)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot):
    await bot.add_cog(Trades(bot))

