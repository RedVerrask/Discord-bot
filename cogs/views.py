import discord
from .professions import Professions
from .recipes import Recipes, RecipesMainView

# ======================================================
# Home View
# ======================================================
class HomeView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", recipes_cog: "Recipes"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Artisan", style=discord.ButtonStyle.primary, custom_id="home_artisan")
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Artisan Menu:",
            view=AddArtisanView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary, custom_id="home_recipes")
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Recipe Menu:",
            view=RecipesMainView(self.recipes_cog),
            ephemeral=True
        )

# ======================================================
# Tier Select (returns to Artisan menu)
# ======================================================
class TierSelectView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", recipes_cog: "Recipes", user_id, profession):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self.user_id = user_id
        self.profession = profession

    @discord.ui.select(
        placeholder="Choose your tier…",
        options=[
            discord.SelectOption(label="Novice", value="1"),
            discord.SelectOption(label="Apprentice", value="2"),
            discord.SelectOption(label="Journeyman", value="3"),
            discord.SelectOption(label="Master", value="4"),
            discord.SelectOption(label="Grandmaster", value="5"),
        ],
        custom_id="tier_select_template"
    )
    async def select_tier(self, interaction: discord.Interaction, select: discord.ui.Select):
        tier = select.values[0]
        self.professions_cog.set_user_profession(self.user_id, self.profession, tier)
        await interaction.response.edit_message(
            content=f"✅ You are now **Tier {tier} {self.profession}**!\n\nReturning to Artisan Menu…",
            view=AddArtisanView(self.professions_cog, self.recipes_cog)
        )

# ======================================================
# Gathering / Processing / Crafting
# ======================================================
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        for prof in ["Mining", "Lumberjacking", "Fishing", "Herbalism", "Hunting"]:
            self.add_item(self._btn(prof, f"gather_{prof.lower()}"))
        self.add_item(self._back())

    def _btn(self, label, cid):
        b = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=cid)
        async def cb(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, label),
                ephemeral=True
            )
        b.callback = cb
        return b

    def _back(self):
        b = discord.ui.Button(label="Back", style=discord.ButtonStyle.danger, custom_id="gather_back")
        async def cb(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )
        b.callback = cb
        return b

class AddProcessingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        for prof in ["Stonemasonry", "Tanning", "Weaving", "Metalworking", "Farming", "Lumber Milling", "Alchemy", "Animal Husbandry", "Cooking"]:
            self.add_item(self._btn(prof, f"process_{prof.lower().replace(' ', '_')}"))
        self.add_item(self._back())

    def _btn(self, label, cid):
        b = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=cid)
        async def cb(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, label),
                ephemeral=True
            )
        b.callback = cb
        return b

    def _back(self):
        b = discord.ui.Button(label="Back", style=discord.ButtonStyle.danger, custom_id="process_back")
        async def cb(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )
        b.callback = cb
        return b

class AddCraftingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        for prof in ["Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry", "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"]:
            self.add_item(self._btn(prof, f"craft_{prof.lower().replace(' ', '_')}"))
        self.add_item(self._back())

    def _btn(self, label, cid):
        b = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=cid)
        async def cb(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, label),
                ephemeral=True
            )
        b.callback = cb
        return b

    def _back(self):
        b = discord.ui.Button(label="Back", style=discord.ButtonStyle.danger, custom_id="craft_back")
        async def cb(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )
        b.callback = cb
        return b

# ======================================================
# Root Artisan Menu
# ======================================================
class AddArtisanView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Gathering Professions", style=discord.ButtonStyle.secondary, custom_id="artisan_gathering")
    async def gathering(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Gathering Menu:", view=AddGathererView(self.professions_cog, self.recipes_cog), ephemeral=True)

    @discord.ui.button(label="Processing Professions", style=discord.ButtonStyle.secondary, custom_id="artisan_processing")
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Processing Menu:", view=AddProcessingView(self.professions_cog, self.recipes_cog), ephemeral=True)

    @discord.ui.button(label="Crafting Professions", style=discord.ButtonStyle.secondary, custom_id="artisan_crafting")
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Crafting Menu:", view=AddCraftingView(self.professions_cog, self.recipes_cog), ephemeral=True)

    @discord.ui.button(label="View Current Professions", style=discord.ButtonStyle.success, custom_id="artisan_view_current")
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id if interaction.guild else None
        embeds = await self.professions_cog.format_artisan_registry(interaction.client, guild_id=guild_id)

        home_button = discord.ui.Button(label="🏠 Home", style=discord.ButtonStyle.primary, custom_id="go_home")

        async def back_home(inter):
            await inter.response.edit_message(content="Returning to Home:", view=HomeView(self.professions_cog, self.recipes_cog))

        home_button.callback = back_home
        view = discord.ui.View(timeout=None)
        view.add_item(home_button)

        await interaction.response.send_message(embeds=embeds, view=view, ephemeral=True)

