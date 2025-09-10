# recipes.py
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import math
import os

PORTFOLIO_FILE = "portfolios.json"

# ---------------------------
# ----- Recipe Views --------
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
            self.add_item(Select(
                placeholder="Select a profession...",
                options=options,
                custom_id="select_profession"
            ))

    @discord.ui.select(custom_id="select_profession")
    async def select_profession(self, interaction: discord.Interaction, select: Select):
        profession = select.values[0]

        # Instantiate the next view, compatible with user_id/profession
        view = self.next_view_class(self.recipes_cog, user_id=self.user_id, profession=profession, **self.next_view_kwargs)
        await interaction.response.edit_message(
            content=f"Showing recipes for **{profession}**:",
            view=view
        )







class RecipesMainView(View):
    def __init__(self, recipes_cog):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog

        self.add_item(Select(placeholder="Choose an option...",
            options=[
                discord.SelectOption(label="Learn Recipe", value="learn"),
                discord.SelectOption(label="All Recipes", value="all"),
                discord.SelectOption(label="Learned Recipes", value="learned"),
                discord.SelectOption(label="Search Recipes", value="search"),
            ],
            custom_id="main_select"
        ))

    @discord.ui.select(custom_id="main_select")
    async def select_option(self, interaction: discord.Interaction, select: Select):
        choice = select.values[0]

        if choice == "learn":
            if not self.recipes_cog.user_has_profession(interaction.user.id):
                await interaction.response.send_message("You must have a profession to learn recipes.", ephemeral=True)
                return
            await interaction.response.edit_message(
                content="Select a profession first:",
                view=ProfessionSelectView(self.recipes_cog, interaction.user.id, RecipeListView)
            )

        elif choice == "all":
            await interaction.response.edit_message(
                content="Select a profession first:",
                view=ProfessionSelectView(self.recipes_cog, interaction.user.id, AllRecipesView)
            )

        elif choice == "learned":
            await interaction.response.edit_message(
                content="Select a profession first:",
                view=ProfessionSelectView(self.recipes_cog, interaction.user.id, UserPortfolioView)
            )

        elif choice == "search":
            await interaction.response.send_modal(SearchRecipeModal(self.recipes_cog, interaction.user.id))




# ---------------------------
# ----- Search Modal -------
# ---------------------------

class SearchRecipeModal(Modal):
    def __init__(self, recipes_cog, user_id, profession=None):
        super().__init__(title="Search Recipes")
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.profession = profession
        self.add_item(TextInput(label="Enter recipe name", placeholder="Type part of the recipe name here..."))

    async def on_submit(self, interaction: discord.Interaction):
        query = self.children[0].value.lower()
        results = [r for r in self.recipes_cog.get_all_recipes() if query in r["name"].lower() and (not self.profession or r["profession"] == self.profession)]

        if not results:
            await interaction.response.send_message("No recipes found matching your query.", ephemeral=True)
            return

        # Add the pagination notice
        message_text = f"Found {len(results)} recipe(s). Showing {min(10, len(results))} per page:"
        await interaction.response.send_message(
            message_text,
            view=RecipeListView(self.recipes_cog, self.user_id, recipes=results),
            ephemeral=True
        )


# ---------------------------
# ----- Recipe List View ----
# ---------------------------

class RecipeListView(discord.ui.View):
    def __init__(self, recipes_cog, user_id, recipes=None, page=0, per_page=10, profession=None):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.page = page
        self.per_page = per_page
        self.profession = profession
        all_recipes = recipes if recipes else self.recipes_cog.get_all_recipes()
        # Filter by profession
        self.recipes = [r for r in all_recipes if (not profession or r["profession"] == profession)]
        self.update_buttons()


    def update_buttons(self):
        self.clear_items()
        start = self.page * self.per_page
        end = start + self.per_page
        for recipe in self.recipes[start:end]:
            label = f"{recipe['name']} ({recipe['profession']} L{recipe['level']})"
            self.add_item(RecipeButton(self.recipes_cog, self.user_id, recipe, label))

        # Pagination
        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if (self.page + 1) * self.per_page < len(self.recipes):
            self.add_item(NextPageButton(self))

        # Back button
        self.add_item(BackToMainButton(self.recipes_cog))


