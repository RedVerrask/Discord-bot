# cogs/recipes.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Dict, List, Any, Optional

from utils.data import load_json, save_json
from cogs.hub import refresh_hub

RECIPES_FILE = "data/recipes.json"
RECIPES_GROUPED_FILE = "data/recipes_grouped.json"
LEARNED_FILE = "data/learned_recipes.json"
ARTISAN_FILE = "data/artisan_registry.json"


def _normalize_grouped(raw: Any) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    if isinstance(raw, dict):
        for prof, items in raw.items():
            for r in items or []:
                grouped.setdefault(prof, []).append({
                    "name": r.get("name", "Unknown"),
                    "profession": prof,
                    "link": r.get("link") or r.get("url") or ""
                })
    elif isinstance(raw, list):
        for r in raw:
            if isinstance(r, dict):
                grouped.setdefault(r.get("profession", "Unknown"), []).append({
                    "name": r.get("name", "Unknown"),
                    "profession": r.get("profession", "Unknown"),
                    "link": r.get("link") or r.get("url") or ""
                })
    return grouped


class Recipes(commands.Cog):
    """Handles recipes, learning/unlearning, searching, and registry sync."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recipes: List[Dict[str, Any]] = load_json(RECIPES_FILE, [])
        grouped_raw = load_json(RECIPES_GROUPED_FILE, {})
        self.grouped = _normalize_grouped(grouped_raw or self.recipes)
        self.learned: Dict[str, Dict[str, List[Dict[str, str]]]] = load_json(LEARNED_FILE, {})
        self.registry: Dict[str, List[int]] = load_json(ARTISAN_FILE, {})

    def _save_learned(self):
        save_json(LEARNED_FILE, self.learned)

    def _save_registry(self):
        save_json(ARTISAN_FILE, self.registry)

    def get_user_recipes(self, user_id: int):
        return self.learned.get(str(user_id), {})

    def add_learned_recipe(self, user_id: int, profession: str, name: str, link: str = "") -> bool:
        store = self.learned.setdefault(str(user_id), {})
        bucket = store.setdefault(profession, [])
        if any(r["name"].lower() == name.lower() for r in bucket):
            return False
        bucket.append({"name": name, "link": link})
        bucket.sort(key=lambda x: x["name"])
        self._save_learned()
        users = self.registry.setdefault(name, [])
        if user_id not in users:
            users.append(user_id)
            self._save_registry()
        return True

    def remove_learned_recipe(self, user_id: int, profession: str, name: str) -> bool:
        bucket = self.learned.get(str(user_id), {}).get(profession, [])
        before = len(bucket)
        bucket[:] = [r for r in bucket if r["name"].lower() != name.lower()]
        removed = len(bucket) < before
        if removed:
            self._save_learned()
            users = self.registry.get(name, [])
            if user_id in users:
                users.remove(user_id)
                if users:
                    self.registry[name] = users
                else:
                    self.registry.pop(name, None)
                self._save_registry()
        return removed

    def search_recipes(self, query: str, professions: Optional[List[str]] = None):
        q = (query or "").lower().strip()
        results: List[Dict[str, str]] = []
        for prof, items in self.grouped.items():
            if professions and prof not in professions:
                continue
            for r in items:
                if q in r.get("name", "").lower():
                    results.append(r)
        return results[:100]

    # ---------------- UI ----------------
    class LearnRecipeModal(Modal, title="📗 Learn a Recipe"):
        def __init__(self, cog: "Recipes", user_id: int):
            super().__init__(timeout=240)
            self.cog, self.user_id = cog, user_id
            self.query = TextInput(label="Recipe Name", required=True)
            self.add_item(self.query)

        async def on_submit(self, interaction: discord.Interaction):
            matches = self.cog.search_recipes(self.query.value)
            if not matches:
                return await interaction.response.send_message(
                    f"⚠️ No recipes found for **{self.query.value}**.", ephemeral=True
                )
            opts = [
                discord.SelectOption(
                    label=r["name"][:100],
                    description=r.get("profession") or "Unknown",
                    value=f"{r['name']}|{r.get('profession','Unknown')}|{r.get('link','')}"
                )
                for r in matches[:25]
            ]
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="📗 Select a Recipe",
                    description=f"Found **{len(matches)}** matches.",
                    color=discord.Color.green()
                ),
                view=Recipes._LearnSelectView(self.cog, self.user_id, opts)
            )

    class _LearnSelectView(View):
        def __init__(self, cog, user_id, options):
            super().__init__(timeout=240)
            self.add_item(Recipes._LearnSelect(cog, user_id, options))

        class _LearnSelect(Select):
            def __init__(self, cog, user_id, options):
                super().__init__(placeholder="Choose recipe…", options=options)
                self.cog, self.user_id = cog, user_id

            async def callback(self, interaction: discord.Interaction):
                try:
                    name, prof, link = self.values[0].split("|", 2)
                except ValueError:
                    return await interaction.response.send_message("⚠️ Invalid selection.", ephemeral=True)
                added = self.cog.add_learned_recipe(self.user_id, prof, name, link)
                msg = f"✅ Learned **{name}**." if added else f"⚠️ Already learned **{name}**."
                await interaction.response.send_message(msg, ephemeral=True)
                await refresh_hub(interaction, "recipes")

    class UnlearnListView(View):
        def __init__(self, cog, user_id, profession, items):
            super().__init__(timeout=240)
            for r in items or []:
                self.add_item(Recipes._UnlearnBtn(cog, user_id, profession, r["name"]))

        class _UnlearnBtn(Button):
            def __init__(self, cog, user_id, profession, name):
                super().__init__(label=f"Unlearn {name}", style=discord.ButtonStyle.danger)
                self.cog, self.user_id, self.profession, self.name = cog, user_id, profession, name

            async def callback(self, interaction: discord.Interaction):
                self.cog.remove_learned_recipe(self.user_id, self.profession, self.name)
                await interaction.response.send_message(f"🗑 Unlearned **{self.name}**.", ephemeral=True)
                await refresh_hub(interaction, "recipes")

    # ---------------- Hub ----------------
    def build_recipe_buttons(self, user_id: int):
        v = View(timeout=240)
        v.add_item(Button(label="📗 Learn", style=discord.ButtonStyle.success, custom_id=f"rc_learn_{user_id}"))
        v.add_item(Button(label="📘 Learned", style=discord.ButtonStyle.primary, custom_id=f"rc_learned_{user_id}"))
        v.add_item(Button(label="🔍 Search", style=discord.ButtonStyle.secondary, custom_id=f"rc_search_{user_id}"))
        return v

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        cid = getattr(interaction.data, "get", lambda k: None)("custom_id") if getattr(interaction, "data", None) else None
        if not cid: return
        uid = interaction.user.id

        if cid == f"rc_learn_{uid}":
            return await interaction.response.send_modal(Recipes.LearnRecipeModal(self, uid))
        if cid == f"rc_learned_{uid}":
            e = discord.Embed(title="📘 Learned Recipes", description="Pick a profession.", color=discord.Color.blue())
            v = Recipes.ViewLearnedView(self, uid)
            return await interaction.response.edit_message(embed=e, view=v)
        if cid == f"rc_search_{uid}":
            return await interaction.response.send_modal(Recipes.SearchRecipeModal(self, uid))


async def setup(bot: commands.Bot):
    await bot.add_cog(Recipes(bot))
