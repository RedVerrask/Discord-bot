import discord
from discord.ext import commands
import json
import os

RECIPES_FILE = "data/recipes.json"

def load_recipes():
    if not os.path.exists(RECIPES_FILE):
        return {}
    with open(RECIPES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ======================================================
# Recipes Cog
# ======================================================
class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recipes = load_recipes()

    def get_recipes_by_profession(self, profession):
        """Get all recipes matching a given profession."""
        return self.recipes.get(profession, [])

    def get_all_professions(self):
        return list(self.recipes.keys())

    def search_recipes(self, query):
        """Search recipes globally by name."""
        matches = []
        for profession, items in self.recipes.items():
            for recipe in items:
                if query.lower() in recipe["name"].lower():
                    matches.append(recipe)
        return matches


# ======================================================
# Recipe Browser View
# ======================================================
class RecipesMainView(discord.ui.View):
    def __init__(self, recipes_cog, user):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

    # ================================
    # Profession Filtered Recipes
    # ================================
    @discord.ui.button(label="📜 Browse My Recipes", style=discord.ButtonStyle.primary, custom_id="recipes_browse")
    async def browse_my_recipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        profile_cog = interaction.client.get_cog("Profile")
        professions_cog = interaction.client.get_cog("Professions")

        professions = professions_cog.get_user_professions(interaction.user.id)

        if not professions:
            await interaction.response.send_message(
                "⚠️ You don’t have any professions selected!\n"
                "Set your professions first to see relevant recipes.",
                ephemeral=True
            )
            return

        options = [
            discord.SelectOption(label=p["name"], value=p["name"])
            for p in professions
        ]

        view = discord.ui.View(timeout=None)
        dropdown = discord.ui.Select(placeholder="Select a profession to browse recipes...", options=options, min_values=1, max_values=1, custom_id="recipes_profession_dropdown")

        async def dropdown_callback(select_interaction: discord.Interaction):
            selected_profession = dropdown.values[0]
            await self._show_recipes(select_interaction, selected_profession)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        await interaction.response.send_message(
            "📜 **Choose a profession to view recipes:**",
            view=view,
            ephemeral=True
        )

    # ================================
    # Global Recipe Search
    # ================================
    @discord.ui.button(label="🔍 Search Recipes", style=discord.ButtonStyle.secondary, custom_id="recipes_search")
    async def search_recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RecipeSearchModal(self.recipes_cog)
        await interaction.response.send_modal(modal)

    # ================================
    # Show Recipes For Profession
    # ================================
    async def _show_recipes(self, interaction, profession):
        recipes = self.recipes_cog.get_recipes_by_profession(profession)

        if not recipes:
            await interaction.response.send_message(
                f"⚠️ No recipes found for **{profession}**.",
                ephemeral=True
            )
            return

        page = 0
        per_page = 5

        async def send_page(page_num):
            start = page_num * per_page
            end = start + per_page
            current_recipes = recipes[start:end]

            embed = discord.Embed(
                title=f"📜 {profession} Recipes (Page {page_num + 1}/{(len(recipes) - 1) // per_page + 1})",
                description="Filtered recipes based on your professions",
                color=discord.Color.gold()
            )

            for recipe in current_recipes:
                name = recipe.get("name", "Unknown Recipe")
                link = recipe.get("link", None)
                if link:
                    embed.add_field(name=f"🧩 {name}", value=f"[View on Ashes Codex]({link})", inline=False)
                else:
                    embed.add_field(name=f"🧩 {name}", value="No link available", inline=False)

            view = discord.ui.View(timeout=None)

            if page_num > 0:
                prev_button = discord.ui.Button(label="⬅ Prev", style=discord.ButtonStyle.secondary)
                async def prev_callback(i): await send_page(page_num - 1)
                prev_button.callback = prev_callback
                view.add_item(prev_button)

            if end < len(recipes):
                next_button = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.secondary)
                async def next_callback(i): await send_page(page_num + 1)
                next_button.callback = next_callback
                view.add_item(next_button)

            close_button = discord.ui.Button(label="❌ Close", style=discord.ButtonStyle.danger)
            async def close_callback(i): await i.response.edit_message(content="Menu closed.", view=None)
            close_button.callback = close_callback
            view.add_item(close_button)

            await interaction.response.edit_message(embed=embed, view=view)

        await send_page(page)


# ======================================================
# Recipe Search Modal
# ======================================================
class RecipeSearchModal(discord.ui.Modal, title="🔍 Search Recipes"):
    def __init__(self, recipes_cog):
        super().__init__()
        self.recipes_cog = recipes_cog

        self.query = discord.ui.TextInput(
            label="Search for a recipe",
            placeholder="Example: Obsidian Dagger, Phoenix Cloak...",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        matches = self.recipes_cog.search_recipes(self.query.value)

        embed = discord.Embed(
            title=f"🔍 Recipes matching '{self.query.value}'",
            color=discord.Color.green()
        )

        if not matches:
            embed.description = "⚠️ No recipes found."
        else:
            for recipe in matches[:10]:
                name = recipe.get("name", "Unknown Recipe")
                link = recipe.get("link", None)
                if link:
                    embed.add_field(name=f"🧩 {name}", value=f"[View on Ashes Codex]({link})", inline=False)
                else:
                    embed.add_field(name=f"🧩 {name}", value="No link available", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ======================================================
# Cog Setup
# ======================================================
async def setup(bot):
    await bot.add_cog(Recipes(bot))
