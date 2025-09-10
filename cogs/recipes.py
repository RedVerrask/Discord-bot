import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import os

PORTFOLIO_FILE = "portfolios.json"

# ------------------------------------------------------
# Helper — Pagination Buttons
# ------------------------------------------------------
class PrevPageButton(Button):
    def __init__(self, view):
        super().__init__(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.update_view()
        await interaction.response.edit_message(embed=self.view_ref.embed, view=self.view_ref)

class NextPageButton(Button):
    def __init__(self, view):
        super().__init__(label="➡️ Next", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.update_view()
        await interaction.response.edit_message(embed=self.view_ref.embed, view=self.view_ref)

class BackToMainButton(Button):
    def __init__(self, recipes_cog):
        super().__init__(label="🔙 Back to Recipes", style=discord.ButtonStyle.danger)
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="📜 Recipes Menu:",
            embed=None,
            view=RecipesMainView(self.recipes_cog)
        )

# ------------------------------------------------------
# Paginated Recipe Viewer
# ------------------------------------------------------
class RecipeListView(View):
    def __init__(self, recipes_cog, user_id, recipes, page=0, per_page=10):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipes = recipes
        self.page = page
        self.per_page = per_page
        self.update_view()

    def update_view(self):
        self.clear_items()
        start = self.page * self.per_page
        end = start + self.per_page
        recipes_to_show = self.recipes[start:end]

        # Build embed
        self.embed = discord.Embed(
            title="📜 Recipes",
            description=f"Showing **{start+1}-{min(end, len(self.recipes))}** of **{len(self.recipes)}**",
            color=discord.Color.green()
        )

        for recipe in recipes_to_show:
            self.embed.add_field(
                name=recipe["name"],
                value=f"**Profession:** {recipe['profession']}\n"
                      f"**Level:** {recipe['level']}\n"
                      f"[View Recipe]({recipe['url']})",
                inline=False
            )

        # Pagination buttons
        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if end < len(self.recipes):
            self.add_item(NextPageButton(self))
        self.add_item(BackToMainButton(self.recipes_cog))

# ------------------------------------------------------
# Learn Recipe Options
# ------------------------------------------------------
class LearnRecipeOptionsView(View):
    def __init__(self, recipes_cog, user_id):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id

    @discord.ui.button(label="📜 Browse Recipes", style=discord.ButtonStyle.primary)
    async def browse(self, interaction: discord.Interaction, button: discord.ui.Button):
        professions_cog = self.recipes_cog.bot.get_cog("Professions")
        user_professions = professions_cog.get_user_professions(self.user_id) if professions_cog else []

        if not user_professions:
            await interaction.response.send_message(
                "⚠️ You don’t have any professions set.", ephemeral=True
            )
            return

        options = [discord.SelectOption(label=prof, value=prof) for prof in user_professions]
        select = discord.ui.Select(placeholder="Select a profession…", options=options)
        view = discord.ui.View(timeout=None)
        view.add_item(select)

        async def select_callback(inter, select=select):
            profession = select.values[0]
            recipes = [
                r for r in self.recipes_cog.get_all_recipes()
                if r["profession"].lower() == profession.lower()
            ]
            if not recipes:
                await inter.response.send_message(f"⚠️ No recipes found for **{profession}**.", ephemeral=True)
                return
            await inter.response.edit_message(
                content=f"📜 Recipes for **{profession}**:",
                embed=RecipeListView(self.recipes_cog, self.user_id, recipes).embed,
                view=RecipeListView(self.recipes_cog, self.user_id, recipes)
            )

        select.callback = select_callback
        await interaction.response.edit_message(
            content="Select your profession to browse recipes:",
            view=view
        )

    @discord.ui.button(label="⌨️ Type Recipe Name", style=discord.ButtonStyle.secondary)
    async def type_recipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchRecipeModal(self.recipes_cog, self.user_id))

# ------------------------------------------------------
# Search Recipe Modal
# ------------------------------------------------------
class SearchRecipeModal(Modal):
    def __init__(self, recipes_cog, user_id):
        super().__init__(title="🔍 Search Recipes")
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe_input = TextInput(label="Recipe Name", placeholder="Type part of a recipe name…")
        self.add_item(self.recipe_input)

    async def on_submit(self, interaction: discord.Interaction):
        query = self.recipe_input.value.lower()
        results = [r for r in self.recipes_cog.get_all_recipes() if query in r["name"].lower()]

        if not results:
            await interaction.response.send_message("⚠️ No recipes found.", ephemeral=True)
            return

        await interaction.response.send_message(
            content=f"Found **{len(results)}** recipe(s):",
            embed=RecipeListView(self.recipes_cog, self.user_id, results).embed,
            view=RecipeListView(self.recipes_cog, self.user_id, results),
            ephemeral=True
        )

