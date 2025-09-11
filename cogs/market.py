import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any, Optional, Tuple
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

MARKET_FILE = "data/market.json"
PROFILE_FILE = "data/profiles.json"

def _ci(s: str) -> str:
    return (s or "").strip().casefold()

class Market(commands.Cog):
    """
    Market: post, browse, filter by wishlist matches.
    Integrates with Mailbox (if loaded) to auto-notify wishlist owners when
    new listings matching their wishlist are posted.
    Storage layout:
      market.json = { "user_id": [ { "item","price_str","village","note" }, ... ], ... }
      profiles.json = { "user_id": { "wishlist": [...] , ... }, ... }
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { user_id: [ listing, ... ] }
        self.market: Dict[str, List[Dict[str, Any]]] = load_json(MARKET_FILE, {})
        # user profiles (for wishlist)
        self.profiles: Dict[str, Dict[str, Any]] = load_json(PROFILE_FILE, {})

    # ------------------------------- Persist ---------------------------------
    def _save(self):
        save_json(MARKET_FILE, self.market)

    # ------------------------------- Public API ------------------------------
    def get_user_listings(self, user_id: int) -> List[Dict[str, Any]]:
        return self.market.get(str(user_id), [])

    def add_listing(
        self,
        user_id: int,
        item: str,
        price_str: str,
        village: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        listing = {
            "item": item.strip(),
            "price_str": price_str.strip() or "—",
            "village": village.strip() or "—",
            "note": note.strip(),
        }
        self.market.setdefault(str(user_id), []).append(listing)
        self._save()
        # Try to notify wishlist owners (excluding lister)
        self._notify_wishlist_matches(user_id, listing)
        return listing

    def remove_listing(self, user_id: int, item: str) -> bool:
        cur = self.market.get(str(user_id), [])
        lowered = _ci(item)
        new_list = [l for l in cur if _ci(l.get("item","")) != lowered]
        changed = len(new_list) != len(cur)
        self.market[str(user_id)] = new_list
        if changed:
            self._save()
        return changed

    def _flatten_listings(self) -> List[Tuple[int, Dict[str, Any]]]:
        out: List[Tuple[int, Dict[str, Any]]] = []
        for uid, lst in self.market.items():
            for l in lst:
                out.append((int(uid), l))
        return out

    def search_listings(
        self,
        query: str = "",
        wishlist_only_for: Optional[int] = None
    ) -> List[Tuple[int, Dict[str, Any]]]:
        query_cf = _ci(query)
        items = self._flatten_listings()
        if query_cf:
            items = [(uid, l) for uid, l in items if query_cf in _ci(l.get("item",""))]
        if wishlist_only_for is not None:
            wl = [ _ci(w) for w in self.profiles.get(str(wishlist_only_for), {}).get("wishlist", []) ]
            if wl:
                items = [(uid, l) for uid, l in items if _ci(l.get("item","")) in wl]
            else:
                items = []
        # Sort by item name asc
        items.sort(key=lambda t: _ci(t[1].get("item","")))
        return items

    def get_wishlist_match_count(self, user_id: int) -> int:
        wl = [ _ci(w) for w in self.profiles.get(str(user_id), {}).get("wishlist", []) ]
        if not wl:
            return 0
        cnt = 0
        for _, l in self._flatten_listings():
            if _ci(l.get("item","")) in wl:
                cnt += 1
        return cnt

    # -------------------------- Mailbox Integration --------------------------
    def _notify_wishlist_matches(self, lister_id: int, listing: Dict[str, Any]):
        """
        Sends a mailbox message to users whose wishlist contains the posted item.
        Safe no-op if Mailbox cog is absent.
        """
        # Skip if no mailbox
        mail_cog = self.bot.get_cog("Mailbox")
        if not mail_cog or not hasattr(mail_cog, "send_message"):
            return

        item_cf = _ci(listing.get("item",""))
        if not item_cf:
            return

        for uid_str, prof in self.profiles.items():
            uid = int(uid_str)
            if uid == lister_id:
                continue
            wl = prof.get("wishlist", []) or []
            if any(_ci(x) == item_cf for x in wl):
                subject = "Wishlist match in the Market"
                body = (
                    f"Good news! **{listing.get('item','')}** was just listed on the Market.\n\n"
                    f"**Price:** {listing.get('price_str','—')}\n"
                    f"**Village:** {listing.get('village','—')}\n"
                    f"**Note:** {listing.get('note','') or '—'}\n\n"
                    f"(Open `/home` → Market to view.)"
                )
                try:
                    mail_cog.send_message(from_id=lister_id, to_id=uid, subject=subject, body=body)  # type: ignore
                except Exception:
                    # If DM fails for any reason, ignore silently.
                    pass

    # ----------------------------- UI: Modals --------------------------------
    class AddListingModal(Modal, title="💰 Post Market Listing"):
        def __init__(self, cog: "Market", user_id: int):
            super().__init__(timeout=300)
            self.cog = cog
            self.user_id = user_id

            self.item = TextInput(label="Item", placeholder="e.g. Obsidian Dagger", required=True)
            self.price_str = TextInput(label="Price", placeholder="e.g. 1500g or 'Offer'", required=False)
            self.village = TextInput(label="Village / Region", placeholder="Optional", required=False)
            self.note = TextInput(label="Note", style=discord.TextStyle.long, placeholder="Optional extra info", required=False)
            self.add_item(self.item)
            self.add_item(self.price_str)
            self.add_item(self.village)
            self.add_item(self.note)

        async def on_submit(self, interaction: discord.Interaction):
            self.cog.add_listing(
                self.user_id,
                self.item.value,
                self.price_str.value or "—",
                self.village.value or "—",
                self.note.value or ""
            )
            await refresh_hub(interaction, section="market")

    class RemoveListingView(View):
        def __init__(self, cog: "Market", user_id: int):
            super().__init__(timeout=200)
            self.cog = cog
            self.user_id = user_id
            items = self.cog.get_user_listings(user_id)
            if not items:
                self.add_item(Button(label="No listings to remove", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                for l in items[:25]:
                    name = l.get("item","?")
                    self.add_item(self._RemoveBtn(self.cog, self.user_id, name))

        class _RemoveBtn(Button):
            def __init__(self, cog: "Market", user_id: int, item_name: str):
                super().__init__(label=item_name[:80], style=discord.ButtonStyle.danger)
                self.cog = cog
                self.user_id = user_id
                self.item_name = item_name

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_listing(self.user_id, self.item_name)
                await refresh_hub(interaction, section="market")

    # ----------------------------- UI: Browse --------------------------------
    class BrowseView(View):
        def __init__(self, cog: "Market", user_id: int, mode: str = "all", page: int = 0, query: str = ""):
            """
            mode: "all" or "matches"
            """
            super().__init__(timeout=300)
            self.cog = cog
            self.user_id = user_id
            self.mode = mode
            self.page = page
            self.per_page = 6
            self.query = query
            self._build()

        def _build(self):
            self.clear_items()
            wishlist_only = self.user_id if self.mode == "matches" else None
            rows = self.cog.search_listings(query=self.query, wishlist_only_for=wishlist_only)

            start = self.page * self.per_page
            end = start + self.per_page
            page_rows = rows[start:end]

            # Listing buttons
            wl = [ _ci(w) for w in self.cog.profiles.get(str(self.user_id), {}).get("wishlist", []) ]
            for uid, listing in page_rows:
                label = f"{listing.get('item','?')} — {listing.get('price_str','—')} | {listing.get('village','—')}"
                b = self._ListingBtn(self.cog, self.user_id, uid, listing)
                # highlight wishlist hits
                b.style = discord.ButtonStyle.success if _ci(listing.get('item','')) in wl else discord.ButtonStyle.primary
                b.label = label[:80]
                self.add_item(b)

            # Pagination
            if start > 0:
                self.add_item(self._Prev(self.cog, self.user_id, self.mode, self.page, self.query))
            if end < len(rows):
                self.add_item(self._Next(self.cog, self.user_id, self.mode, self.page, self.query))

            # Optional: small search box
            self.add_item(self._SearchBtn(self.cog, self.user_id, self.mode))

        class _ListingBtn(Button):
            def __init__(self, cog: "Market", user_id: int, seller_id: int, listing: Dict[str, Any]):
                super().__init__(style=discord.ButtonStyle.primary)
                self.cog = cog
                self.user_id = user_id
                self.seller_id = seller_id
                self.listing = listing

            async def callback(self, interaction: discord.Interaction):
                seller = interaction.guild.get_member(self.seller_id) if interaction.guild else None
                seller_name = seller.display_name if seller else str(self.seller_id)
                e = discord.Embed(
                    title=f"{self.listing.get('item','?')}",
                    description=(
                        f"**Price:** {self.listing.get('price_str','—')}\n"
                        f"**Village:** {self.listing.get('village','—')}\n"
                        f"**Note:** {self.listing.get('note','') or '—'}\n"
                        f"**Seller:** {seller_name}"
                    ),
                    color=discord.Color.teal()
                )
                v = View(timeout=180)
                v.add_item(self._MessageBtn(self.cog, self.user_id, self.seller_id, self.listing))
                await interaction.response.edit_message(embed=e, view=v)

            class _MessageBtn(Button):
                def __init__(self, cog: "Market", from_user_id: int, to_user_id: int, listing: Dict[str, Any]):
                    super().__init__(label="✉️ Message Seller", style=discord.ButtonStyle.success)
                    self.cog = cog
                    self.from_user_id = from_user_id
                    self.to_user_id = to_user_id
                    self.listing = listing

                async def callback(self, interaction: discord.Interaction):
                    mail = interaction.client.get_cog("Mailbox")
                    if not mail or not hasattr(mail, "ComposeModal"):
                        return await interaction.response.send_message(
                            "📬 Mailbox unavailable. Enable the Mailbox cog.", ephemeral=True
                        )
                    subject = f"Interested in {self.listing.get('item','?')}"
                    body = (
                        f"Hey! I'm interested in **{self.listing.get('item','?')}**.\n"
                        f"My offer: (enter here)\n\n"
                        f"— Sent from Market"
                    )
                    await interaction.response.send_modal(mail.ComposeModal(mail, self.from_user_id, self.to_user_id, subject, body))  # type: ignore

        class _Prev(Button):
            def __init__(self, cog: "Market", user_id: int, mode: str, page: int, query: str):
                super().__init__(label="⬅ Prev", style=discord.ButtonStyle.secondary)
                self.cog = cog; self.user_id = user_id; self.mode = mode; self.page = page - 1; self.query = query
            async def callback(self, interaction: discord.Interaction):
                v = Market.BrowseView(self.cog, self.user_id, self.mode, self.page, self.query)
                await interaction.response.edit_message(view=v)

        class _Next(Button):
            def __init__(self, cog: "Market", user_id: int, mode: str, page: int, query: str):
                super().__init__(label="Next ➡", style=discord.ButtonStyle.secondary)
                self.cog = cog; self.user_id = user_id; self.mode = mode; self.page = page + 1; self.query = query
            async def callback(self, interaction: discord.Interaction):
                v = Market.BrowseView(self.cog, self.user_id, self.mode, self.page, self.query)
                await interaction.response.edit_message(view=v)

        class _SearchBtn(Button):
            def __init__(self, cog: "Market", user_id: int, mode: str):
                super().__init__(label="🔎 Search", style=discord.ButtonStyle.secondary)
                self.cog = cog; self.user_id = user_id; self.mode = mode
            async def callback(self, interaction: discord.Interaction):
                await interaction.response.send_modal(Market.SearchModal(self.cog, self.user_id, self.mode))

    class SearchModal(Modal, title="🔎 Search Market"):
        def __init__(self, cog: "Market", user_id: int, mode: str):
            super().__init__(timeout=180)
            self.cog = cog; self.user_id = user_id; self.mode = mode
            self.query = TextInput(label="Query", placeholder="Item contains...", required=False)
            self.add_item(self.query)
        async def on_submit(self, interaction: discord.Interaction):
            v = Market.BrowseView(self.cog, self.user_id, self.mode, page=0, query=self.query.value or "")
            e = discord.Embed(title="💰 Market — Search Results", color=discord.Color.teal())
            await interaction.response.edit_message(embed=e, view=v)

    # --------------------------- Hub Buttons (section) -----------------------
    def build_market_buttons(self, user_id: int) -> View:
        v = View(timeout=200)
        match_count = self.get_wishlist_match_count(user_id)
        badge = f" ({match_count})" if match_count else ""
        v.add_item(Button(label="💰 Post Listing", style=discord.ButtonStyle.success, custom_id=f"mk_add_{user_id}"))
        v.add_item(Button(label=f"⭐ Wishlist Matches{badge}", style=discord.ButtonStyle.primary, custom_id=f"mk_match_{user_id}"))
        v.add_item(Button(label="📋 Browse All", style=discord.ButtonStyle.secondary, custom_id=f"mk_all_{user_id}"))
        v.add_item(Button(label="🗑 Remove Listing", style=discord.ButtonStyle.danger, custom_id=f"mk_rm_{user_id}"))
        return v

    # --------------------------- Interaction Handler ------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type or not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        if cid == f"mk_add_{uid}":
            return await interaction.response.send_modal(Market.AddListingModal(self, uid))

        if cid == f"mk_rm_{uid}":
            e = discord.Embed(title="🗑 Remove Listing", description="Select a listing to remove.", color=discord.Color.red())
            v = Market.RemoveListingView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"mk_match_{uid}":
            e = discord.Embed(title="⭐ Wishlist Matches", description="Listings that match your wishlist.", color=discord.Color.green())
            v = Market.BrowseView(self, uid, mode="matches", page=0)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"mk_all_{uid}":
            e = discord.Embed(title="💰 Market — All Listings", color=discord.Color.teal())
            v = Market.BrowseView(self, uid, mode="all", page=0)
            return await interaction.response.edit_message(embed=e, view=v)


async def setup(bot: commands.Bot):
    await bot.add_cog(Market(bot))
