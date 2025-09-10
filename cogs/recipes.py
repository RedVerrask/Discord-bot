import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import os

PORTFOLIO_FILE = "portfolios.json"

# ---------------------------
# Recipes Cog
# ---------------------------
class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("recipes.json", "r", encoding="utf-8") as f:
            self.recipes_data = json.load(f)
        self.user_portfolios = self.load_portfolios()

    # -------------------------------------
    # Recipes Data Helpers
    # -------------------------------------
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

    def learn_recipe(self, user_id, recipe):
        uid = str(user_id)
        if uid not in self.user_portfolios:
            self.user_portfolios[uid] = []
        if recipe not in self.user_portfolios[uid]:
            self.user_portfolios[uid].append(recipe)
            self.save_portfolios()

    def get_users_with_recipes(self):
        users = {}
        for uid, portfolio in self.user_portfolios.items():
            if portfolio:
                member = self.bot.get_user(int(uid))
                users[uid] = member.display_name if member else f"User {uid}"
        return users

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

# ---------------------------
# Dropdown to Select Profession
# ---------------------------
class ProfessionSelectView(View):
    def __init__(self, recipes_cog, user_id, next_view_class, **kwargs):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.next_view_class = next_view_class
        self.next_view_kwargs = kwargs

        professions_cog = recipes_cog.bot.get_cog("Professions")
        user_professions = professions_cog.get_user_professions(user_id) if professions_cog else []

        if not user_professions:
            self.add_item(Button(label="No professions found", disabled=True))
        else:
            options = [discord.SelectOption(label=prof, value=prof) for prof in user_professions]
            select = Select(placeholder="Select a profession...", options=options)
            select.callback = self.on_select
            self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        profession = interaction.data["values"][0]
        recipes = [r for r in self.recipes_cog.get_all_recipes() if r["profession"] == profession]
        if not recipes:
            await interaction.response.send_message(f"⚠️ No recipes found for **{profession}**.", ephemeral=True)
            return

        view = RecipeListView(self.recipes_cog, self.user_id, recipes=recipes, profession=profession)
        await interaction.response.edit_message(
            content=f"📜 Showing recipes for **{profession}**:",
            embed=view.embed,
            view=view
        )

# ---------------------------
# Search Recipes View
# ---------------------------
class SearchRecipesView(View):
    def __init__(self, recipes_cog, user_id):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id

        professions = sorted(list({r["profession"] for r in self.recipes_cog.get_all_recipes()}))
        options = [discord.SelectOption(label="All Professions", value="all")] + [
            discord.SelectOption(label=prof, value=prof) for prof in professions
        ]

        select = Select(placeholder="Choose a profession...", options=options)
        select.callback = self.search
        self.add_item(select)

    async def search(self, interaction: discord.Interaction):
        profession = interaction.data["values"][0]
        recipes = self.recipes_cog.get_all_recipes()

        if profession != "all":
            recipes = [r for r in recipes if r["profession"].lower() == profession.lower()]

        if not recipes:
            await interaction.response.send_message("⚠️ No recipes found.", ephemeral=True)
            return

        view = RecipeListView(self.recipes_cog, self.user_id, recipes)
        await interaction.response.edit_message(
            content=f"📜 Showing recipes for **{profession}**" if profession != "all" else "📜 Showing all recipes:",
            embed=view.embed,
            view=view
        )

# ---------------------------
# Recipe List View (with Pagination)
# ---------------------------
class RecipeListView(View):
    def __init__(self, recipes_cog, user_id, recipes=None, page=0, per_page=10, profession=None):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.page = page
        self.per_page = per_page
        self.profession = profession

        self.recipes = recipes if recipes else self.recipes_cog.get_all_recipes()
        self.embed = self.create_embed()
        self.update_buttons()

    def create_embed(self):
        embed = discord.Embed(
            title="📜 Recipes",
            description=f"Showing {self.page * self.per_page + 1}-{min((self.page + 1) * self.per_page, len(self.recipes))} "
                        f"of {len(self.recipes)}",
            color=discord.Color.green()
        )

        start = self.page * self.per_page
        end = start + self.per_page
        for recipe in self.recipes[start:end]:
            embed.add_field(
                name=recipe['name'],
                value=f"**Profession:** {recipe['profession']}\n**Level:** {recipe['level']}\n[🔗 View Recipe]({recipe['url']})",
                inline=False
            )
        return embed

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if (self.page + 1) * self.per_page < len(self.recipes):
            self.add_item(NextPageButton(self))
        self.add_item(BackToMainButton(self.recipes_cog))

class PrevPageButton(Button):
    def __init__(self, view):
        super().__init__(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.embed = self.view_ref.create_embed()
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.embed, view=self.view_ref)

class NextPageButton(Button):
    def __init__(self, view):
        super().__init__(label="Next ➡️", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.embed = self.view_ref.create_embed()
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.embed, view=self.view_ref)

class BackToMainButton(Button):
    def __init__(self, recipes_cog):
        super().__init__(label="🏠 Back", style=discord.ButtonStyle.secondary)
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="📖 Recipes Menu:",
            view=RecipesMainView(self.recipes_cog),
            embed=None
        )

# ---------------------------
# Recipes Main Menu View
# ---------------------------
class RecipesMainView(View):
    def __init__(self, recipes_cog):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog

        select = Select(
            placeholder="Choose an option...",
            options=[
                discord.SelectOption(label="Learn Recipe", value="learn"),
                discord.SelectOption(label="Search Recipes", value="search"),
                discord.SelectOption(label="Learned Recipes", value="learned"),
            ]
        )
        select.callback = self.select_option
        self.add_item(select)

    async def select_option(self, interaction: discord.Interaction):
        choice = interaction.data['values'][0]
        user_id = interaction.user.id

        if choice == "learn":
            if not self.recipes_cog.user_has_profession(user_id):
                await interaction.response.send_message("⚠️ You must have a profession to learn recipes.", ephemeral=True)
                return
            await interaction.response.edit_message(
                content="Select a profession to browse recipes:",
                view=ProfessionSelectView(self.recipes_cog, user_id, RecipeListView),
                embed=None
            )

        elif choice == "search":
            await interaction.response.edit_message(
                content="Search recipes by profession or view all:",
                view=SearchRecipesView(self.recipes_cog, user_id),
                embed=None
            )

        elif choice == "learned":
            users_with_recipes = self.recipes_cog.get_users_with_recipes()
            if not users_with_recipes:
                await interaction.response.send_message("⚠️ No users have learned recipes yet.", ephemeral=True)
                return

            options = [discord.SelectOption(label=name, value=uid) for uid, name in users_with_recipes.items()]
            select = Select(placeholder="Select a user...", options=options)
            async def on_select(inter):
                uid = select.values[0]
                portfolio = self.recipes_cog.get_portfolio(uid)
                embed = discord.Embed(
                    title=f"📜 Recipes Learned by {users_with_recipes[uid]}",
                    color=discord.Color.blue()
                )
                for recipe in portfolio:
                    embed.add_field(
                        name=recipe["name"],
                        value=f"{recipe['profession']} L{recipe['level']} - [🔗 Link]({recipe['url']})",
                        inline=False
                    )
                await inter.response.send_message(embed=embed, ephemeral=True)
            select.callback = on_select
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.edit_message(
                content="Select a user to view their learned recipes:",
                view=view,
                embed=None
            )

# ---------------------------
# Setup Cog
# ---------------------------
async def setup(bot):
    await bot.add_cog(Recipes(bot))
