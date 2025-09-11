import os
import json
import discord
from discord.ext import commands
from typing import Dict, List, Any, Optional, Tuple

DATA_DIR = "data"
RECIPES_FILE = os.path.join(DATA_DIR, "recipes.json")
LEARNED_FILE = os.path.join(DATA_DIR, "learned_recipes.json")

# ---------------- JSON helpers ----------------
def _load_json(path: str, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _get_learned(user_id: int) -> Dict[str, List[Dict[str, str]]]:
    store = _load_json(LEARNED_FILE, default={})
    return store.get(str(user_id), {})

def _load_grouped_recipes_from_file() -> Dict[str, List[Dict[str, str]]]:
    raw = _load_json(RECIPES_FILE, default=[])
    grouped: Dict[str, List[Dict[str, str]]] = {}
    if isinstance(raw, dict):
        for prof, items in raw.items():
            grouped.setdefault(prof, [])
            for r in items or []:
                if isinstance(r, dict):
                    grouped[prof].append({
                        "name": r.get("name", "Unknown"),
                        "profession": prof,
                        "link": (r.get("url") or r.get("link") or "")
                    })
    elif isinstance(raw, list):
        for r in raw:
            if isinstance(r, dict):
                prof = (r.get("profession") or "Unknown").strip() or "Unknown"
                grouped.setdefault(prof, []).append({
                    "name": r.get("name", "Unknown"),
                    "profession": prof,
                    "link": (r.get("url") or r.get("link") or "")
                })
    return grouped

# ---------------- Hub <-> Refresh API ----------------
async def refresh_hub(interaction: discord.Interaction, user_id: int, section: str):
    """
    Re-render the same hub message in place where possible.
    For modal submissions, we may send a new ephemeral hub after ack.
    """
    hub_cog: "Hub" = interaction.client.get_cog("Hub")  # type: ignore
    if not hub_cog:
        return
    embed, view = await hub_cog.render(user_id, section)
    try:
        # If we are inside a component interaction tied to the hub message:
        if not interaction.response.is_done() and getattr(interaction, "message", None):
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # Fallback: send a fresh ephemeral hub (modal submit flow)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        pass

# ---------------- Main Hub View ----------------
class HubView(discord.ui.View):
    def __init__(self, cog: "Hub", user_id: int, section: str = "home"):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.section = section

        # Top nav (persistent, edits in place)
        self.add_item(self._NavBtn("🏰 Home", "home", discord.ButtonStyle.primary))
        self.add_item(self._NavBtn("👤 Profile", "profile", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("🛠️ Professions", "professions", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("📜 Recipes", "recipes", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("💰 Market", "market", discord.ButtonStyle.success))

        # Extras on home
        if self.section == "home":
            self.add_item(self._GearBtn())
            self.add_item(self._LoreBtn())

        # Debug utilities
        if self.cog.bot.debug_mode:
            self.add_item(self._DebugStateBtn())

    # ---------- Nav Button ----------
    class _NavBtn(discord.ui.Button):
        def __init__(self, label: str, section: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style)
            self._section = section

        async def callback(self, itx: discord.Interaction):
            v: HubView = self.view  # type: ignore
            # Only owner can use their hub
            if itx.user.id != v.user_id:
                return await itx.response.send_message("⚠️ This hub belongs to someone else.", ephemeral=True)
            embed, view = await v.cog.render(v.user_id, self._section)
            await itx.response.edit_message(embed=embed, view=view)

    # ---------- Gear ----------
    class _GearBtn(discord.ui.Button):
        def __init__(self): super().__init__(label="⚔️ Gear Lookup", style=discord.ButtonStyle.secondary)
        async def callback(self, itx: discord.Interaction):
            e = discord.Embed(title="⚔️ Gear Lookup", description="Coming soon: search gear stats & sources.", color=discord.Color.blurple())
            await itx.response.send_message(embed=e, ephemeral=True)

    # ---------- Lore ----------
    class _LoreBtn(discord.ui.Button):
        def __init__(self): super().__init__(label="📖 Lore Drops", style=discord.ButtonStyle.secondary)
        async def callback(self, itx: discord.Interaction):
            e = discord.Embed(title="📜 Lore Drop", description="The **Riverlands** were once home to House Kordath...", color=discord.Color.gold())
            e.set_footer(text="More lore integrations coming soon!")
            await itx.response.send_message(embed=e, ephemeral=True)

    # ---------- Debug ----------
    class _DebugStateBtn(discord.ui.Button):
        def __init__(self): super().__init__(label="🔍 Inspect State", style=discord.ButtonStyle.danger)
        async def callback(self, itx: discord.Interaction):
            bot = itx.client
            profiles = bot.get_cog("Profile").profiles if bot.get_cog("Profile") else {}
            prof_reg = bot.get_cog("Professions").artisan_registry if bot.get_cog("Professions") else {}
            recipes = bot.get_cog("Recipes").learned if bot.get_cog("Recipes") else {}
            market = bot.get_cog("Market").market if bot.get_cog("Market") else {}
            e = discord.Embed(title="🔍 Debug State", color=discord.Color.red())
            e.add_field(name="Profiles", value=f"{len(profiles)} users", inline=True)
            e.add_field(name="Professions", value=f"{len(prof_reg)} professions", inline=True)
            e.add_field(name="Recipes", value=f"{len(recipes)} users", inline=True)
            e.add_field(name="Market Listings", value=f"{len(market)} items", inline=True)
            await itx.response.send_message(embed=e, ephemeral=True)

# ---------------- Section Views ----------------
class ProfilePanel(discord.ui.View):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=600)
        self.hub = hub
        self.user_id = user_id
        self.add_item(self._SetClassesBtn(hub, user_id))
        self.add_item(self._AddWishlistBtn(hub, user_id))
        self.add_item(self._RemoveWishlistBtn(hub, user_id))

    # ---- Set Classes
    class _SetClassesBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="🎭 Set Classes", style=discord.ButtonStyle.primary)
            self.hub = hub
            self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            if itx.user.id != self.user_id:
                return await itx.response.send_message("⚠️ Not your profile.", ephemeral=True)
            await itx.response.send_modal(SetClassesModal(self.hub, self.user_id))

    # ---- Add Wishlist
    class _AddWishlistBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="➕ Add Wishlist Item", style=discord.ButtonStyle.success)
            self.hub = hub
            self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            if itx.user.id != self.user_id:
                return await itx.response.send_message("⚠️ Not your profile.", ephemeral=True)
            await itx.response.send_modal(AddWishlistModal(self.hub, self.user_id))

    # ---- Remove Wishlist
    class _RemoveWishlistBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="➖ Remove Wishlist Item", style=discord.ButtonStyle.secondary)
            self.hub = hub
            self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            prof = self.hub.profile.get_profile(self.user_id)
            items = prof.get("wishlist", [])
            if not items:
                return await itx.response.send_message("📭 Wishlist is empty.", ephemeral=True)
            options = [discord.SelectOption(label=i, value=i) for i in items[:25]]
            v = discord.ui.View(timeout=120)
            sel = discord.ui.Select(placeholder="Select item to remove…", options=options, max_values=1)
            async def on_pick(sitx: discord.Interaction):
                name = sel.values[0]
                self.hub.profile.remove_wishlist_item(self.user_id, name)
                await sitx.response.send_message(f"🗑️ Removed **{name}**.", ephemeral=True)
                await refresh_hub(sitx, self.user_id, "profile")
            sel.callback = on_pick
            v.add_item(sel)
            await itx.response.send_message("Choose an item:", view=v, ephemeral=True)

