import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import os
from collections import defaultdict

PORTFOLIO_FILE = "portfolios.json"


# ======================================================
# Recipes Cog
# ======================================================
class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Load and normalize recipe data
        with open("recipes.json", "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.all_recipes = self._normalize_recipes(raw)
        self.user_portfolios = self._load_portfolios()

        # Build indexes for speed
        self.professions = sorted({r["profession"] for r in self.all_recipes})
        self.by_profession = defaultdict(list)
        for r in self.all_recipes:
            self.by_profession[r["profession"].lower()].append(r)

    # ------------- Data Helpers -------------
    def _normalize_recipes(self, data):
        recipes_list = data if isinstance(data, list) else data.get("recipes", [])
        cleaned = []
        for r in recipes_list:
            if not isinstance(r, dict):
                continue
            recipe = {}
            # Name
            name = str(r.get("name", "")).strip()
            if name.startswith("Recipe: "):
                name = name[8:]
            recipe["name"] = name or "Unknown"
            # Level
            try:
                recipe["level"] = int(r.get("level", 0))
            except (ValueError, TypeError):
                recipe["level"] = 0
            # Profession
            recipe["profession"] = str(r.get("profession", "Unknown")).strip()
            # URL
            url = str(r.get("url", "")).strip()
            recipe["url"] = url if url else "https://example.com"
            # Precompute lowercase name for faster search
            recipe["_name_lc"] = recipe["name"].casefold()
            cleaned.append(recipe)
        return cleaned

    def search_recipes(self, query: str, profession: str | None = None, limit: int | None = None):
        """Case-insensitive partial search. All tokens must appear in the name."""
        q = (query or "").strip().casefold()
        if not q:
            return []

        tokens = [t for t in q.split() if t]
        pool = self.all_recipes if not profession or profession.lower() == "all" \
               else self.by_profession.get(profession.lower(), [])

        out = []
        for r in pool:
            name = r["_name_lc"]
            if all(tok in name for tok in tokens):
                out.append(r)
                if limit and len(out) >= limit:
                    break
        return out

    def user_has_profession(self, user_id: int) -> bool:
        professions_cog = self.bot.get_cog("Professions")
        return bool(professions_cog and professions_cog.get_user_professions(user_id))

    def learn_recipe(self, user_id, recipe):
        uid = str(user_id)
        entry = {
            "name": recipe["name"],
            "profession": recipe["profession"],
            "level": recipe["level"],
            "url": recipe["url"],
        }
        lst = self.user_portfolios.setdefault(uid, [])
        if all(r["name"] != entry["name"] for r in lst):
            lst.append(entry)
            self._save_portfolios()

    def get_users_with_recipes(self):
        users = {}
        for uid, portfolio in self.user_portfolios.items():
            if portfolio:
                member = self.bot.get_user(int(uid))
                users[uid] = member.display_name if member else f"User {uid}"
        return users

    def get_portfolio(self, user_id):
        return self.user_portfolios.get(str(user_id), [])

    # ------------- Portfolio I/O -------------
    def _load_portfolios(self):
        if not os.path.exists(PORTFOLIO_FILE):
            return {}
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_portfolios(self):
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(self.user_portfolios, f, ensure_ascii=False, indent=4)


# ======================================================
# Type-to-Search Modal (used by Search + Learn)
# ======================================================
class RecipeSearchModal(Modal, title="Search Recipes"):
    query = TextInput(label="Recipe name (partial ok)", placeholder="e.g., ‘sword’, ‘oak plank’, ‘stew’", required=True)

    def __init__(self, recipes_cog: Recipes, user_id: int, profession: str | None = None):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.profession = profession

    async def on_submit(self, interaction: discord.Interaction):
        results = self.recipes_cog.search_recipes(self.query.value, self.profession)
        if not results:
            await interaction.response.send_message("⚠️ No recipes matched.", ephemeral=True)
            return

        view = RecipeListView(self.recipes_cog, self.user_id, recipes=results, per_page=6)
        await interaction.response.send_message(
            content=f"🔎 Results for “{self.query.value}”"
                    + (f" in **{self.profession}**" if self.profession and self.profession != "all" else "") + ":",
            embed=view.embed,
            view=view,
            ephemeral=True
        )


# ======================================================
# Profession picker for LEARN (uses RECIPE professions, not player professions)
# ======================================================
class LearnByProfessionView(View):
    def __init__(self, recipes_cog: Recipes, user_id: int):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Browse by recipe profession…",
        options=[discord.SelectOption(label="All Professions", value="all")],
        custom_id="learn_profession_from_recipes"
    )
    async def select_profession(self, interaction: discord.Interaction, select: Select):
        # hydrate options if first time
        if len(select.options) == 1:  # only "All Professions" present
            select.options = [discord.SelectOption(label="All Professions", value="all")] + [
                discord.SelectOption(label=p, value=p) for p in self.recipes_cog.professions
            ]
            await interaction.response.edit_message(content="Pick a profession to browse:", view=self)
            return

        profession = select.values[0] if select.values else "all"
        pool = self.recipes_cog.all_recipes if profession == "all" else self.recipes_cog.by_profession.get(profession.lower(), [])
        if not pool:
            await interaction.response.send_message("⚠️ No recipes found.", ephemeral=True)
            return

        view = RecipeListView(self.recipes_cog, self.user_id, recipes=pool, per_page=6)
        await interaction.response.edit_message(
            content=f"📜 Browsing **{profession}** recipes" if profession != "all" else "📜 Browsing all recipes",
            embed=view.embed,
            view=view
        )


