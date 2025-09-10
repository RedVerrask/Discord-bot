import discord
from .professions import Professions
from .recipes import Recipes, RecipesMainView

# ------------------------------------------------------
# Home View (Main Menu)
# ------------------------------------------------------
class HomeView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", recipes_cog: "Recipes"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(
        label="Artisan",
        style=discord.ButtonStyle.primary,
        custom_id="home_artisan"
    )
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Artisan Menu:",
            view=AddArtisanView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(
        label="Recipes",
        style=discord.ButtonStyle.primary,
        custom_id="home_recipes"
    )
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Recipe Menu:",
            view=RecipesMainView(self.recipes_cog),
            ephemeral=True
        )

# ------------------------------------------------------
# Tier Selection View
# ------------------------------------------------------
class TierSelectView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", user_id, profession):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.user_id = user_id
        self.profession = profession

        select = discord.ui.Select(
            placeholder="Choose your tier...",
            options=[
                discord.SelectOption(label="Novice", description="Just starting out", value="1"),
                discord.SelectOption(label="Apprentice", description="Learning the ropes", value="2"),
                discord.SelectOption(label="Journeyman", description="Skilled worker", value="3"),
                discord.SelectOption(label="Master", description="Expert level", value="4"),
                discord.SelectOption(label="Grandmaster", description="The very best", value="5"),
            ],
            custom_id=f"tier_select_{profession.lower()}"
        )
        select.callback = self.select_tier
        self.add_item(select)

    async def select_tier(self, interaction: discord.Interaction):
        tier = interaction.data["values"][0]
        self.professions_cog.set_user_profession(self.user_id, self.profession, tier)

        await interaction.response.edit_message(
            content=f"✅ You are now **Tier {tier} {self.profession}**!\n\nReturning to Artisan Menu...",
            view=AddArtisanView(self.professions_cog, self.profession)
    )


# ------------------------------------------------------
# Gathering Professions View
# ------------------------------------------------------
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self._setup_buttons()

    def _setup_buttons(self):
        for prof in ["Mining", "Lumberjacking", "Fishing", "Herbalism", "Hunting"]:
            self.add_item(self._create_profession_button(prof))

        self.add_item(self._create_back_button())

    def _create_profession_button(self, label):
        btn = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"gather_{label.lower()}"
        )

        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, interaction.user.id, label),
                ephemeral=True
            )

        btn.callback = callback
        return btn

    def _create_back_button(self):
        btn = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.danger,
            custom_id="gather_back"
        )

        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        btn.callback = back_callback
        return btn

# ------------------------------------------------------
# Processing Professions View
# ------------------------------------------------------
class AddProcessingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self._setup_buttons()

    def _setup_buttons(self):
        buttons = [
            "Stonemasonry", "Tanning", "Weaving", "Metalworking",
            "Farming", "Lumber Milling", "Alchemy",
            "Animal Husbandry", "Cooking"
        ]
        for prof in buttons:
            self.add_item(self._create_profession_button(prof))

        self.add_item(self._create_back_button())

    def _create_profession_button(self, label):
        btn = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"process_{label.lower().replace(' ', '_')}"
        )

        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, interaction.user.id, label),
                ephemeral=True
            )

        btn.callback = callback
        return btn

    def _create_back_button(self):
        btn = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.danger,
            custom_id="process_back"
        )

        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        btn.callback = back_callback
        return btn

# ------------------------------------------------------
# Crafting Professions View
# ------------------------------------------------------
class AddCraftingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self._setup_buttons()

    def _setup_buttons(self):
        buttons = [
            "Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
            "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"
        ]
        for prof in buttons:
            self.add_item(self._create_profession_button(prof))

        self.add_item(self._create_back_button())

    def _create_profession_button(self, label):
        btn = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"craft_{label.lower().replace(' ', '_')}"
        )

        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, interaction.user.id, label),
                ephemeral=True
            )

        btn.callback = callback
        return btn

    def _create_back_button(self):
        btn = discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.danger,
            custom_id="craft_back"
        )

        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        btn.callback = back_callback
        return btn

# ------------------------------------------------------
# Main Artisan View (Root Menu)
# ------------------------------------------------------
class AddArtisanView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(
        label="Gathering Professions",
        style=discord.ButtonStyle.secondary,
        custom_id="artisan_gathering"
    )
    async def gathering(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Gathering Menu:",
            view=AddGathererView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(
        label="Processing Professions",
        style=discord.ButtonStyle.secondary,
        custom_id="artisan_processing"
    )
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Processing Menu:",
            view=AddProcessingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(
        label="Crafting Professions",
        style=discord.ButtonStyle.secondary,
        custom_id="artisan_crafting"
    )
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Crafting Menu:",
            view=AddCraftingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

@discord.ui.button(
    label="View Current Professions",
    style=discord.ButtonStyle.secondary,
    custom_id="artisan_view_current"
)
async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
    guild_id = interaction.guild.id if interaction.guild else None
    embeds = await self.professions_cog.format_artisan_registry(
        interaction.client,
        guild_id=guild_id
    )

    home_button = discord.ui.Button(
        label="🏠 Home",
        style=discord.ButtonStyle.primary,
        custom_id="go_home"
    )

    async def back_home(inter):
        await inter.response.edit_message(
            content="Returning to Home:",
            view=HomeView(self.professions_cog, self.recipes_cog)
        )

    home_button.callback = back_home
    view = discord.ui.View(timeout=None)
    view.add_item(home_button)

    await interaction.response.send_message(embeds=embeds, view=view, ephemeral=True)
