# cogs/hub.py
import os
import json
import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List

# ---------- File helpers (safe, no-crash) ----------
DATA_DIR = "data"

def _path(*names: str) -> str:
    """
    Prefer data/<name>.json if it exists, else <name>.json, else default to data path for writes.
    """
    name = os.path.join(*names)
    p1 = os.path.join(DATA_DIR, name)
    if os.path.exists(p1):
        return p1
    p2 = name
    if os.path.exists(p2):
        return p2
    # default write location
    os.makedirs(os.path.dirname(p1), exist_ok=True)
    return p1

def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Core files the bot uses (present or future)
PROFILES_FILE  = _path("profiles.json")
RECIPES_FILE   = _path("recipes.json")
LEARNED_FILE   = _path("learned_recipes.json")
MARKET_FILE    = _path("market.json")
TRADES_FILE    = _path("trades.json")
MAILBOX_FILE   = _path("mailbox.json")
REGISTRY_FILE  = _path("artisan_registry.json")
GROUPED_FILE   = _path("recipes_grouped.json")
ACTIVITY_FILE  = _path("activity.json")  # new, optional

# ---------- Public helper: record lightweight activity (optional by other cogs) ----------
def log_activity(kind: str, user_id: int, detail: str):
    """
    Append a small activity item others can show on the Home dashboard.
    Example kinds: "mail", "market", "trade", "recipe", "profession"
    """
    rec = {"kind": kind, "user": int(user_id), "detail": str(detail)}
    store: List[Dict[str, Any]] = _load_json(ACTIVITY_FILE, [])
    store.append(rec)
    # keep last 100 for sanity
    store = store[-100:]
    _save_json(ACTIVITY_FILE, store)

# ---------- Public helper: refresh the hub (edit SAME message) ----------
async def refresh_hub(interaction: discord.Interaction, section: str = "home"):
    """
    Force-refresh the user's hub message (edits the same message).
    Safe to call from any cog after a state change.
    """
    hub: Optional["Hub"] = interaction.client.get_cog("Hub")  # type: ignore
    if not hub:
        return
    user_id = interaction.user.id
    embed = await hub.render_section(interaction, user_id, section, hub.bot.debug_mode)
    view = HubView(hub, user_id, section=section, debug=hub.bot.debug_mode)
    view.attach_section_controls(section, user_id)

    try:
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=view)
    except discord.NotFound:
        # If the original hub message is gone, send a fresh ephemeral hub
        await hub._send_hub_ephemeral(interaction, user_id, section=section)


