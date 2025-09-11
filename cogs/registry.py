import json
import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any, Optional, Tuple
from utils.data import load_json, save_json
from cogs.hub import refresh_hub

REGISTRY_FILE = "data/artisan_registry.json"
RECIPES_FILE = "data/recipes.json"
PROFILES_FILE = "data/profiles.json"

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _short(s: str, n: int = 80) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"

class Registry(commands.Cog):
    """
    Guild Recipe Registry
    Tracks: recipe -> { profession, users: [ {id, name, tier} ] }
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.registry: Dict[str, Dict[str, Any]] = load_json(REGISTRY_FILE, {})
        self.recipes: List[Dict[str, Any]] = load_json(RECIPES_FILE, [])
        self.profiles: Dict[str, Any] = load_json(PROFILES_FILE, {})

    # -----------------------------
    # Persistence
    # -----------------------------
    def _save(self):
        save_json(REGISTRY_FILE, self.registry)

    # -----------------------------
    # Helpers
    # -----------------------------
    def _resolve_profession_for_recipe(self, recipe_name: str) -> Optional[str]:
        """Find profession for a recipe via recipes.json (case-insensitive)."""
        rn = _norm(recipe_name)
        for r in self.recipes:
            if _norm(r.get("name", "")) == rn:
                return r.get("profession") or r.get("prof") or "Unknown"
        # fallback: substring match
        for r in self.recipes:
            if rn in _norm(r.get("name", "")):
                return r.get("profession") or r.get("prof") or "Unknown"
        return None

    def _get_user_prof_tier(self, user_id: int, profession: str) -> Optional[str]:
        """Ask Professions cog for user's tier in a profession (string)."""
        pro = self.bot.get_cog("Professions")
        if not pro or not hasattr(pro, "get_user_professions"):
            return None
        try:
            profs = pro.get_user_professions(user_id)  # expected: [{name, tier|level}]
            for p in profs or []:
                if _norm(p.get("name", "")) == _norm(profession):
                    # prefer tier, fall back to level
                    return str(p.get("tier") or p.get("level") or "")
        except Exception:
            pass
        return None

    def _upsert_entry(self, recipe_name: str, profession: str) -> Dict[str, Any]:
        key = recipe_name
        entry = self.registry.setdefault(key, {"profession": profession or "Unknown", "users": []})
        # keep canonical profession once set
        if profession and entry.get("profession") in (None, "", "Unknown"):
            entry["profession"] = profession
        return entry

    def _remove_user_from_entry(self, entry: Dict[str, Any], user_id: int):
        entry["users"] = [u for u in entry.get("users", []) if int(u.get("id", 0)) != int(user_id)]

    def _find_recipe_candidates(self, query: str) -> List[str]:
        q = _norm(query)
        names = set()
        for r in self.recipes:
            name = r.get("name")
            if name and q in _norm(name):
                names.add(name)
        # if already tracked in registry but not in recipes.json, include those too
        for tracked in self.registry.keys():
            if q in _norm(tracked):
                names.add(tracked)
        return sorted(names)

    # -----------------------------
    # Public API (call from other cogs)
    # -----------------------------
    def index_learn(self, user_id: int, recipe_name: str, profession: Optional[str] = None):
        """
        Add a user as a crafter for a recipe. Profession auto-resolves if omitted.
        Tier is pulled from Professions cog if available.
        """
        profession = profession or self._resolve_profession_for_recipe(recipe_name) or "Unknown"
        tier = self._get_user_prof_tier(user_id, profession) or ""
        user = self.bot.get_user(user_id)
        display = user.display_name if user else str(user_id)

        entry = self._upsert_entry(recipe_name, profession)
        # prevent duplicates
        for u in entry["users"]:
            if int(u.get("id", 0)) == int(user_id):
                # update name/tier if changed
                u["name"] = display
                if tier:
                    u["tier"] = tier
                self._save()
                return

        entry["users"].append({"id": int(user_id), "name": display, **({"tier": tier} if tier else {})})
        # sort users by name for stable display
        entry["users"].sort(key=lambda x: _norm(x.get("name", "")))
        self._save()

    def unindex_learn(self, user_id: int, recipe_name: str):
        """Remove a user's ability entry for a recipe."""
        entry = self.registry.get(recipe_name)
        if not entry:
            return
        self._remove_user_from_entry(entry, user_id)
        # cleanup empty
        if not entry.get("users"):
            self.registry.pop(recipe_name, None)
        self._save()

    def search_registry(self, recipe_query: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Return [(recipe_name, entry)] matching the query, registry-first."""
        names = self._find_recipe_candidates(recipe_query)
        out: List[Tuple[str, Dict[str, Any]]] = []
        for name in names:
            entry = self.registry.get(name) or {"profession": self._resolve_profession_for_recipe(name) or "Unknown", "users": []}
            out.append((name, entry))
        return out

    def wishlist_matches_for(self, user_id: int) -> List[Tuple[str, Dict[str, Any]]]:
        """Return [(wishlist_item, entry)] where someone can craft it."""
        profile = self.profiles.get(str(user_id), {})
        wl = [w for w in profile.get("wishlist", []) if isinstance(w, str)]
        matches: List[Tuple[str, Dict[str, Any]]] = []
        for item in wl:
            entry = self.registry.get(item)
            if entry and entry.get("users"):
                matches.append((item, entry))
        # Sort: items with more crafters first, then by name
        matches.sort(key=lambda x: (-len(x[1].get("users", [])), _norm(x[0])))
        return matches

    # -----------------------------
    # Hub Buttons
    # -----------------------------
    def build_registry_buttons(self, user_id: int) -> View:
        v = View(timeout=240)
        v.add_item(Button(label="🔍 Search Recipe", style=discord.ButtonStyle.primary, custom_id=f"reg_search_{user_id}"))
        v.add_item(Button(label="📜 Wishlist Matches", style=discord.ButtonStyle.success, custom_id=f"reg_wishlist_{user_id}"))
        v.add_item(Button(label="🧑‍🎨 View All Artisans", style=discord.ButtonStyle.secondary, custom_id=f"reg_artisans_{user_id}"))
        return v

    # -----------------------------
    # UI: Modals / Views
    # -----------------------------
    class SearchModal(Modal, title="🔍 Search Guild Registry"):
        def __init__(self, cog: "Registry", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.query = TextInput(label="Recipe name", placeholder="e.g. Obsidian Dagger", required=True)
            self.add_item(self.query)

        async def on_submit(self, interaction: discord.Interaction):
            results = self.cog.search_registry(self.query.value)
            if not results:
                e = discord.Embed(title="🔍 Results", description=f"No matches for **{self.query.value}**.", color=discord.Color.red())
                return await interaction.response.edit_message(embed=e, view=None)

            # Show top result fully, list others briefly
            name, entry = results[0]
            e = discord.Embed(
                title=f"📜 {name}",
                description=f"**Profession:** {entry.get('profession','Unknown')}",
                color=discord.Color.green()
            )

            users = entry.get("users", [])
            if not users:
                e.add_field(name="Crafters", value="*Nobody registered yet.*", inline=False)
            else:
                lines = [f"• **{u.get('name','Unknown')}**{(' — Tier ' + str(u.get('tier'))) if u.get('tier') else ''}" for u in users[:10]]
                if len(users) > 10:
                    lines.append(f"…and {len(users)-10} more")
                e.add_field(name="Crafters", value="\n".join(lines), inline=False)

            # If there are registered crafters, offer a selector to message one
            v = View(timeout=240)
            if users:
                options = []
                for u in users[:25]:
                    label = _short(f"{u.get('name', 'Unknown')} ({u.get('tier','?')})", 100)
                    options.append(discord.SelectOption(label=label, value=str(int(u["id"]))))

                v.add_item(Registry._CrafterSelect(self.cog, self.user_id, name, options))

            await interaction.response.edit_message(embed=e, view=v)

    class _CrafterSelect(Select):
        def __init__(self, cog: "Registry", user_id: int, recipe_name: str, options: List[discord.SelectOption]):
            super().__init__(placeholder="Message a crafter…", options=options, min_values=1, max_values=1)
            self.cog = cog
            self.user_id = user_id
            self.recipe_name = recipe_name

        async def callback(self, interaction: discord.Interaction):
            to_user_id = int(self.values[0])
            mailbox = interaction.client.get_cog("Mailbox")
            if not mailbox:
                return await interaction.response.send_message("📬 Mailbox unavailable.", ephemeral=True)

            subject = f"Craft Request — {self.recipe_name}"
            body = f"Hey! Could you craft **{self.recipe_name}** for me?"
            modal = mailbox.ComposeModal(mailbox, from_user_id=self.user_id, to_user_id=to_user_id,
                                         subject_prefill=subject, body_prefill=body)
            await interaction.response.send_modal(modal)

    class WishlistMatchesView(View):
        def __init__(self, cog: "Registry", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id

            matches = self.cog.wishlist_matches_for(user_id)
            if not matches:
                self.add_item(Button(label="No wishlist matches", style=discord.ButtonStyle.secondary, disabled=True))
            else:
                # Build a select: each option is "Item — N crafters"
                options: List[discord.SelectOption] = []
                for item, entry in matches[:25]:
                    cnt = len(entry.get("users", []))
                    options.append(discord.SelectOption(label=_short(f"{item} — {cnt} crafter(s)"), value=item))
                self.add_item(Registry._MatchSelect(self.cog, self.user_id, options))

    class _MatchSelect(Select):
        def __init__(self, cog: "Registry", user_id: int, options: List[discord.SelectOption]):
            super().__init__(placeholder="Choose a wishlist item…", options=options, min_values=1, max_values=1)
            self.cog = cog
            self.user_id = user_id

        async def callback(self, interaction: discord.Interaction):
            item = self.values[0]
            entry = self.cog.registry.get(item, {"profession": self.cog._resolve_profession_for_recipe(item) or "Unknown", "users": []})
            users = entry.get("users", [])
            e = discord.Embed(
                title=f"📜 {item}",
                description=f"**Profession:** {entry.get('profession','Unknown')}",
                color=discord.Color.gold()
            )
            if not users:
                e.add_field(name="Crafters", value="*No one registered yet.*", inline=False)
                return await interaction.response.edit_message(embed=e, view=None)

            # Show crafters, add a select to message one
            lines = [f"• **{u.get('name','Unknown')}**{(' — Tier ' + str(u.get('tier'))) if u.get('tier') else ''}" for u in users[:10]]
            if len(users) > 10:
                lines.append(f"…and {len(users)-10} more")
            e.add_field(name="Crafters", value="\n".join(lines), inline=False)

            v = View(timeout=240)
            options = []
            for u in users[:25]:
                label = _short(f"{u.get('name', 'Unknown')} ({u.get('tier','?')})", 100)
                options.append(discord.SelectOption(label=label, value=str(int(u["id"]))))

            v.add_item(Registry._CrafterSelect(self.cog, self.user_id, item, options))
            await interaction.response.edit_message(embed=e, view=v)

    # -----------------------------
    # Hub/Interaction wiring
    # -----------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type or not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")  # type: ignore[attr-defined]
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        # Open search modal
        if cid == f"reg_search_{uid}":
            modal = Registry.SearchModal(self, uid)
            return await interaction.response.send_modal(modal)

        # Wishlist matches
        if cid == f"reg_wishlist_{uid}":
            matches = self.wishlist_matches_for(uid)
            e = discord.Embed(
                title="📜 Wishlist Matches",
                description=("Select one of your wishlist items that has available crafters." if matches else "No matches yet."),
                color=discord.Color.green() if matches else discord.Color.red(),
            )
            v = Registry.WishlistMatchesView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        # Overview / Stats
        if cid == f"reg_artisans_{uid}":
            n_recipes = len(self.registry)
            unique_users = set()
            profs = set()
            for name, entry in self.registry.items():
                profs.add(entry.get("profession", "Unknown"))
                for u in entry.get("users", []):
                    unique_users.add(int(u.get("id", 0)))

            e = discord.Embed(
                title="🧑‍🎨 Guild Artisans — Overview",
                color=discord.Color.blurple(),
                description=(
                    f"• **{n_recipes}** recipes tracked\n"
                    f"• **{len(unique_users)}** artisans registered\n"
                    f"• **{len(profs)}** professions represented"
                ),
            )
            return await interaction.response.edit_message(embed=e, view=None)

    # (Optional) Trigger registry refresh from Hub after external updates
    async def refresh_registry_panel(self, interaction: discord.Interaction):
        await refresh_hub(interaction, section="registry")


async def setup(bot: commands.Bot):
    await bot.add_cog(Registry(bot))