# ======================================================
# Main Recipes Menu
# ======================================================
class RecipesMainView(View):
    def __init__(self, recipes_cog: Recipes):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog

    @discord.ui.select(
        placeholder="Choose an option…",
        options=[
            discord.SelectOption(label="Learn Recipe", value="learn"),
            discord.SelectOption(label="Search Recipes (type)", value="search"),
            discord.SelectOption(label="Learned Recipes", value="learned"),
        ],
        custom_id="recipes_main_select"
    )
    async def main_select(self, interaction: discord.Interaction, select: Select):
        choice = select.values[0]
        user_id = interaction.user.id

        # --- Learn Recipe ---
        if choice == "learn":
            # NEW: no dependency on user's professions
            view = View(timeout=None)

            @discord.ui.button(label="⌨️ Type Recipe Name", style=discord.ButtonStyle.primary, custom_id="learn_type")
            async def _type_btn(btn_inter: discord.Interaction, _btn: Button):
                await btn_inter.response.send_modal(RecipeSearchModal(self.recipes_cog, user_id))

            @discord.ui.button(label="📜 Browse by Recipe Profession", style=discord.ButtonStyle.secondary, custom_id="learn_browse_prof")
            async def _browse_btn(btn_inter: discord.Interaction, _btn: Button):
                await btn_inter.response.edit_message(
                    content="Select a profession to browse:",
                    view=LearnByProfessionView(self.recipes_cog, user_id),
                    embed=None
                )

            view.add_item(_type_btn)   # type: ignore
            view.add_item(_browse_btn) # type: ignore
            await interaction.response.edit_message(
                content="How would you like to learn a recipe?",
                view=view,
                embed=None
            )
            return

        # --- Search Recipes (type-only) ---
        if choice == "search":
            await interaction.response.send_modal(RecipeSearchModal(self.recipes_cog, user_id))
            return

        # --- Learned Recipes (user picker) ---
        if choice == "learned":
            users_with_recipes = self.recipes_cog.get_users_with_recipes()
            if not users_with_recipes:
                await interaction.response.send_message("⚠️ No users have learned recipes yet.", ephemeral=True)
                return

            view = View(timeout=None)

            @discord.ui.select(
                placeholder="Select a user…",
                options=[discord.SelectOption(label=name, value=uid) for uid, name in users_with_recipes.items()],
                custom_id="recipes_learned_user"
            )
            async def _user_pick(sel_inter: discord.Interaction, sel: Select):
                uid = sel.values[0]
                portfolio = self.recipes_cog.get_portfolio(uid) or []
                embed = discord.Embed(
                    title=f"📜 Recipes Learned by {users_with_recipes[uid]}",
                    color=discord.Color.blue()
                )
                if not portfolio:
                    embed.description = "*No recipes learned yet.*"
                else:
                    for r in portfolio[:20]:
                        embed.add_field(
                            name=r["name"],
                            value=f"{r['profession']} L{r['level']} — [🔗 Link]({r['url']})",
                            inline=False
                        )
                    if len(portfolio) > 20:
                        embed.set_footer(text=f"And {len(portfolio) - 20} more…")
                await sel_inter.response.send_message(embed=embed, ephemeral=True)

            view.add_item(_user_pick)  # type: ignore
            await interaction.response.edit_message(
                content="Select a user to view their learned recipes:",
                view=view,
                embed=None
            )
            return