# =========================
# View
# =========================
class HubView(discord.ui.View):
    """
    Navigation row + dynamic section controls merged in.
    Button labels can include live counts (badges) by passing computed labels from Hub.get_dashboard_counts().
    """
    def __init__(self, cog: "Hub", user_id: int, section: str = "home", debug: bool = False):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.section = section
        self.debug = debug

        # Compute badges for nav labels
        counts = self.cog.get_dashboard_counts(user_id)
        mailbox_label = "📬 Mailbox" + (f" ({counts['mail_unread']})" if counts["mail_unread"] > 0 else "")
        market_label  = "💰 Market" + (f" ({counts['market_wishlist_matches']})" if counts["market_wishlist_matches"] > 0 else "")
        trades_label  = "📦 Trades" + (f" ({counts['trade_wishlist_matches']})" if counts["trade_wishlist_matches"] > 0 else "")

        # Top nav
        self.add_item(self._NavBtn("🏰 Home", "home", discord.ButtonStyle.primary))
        self.add_item(self._NavBtn("👤 Profile", "profile", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("🛠️ Professions", "professions", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("📜 Recipes", "recipes", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn(market_label, "market", discord.ButtonStyle.success))
        self.add_item(self._NavBtn(mailbox_label, "mailbox", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn("📜 Registry", "registry", discord.ButtonStyle.secondary))
        self.add_item(self._NavBtn(trades_label, "trades", discord.ButtonStyle.secondary))

        # Utility
        if section != "home":
            self.add_item(self._BackBtn())

    def attach_section_controls(self, section: str, user_id: int):
        """
        Ask the relevant cog for a per-section control View and merge its items here.
        This keeps nav on the first row; section controls are appended below.
        """
        # Quick actions for Home
        if section == "home":
            quick = self.cog.build_home_quick_actions(user_id)
            if quick:
                for item in quick.children:
                    self.add_item(item)

        cog_map = {
            "profile": ("Profile", "build_profile_buttons"),
            "recipes": ("Recipes", "build_recipe_buttons"),
            "market": ("Market", "build_market_buttons"),
            "professions": ("Professions", "build_professions_buttons"),
            "mailbox": ("Mailbox", "build_mailbox_buttons"),
            "registry": ("Registry", "build_registry_buttons"),
            "trades": ("Trades", "build_trades_buttons"),
        }
        if section not in cog_map:
            return
        cog_name, method_name = cog_map[section]
        cog = self.cog.bot.get_cog(cog_name)
        if cog and hasattr(cog, method_name):
            try:
                subview = getattr(cog, method_name)(user_id)  # expected to return a discord.ui.View
                if isinstance(subview, discord.ui.View):
                    for item in subview.children:
                        self.add_item(item)
            except Exception:
                pass

    class _NavBtn(discord.ui.Button):
        def __init__(self, label: str, target: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style)
            self.target = target

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message(
                    "This hub belongs to someone else. Use `/home` to open your own.",
                    ephemeral=True,
                )
            embed = await v.cog.render_section(interaction, v.user_id, self.target, v.debug)
            new_view = HubView(v.cog, v.user_id, section=self.target, debug=v.debug)
            new_view.attach_section_controls(self.target, v.user_id)
            await interaction.response.edit_message(embed=embed, view=new_view)

    class _BackBtn(discord.ui.Button):
        def __init__(self):
            super().__init__(label="⬅ Back to Home", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            embed = await v.cog.render_section(interaction, v.user_id, "home", v.debug)
            new_view = HubView(v.cog, v.user_id, section="home", debug=v.debug)
            new_view.attach_section_controls("home", v.user_id)
            await interaction.response.edit_message(embed=embed, view=new_view)


# =========================
# Cog
# =========================
class Hub(commands.Cog):
    """Single-message persistent hub. All other features are UI-only from here."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /home (hybrid so it works as slash and prefix in a pinch)
    @commands.hybrid_command(name="home", description="Open your guild hub")
    async def home(self, ctx: commands.Context):
        await self._send_hub_context(ctx, section="home")

    # -------- Send helpers --------
    async def _send_hub_context(self, ctx: commands.Context, section: str = "home"):
        embed = await self.render_section(None, ctx.author.id, section, self.bot.debug_mode)
        view = HubView(self, ctx.author.id, section=section, debug=self.bot.debug_mode)
        view.attach_section_controls(section, ctx.author.id)
        if getattr(ctx, "interaction", None) is not None:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await ctx.send(embed=embed, view=view)

    async def _send_hub_ephemeral(self, interaction: discord.Interaction, user_id: int, section: str = "home"):
        embed = await self.render_section(interaction, user_id, section, self.bot.debug_mode)
        view = HubView(self, user_id, section=section, debug=self.bot.debug_mode)
        view.attach_section_controls(section, user_id)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # -------- Dashboard counts used by HubView (badges) & home embed --------
    def get_dashboard_counts(self, user_id: int) -> Dict[str, int]:
        """
        Returns mailbox unread, wishlist matches in market/trades, learned count, professions count.
        Uses cogs when available; safely falls back to JSON files.
        """
        # Mailbox unread
        mail_unread = 0
        mail_cog = self.bot.get_cog("Mailbox")
        if mail_cog and hasattr(mail_cog, "get_inbox"):
            try:
                inbox = mail_cog.get_inbox(user_id)  # type: ignore
                mail_unread = len([m for m in inbox if not m.get("read")])
            except Exception:
                pass
        else:
            inbox = _load_json(MAILBOX_FILE, {}).get(str(user_id), [])
            mail_unread = len([m for m in inbox if not m.get("read")])

        # Wishlist
        profiles = _load_json(PROFILES_FILE, {})
        wishlist = [w.lower() for w in profiles.get(str(user_id), {}).get("wishlist", [])]

        # Market wishlist matches
        market_matches = 0
        market = _load_json(MARKET_FILE, [])
        # market is expected like [ {item, price_str, seller_id, ...}, ... ] or by-user dict; handle both
        if isinstance(market, dict):
            all_listings = []
            for uid, items in market.items():
                for it in items:
                    all_listings.append(it)
        else:
            all_listings = market
        try:
            for it in all_listings:
                name = str(it.get("item", "")).lower()
                if name and any(name == w for w in wishlist):
                    market_matches += 1
        except Exception:
            market_matches = 0

        # Trades wishlist matches
        trade_matches = 0
        trades = _load_json(TRADES_FILE, {})
        try:
            for uid, posts in trades.items():
                for t in posts:
                    name = str(t.get("item", "")).lower()
                    if name and any(name == w for w in wishlist):
                        trade_matches += 1
        except Exception:
            trade_matches = 0

        # Learned recipes total
        learned_total = 0
        learned = _load_json(LEARNED_FILE, {})
        try:
            mine = learned.get(str(user_id), {})
            if isinstance(mine, dict):
                learned_total = sum(len(v) for v in mine.values())
        except Exception:
            pass

        # Professions count
        prof_count = 0
        prof_cog = self.bot.get_cog("Professions")
        if prof_cog and hasattr(prof_cog, "get_user_professions"):
            try:
                profs = prof_cog.get_user_professions(user_id)  # type: ignore
                prof_count = len(profs) if profs else 0
            except Exception:
                pass

        return {
            "mail_unread": mail_unread,
            "market_wishlist_matches": market_matches,
            "trade_wishlist_matches": trade_matches,
            "learned_total": learned_total,
            "professions_count": prof_count,
        }

    # -------- Quick actions on Home --------
    def build_home_quick_actions(self, user_id: int) -> Optional[discord.ui.View]:
        """
        Buttons under Home to deep-link to common actions.
        """
        counts = self.get_dashboard_counts(user_id)
        v = discord.ui.View(timeout=240)

        # Inbox
        v.add_item(
            discord.ui.Button(
                label=f"Open Inbox ({counts['mail_unread']} unread)" if counts["mail_unread"] else "Open Inbox",
                style=discord.ButtonStyle.primary,
                custom_id=f"hub_open_inbox_{user_id}",
            )
        )
        # Market wishlist matches
        v.add_item(
            discord.ui.Button(
                label=f"Wishlist in Market ({counts['market_wishlist_matches']})"
                if counts["market_wishlist_matches"]
                else "Wishlist in Market",
                style=discord.ButtonStyle.success,
                custom_id=f"hub_market_wishlist_{user_id}",
            )
        )
        # Trades wishlist matches
        v.add_item(
            discord.ui.Button(
                label=f"Wishlist in Trades ({counts['trade_wishlist_matches']})"
                if counts["trade_wishlist_matches"]
                else "Wishlist in Trades",
                style=discord.ButtonStyle.secondary,
                custom_id=f"hub_trades_wishlist_{user_id}",
            )
        )
        # Learned recipes
        v.add_item(
            discord.ui.Button(
                label=f"My Learned Recipes ({counts['learned_total']})"
                if counts["learned_total"]
                else "My Learned Recipes",
                style=discord.ButtonStyle.secondary,
                custom_id=f"hub_recipes_learned_{user_id}",
            )
        )
        return v

    # -------- Router --------
    async def render_section(self, interaction, user_id: int, section: str, debug: bool = False):
        if section == "home":
            return await self.render_home(user_id)
        if section == "profile":
            return await self.render_profile(user_id)
        if section == "professions":
            return await self.render_professions(user_id)
        if section == "recipes":
            return await self.render_recipes(user_id)
        if section == "market":
            return await self.render_market(user_id)
        if section == "mailbox":
            return await self.render_mailbox(user_id)
        if section == "registry":
            return await self.render_registry(user_id)
        if section == "trades":
            return await self.render_trades(user_id)
        return await self.render_home(user_id)

    # -------- Embeds (safe fallbacks that defer to cogs when available) --------
    async def render_home(self, user_id: int) -> discord.Embed:
        counts = self.get_dashboard_counts(user_id)
        # Recent activity (last 5 items for this user, if any exist)
        activity: List[Dict[str, Any]] = _load_json(ACTIVITY_FILE, [])
        recent_lines: List[str] = []
        for rec in reversed(activity):
            if rec.get("user") == int(user_id):
                kind = str(rec.get("kind", "event"))
                detail = str(rec.get("detail", ""))
                icon = {
                    "mail": "📬",
                    "market": "💰",
                    "trade": "📦",
                    "recipe": "📜",
                    "profession": "🛠️",
                }.get(kind, "🟡")
                recent_lines.append(f"{icon} {detail}")
                if len(recent_lines) >= 5:
                    break

        e = discord.Embed(
            title="🏰 Guild Codex",
            description=(
                "Your unified hub for **Profiles**, **Professions**, **Recipes**, **Market**, **Mailbox**, **Registry**, and **Trades**.\n\n"
                "### 🔎 Overview\n"
                f"• 📬 **Unread Mail:** {counts['mail_unread']}\n"
                f"• 💰 **Wishlist Matches (Market):** {counts['market_wishlist_matches']}\n"
                f"• 📦 **Wishlist Matches (Trades):** {counts['trade_wishlist_matches']}\n"
                f"• 📘 **Learned Recipes:** {counts['learned_total']}\n"
                f"• 🛠️ **Professions:** {counts['professions_count']}\n"
            ),
            color=discord.Color.gold(),
        )
        if recent_lines:
            e.add_field(name="📰 Recent Alerts", value="\n".join(recent_lines), inline=False)
        e.set_footer(text="Use the buttons below for quick actions and navigation.")
        return e

    async def render_profile(self, user_id: int) -> discord.Embed:
        prof_cog = self.bot.get_cog("Profile")
        if prof_cog and hasattr(prof_cog, "build_profile_embed"):
            try:
                user = self.bot.get_user(user_id) or discord.Object(id=user_id)  # type: ignore
                built = prof_cog.build_profile_embed(user)  # type: ignore
                if isinstance(built, discord.Embed):
                    # --- Augment with professions if Professions cog exists ---
                    pro_cog = self.bot.get_cog("Professions")
                    if pro_cog and hasattr(pro_cog, "get_user_professions"):
                        profs = pro_cog.get_user_professions(user_id)  # { name: tier }
                        if profs:
                            lines = [f"• **{p}** — {tier}" for p, tier in profs.items()]
                            built.add_field(name="🛠️ Professions", value="\n".join(lines), inline=False)
                    return built
            except Exception as ex:
                e = discord.Embed(title="👤 Profile", color=discord.Color.red())
                e.add_field(name="Notice", value=f"Profile temporarily unavailable.\n{type(ex).__name__}: {ex}", inline=False)
                return e

        # Fallback if Profile cog not loaded
        e = discord.Embed(
            title="👤 Profile",
            description="Set your character name, classes, wishlist, and professions.",
            color=discord.Color.blue(),
        )
        return e




    async def render_recipes(self, user_id: int) -> discord.Embed:
        e = discord.Embed(title="📜 Recipes", color=discord.Color.green())
        e.description = "Learn new recipes, view your learned list, or browse others in the guild."
        rec_cog = self.bot.get_cog("Recipes")
        try:
            if rec_cog and hasattr(rec_cog, "get_user_recipes"):
                learned = rec_cog.get_user_recipes(user_id)  # type: ignore
            else:
                store = _load_json(LEARNED_FILE, {})
                learned = store.get(str(user_id), {})
            total = sum(len(v) for v in learned.values()) if isinstance(learned, dict) else 0
            e.add_field(name="📘 Learned", value=f"{total} total", inline=False)
        except Exception as ex:
            e.add_field(name="Notice", value=f"Recipes data unavailable.\n{type(ex).__name__}: {ex}", inline=False)
        return e

    async def render_market(self, user_id: int) -> discord.Embed:
        e = discord.Embed(title="💰 Market", color=discord.Color.teal())
        e.description = "Browse listings, post items, and see wishlist matches."
        mkt_cog = self.bot.get_cog("Market")
        try:
            mine = []
            if mkt_cog and hasattr(mkt_cog, "get_user_listings"):
                mine = mkt_cog.get_user_listings(user_id)  # type: ignore
            else:
                # JSON fallback
                raw = _load_json(MARKET_FILE, [])
                if isinstance(raw, dict):
                    mine = raw.get(str(user_id), [])
                elif isinstance(raw, list):
                    mine = [it for it in raw if int(it.get("seller_id", 0)) == int(user_id)]
            if mine:
                rows = [f"• {m.get('item','?')} — {m.get('price_str','?')}  |  {m.get('village','?')}" for m in mine[:6]]
                e.add_field(name="My Listings", value="\n".join(rows), inline=False)
            else:
                e.add_field(name="My Listings", value="*No active listings.*", inline=False)
        except Exception as ex:
            e.add_field(name="Notice", value=f"Market data unavailable.\n{type(ex).__name__}: {ex}", inline=False)
        return e

    async def render_mailbox(self, user_id: int) -> discord.Embed:
        mail_cog = self.bot.get_cog("Mailbox")
        e = discord.Embed(title="📬 Mailbox", color=discord.Color.blurple())
        try:
            if mail_cog and hasattr(mail_cog, "get_inbox"):
                inbox = mail_cog.get_inbox(user_id)  # type: ignore
            else:
                inbox = _load_json(MAILBOX_FILE, {}).get(str(user_id), [])
            unread = len([m for m in inbox if not m.get("read")])
            e.description = f"📨 You have **{len(inbox)}** messages (**{unread} unread**)."
            e.set_footer(text="Use the buttons below to manage your mailbox.")
        except Exception as ex:
            e.add_field(name="Notice", value=f"Mailbox unavailable.\n{type(ex).__name__}: {ex}", inline=False)
        return e

    async def render_registry(self, user_id: int) -> discord.Embed:
        e = discord.Embed(
            title="📜 Guild Recipe Registry",
            description="Search recipes and see **who can craft what** across the guild.",
            color=discord.Color.green(),
        )
        e.set_footer(text="Use the button below to search recipes.")
        return e

    async def render_trades(self, user_id: int) -> discord.Embed:
        e = discord.Embed(
            title="📦 Trade Board",
            description="Post items for sale, request items, and make trade offers.",
            color=discord.Color.orange(),
        )
        try:
            trades = _load_json(TRADES_FILE, {})
            my = trades.get(str(user_id), [])
            if my:
                lines = [f"**{t.get('type','?')}** — {t.get('item','?')} ({t.get('price','—')})" for t in my[:6]]
                e.add_field(name="📜 Your Trades", value="\n".join(lines), inline=False)
            else:
                e.add_field(name="📜 Your Trades", value="*You have no posted trades.*", inline=False)
        except Exception as ex:
            e.add_field(name="Notice", value=f"Trades unavailable.\n{type(ex).__name__}: {ex}", inline=False)
        e.set_footer(text="Use the buttons below to manage your trades.")
        return e

    # -------- Listener for Home quick-actions --------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")  # type: ignore
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        # Quick action: open inbox (Hub Home)
        if cid == f"hub_open_inbox_{uid}":
            embed = await self.render_mailbox(uid)
            view = HubView(self, uid, section="mailbox", debug=self.bot.debug_mode)
            view.attach_section_controls("mailbox", uid)
            return await interaction.response.edit_message(embed=embed, view=view)

        # Quick action: market wishlist matches
        if cid == f"hub_market_wishlist_{uid}":
            # If Market cog supports a filtered embed, use it; else just go to market.
            embed = await self.render_market(uid)
            view = HubView(self, uid, section="market", debug=self.bot.debug_mode)
            view.attach_section_controls("market", uid)
            return await interaction.response.edit_message(embed=embed, view=view)

        # Quick action: trades wishlist matches
        if cid == f"hub_trades_wishlist_{uid}":
            embed = await self.render_trades(uid)
            view = HubView(self, uid, section="trades", debug=self.bot.debug_mode)
            view.attach_section_controls("trades", uid)
            return await interaction.response.edit_message(embed=embed, view=view)

        # Quick action: my learned recipes
        if cid == f"hub_recipes_learned_{uid}":
            embed = await self.render_recipes(uid)
            view = HubView(self, uid, section="recipes", debug=self.bot.debug_mode)
            view.attach_section_controls("recipes", uid)
            return await interaction.response.edit_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot))