class ProfessionsPanel(discord.ui.View):
    CATS = {
        "⛏️ Gathering": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
        "⚙️ Processing": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling", "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
        "🛠️ Crafting":   ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry", "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"],
    }
    TIERS = [
        discord.SelectOption(label="Novice (1)", value="1"),
        discord.SelectOption(label="Apprentice (2)", value="2"),
        discord.SelectOption(label="Journeyman (3)", value="3"),
        discord.SelectOption(label="Master (4)", value="4"),
        discord.SelectOption(label="Grandmaster (5)", value="5"),
    ]

    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=600)
        self.hub = hub
        self.user_id = user_id
        for label in self.CATS.keys():
            self.add_item(self._CatBtn(hub, user_id, label))
        self.add_item(self._RemoveBtn(hub, user_id))

    class _CatBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int, label: str):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.hub = hub
            self.user_id = user_id
            self.label_str = label
        async def callback(self, itx: discord.Interaction):
            profs = ProfessionsPanel.CATS[self.label_str]
            options = [discord.SelectOption(label=p, value=p) for p in profs]
            sel = discord.ui.Select(placeholder="Select profession…", options=options, max_values=1)
            v = discord.ui.View(timeout=120)
            v.add_item(sel)

            async def on_pick(sitx: discord.Interaction):
                profession = sel.values[0]
                # Tier selection
                tier_sel = discord.ui.Select(placeholder=f"Tier for {profession}", options=ProfessionsPanel.TIERS, max_values=1)
                v2 = discord.ui.View(timeout=120)
                v2.add_item(tier_sel)
                async def on_tier(done_itx: discord.Interaction):
                    tier = tier_sel.values[0]
                    ok = self.hub.prof.set_user_profession(self.user_id, profession, tier)
                    if ok:
                        await done_itx.response.send_message(f"✅ Set **{profession}** to Tier **{tier}**.", ephemeral=True)
                        await refresh_hub(done_itx, self.user_id, "professions")
                        await refresh_hub(done_itx, self.user_id, "profile")
                    else:
                        await done_itx.response.send_message("⚠️ You can only have up to 2 professions. Remove one first.", ephemeral=True)
                tier_sel.callback = on_tier
                await sitx.response.send_message(f"Select tier for **{profession}**:", view=v2, ephemeral=True)

            sel.callback = on_pick
            await itx.response.send_message("Choose a profession:", view=v, ephemeral=True)

    class _RemoveBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="❌ Remove Profession", style=discord.ButtonStyle.danger)
            self.hub = hub
            self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            profs = self.hub.prof.get_user_professions(self.user_id)
            if not profs:
                return await itx.response.send_message("You have no professions to remove.", ephemeral=True)
            options = [discord.SelectOption(label=p["name"], value=p["name"]) for p in profs[:25]]
            v = discord.ui.View(timeout=120)
            sel = discord.ui.Select(placeholder="Select profession to remove…", options=options, max_values=1)
            async def on_pick(sitx: discord.Interaction):
                name = sel.values[0]
                changed = self.hub.prof.remove_user_profession(self.user_id, name)
                if changed:
                    await sitx.response.send_message(f"🗑️ Removed **{name}**.", ephemeral=True)
                    await refresh_hub(sitx, self.user_id, "professions")
                    await refresh_hub(sitx, self.user_id, "profile")
                else:
                    await sitx.response.send_message("⚠️ You don't have that profession.", ephemeral=True)
            sel.callback = on_pick
            v.add_item(sel)
            await itx.response.send_message("Choose a profession to remove:", view=v, ephemeral=True)

