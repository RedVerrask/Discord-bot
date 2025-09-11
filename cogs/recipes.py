import discord
from discord.ext import commands
import json
import os

RECIPES_FILE = "data/recipes.json"
LEARNED_FILE = "data/learned_recipes.json"

# =========================
# JSON Helpers
# =========================
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# =========================
# Recipes Cog
# =========================
class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recipes = load_json(RECIPES_FILE)
        self.learned = load_json(LEARNED_FILE)

    # Get a user's learned recipes
    def get_user_recipes(self, user_id):
        return self.learned.get(str(user_id), {})

    # Add a recipe to user's learned list
    def add_learned_recipe(self, user_id, profession, recipe_name, link):
        user_id = str(user_id)
        if user_id not in self.learned:
            self.learned[user_id] = {}
        if profession not in self.learned[user_id]:
            self.learned[user_id][profession] = []

        # Avoid duplicates
        if any(r["name"] == recipe_name for r in self.learned[user_id][profession]):
            return False

        self.learned[user_id][profession].append({"name": recipe_name, "link": link})
        save_json(LEARNED_FILE, self.learned)
        return True

    # Remove a learned recipe
    def remove_learned_recipe(self, user_id, profession, recipe_name):
        user_id = str(user_id)
        if user_id in self.learned and profession in self.learned[user_id]:
            self.learned[user_id][profession] = [
                r for r in self.learned[user_id][profession] if r["name"] != recipe_name
            ]
            save_json(LEARNED_FILE, self.learned)

    # Search recipes by partial name (optionally limit to professions)
    def search_recipes(self, query, professions=None):
        results = []
        query = query.lower()
        for profession, recipes in self.recipes.items():
            if professions and profession not in professions:
                continue
            for recipe in recipes:
                if query in recipe["name"].lower():
                    results.append({
                        "name": recipe["name"],
                        "link": recipe.get("link"),
                        "profession": profession
                    })
        return results