class RecipeButton(Button):
    def __init__(self, recipes_cog, user_id, recipe, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe = recipe

    async def callback(self, interaction: discord.Interaction):
        try:
            # Acknowledge the interaction first
            await interaction.response.defer(ephemeral=True)

            # Then send the message with the confirmation view
            await interaction.followup.send(
                f"Do you want to learn **{self.recipe['name']}**?",
                view=ConfirmLearnView(self.recipes_cog, self.user_id, self.recipe),
                ephemeral=True
            )
        except Exception as e:
            # Use followup here too since response might already be deferred
            await interaction.followup.send(f"Error: {e}", ephemeral=True)



class ConfirmLearnView(View):
    def __init__(self, recipes_cog, user_id, recipe):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe = recipe

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.recipes_cog.learn_recipe(self.user_id, self.recipe)
        await interaction.response.edit_message(content=f"✅ You learned **{self.recipe['name']}**!", view=None)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Cancelled learning recipe.", view=None)



# ---------------------------
# ----- Pagination Buttons ---
# ---------------------------

class PrevPageButton(Button):
    def __init__(self, view):
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class NextPageButton(Button):
    def __init__(self, view):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(view=self.view_ref)


class BackToMainButton(Button):
    def __init__(self, recipes_cog):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Recipes Menu:",
            view=RecipesMainView(self.recipes_cog)
        )

# ---------------------------
# ----- User Portfolio View --
# ---------------------------

class UserPortfolioView(View):
    def __init__(self, recipes_cog, user_id=None, profession=None, **kwargs):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.users = self.recipes_cog.get_users_with_portfolio()
        if not self.users:
            self.add_item(Button(label="No users found", disabled=True))
        else:
            for uid, name in self.users.items():
                self.add_item(UserButton(self.recipes_cog, uid, name))




class UserButton(Button):
    def __init__(self, recipes_cog, user_id, name):
        super().__init__(label=name, style=discord.ButtonStyle.secondary)
        self.recipes_cog = recipes_cog
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            portfolio = self.recipes_cog.get_portfolio(self.user_id)
            embed = discord.Embed(title=f"{interaction.user.display_name}'s Portfolio", color=discord.Color.blue())
            for recipe in portfolio:
                embed.add_field(
                    name=recipe['name'],
                    value=f"{recipe['profession']} L{recipe['level']} - [Link]({recipe['url']})",
                    inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)


# ---------------------------
# ----- All Recipes View ----
# ---------------------------

class AllRecipesView(View):
    def __init__(self, recipes_cog, user_id, profession=None):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.page = 0
        self.per_page = 10
        all_recipes = self.recipes_cog.get_all_recipes()
        self.recipes = [r for r in all_recipes if (not profession or r["profession"] == profession)]
        self.update_buttons()


    def update_buttons(self):
        self.clear_items()
        start = self.page * self.per_page
        end = start + self.per_page

        for recipe in self.recipes[start:end]:
            learned = self.recipes_cog.has_learned(self.user_id, recipe['name'])
            style = discord.ButtonStyle.success if learned else discord.ButtonStyle.danger
            label = f"{recipe['name']} ({recipe['profession']} L{recipe['level']})"
            self.add_item(RecipeButtonColored(self.recipes_cog, self.user_id, recipe, label, style))

        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if (self.page + 1) * self.per_page < len(self.recipes):
            self.add_item(NextPageButton(self))

        self.add_item(BackToMainButton(self.recipes_cog))


class RecipeButtonColored(Button):
    def __init__(self, recipes_cog, user_id, recipe, label, style):
        super().__init__(label=label, style=style)
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.recipe = recipe

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            embed = discord.Embed(
                title=self.recipe["name"],
                description=f"Profession: {self.recipe['profession']}\nLevel: {self.recipe['level']}",
                color=discord.Color.green() if self.recipes_cog.has_learned(self.user_id, self.recipe['name']) else discord.Color.red()
            )
            embed.add_field(name="Link", value=f"[View Recipe]({self.recipe['url']})", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)


# ---------------------------
# ----- Cog ----------------
# ---------------------------

class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("recipes.json", "r", encoding="utf-8") as f:
            self.recipes_data = json.load(f)
        self.user_portfolios = self.load_portfolios()  # Load from portfolios.json

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
        if not professions_cog:
            return False  # Professions cog not loaded
        # Assuming Professions cog has a method `get_user_professions(user_id)` returning a list
        user_professions = professions_cog.get_user_professions(user_id)
        return bool(user_professions)

    def has_learned(self, user_id, recipe_name):
        return any(r['name'] == recipe_name for r in self.user_portfolios.get(str(user_id), []))

    def learn_recipe(self, user_id, recipe):
        uid = str(user_id)
        if uid not in self.user_portfolios:
            self.user_portfolios[uid] = []
        if recipe not in self.user_portfolios[uid]:
            self.user_portfolios[uid].append(recipe)
            self.save_portfolios()

    def get_users_with_portfolio(self):
        users = {}
        for uid in self.user_portfolios:
            member = self.bot.get_user(int(uid))  # fetch Discord User object
            if member:
                users[uid] = member.display_name
            else:
                users[uid] = f"User{uid}"  # fallback
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


async def setup(bot):
    await bot.add_cog(Recipes(bot))