class RecipesPanel(discord.ui.View):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=600)
        self.hub = hub
        self.user_id = user_id
        self.add_item(self._LearnBtn(hub, user_id))
        self.add_item(self._SearchBtn(hub, user_id))
        self.add_item(self._ViewLearnedBtn(hub, user_id))

    class _LearnBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="📘 Learn Recipe", style=discord.ButtonStyle.primary)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            await itx.response.send_modal(LearnRecipeModal(self.hub, self.user_id))

    class _SearchBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="🔍 Search Recipes", style=discord.ButtonStyle.secondary)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            await itx.response.send_modal(SearchRecipeModal(self.hub, self.user_id))

    class _ViewLearnedBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="📖 Learned Recipes", style=discord.ButtonStyle.success)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            # Build paginated view
            learned = self.hub.recipes.get_user_recipes(self.user_id)
            items: List[Tuple[str, str]] = []  # (prof, name)
            for prof, arr in learned.items():
                for r in arr:
                    items.append((prof, r.get("name","?")))
            if not items:
                return await itx.response.send_message("You haven't learned any recipes yet.", ephemeral=True)
            embed, view = self.hub.make_learned_embed(self.user_id, items, page=1)
            await itx.response.send_message(embed=embed, view=view, ephemeral=True)

class MarketPanel(discord.ui.View):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=600)
        self.hub = hub
        self.user_id = user_id
        self.add_item(self._AddBtn(hub, user_id))
        self.add_item(self._RemoveBtn(hub, user_id))
        self.add_item(self._MyListBtn(hub, user_id))
        self.add_item(self._SearchBtn(hub, user_id))

    class _AddBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="➕ Add Listing", style=discord.ButtonStyle.success)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            await itx.response.send_modal(AddListingModal(self.hub, self.user_id))

    class _RemoveBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="🗑️ Remove Listing", style=discord.ButtonStyle.secondary)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            listings = self.hub.market.get_user_listings(self.user_id)
            if not listings:
                return await itx.response.send_message("You have no active listings.", ephemeral=True)
            options = [discord.SelectOption(label=l["item"], value=l["item"]) for l in listings[:25]]
            sel = discord.ui.Select(placeholder="Select listing to remove…", options=options, max_values=1)
            v = discord.ui.View(timeout=120)
            v.add_item(sel)
            async def on_pick(sitx: discord.Interaction):
                item = sel.values[0]
                ok = self.hub.market.remove_listing(self.user_id, item)
                if ok:
                    await sitx.response.send_message(f"🗑️ Removed **{item}**.", ephemeral=True)
                    await refresh_hub(sitx, self.user_id, "market")
                    await refresh_hub(sitx, self.user_id, "profile")
                else:
                    await sitx.response.send_message("⚠️ Listing not found.", ephemeral=True)
            sel.callback = on_pick
            await itx.response.send_message("Choose a listing:", view=v, ephemeral=True)

    class _MyListBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="📦 My Listings", style=discord.ButtonStyle.primary)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            embed, view = self.hub.make_my_listings_embed(self.user_id, page=1)
            await itx.response.send_message(embed=embed, view=view, ephemeral=True)

    class _SearchBtn(discord.ui.Button):
        def __init__(self, hub: "Hub", user_id: int):
            super().__init__(label="🔎 Search Market", style=discord.ButtonStyle.secondary)
            self.hub = hub; self.user_id = user_id
        async def callback(self, itx: discord.Interaction):
            await itx.response.send_modal(SearchMarketModal(self.hub, self.user_id))

