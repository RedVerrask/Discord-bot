# cogs/hub.py
import discord
from discord.ext import commands
import json, os
from typing import Dict, List, Any, Optional

DATA_DIR = "data"
RECIPES_FILE = os.path.join(DATA_DIR, "recipes.json")
LEARNED_FILE = os.path.join(DATA_DIR, "learned_recipes.json")

# --------------- small json helpers ---------------

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

# --------------- tiny recipe helpers (works with your Recipes cog or standalone) ---------------

def _ensure_grouped_recipes(raw) -> Dict[str, List[Dict[str, str]]]:
    """
    Accepts either:
      - grouped dict { profession: [ {name, profession, url, level?}, ... ] }
      - flat list [ {name, profession, url, ...}, ... ]
      - flat list of names (legacy)
    Returns grouped dict with items -> dict(name, profession, link).
    """
    grouped: Dict[str, List[Dict[str, str]]] = {}
    if isinstance(raw, dict):
        # normalize keys inside each list
        for prof, items in raw.items():
            for r in items:
                name = r.get("name", "Unknown Recipe") if isinstance(r, dict) else str(r)
                url = (r.get("url") or r.get("link") or "").strip() if isinstance(r, dict) else ""
                item = {"name": name, "profession": prof, "link": url}
                grouped.setdefault(prof, []).append(item)
        return grouped

    # flat list
    if isinstance(raw, list):
        for r in raw:
            if isinstance(r, dict):
                prof = r.get("profession", "Unknown") or "Unknown"
                name = r.get("name", "Unknown Recipe")
                url = (r.get("url") or r.get("link") or "").strip()
            else:
                prof = "Unknown"
                name = str(r)
                url = ""
            grouped.setdefault(prof, []).append({"name": name, "profession": prof, "link": url})
        return grouped

    return {}

def _load_grouped_recipes_from_file() -> Dict[str, List[Dict[str, str]]]:
    raw = _load_json(RECIPES_FILE, default=[])
    return _ensure_grouped_recipes(raw)

def _search_recipes_local(query: str, professions: Optional[List[str]] = None) -> List[Dict[str, str]]:
    query = (query or "").lower().strip()
    grouped = _load_grouped_recipes_from_file()
    hits: List[Dict[str, str]] = []
    for prof, items in grouped.items():
        if professions and prof not in professions:
            continue
        for r in items:
            if query in r["name"].lower():
                hits.append(r)
    return hits

def _get_learned(user_id: int) -> Dict[str, List[Dict[str, str]]]:
    store = _load_json(LEARNED_FILE, default={})
    return store.get(str(user_id), {})

def _save_learned(user_id: int, learned: Dict[str, List[Dict[str, str]]]):
    store = _load_json(LEARNED_FILE, default={})
    store[str(user_id)] = learned
    _save_json(LEARNED_FILE, store)

def _add_learned(user_id: int, prof: str, name: str, link: str) -> bool:
    learned = _get_learned(user_id)
    bucket = learned.setdefault(prof, [])
    if any(x["name"].lower() == name.lower() for x in bucket):
        return False
    bucket.append({"name": name, "link": link})
    # sort by name for tidiness
    bucket.sort(key=lambda x: x["name"])
    _save_learned(user_id, learned)
    return True