# ======================================================
# Paginated Recipe List + Learn Buttons
# ======================================================
class RecipeListView(View):
    def __init__(self, recipes_cog: Recipes, user_id: int, recipes=None, page=0, per_page=6, profession=None):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.page = page
        self.per_page = max(1, min(per_page, 10))  # keep UI snappy
        self.profession = profession
        self.recipes = list(recipes) if recipes is not None else recipes_cog.all_recipes
        self.embed = self._build_embed()
        self._rebuild_buttons()

    # Build a lightweight embed
    def _build_embed(self):
        total = len(self.recipes)
        start = self.page * self.per_page
        end = min(start + self.per_page, total)

        embed = discord.Embed(
            title="📜 Recipes",
            description=f"Showing {start+1}-{end} of {total}",
            color=discord.Color.green()
        )
        for r in self.recipes[start:end]:
            embed.add_field(
                name=r["name"],
                value=f"**Prof:** {r['profession']}  •  **Lv:** {r['level']}\n[🔗 View]({r['url']})",
                inline=False
            )
        return embed

    def _rebuild_buttons(self):
        self.clear_items()
        # Current page recipe buttons (one per recipe)
        start = self.page * self.per_page
        end = min(start + self.per_page, len(self.recipes))

        for r in self.recipes[start:end]:
            label = (r["name"][:78] + "…") if len(r["name"]) > 80 else r["name"]
            self.add_item(RecipeButton(self.recipes_cog, self.user_id, r, label))

        # Pagination + Back
        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if end < len(self.recipes):
            self.add_item(NextPageButton(self))
        self.add_item(BackToMainButton(self.recipes_cog))

    async def refresh(self, interaction: discord.Interaction):
        self.embed = self._build_embed()
        self._rebuild_buttons()
        await interaction.response.edit_message(embed=self.embed, view=self)


class RecipeButton(Button):
    def __init__(self, recipes_cog: Recipes, user_id: int, recipe: dict, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"recipe_{hash(label) % 10_000_000}")
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe = recipe

    async def callback(self, interaction: discord.Interaction):
        view = ConfirmLearnView(self.recipes_cog, self.user_id, self.recipe)
        await interaction.response.send_message(
            f"Learn **{self.recipe['name']}**?",
            view=view,
            ephemeral=True
        )


class ConfirmLearnView(View):
    def __init__(self, recipes_cog: Recipes, user_id: int, recipe: dict):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe = recipe

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success, custom_id="confirm_learn")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.recipes_cog.learn_recipe(self.user_id, self.recipe)
        await interaction.response.edit_message(
            content=f"✅ You learned **{self.recipe['name']}**!",
            view=None
        )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_learn")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


class PrevPageButton(Button):
    def __init__(self, view: RecipeListView):
        super().__init__(label="⬅️ Prev", style=discord.ButtonStyle.secondary, custom_id="recipes_prev")
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        await self.view_ref.refresh(interaction)


class NextPageButton(Button):
    def __init__(self, view: RecipeListView):
        super().__init__(label="Next ➡️", style=discord.ButtonStyle.secondary, custom_id="recipes_next")
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        await self.view_ref.refresh(interaction)


class BackToMainButton(Button):
    def __init__(self, recipes_cog: Recipes):
        super().__init__(label="🏠 Back", style=discord.ButtonStyle.secondary, custom_id="recipes_back")
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="📖 Recipes Menu:",
            view=RecipesMainView(self.recipes_cog),
            embed=None
        )


# ======================================================
# Setup
# ======================================================
async def setup(bot):
    await bot.add_cog(Recipes(bot))