# ------------------------------------------------------
# Search Recipes View
# ------------------------------------------------------
class SearchRecipesView(View):
    def __init__(self, recipes_cog, user_id):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id

        professions = sorted(list({r["profession"] for r in self.recipes_cog.get_all_recipes()}))
        options = [discord.SelectOption(label="All Professions", value="all")] + [
            discord.SelectOption(label=prof, value=prof) for prof in professions
        ]
        select = discord.ui.Select(placeholder="Choose a profession…", options=options)
        self.add_item(select)

        async def search_callback(interaction: discord.Interaction, select=select):
            profession = select.values[0]
            recipes = self.recipes_cog.get_all_recipes()
            if profession != "all":
                recipes = [r for r in recipes if r["profession"].lower() == profession.lower()]
            if not recipes:
                await interaction.response.send_message("⚠️ No recipes found.", ephemeral=True)
                return
            await interaction.response.edit_message(
                content=f"📜 Showing recipes for **{profession}**" if profession != "all" else "📜 Showing all recipes:",
                embed=RecipeListView(self.recipes_cog, self.user_id, recipes).embed,
                view=RecipeListView(self.recipes_cog, self.user_id, recipes)
            )

        select.callback = search_callback

# ------------------------------------------------------
# Learned Recipes View
# ------------------------------------------------------
class LearnedRecipesUserView(View):
    def __init__(self, recipes_cog, users_with_recipes):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.users_with_recipes = users_with_recipes

        options = [
            discord.SelectOption(label=name, value=uid)
            for uid, name in self.users_with_recipes.items()
        ]
        select = discord.ui.Select(placeholder="Select a user…", options=options)
        self.add_item(select)

        async def show_user_recipes(interaction: discord.Interaction, select=select):
            user_id = select.values[0]
            portfolio = self.recipes_cog.get_portfolio(user_id)
            if not portfolio:
                await interaction.response.send_message("⚠️ This user hasn't learned any recipes yet.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📜 Recipes Learned by {self.users_with_recipes[user_id]}",
                color=discord.Color.blue()
            )
            for recipe in portfolio:
                embed.add_field(
                    name=recipe["name"],
                    value=f"{recipe['profession']} L{recipe['level']} - [View Recipe]({recipe['url']})",
                    inline=False
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        select.callback = show_user_recipes

# ------------------------------------------------------
# Recipes Main Menu
# ------------------------------------------------------
class RecipesMainView(View):
    def __init__(self, recipes_cog):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog

        select = discord.ui.Select(
            placeholder="Choose an option…",
            options=[
                discord.SelectOption(label="Learn Recipe", value="learn"),
                discord.SelectOption(label="Learned Recipes", value="learned"),
                discord.SelectOption(label="Search Recipes", value="search"),
            ]
        )
        self.add_item(select)

        async def menu_callback(interaction: discord.Interaction, select=select):
            choice = select.values[0]
            user_id = interaction.user.id

            if choice == "learn":
                if not self.recipes_cog.user_has_profession(user_id):
                    await interaction.response.send_message(
                        "⚠️ You must have a profession to learn recipes.", ephemeral=True
                    )
                    return
                await interaction.response.send_message(
                    "How would you like to learn a recipe?",
                    view=LearnRecipeOptionsView(self.recipes_cog, user_id),
                    ephemeral=True
                )

            elif choice == "learned":
                users_with_recipes = self.recipes_cog.get_users_with_recipes()
                if not users_with_recipes:
                    await interaction.response.send_message(
                        "⚠️ No users have learned recipes yet.", ephemeral=True
                    )
                    return
                await interaction.response.send_message(
                    "Select a user to view their learned recipes:",
                    view=LearnedRecipesUserView(self.recipes_cog, users_with_recipes),
                    ephemeral=True
                )

            elif choice == "search":
                await interaction.response.send_message(
                    "Select a profession to search recipes:",
                    view=SearchRecipesView(self.recipes_cog, user_id),
                    ephemeral=True
                )

        select.callback = menu_callback

# ------------------------------------------------------
# Recipes Cog
# ------------------------------------------------------
class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("recipes.json", "r", encoding="utf-8") as f:
            self.recipes_data = json.load(f)
        self.user_portfolios = self.load_portfolios()

    def get_all_recipes(self):
        recipes_list = self.recipes_data if isinstance(self.recipes_data, list) else self.recipes_data.get("recipes", [])
        cleaned = []
        for r in recipes_list:
            recipe = r.copy()
            if recipe["name"].startswith("Recipe: "):
                recipe["name"] = recipe["name"][8:]
            recipe["level"] = int(recipe["level"])
            cleaned.append(recipe)
        return cleaned

    def user_has_profession(self, user_id):
        professions_cog = self.bot.get_cog("Professions")
        return bool(professions_cog and professions_cog.get_user_professions(user_id))

    def get_users_with_recipes(self):
        users = {}
        for uid, portfolio in self.user_portfolios.items():
            if portfolio:
                member = self.bot.get_user(int(uid))
                users[uid] = member.display_name if member else f"User {uid}"
        return users

    def has_learned(self, user_id, recipe_name):
        return any(r["name"] == recipe_name for r in self.user_portfolios.get(str(user_id), []))

    def learn_recipe(self, user_id, recipe):
        uid = str(user_id)
        if uid not in self.user_portfolios:
            self.user_portfolios[uid] = []
        if recipe not in self.user_portfolios[uid]:
            self.user_portfolios[uid].append(recipe)
            self.save_portfolios()

    def get_portfolio(self, user_id):
        return self.user_portfolios.get(str(user_id), [])

    def load_portfolios(self):
        if not os.path.exists(PORTFOLIO_FILE):
            return {}
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_portfolios(self):
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(self.user_portfolios, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(Recipes(bot))