def _scan_guild_learned() -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    { user_id: { profession: [ {name, link}, ... ] } }
    """
    return _load_json(LEARNED_FILE, default={})

# --------------- Hub View ---------------

class HubView(discord.ui.View):
    def __init__(self, cog: "Hub", user_id: int, section: str = "home", debug: bool = False, extra: Optional[dict] = None):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.section = section
        self.debug = debug
        self.extra = extra or {}

        # Top row primary navigation
        self.add_item(self.HomeBtn(self))
        self.add_item(self.ProfileBtn(self))
        self.add_item(self.ProfessionsBtn(self))
        self.add_item(self.RecipesBtn(self))
        self.add_item(self.MarketBtn(self))
        self.add_item(self.GearBtn(self))
        self.add_item(self.LoreBtn(self))
        self.add_item(self.MailboxBtn(self))

        # Utility row
        if self.section != "home":
            self.add_item(self.BackBtn(self))
        self.add_item(self.DebugBtn(self, enabled=self.debug))

    # ---- buttons (each button class keeps self.view to access state) ----
    class _BaseNavButton(discord.ui.Button):
        def __init__(self, label: str, style: discord.ButtonStyle, section: str, emoji: Optional[str] = None, row: Optional[int] = None):
            super().__init__(label=label, style=style, emoji=emoji, row=row)
            self._section = section

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            # Only allow the opener to drive their own ephemeral hub
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("This hub belongs to someone else. Use `/home` to open your own.", ephemeral=True)
            embed = await v.cog.render_section(interaction, v.user_id, self._section, debug=v.debug)
            new_view = HubView(v.cog, v.user_id, section=self._section, debug=v.debug)
            await interaction.response.edit_message(embed=embed, view=new_view)

    class HomeBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Home", discord.ButtonStyle.primary, "home", emoji="🏰")

    class ProfileBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Profile", discord.ButtonStyle.secondary, "profile", emoji="👤")

    class ProfessionsBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Professions", discord.ButtonStyle.secondary, "professions", emoji="🛠️")

    class RecipesBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Recipes", discord.ButtonStyle.secondary, "recipes", emoji="📜")

    class MarketBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Market", discord.ButtonStyle.success, "market", emoji="💰")

    class GearBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Gear", discord.ButtonStyle.secondary, "gear", emoji="⚔️")

    class LoreBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Lore", discord.ButtonStyle.secondary, "lore", emoji="📖")

    class MailboxBtn(_BaseNavButton):
        def __init__(self, view: "HubView"):
            super().__init__("Mailbox", discord.ButtonStyle.secondary, "mailbox", emoji="📬")

    class BackBtn(discord.ui.Button):
        def __init__(self, view: "HubView"):
            super().__init__(label="Back to Home", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("This hub belongs to someone else. Use `/home` to open your own.", ephemeral=True)
            embed = await v.cog.render_section(interaction, v.user_id, "home", debug=v.debug)
            new_view = HubView(v.cog, v.user_id, section="home", debug=v.debug)
            await interaction.response.edit_message(embed=embed, view=new_view)

    class DebugBtn(discord.ui.Button):
        def __init__(self, view: "HubView", enabled: bool):
            label = "🐞 Debug: ON" if enabled else "🐞 Debug: OFF"
            style = discord.ButtonStyle.danger if enabled else discord.ButtonStyle.secondary
            super().__init__(label=label, style=style, row=1)

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("This hub belongs to someone else. Use `/home` to open your own.", ephemeral=True)
            new_debug = not v.debug
            embed = await v.cog.render_section(interaction, v.user_id, v.section, debug=new_debug)
            new_view = HubView(v.cog, v.user_id, section=v.section, debug=new_debug)
            await interaction.response.edit_message(embed=embed, view=new_view)

# --------------- Modals & Selects that UPDATE the SAME HUB MESSAGE ---------------

class LearnRecipeModal(discord.ui.Modal, title="📗 Learn Recipe"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=180)
        self.hub = hub
        self.user_id = user_id
        self.query = discord.ui.TextInput(
            label="Enter Recipe Name",
            placeholder="e.g. Obsidian Dagger",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        # get professions for this user if available
        professions = []
        prof_cog = interaction.client.get_cog("Professions")  # type: ignore
        try:
            if prof_cog and hasattr(prof_cog, "get_user_professions"):
                professions = [p["name"] for p in prof_cog.get_user_professions(self.user_id)]
        except Exception:
            professions = []

        # use Recipes cog if present; fall back to local
        recipes_cog = interaction.client.get_cog("Recipes")  # type: ignore
        try:
            if recipes_cog and hasattr(recipes_cog, "search_recipes"):
                matches = recipes_cog.search_recipes(self.query.value, professions)
            else:
                matches = _search_recipes_local(self.query.value, professions)
        except Exception:
            matches = _search_recipes_local(self.query.value, professions)

        matches = matches[:25]  # dropdown limit
        embed = discord.Embed(
            title="📗 Select a recipe to learn",
            description=f"Results for **{self.query.value}** ({len(matches)} shown):",
            color=discord.Color.green()
        )
        if not matches:
            embed.description = "⚠️ No recipes found."
            return await interaction.response.edit_message(embed=embed, view=HubView(self.hub, self.user_id, section="recipes"))

        # build a dropdown
        options = []
        for r in matches:
            label = r["name"][:100]
            desc = r.get("profession", "Unknown")
            options.append(discord.SelectOption(label=label, description=desc, value=json.dumps(r)[:100]))  # keep value small

        select = LearnSelect(self.hub, self.user_id, options)
        view = HubView(self.hub, self.user_id, section="recipes")
        view.add_item(select)
        await interaction.response.edit_message(embed=embed, view=view)

class LearnSelect(discord.ui.Select):
    def __init__(self, hub: "Hub", user_id: int, options: List[discord.SelectOption]):
        super().__init__(placeholder="Choose a recipe to learn…", options=options, min_values=1, max_values=1, row=2)
        self.hub = hub
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        try:
            data = json.loads(self.values[0])
        except Exception:
            return await interaction.response.send_message("Invalid selection.", ephemeral=True)

        name = data.get("name", "Unknown Recipe")
        prof = data.get("profession", "Unknown")
        link = data.get("link", "")

        # prefer Recipes cog add method, else local
        added = False
        try:
            recipes_cog = interaction.client.get_cog("Recipes")  # type: ignore
            if recipes_cog and hasattr(recipes_cog, "add_learned_recipe"):
                added = recipes_cog.add_learned_recipe(self.user_id, prof, name, link)
            else:
                added = _add_learned(self.user_id, prof, name, link)
        except Exception:
            added = _add_learned(self.user_id, prof, name, link)

        msg = f"✅ Learned **{name}**!" if added else f"⚠️ You already learned **{name}**."
        embed = await self.hub.render_recipes_embed(interaction, self.user_id, banner=msg)
        view = HubView(self.hub, self.user_id, section="recipes")
        await interaction.response.edit_message(embed=embed, view=view)

class SearchRecipeModal(discord.ui.Modal, title="🔍 Search Recipes"):
    def __init__(self, hub: "Hub", user_id: int):
        super().__init__(timeout=180)
        self.hub = hub
        self.user_id = user_id
        self.query = discord.ui.TextInput(
            label="Search for Recipe",
            placeholder="e.g. Phoenix Cloak",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        recipes_cog = interaction.client.get_cog("Recipes")  # type: ignore
        try:
            if recipes_cog and hasattr(recipes_cog, "search_recipes"):
                matches = recipes_cog.search_recipes(self.query.value)
            else:
                matches = _search_recipes_local(self.query.value)
        except Exception:
            matches = _search_recipes_local(self.query.value)

        embed = discord.Embed(
            title=f"🔍 Results: {self.query.value}",
            color=discord.Color.purple()
        )
        if not matches:
            embed.description = "⚠️ No recipes found."
        else:
            for r in matches[:10]:
                link = r.get("link") or r.get("url") or ""
                prof = r.get("profession", "Unknown")
                embed.add_field(
                    name=r.get("name", "Unknown"),
                    value=f"**Profession:** {prof}\n{'[View on Ashes Codex](' + link + ')' if link else ''}",
                    inline=False
                )

        # keep nav consistent
        view = HubView(self.hub, self.user_id, section="recipes")
        await interaction.response.edit_message(embed=embed, view=view)

# --------------- Hub Cog ---------------

class Hub(commands.Cog):
    """Dynamic one-message hub with editable panels."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------- public: /home --------
    @commands.command(name="home", help="Open your guild home menu (prefix command fallback)")
    async def legacy_home_prefix(self, ctx: commands.Context):
        await self._open_home(ctx)

    @commands.hybrid_command(name="home", description="Open your guild home menu")
    async def home(self, ctx: commands.Context):
        await self._open_home(ctx)

    async def _open_home(self, ctx: commands.Context):
        embed = await self.render_section(None, ctx.author.id, "home")
        view = HubView(self, ctx.author.id, section="home")
        # ephemeral is only available via Interaction. For hybrid command, respond with interaction if present.
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # fallback (non-ephemeral) if using prefix in test guild
            await ctx.send(embed=embed, view=view)

    # -------- section router --------
    async def render_section(self, interaction: Optional[discord.Interaction], user_id: int, section: str, debug: bool = False) -> discord.Embed:
        if section == "home":
            return await self.render_home_embed(interaction, user_id, debug)
        if section == "profile":
            return await self.render_profile_embed(interaction, user_id, debug)
        if section == "professions":
            return await self.render_professions_embed(interaction, user_id, debug)
        if section == "recipes":
            return await self.render_recipes_embed(interaction, user_id, debug)
        if section == "market":
            return await self.render_market_embed(interaction, user_id, debug)
        if section == "gear":
            return await self.render_gear_embed(interaction, user_id, debug)
        if section == "lore":
            return await self.render_lore_embed(interaction, user_id, debug)
        if section == "mailbox":
            return await self.render_mailbox_embed(interaction, user_id, debug)
        # default
        return await self.render_home_embed(interaction, user_id, debug)

    # -------- embeds --------
    async def render_home_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(
            title="🏰 Guild Codex",
            description="Your guide to artisans, recipes, and knowledge.",
            color=discord.Color.gold()
        )
        e.set_footer(text="Ashes of Creation - Guild Codex")
        if debug:
            e.add_field(name="🐞 Debug", value="section=home", inline=False)
        return e

    async def render_profile_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        user = interaction.user if interaction else None  # type: ignore
        title = f"👤 {user.display_name}'s Profile" if user else "👤 Profile"
        e = discord.Embed(title=title, color=discord.Color.blue())
        e.description = "Edit your classes, wishlist, and view listings."

        # If Profile cog provides a richer embed, use it.
        prof_cog = self.bot.get_cog("Profile")
        try:
            if prof_cog and hasattr(prof_cog, "build_profile_embed"):
                # Fall back-safe call; guard missing keys inside build_profile_embed
                return prof_cog.build_profile_embed(user or interaction.user)  # type: ignore
        except Exception as ex:
            e.add_field(name="Notice", value=f"Profile detail temporarily unavailable.\n`{type(ex).__name__}: {ex}`", inline=False)

        # Minimal fallback
        learned = _get_learned(user_id)
        total = sum(len(v) for v in learned.values())
        if total:
            lines = []
            for prof, lst in learned.items():
                lines.append(f"**{prof}** — {len(lst)} learned")
            e.add_field(name="Recipes Learned", value="\n".join(lines), inline=False)
        else:
            e.add_field(name="Recipes Learned", value="*None yet. Head to the Recipes tab to learn some!*", inline=False)

        if debug:
            e.add_field(name="🐞 Debug", value="section=profile", inline=False)
        return e

    async def render_professions_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(title="🛠️ Professions", color=discord.Color.orange())
        prof_cog = self.bot.get_cog("Professions")
        try:
            if prof_cog and hasattr(prof_cog, "get_user_professions"):
                profs = prof_cog.get_user_professions(user_id)  # type: ignore
                if profs:
                    s = "\n".join([f"• {p['name']} — L{p.get('level','?')}" for p in profs])
                else:
                    s = "*You have not selected any professions yet.*"
                e.add_field(name="Your Professions", value=s, inline=False)
        except Exception as ex:
            e.add_field(name="Notice", value=f"Professions data unavailable.\n`{type(ex).__name__}: {ex}`", inline=False)
        if debug:
            e.add_field(name="🐞 Debug", value="section=professions", inline=False)
        return e

    async def render_recipes_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False, banner: Optional[str] = None) -> discord.Embed:
        e = discord.Embed(title="📜 Recipes", color=discord.Color.green())
        e.description = "• **Learn Recipes**\n• **Learned Recipes**\n• **Search Recipes**\n\nUse the buttons below."

        if banner:
            e.add_field(name="Update", value=banner, inline=False)

        # Add the recipe action buttons by returning an embed (view is built by HubView)
        return e

    async def render_market_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(title="💰 Market", description="Browse listings and wishlist matches.", color=discord.Color.teal())
        market_cog = self.bot.get_cog("Market")
        try:
            if market_cog and hasattr(market_cog, "build_market_summary_embed"):
                return market_cog.build_market_summary_embed(user_id)  # type: ignore
        except Exception as ex:
            e.add_field(name="Notice", value=f"Market summary unavailable.\n`{type(ex).__name__}: {ex}`", inline=False)
        if debug:
            e.add_field(name="🐞 Debug", value="section=market", inline=False)
        return e

    async def render_gear_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(title="⚔️ Gear Lookup", description="Coming soon! You’ll be able to search gear stats, rarity, and sources here.", color=discord.Color.blurple())
        if debug:
            e.add_field(name="🐞 Debug", value="section=gear", inline=False)
        return e

    async def render_lore_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(title="📖 Lore Drop", description="Did you know?\n\nThe **Riverlands** were once home to House Kordath...", color=discord.Color.gold())
        if debug:
            e.add_field(name="🐞 Debug", value="section=lore", inline=False)
        return e

    async def render_mailbox_embed(self, interaction: Optional[discord.Interaction], user_id: int, debug: bool = False) -> discord.Embed:
        e = discord.Embed(title="📬 Mailbox", description="Mailbox is not enabled yet.\nComing soon: orders, trades, and messages.", color=discord.Color.dark_grey())
        if debug:
            e.add_field(name="🐞 Debug", value="section=mailbox", inline=False)
        return e

