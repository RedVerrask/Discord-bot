import os
import json
import discord
from discord.ext import commands
from typing import Dict, List, Any, Optional

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
    hub_cog: "Hub" = interaction.client.get_cog("Hub")  # type: ignore
    if not hub_cog:
        return
    embed = await hub_cog.render_section(interaction, user_id, section)
    view = HubView(hub_cog, user_id, section=section, debug=hub_cog.bot.debug_mode)
    try:
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=view)
    except discord.NotFound:
        pass


# ---------------- Hub View ----------------
class HubView(discord.ui.View):
    def __init__(self, cog: "Hub", user_id: int, section: str = "home", debug: bool = False):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.section = section
        self.debug = debug

        # Top nav
        self.add_item(self.HomeBtn(self))
        self.add_item(self.ProfileBtn(self))
        self.add_item(self.ProfessionsBtn(self))
        self.add_item(self.RecipesBtn(self))
        self.add_item(self.MarketBtn(self))

        # Extra features
        if section == "home":
            self.add_item(self.GearBtn())
            self.add_item(self.LoreBtn())

        # Utilities
        if self.section != "home":
            self.add_item(self.BackBtn(self))
        if self.cog.bot.debug_mode:
            self.add_item(self.DebugBtn(self))
            self.add_item(self.StateBtn(self))

    # --------- Base Nav ---------
    class _BaseNavButton(discord.ui.Button):
        def __init__(self, label: str, style: discord.ButtonStyle, section: str, emoji: Optional[str] = None):
            super().__init__(label=label, style=style, emoji=emoji)
            self._section = section

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            if interaction.user.id != v.user_id:
                return await interaction.response.send_message("⚠️ This hub belongs to someone else. Use `/home` to open yours.", ephemeral=True)
            embed = await v.cog.render_section(interaction, v.user_id, self._section, debug=v.debug)
            await interaction.response.edit_message(embed=embed, view=HubView(v.cog, v.user_id, section=self._section, debug=v.debug))

    class HomeBtn(_BaseNavButton):
        def __init__(self, view): super().__init__("Home", discord.ButtonStyle.primary, "home", "🏰")

    class ProfileBtn(_BaseNavButton):
        def __init__(self, view): super().__init__("Profile", discord.ButtonStyle.secondary, "profile", "👤")

    class ProfessionsBtn(_BaseNavButton):
        def __init__(self, view): super().__init__("Professions", discord.ButtonStyle.secondary, "professions", "🛠️")

    class RecipesBtn(_BaseNavButton):
        def __init__(self, view): super().__init__("Recipes", discord.ButtonStyle.secondary, "recipes", "📜")

    class MarketBtn(_BaseNavButton):
        def __init__(self, view): super().__init__("Market", discord.ButtonStyle.success, "market", "💰")

    # --------- Utilities ---------
    class BackBtn(discord.ui.Button):
        def __init__(self, view):
            super().__init__(label="⬅ Back", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            embed = await v.cog.render_section(interaction, v.user_id, "home", debug=v.debug)
            await interaction.response.edit_message(embed=embed, view=HubView(v.cog, v.user_id, section="home", debug=v.debug))

    class DebugBtn(discord.ui.Button):
        def __init__(self, view):
            label = "🐞 Debug Mode: ON"
            super().__init__(label=label, style=discord.ButtonStyle.danger)

        async def callback(self, interaction: discord.Interaction):
            v: HubView = self.view  # type: ignore
            bot = v.cog.bot
            bot.debug_mode = not bot.debug_mode
            await interaction.response.send_message(f"✅ Debug mode toggled: **{'ON' if bot.debug_mode else 'OFF'}**", ephemeral=True)

    class StateBtn(discord.ui.Button):
        def __init__(self, view):
            super().__init__(label="🔍 Inspect State", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            bot = interaction.client
            profiles = bot.get_cog("Profile").profiles if bot.get_cog("Profile") else {}
            professions = bot.get_cog("Professions").artisan_registry if bot.get_cog("Professions") else {}
            recipes = bot.get_cog("Recipes").learned if bot.get_cog("Recipes") else {}
            market = bot.get_cog("Market").market if bot.get_cog("Market") else {}

            embed = discord.Embed(title="🔍 Debug State", color=discord.Color.red())
            embed.add_field(name="Profiles", value=f"{len(profiles)} users", inline=True)
            embed.add_field(name="Professions", value=f"{len(professions)} professions", inline=True)
            embed.add_field(name="Recipes", value=f"{len(recipes)} users", inline=True)
            embed.add_field(name="Market Listings", value=f"{len(market)} items", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------- Extra Features ---------
    class GearBtn(discord.ui.Button):
        def __init__(self):
            super().__init__(label="⚔️ Gear Lookup", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            embed = discord.Embed(
                title="⚔️ Gear Lookup",
                description="Coming soon! You'll be able to search gear stats, rarity, and sources here.",
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    class LoreBtn(discord.ui.Button):
        def __init__(self):
            super().__init__(label="📖 Lore Drops", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            embed = discord.Embed(
                title="📜 Lore Drop",
                description="Did you know?\n\nThe **Riverlands** were once home to House Kordath...",
                color=discord.Color.gold()
            )
            embed.set_footer(text="More lore integrations coming soon!")
            await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------- Hub Cog ----------------
class Hub(commands.Cog):
    """One-message hub with live-refreshing panels + debugging tools."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="home", description="Open your guild hub")
    async def home(self, ctx: commands.Context):
        embed = await self.render_section(None, ctx.author.id, "home")
        view = HubView(self, ctx.author.id, section="home", debug=self.bot.debug_mode)
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await ctx.send(embed=embed, view=view)

    # Router
    async def render_section(self, interaction: Optional[discord.Interaction], user_id: int, section: str, debug: bool = False) -> discord.Embed:
        if self.bot.debug_mode:
            self.bot.logger = getattr(self.bot, "logger", None)
            if self.bot.logger:
                self.bot.logger.info(f"[DEBUG] Hub refresh: user={user_id} section={section}")

        if section == "home":         return await self.render_home(user_id)
        if section == "profile":      return await self.render_profile(interaction, user_id)
        if section == "professions":  return await self.render_professions(interaction, user_id)
        if section == "recipes":      return await self.render_recipes(user_id)
        if section == "market":       return await self.render_market(user_id)
        return await self.render_home(user_id)

    # Embeds
    async def render_home(self, user_id: int) -> discord.Embed:
        e = discord.Embed(
            title="🏰 Guild Codex",
            description="Your guide to artisans, recipes, and market intel.\nUse the buttons below.",
            color=discord.Color.gold(),
        )
        e.set_footer(text="Ashes of Creation — Guild Codex")
        return e

    async def render_profile(self, interaction: Optional[discord.Interaction], user_id: int) -> discord.Embed:
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            user = (interaction.user if interaction else self.bot.get_user(user_id))  # type: ignore
            return profile_cog.build_profile_embed(user)
        return discord.Embed(title="👤 Profile", description="Profile unavailable.", color=discord.Color.red())

    async def render_professions(self, interaction: Optional[discord.Interaction], user_id: int) -> discord.Embed:
        prof_cog = self.bot.get_cog("Professions")
        e = discord.Embed(title="🛠️ Professions", description="Choose a category below:", color=discord.Color.orange())
        if prof_cog:
            profs = prof_cog.get_user_professions(user_id)
            if profs:
                s = "\n".join([f"• {p['name']} — Tier {p.get('tier', '1')}" for p in profs])
            else:
                s = "*You have not selected any professions yet.*"
            e.add_field(name="Your Professions", value=s, inline=False)

        # Add profession category buttons dynamically
        view = discord.ui.View(timeout=None)
        for label, profs in {
            "⛏️ Gathering": ["Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"],
            "⚙️ Processing": ["Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling", "Metalworking", "Stonemasonry", "Tanning", "Weaving"],
            "🛠️ Crafting": ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry", "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"]
        }.items():
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary)
            async def make_dropdown_callback(inter, profs=profs):
                opts = [discord.SelectOption(label=p, value=p) for p in profs]
                dropdown = discord.ui.Select(placeholder=f"Select profession...", options=opts)
                v2 = discord.ui.View(timeout=None)
                v2.add_item(dropdown)
                async def on_select(sitx: discord.Interaction):
                    prof = dropdown.values[0]
                    await sitx.response.send_message(f"Now select a tier for {prof}. Use `/setprofession {prof} <tier>`.", ephemeral=True)
                dropdown.callback = on_select
                await inter.response.send_message(f"Choose your profession:", view=v2, ephemeral=True)
            button.callback = make_dropdown_callback
            view.add_item(button)

        if interaction:
            await interaction.response.send_message(embed=e, view=view, ephemeral=True)
        return e

    async def render_recipes(self, user_id: int) -> discord.Embed:
        e = discord.Embed(
            title="📜 Recipes",
            description="• **/learnrecipe** to learn\n• **/unlearnrecipe** to remove\n• **/searchrecipe** to find",
            color=discord.Color.green(),
        )
        learned = _get_learned(user_id)
        total = sum(len(v) for v in learned.values())
        e.add_field(name="📘 Learned Recipes", value=f"{total} total" if total else "*None yet*", inline=False)
        grouped = _load_grouped_recipes_from_file()
        e.add_field(name="📚 Recipe Catalog", value=f"{sum(len(v) for v in grouped.values())} items", inline=False)
        return e

    async def render_market(self, user_id: int) -> discord.Embed:
        e = discord.Embed(title="💰 Market", description="Post listings and see wishlist matches.\nUse **/marketadd** and **/marketlist**.", color=discord.Color.teal())
        market_cog = self.bot.get_cog("Market")
        if market_cog:
            my_listings = market_cog.get_user_listings(user_id)
            if my_listings:
                rows = "\n".join([f"• {m['item']} — {m.get('price_str', m.get('price','?'))} | {m['village']}" for m in my_listings[:8]])
                e.add_field(name="My Listings", value=rows, inline=False)
            else:
                e.add_field(name="My Listings", value="*No active listings*", inline=False)
        return e


async def setup(bot: commands.Bot):
    await bot.add_cog(Hub(bot))

