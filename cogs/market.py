import os
import json
import discord
from discord.ext import commands
from typing import Any, Dict, List
from cogs.hub import refresh_hub

MARKET_FILE = "data/market.json"

def _load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class Market(commands.Cog):
    """
    Simple JSON-backed market:
      - add/remove/list user listings
      - find wishlist matches
    Listing schema:
      { item, price, price_str, village, seller_id, note }
    """
    def __init__(self, bot):
        self.bot = bot
        self.market: List[Dict[str, Any]] = _load_json(MARKET_FILE, [])

    # --------- helpers ----------
    def _save(self):
        _save_json(MARKET_FILE, self.market)

    def get_user_listings(self, user_id: int) -> List[Dict[str, Any]]:
        return [m for m in self.market if str(m.get("seller_id")) == str(user_id)]

    def find_matches_for_wishlist(self, wishlist: List[str]) -> List[Dict[str, Any]]:
        if not wishlist:
            return []
        wl = [w.lower() for w in wishlist]
        hits: List[Dict[str, Any]] = []
        for m in self.market:
            name = str(m.get("item", "")).lower()
            if any(w in name for w in wl):
                hits.append(m)
        return hits

    # --------- mutations ----------
    def add_listing(self, seller_id: int, item: str, price: int | None, village: str, note: str | None = None):
        price_str = f"{price}g" if isinstance(price, int) and price >= 0 else "?"
        entry = {
            "item": item.strip(),
            "price": price if isinstance(price, int) else None,
            "price_str": price_str,
            "village": (village or "Unknown").strip() or "Unknown",
            "seller_id": str(seller_id),
            "note": (note or "").strip() or None,
        }
        self.market.append(entry)
        self._save()
        return entry

    def remove_listing(self, seller_id: int, item: str) -> bool:
        before = len(self.market)
        self.market = [m for m in self.market if not (str(m.get("seller_id")) == str(seller_id) and str(m.get("item")) == item)]
        changed = len(self.market) != before
        if changed:
            self._save()
        return changed

    # --------- commands ----------
    @commands.hybrid_command(name="marketadd", description="Add a market listing")
    async def market_add_cmd(self, ctx: commands.Context, item: str, price: int, village: str, note: str | None = None):
        entry = self.add_listing(ctx.author.id, item, price, village, note)
        await ctx.reply(f"✅ Listed **{entry['item']}** for **{entry['price_str']}** in **{entry['village']}**.", ephemeral=True)
        if getattr(ctx, "interaction", None):
            await refresh_hub(ctx.interaction, ctx.author.id, section="market")
            await refresh_hub(ctx.interaction, ctx.author.id, section="profile")

    @commands.hybrid_command(name="marketremove", description="Remove one of your market listings by item name")
    async def market_remove_cmd(self, ctx: commands.Context, item: str):
        ok = self.remove_listing(ctx.author.id, item)
        if ok:
            await ctx.reply(f"🗑️ Removed listing for **{item}**.", ephemeral=True)
            if getattr(ctx, "interaction", None):
                await refresh_hub(ctx.interaction, ctx.author.id, section="market")
                await refresh_hub(ctx.interaction, ctx.author.id, section="profile")
        else:
            await ctx.reply("⚠️ Listing not found.", ephemeral=True)

    @commands.hybrid_command(name="marketlist", description="See your market listings (with pagination)")
    async def market_list_cmd(self, ctx: commands.Context, page: int = 1):
        page = max(1, page)
        listings = self.get_user_listings(ctx.author.id)
        if not listings:
            return await ctx.reply("*You have no active listings.*", ephemeral=True)
        per = 10
        start, end = (page - 1) * per, (page - 1) * per + per
        page_items = listings[start:end]
        total_pages = (len(listings) + per - 1) // per

        lines = [f"• **{m['item']}** — {m.get('price_str','?')} | {m['village']}" + (f" — {m['note']}" if m.get('note') else "") for m in page_items]
        embed = discord.Embed(
            title=f"💰 My Listings — Page {page}/{total_pages}",
            description="\n".join(lines) if lines else "*No items on this page*",
            color=discord.Color.teal()
        )
        await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="marketsearch", description="Search market for an item")
    async def market_search_cmd(self, ctx: commands.Context, query: str):
        q = query.lower().strip()
        hits = [m for m in self.market if q in str(m.get("item","")).lower()]
        if not hits:
            return await ctx.reply("🔎 No market matches.", ephemeral=True)
        lines = [f"• **{m['item']}** — {m.get('price_str','?')} | {m['village']} (seller: <@{m['seller_id']}>)" for m in hits[:15]]
        embed = discord.Embed(title=f"🔎 Market results for “{query}”", description="\n".join(lines), color=discord.Color.teal())
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Market(bot))