# --------------- Recipe action buttons (attached on-demand) ---------------

class RecipesActionView(HubView):
    def __init__(self, cog: "Hub", user_id: int, debug: bool = False):
        super().__init__(cog, user_id, section="recipes", debug=debug)
        # add action row
        self.add_item(self.LearnBtn(self))
        self.add_item(self.LearnedBtn(self))
        self.add_item(self.SearchBtn(self))

    class LearnBtn(discord.ui.Button):
        def __init__(self, view: "RecipesActionView"):
            super().__init__(label="📗 Learn Recipes", style=discord.ButtonStyle.success, row=2)

        async def callback(self, interaction: discord.Interaction):
            v: RecipesActionView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("Open your own hub via `/home`.", ephemeral=True)
            await interaction.response.send_modal(LearnRecipeModal(v.cog, v.user_id))

    class LearnedBtn(discord.ui.Button):
        def __init__(self, view: "RecipesActionView"):
            super().__init__(label="📘 Learned Recipes", style=discord.ButtonStyle.primary, row=2)

        async def callback(self, interaction: discord.Interaction):
            v: RecipesActionView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("Open your own hub via `/home`.", ephemeral=True)

            learned = _get_learned(v.user_id)
            e = discord.Embed(title=f"📘 {interaction.user.display_name}'s Learned Recipes", color=discord.Color.blue())
            if not learned:
                e.description = "*You haven’t learned any recipes yet.*"
            else:
                for prof, recipes in learned.items():
                    val = "\n".join([f"• [{r['name']}]({r.get('link','')})" if r.get("link") else f"• {r['name']}" for r in recipes]) or "—"
                    e.add_field(name=prof, value=val, inline=False)

            # also provide "View Others" dropdown
            store = _scan_guild_learned()
            options: List[discord.SelectOption] = []
            guild = interaction.guild
            if guild:
                for uid, recs in store.items():
                    if not recs: 
                        continue
                    member = guild.get_member(int(uid))
                    if not member:
                        continue
                    options.append(discord.SelectOption(label=member.display_name[:100], value=str(uid)))

            view = HubView(v.cog, v.user_id, section="recipes", debug=v.debug)
            if options:
                view.add_item(ViewOthersRecipesSelect(v.cog, v.user_id, options))
            await interaction.response.edit_message(embed=e, view=view)

    class SearchBtn(discord.ui.Button):
        def __init__(self, view: "RecipesActionView"):
            super().__init__(label="🔍 Search Recipes", style=discord.ButtonStyle.secondary, row=2)

        async def callback(self, interaction: discord.Interaction):
            v: RecipesActionView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("Open your own hub via `/home`.", ephemeral=True)
            await interaction.response.send_modal(SearchRecipeModal(v.cog, v.user_id))

class ViewOthersRecipesSelect(discord.ui.Select):
    def __init__(self, hub: "Hub", user_id: int, options: List[discord.SelectOption]):
        super().__init__(placeholder="View others' learned recipes…", options=options, min_values=1, max_values=1, row=3)
        self.hub = hub
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        target_id = int(self.values[0])
        guild = interaction.guild
        target = guild.get_member(target_id) if guild else None
        learned = _get_learned(target_id)

        e = discord.Embed(
            title=f"📘 {target.display_name if target else target_id}'s Learned Recipes",
            color=discord.Color.teal()
        )
        if not learned:
            e.description = "*This player hasn’t learned any recipes yet.*"
        else:
            for profession, lst in learned.items():
                val = "\n".join([f"• [{r['name']}]({r.get('link','')})" if r.get("link") else f"• {r['name']}" for r in lst]) or "—"
                e.add_field(name=profession, value=val, inline=False)

        view = HubView(self.hub, self.user_id, section="recipes")
        await interaction.response.edit_message(embed=e, view=view)

# --------------- setup ---------------

async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot))