# ==========================================================
# Recipes Menu View
# ==========================================================
class RecipesMainView(discord.ui.View):
    def __init__(self, recipes_cog, user):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

    # 📗 Learn Recipes
    @discord.ui.button(label="📗 Learn Recipes", style=discord.ButtonStyle.success)
    async def learn_recipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = LearnRecipeModal(self.recipes_cog, self.user)
        await interaction.response.send_modal(modal)

    # 📘 Learned Recipes
    @discord.ui.button(label="📘 Learned Recipes", style=discord.ButtonStyle.primary)
    async def learned_recipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LearnedRecipesView(self.recipes_cog, self.user)
        await view.send_embed(interaction)

    # 🔍 Search Recipes
    @discord.ui.button(label="🔍 Search Recipes", style=discord.ButtonStyle.secondary)
    async def search_recipes(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SearchRecipeModal(self.recipes_cog)
        await interaction.response.send_modal(modal)

# ==========================================================
# Learn Recipe Modal
# ==========================================================
class LearnRecipeModal(discord.ui.Modal, title="📗 Learn Recipe"):
    def __init__(self, recipes_cog, user):
        super().__init__()
        self.recipes_cog = recipes_cog
        self.user = user

        self.query = discord.ui.TextInput(
            label="Enter Recipe Name",
            placeholder="Example: Obsidian Dagger",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        professions_cog = interaction.client.get_cog("Professions")
        professions = [p["name"] for p in professions_cog.get_user_professions(self.user.id)]

        matches = self.recipes_cog.search_recipes(self.query.value, professions)
        if not matches:
            await interaction.response.send_message("⚠️ No recipes found.", ephemeral=True)
            return

        view = discord.ui.View(timeout=None)
        embed = discord.Embed(
            title="📗 Select Recipe to Learn",
            description=f"Results for **{self.query.value}**:",
            color=discord.Color.green()
        )

        for recipe in matches:
            button = discord.ui.Button(
                label=f"Learn: {recipe['name']}",
                style=discord.ButtonStyle.success
            )

            async def callback(i, r=recipe):
                success = self.recipes_cog.add_learned_recipe(
                    self.user.id, r["profession"], r["name"], r["link"]
                )
                if success:
                    await i.response.send_message(f"✅ Learned **{r['name']}**!", ephemeral=True)
                else:
                    await i.response.send_message(f"⚠️ Already learned **{r['name']}**.", ephemeral=True)
            button.callback = callback
            view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==========================================================
# Learned Recipes View
# ==========================================================
class LearnedRecipesView(discord.ui.View):
    def __init__(self, recipes_cog, user):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

    async def send_embed(self, interaction: discord.Interaction):
        user_recipes = self.recipes_cog.get_user_recipes(self.user.id)
        embed = discord.Embed(
            title=f"📘 {self.user.display_name}'s Learned Recipes",
            color=discord.Color.blue()
        )

        if not user_recipes:
            embed.description = "*You haven’t learned any recipes yet.*"
        else:
            for profession, recipes in user_recipes.items():
                recipe_list = "\n".join(
                    [f"• [{r['name']}]({r['link']})" for r in recipes]
                )
                embed.add_field(name=profession, value=recipe_list, inline=False)

        # Add button to view others’ recipes
        view = discord.ui.View(timeout=None)
        view.add_item(ViewOthersRecipesButton(self.recipes_cog))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==========================================================
# View Others’ Recipes Button
# ==========================================================
class ViewOthersRecipesButton(discord.ui.Button):
    def __init__(self, recipes_cog):
        super().__init__(
            label="👥 View Others' Recipes",
            style=discord.ButtonStyle.secondary
        )
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        members_with_recipes = {
            uid: r for uid, r in self.recipes_cog.learned.items() if r
        }

        if not members_with_recipes:
            await interaction.response.send_message(
                "⚠️ No guild members have learned any recipes yet.",
                ephemeral=True
            )
            return

        options = []
        for uid in members_with_recipes.keys():
            member = guild.get_member(int(uid))
            if member:
                options.append(discord.SelectOption(
                    label=member.display_name,
                    value=str(uid),
                    description="View this player's recipes"
                ))

        dropdown = discord.ui.Select(
            placeholder="Select a guild member...",
            options=options,
            custom_id="recipes_view_others_dropdown"
        )

        view = discord.ui.View(timeout=None)

        async def dropdown_callback(select_interaction: discord.Interaction):
            target_id = dropdown.values[0]
            target_user = guild.get_member(int(target_id))

            recipes = self.recipes_cog.get_user_recipes(target_id)
            embed = discord.Embed(
                title=f"📘 {target_user.display_name}'s Learned Recipes",
                color=discord.Color.teal()
            )

            if not recipes:
                embed.description = "*This player hasn’t learned any recipes yet.*"
            else:
                for profession, learned in recipes.items():
                    recipe_list = "\n".join(
                        [f"• [{r['name']}]({r['link']})" for r in learned]
                    )
                    embed.add_field(name=profession, value=recipe_list, inline=False)

            await select_interaction.response.send_message(embed=embed, ephemeral=True)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        await interaction.response.send_message(
            "Choose a guild member to view their learned recipes:",
            view=view,
            ephemeral=True
        )

# ==========================================================
# Search Recipe Modal
# ==========================================================
class SearchRecipeModal(discord.ui.Modal, title="🔍 Search Recipes"):
    def __init__(self, recipes_cog):
        super().__init__()
        self.recipes_cog = recipes_cog
        self.query = discord.ui.TextInput(
            label="Search for Recipe",
            placeholder="Example: Phoenix Cloak",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        matches = self.recipes_cog.search_recipes(self.query.value)
        embed = discord.Embed(
            title=f"🔍 Search Results for '{self.query.value}'",
            color=discord.Color.purple()
        )

        if not matches:
            embed.description = "⚠️ No recipes found."
        else:
            for recipe in matches[:10]:
                embed.add_field(
                    name=recipe["name"],
                    value=f"**Profession:** {recipe['profession']}\n[View on Ashes Codex]({recipe['link']})",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================================
# Cog Setup
# ==========================================================
async def setup(bot):
    await bot.add_cog(Recipes(bot))
