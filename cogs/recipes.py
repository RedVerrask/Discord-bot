# cogs/recipes.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any, Optional

from utils.data import load_json, save_json
from cogs.hub import refresh_hub

RECIPES_FILE = "data/recipes.json"                 # flat list: [{name, profession, link?}, ...]
RECIPES_GROUPED_FILE = "data/recipes_grouped.json" # grouped form: { profession: [{name, link?}, ...] }
LEARNED_FILE = "data/learned_recipes.json"         # { user_id: { profession: [{name, link}, ...] } }
ARTISAN_FILE = "data/artisan_registry.json"        # { recipe_name: [{user_id, tier}], ... }

def _normalize_grouped(raw: Any) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    if isinstance(raw, dict):
        for prof, items in raw.items():
            for r in items or []:
                name = r.get("name", "Unknown")
                link = r.get("link") or r.get("url") or ""
                grouped.setdefault(prof, []).append({"name": name, "profession": prof, "link": link})
        return grouped
    if isinstance(raw, list):
        for r in raw:
            if not isinstance(r, dict):
                continue
            name = r.get("name", "Unknown")
            prof = r.get("profession", "Unknown")
            link = r.get("link") or r.get("url") or ""
            grouped.setdefault(prof, []).append({"name": name, "profession": prof, "link": link})
        return grouped
    return {}