# ---------------- Modals ----------------
class SetClassesModal(discord.ui.Modal, title="🎭 Set Classes"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.primary = discord.ui.TextInput(label="Primary Class", placeholder="e.g., Fighter", required=False, max_length=32)
        self.secondary = discord.ui.TextInput(label="Secondary Class", placeholder="e.g., Rogue", required=False, max_length=32)
        self.add_item(self.primary); self.add_item(self.secondary)
    async def on_submit(self, itx: discord.Interaction):
        self.hub.profile.set_classes(self.user_id, str(self.primary.value or ""), str(self.secondary.value or ""))
        await itx.response.send_message("✅ Classes updated.", ephemeral=True)
        await refresh_hub(itx, self.user_id, "profile")

class AddWishlistModal(discord.ui.Modal, title="➕ Add Wishlist Item"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.item = discord.ui.TextInput(label="Item name", placeholder="Exact or partial", required=True, max_length=100)
        self.add_item(self.item)
    async def on_submit(self, itx: discord.Interaction):
        ok = self.hub.profile.add_wishlist_item(self.user_id, str(self.item.value))
        msg = f"✅ Added **{self.item.value}**." if ok else "⚠️ Already on your wishlist."
        await itx.response.send_message(msg, ephemeral=True)
        await refresh_hub(itx, self.user_id, "profile")

class LearnRecipeModal(discord.ui.Modal, title="📘 Learn Recipe"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.profession = discord.ui.TextInput(label="Profession", placeholder="e.g., Herbalism", required=True, max_length=40)
        self.name = discord.ui.TextInput(label="Recipe Name", placeholder="Enter the exact or partial name", required=True, max_length=100)
        self.add_item(self.profession); self.add_item(self.name)
    async def on_submit(self, itx: discord.Interaction):
        pro = str(self.profession.value).strip()
        nm = str(self.name.value).strip()
        link = self.hub.recipes.get_recipe_link(nm)
        ok = self.hub.recipes.add_learned_recipe(self.user_id, pro, nm, link)
        if ok:
            await itx.response.send_message(f"✅ Learned **{nm}** ({pro}).", ephemeral=True)
            await refresh_hub(itx, self.user_id, "recipes")
            await refresh_hub(itx, self.user_id, "profile")
        else:
            await itx.response.send_message("⚠️ Already learned.", ephemeral=True)

class SearchRecipeModal(discord.ui.Modal, title="🔍 Search Recipes"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.query = discord.ui.TextInput(label="Search", placeholder="e.g., Tincture", required=True, max_length=100)
        self.prof = discord.ui.TextInput(label="Profession (optional)", placeholder="e.g., Herbalism", required=False, max_length=40)
        self.add_item(self.query); self.add_item(self.prof)
    async def on_submit(self, itx: discord.Interaction):
        p = str(self.prof.value).strip() or None
        hits = self.hub.recipes.search_recipes(str(self.query.value), professions=[p] if p else None, limit=25)
        if not hits:
            return await itx.response.send_message("No matches.", ephemeral=True)
        lines = []
        for h in hits[:10]:
            lvl = f" (Lv {h['level']})" if h.get("level") else ""
            link = f" — <{h['link']}>" if h.get("link") else ""
            lines.append(f"• **{h['name']}** — *{h['profession']}*{lvl}{link}")
        e = discord.Embed(title=f"🔍 Results for “{self.query.value}”", description="\n".join(lines), color=discord.Color.green())
        await itx.response.send_message(embed=e, ephemeral=True)

class AddListingModal(discord.ui.Modal, title="➕ Add Listing"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.item = discord.ui.TextInput(label="Item", required=True, max_length=100)
        self.price = discord.ui.TextInput(label="Price (gold, number)", required=True, max_length=10)
        self.village = discord.ui.TextInput(label="Village", required=True, max_length=40)
        self.note = discord.ui.TextInput(label="Note (optional)", required=False, max_length=120)
        self.add_item(self.item); self.add_item(self.price); self.add_item(self.village); self.add_item(self.note)
    async def on_submit(self, itx: discord.Interaction):
        try:
            price_i = int(str(self.price.value).strip())
        except Exception:
            price_i = None
        entry = self.hub.market.add_listing(self.user_id, str(self.item.value).strip(), price_i, str(self.village.value).strip(), str(self.note.value or "").strip())
        await itx.response.send_message(f"✅ Listed **{entry['item']}** for **{entry['price_str']}** in **{entry['village']}**.", ephemeral=True)
        await refresh_hub(itx, self.user_id, "market")
        await refresh_hub(itx, self.user_id, "profile")

class SearchMarketModal(discord.ui.Modal, title="🔎 Search Market"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__()
        self.hub = hub; self.user_id = user_id
        self.query = discord.ui.TextInput(label="Search", placeholder="e.g., Tincture", required=True, max_length=100)
        self.add_item(self.query)
    async def on_submit(self, itx: discord.Interaction):
        q = str(self.query.value).lower().strip()
        hits = [m for m in self.hub.market.market if q in str(m.get("item","")).lower()]
        if not hits:
            return await itx.response.send_message("No market matches.", ephemeral=True)
        lines = [f"• **{m['item']}** — {m.get('price_str','?')} | {m['village']} (seller: <@{m['seller_id']}>)" for m in hits[:15]]
        e = discord.Embed(title=f"🔎 Market results for “{self.query.value}”", description="\n".join(lines), color=discord.Color.teal())
        await itx.response.send_message(embed=e, ephemeral=True)

# ---------------- Hub Cog ----------------
class Hub(commands.Cog):
    """Single-message hub with full UI flows (ephemeral, edit-in-place where possible)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Register /home slash command directly
        @bot.tree.command(name="home", description="Open your private Guild Codex hub")
        async def home(interaction: discord.Interaction):
            embed, view = await self.render(interaction.user.id, "home")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Quick properties (profile/prof/recipes/market)
    @property
    def profile(self): return self.bot.get_cog("Profile")
    @property
    def prof(self): return self.bot.get_cog("Professions")
    @property
    def recipes(self): return self.bot.get_cog("Recipes")
    @property
    def market(self): return self.bot.get_cog("Market")

    # Keep all your render_* methods here (render_home, render_profile, etc.)
    # ... (they’re already in your file above)

    @commands.hybrid_command(name="hubportal", description="(Admin) Post the hub portal message in this channel")
    @commands.has_permissions(administrator=True)
    async def hubportal(self, ctx: commands.Context):
        """Admin command: posts a permanent portal message for members to open their hub."""
        view = PortalView(self)
        embed = discord.Embed(
            title="🏰 Guild Codex Portal",
            description="Click below to open your personal **Guild Codex** hub.\n\nAll interactions are **private** — only you can see your hub.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed, view=view)
        await ctx.reply(f"✅ Portal posted in {ctx.channel.mention}", ephemeral=True)


class PortalView(discord.ui.View):
    def __init__(self, hub: Hub):
        super().__init__(timeout=None)
        self.hub = hub

    @discord.ui.button(label="Open My Hub", style=discord.ButtonStyle.primary, emoji="🏰")
    async def open_hub(self, itx: discord.Interaction, _: discord.ui.Button):
        embed, view = await self.hub.render(itx.user.id, "home")
        await itx.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot))


# ---------- Pagination Views ----------
class LearnedPagerView(discord.ui.View):
    def __init__(self, hub: Hub, user_id: int, items: List[Tuple[str,str]], page: int, total_pages: int):
        super().__init__(timeout=300)
        self.hub = hub; self.user_id = user_id
        self.items = items; self.page = page; self.total_pages = total_pages
        self.add_item(self._PrevBtn(self)); self.add_item(self._NextBtn(self))
    class _PrevBtn(discord.ui.Button):
        def __init__(self, parent): super().__init__(label="◀ Prev", style=discord.ButtonStyle.secondary); self.p = parent
        async def callback(self, itx: discord.Interaction):
            if self.p.page <= 1: return await itx.response.defer(ephemeral=True)
            e, v = self.p.hub.make_learned_embed(self.p.user_id, self.p.items, self.p.page - 1)
            await itx.response.edit_message(embed=e, view=v)
    class _NextBtn(discord.ui.Button):
        def __init__(self, parent): super().__init__(label="Next ▶", style=discord.ButtonStyle.secondary); self.p = parent
        async def callback(self, itx: discord.Interaction):
            if self.p.page >= self.p.total_pages: return await itx.response.defer(ephemeral=True)
            e, v = self.p.hub.make_learned_embed(self.p.user_id, self.p.items, self.p.page + 1)
            await itx.response.edit_message(embed=e, view=v)

class ListingsPagerView(discord.ui.View):
    def __init__(self, hub: Hub, user_id: int, page: int, total_pages: int):
        super().__init__(timeout=300)
        self.hub = hub; self.user_id = user_id; self.page = page; self.total_pages = total_pages
        self.add_item(self._PrevBtn(self)); self.add_item(self._NextBtn(self))
    class _PrevBtn(discord.ui.Button):
        def __init__(self, p): super().__init__(label="◀ Prev", style=discord.ButtonStyle.secondary); self.p = p
        async def callback(self, itx: discord.Interaction):
            if self.p.page <= 1: return await itx.response.defer(ephemeral=True)
            e, v = self.p.hub.make_my_listings_embed(self.p.user_id, self.p.page - 1)
            await itx.response.edit_message(embed=e, view=v)
    class _NextBtn(discord.ui.Button):
        def __init__(self, p): super().__init__(label="Next ▶", style=discord.ButtonStyle.secondary); self.p = p
        async def callback(self, itx: discord.Interaction):
            if self.p.page >= self.p.total_pages: return await itx.response.defer(ephemeral=True)
            e, v = self.p.hub.make_my_listings_embed(self.p.user_id, self.p.page + 1)
            await itx.response.edit_message(embed=e, view=v)

# ---------------- Portal View ----------------


class PortalView(discord.ui.View):
    def __init__(self, hub: Hub):
        super().__init__(timeout=None)
        self.hub = hub

    @discord.ui.button(label="Open My Hub", style=discord.ButtonStyle.primary, emoji="🏰")
    async def open_hub(self, itx: discord.Interaction, _: discord.ui.Button):
        embed, view = await self.hub.render(itx.user.id, "home")
        await itx.response.send_message(embed=embed, view=view, ephemeral=True)



async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot))