class Recipes(commands.Cog):
    """Handles recipes, learning/unlearning, searching, and registry sync."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recipes: List[Dict[str, Any]] = load_json(RECIPES_FILE, [])
        grouped_raw = load_json(RECIPES_GROUPED_FILE, {})
        self.grouped: Dict[str, List[Dict[str, str]]] = _normalize_grouped(grouped_raw or self.recipes)
        self.learned: Dict[str, Dict[str, List[Dict[str, str]]]] = load_json(LEARNED_FILE, {})
        self.registry: Dict[str, List[Dict[str, Any]]] = load_json(ARTISAN_FILE, {})

    # ---------------- persistence ----------------
    def _save_learned(self):
        save_json(LEARNED_FILE, self.learned)

    def _save_registry(self):
        save_json(ARTISAN_FILE, self.registry)

    # ---------------- public API ----------------
    def get_user_recipes(self, user_id: int) -> Dict[str, List[Dict[str, str]]]:
        return self.learned.get(str(user_id), {})

    def add_learned_recipe(self, user_id: int, profession: str, name: str, link: str = "") -> bool:
        store = self.learned.setdefault(str(user_id), {})
        bucket = store.setdefault(profession, [])
        if any(r["name"].lower() == name.lower() for r in bucket):
            return False
        bucket.append({"name": name, "link": link})
        bucket.sort(key=lambda x: x["name"])
        self._save_learned()

        # registry: track tier too
        profs_cog = self.bot.get_cog("Professions")
        tier = "Unknown"
        if profs_cog and hasattr(profs_cog, "get_user_professions"):
            profs = profs_cog.get_user_professions(user_id)
            for p in profs:
                if p["name"].lower() == profession.lower():
                    tier = p.get("tier", "Unknown")
                    break

        users = self.registry.setdefault(name, [])
        if not any(u["user_id"] == user_id for u in users):
            users.append({"user_id": user_id, "tier": tier})
            self._save_registry()
        return True

    def remove_learned_recipe(self, user_id: int, profession: str, name: str) -> bool:
        store = self.learned.get(str(user_id), {})
        bucket = store.get(profession, [])
        before = len(bucket)
        bucket[:] = [r for r in bucket if r.get("name", "").lower() != name.lower()]
        removed = len(bucket) < before
        if removed:
            self._save_learned()
            # update registry mapping
            users = self.registry.get(name, [])
            users = [u for u in users if u["user_id"] != user_id]
            if users:
                self.registry[name] = users
            else:
                self.registry.pop(name, None)
            self._save_registry()
        return removed

    def search_recipes(self, query: str, professions: Optional[List[str]] = None) -> List[Dict[str, str]]:
        q = (query or "").lower().strip()
        results: List[Dict[str, str]] = []
        for prof, items in self.grouped.items():
            if professions and prof not in professions:
                continue
            for r in items:
                if q in r.get("name", "").lower():
                    results.append(r)
        if not results and self.recipes:
            for r in self.recipes:
                if q in r.get("name", "").lower():
                    if professions and r.get("profession") not in professions:
                        continue
                    results.append({
                        "name": r.get("name", "Unknown"),
                        "profession": r.get("profession", "Unknown"),
                        "link": r.get("link") or r.get("url") or ""
                    })
        return results[:100]

    # ---------------- UI: Modals ----------------
    class LearnRecipeModal(Modal, title="📗 Learn a Recipe"):
        def __init__(self, cog: "Recipes", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.query = TextInput(label="Recipe Name", placeholder="e.g. Obsidian Dagger", required=True)
            self.add_item(self.query)

        async def on_submit(self, interaction: discord.Interaction):
            # Limit results based on unlocked professions
            profs_cog = interaction.client.get_cog("Professions")
            prof_filter: Optional[List[str]] = None
            if profs_cog and hasattr(profs_cog, "get_user_professions"):
                prof_filter = [p["name"] for p in profs_cog.get_user_professions(self.user_id)] or None

            matches = self.cog.search_recipes(self.query.value, prof_filter)
            if not matches:
                embed = discord.Embed(title="📗 Learn Recipe", description=f"⚠️ No recipes found for **{self.query.value}**.", color=discord.Color.red())
                return await interaction.response.edit_message(embed=embed, view=None)

            opts = []
            for r in matches[:25]:
                val = f"{r['name']}|{r.get('profession','Unknown')}|{r.get('link','')}"
                opts.append(discord.SelectOption(label=r["name"][:100], description=f"{r.get('profession','Unknown')}", value=val))

            view = self.cog._LearnSelectView(self.cog, self.user_id, opts)
            embed = discord.Embed(title="📗 Select a Recipe to Learn", description=f"Found **{len(matches)}** matches.", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed, view=view)

    class SearchRecipeModal(Modal, title="🔍 Search Recipes"):
        def __init__(self, cog: "Recipes", user_id: int):
            super().__init__(timeout=240)
            self.cog = cog
            self.user_id = user_id
            self.query = TextInput(label="Search Term", placeholder="e.g. Phoenix Cloak", required=True)
            self.add_item(self.query)

        async def on_submit(self, interaction: discord.Interaction):
            matches = self.cog.search_recipes(self.query.value)
            e = discord.Embed(title=f"🔍 Results: {self.query.value}", color=discord.Color.purple())
            if not matches:
                e.description = "⚠️ No recipes found."
            else:
                for r in matches[:10]:
                    link = r.get("link") or ""
                    prof = r.get("profession", "Unknown")
                    e.add_field(name=r.get("name", "Unknown"), value=f"**Profession:** {prof}\n{'[View Link](' + link + ')' if link else '—'}", inline=False)
            await interaction.response.edit_message(embed=e, view=None)

    # ---------------- Hub: buttons provider ----------------
    def build_recipe_buttons(self, user_id: int) -> discord.ui.View:
        v = View(timeout=240)
        v.add_item(Button(label="📗 Learn Recipe", style=discord.ButtonStyle.success, custom_id=f"rc_learn_{user_id}"))
        v.add_item(Button(label="📘 Learned", style=discord.ButtonStyle.primary, custom_id=f"rc_learned_{user_id}"))
        v.add_item(Button(label="🔍 Search", style=discord.ButtonStyle.secondary, custom_id=f"rc_search_{user_id}"))
        return v

    # ---------------- Interaction listener ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not getattr(interaction, "data", None):
            return
        cid = interaction.data.get("custom_id")
        if not cid or not isinstance(cid, str):
            return

        uid = interaction.user.id

        if cid == f"rc_learn_{uid}":
            modal = Recipes.LearnRecipeModal(self, uid)
            return await interaction.response.send_modal(modal)

        if cid == f"rc_learned_{uid}":
            e = discord.Embed(title="📘 Learned Recipes", description="Select a profession to view recipes.", color=discord.Color.blue())
            v = Recipes.ViewLearnedView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)

        if cid == f"rc_search_{uid}":
            modal = Recipes.SearchRecipeModal(self, uid)
            return await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recipes(bot))
