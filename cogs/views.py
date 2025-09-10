import discord
from .professions import Professions
from .recipes import Recipes, RecipesMainView

# ----- Home View -----
class HomeView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", recipes_cog: "Recipes"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Artisan", style=discord.ButtonStyle.primary)
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Artisan Menu:",
            view=AddArtisanView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RecipesMainView(self.recipes_cog)
        await interaction.response.send_message(
            "Recipe Menu:", view=view, ephemeral=True
        )

# ----- Tier Select View -----
class TierSelectView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", user_id, profession):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.user_id = user_id
        self.profession = profession

    @discord.ui.select(
        placeholder="Choose your tier...",
        options=[
            discord.SelectOption(label="Novice", description="Just starting out", value="1"),
            discord.SelectOption(label="Apprentice", description="Learning the ropes", value="2"),
            discord.SelectOption(label="Journeyman", description="Skilled worker", value="3"),
            discord.SelectOption(label="Master", description="Expert level", value="4"),
            discord.SelectOption(label="Grandmaster", description="The very best", value="5"),
        ]
    )
    async def select_tier(self, interaction: discord.Interaction, select: discord.ui.Select):
        tier = select.values[0]
        self.professions_cog.set_user_profession(self.user_id, self.profession, tier)
        await interaction.response.send_message(
            f"✅ You are now **Tier {tier} {self.profession}**!", ephemeral=True
        )

# ----- Gathering View -----
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    def add_prof_button(self, label):
        async def callback(interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                f"Select your {label} tier:",
                view=TierSelectView(self.professions_cog, interaction.user.id, label),
                ephemeral=True
            )
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)
        btn.callback = callback
        self.add_item(btn)

    def setup_buttons(self):
        for prof in ["Mining", "Lumberjacking", "Fishing", "Herbalism", "Hunting"]:
            self.add_prof_button(prof)

        # Back button
        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Back to home:",
                view=HomeView(self.professions_cog, self.recipes_cog)
            )
        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary)
        back_btn.callback = back_callback
        self.add_item(back_btn)

    def __post_init__(self):
        self.setup_buttons()


# ----- Processing View -----
class AddProcessingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self.buttons = [
            "Stonemasonry", "Tanning", "Weaving", "Metalworking",
            "Farming", "Lumber Milling", "Alchemy", "Animal Husbandry", "Cooking"
        ]
        self.add_buttons()

    def add_buttons(self):
        for prof in self.buttons:
            async def callback(interaction: discord.Interaction, button: discord.ui.Button, prof=prof):
                await interaction.response.send_message(
                    f"Select your {prof} tier:",
                    view=TierSelectView(self.professions_cog, interaction.user.id, prof),
                    ephemeral=True
                )
            btn = discord.ui.Button(label=prof, style=discord.ButtonStyle.secondary)
            btn.callback = callback
            self.add_item(btn)

        # Back button
        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Back to home:",
                view=HomeView(self.professions_cog, self.recipes_cog)
            )
        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary)
        back_btn.callback = back_callback
        self.add_item(back_btn)


# ----- Crafting View -----
class AddCraftingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self.buttons = [
            "Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
            "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"
        ]
        self.add_buttons()

    def add_buttons(self):
        for prof in self.buttons:
            async def callback(interaction: discord.Interaction, button: discord.ui.Button, prof=prof):
                await interaction.response.send_message(
                    f"Select your {prof} tier:",
                    view=TierSelectView(self.professions_cog, interaction.user.id, prof),
                    ephemeral=True
                )
            btn = discord.ui.Button(label=prof, style=discord.ButtonStyle.secondary)
            btn.callback = callback
            self.add_item(btn)

        # Back button
        async def back_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(
                content="Back to home:",
                view=HomeView(self.professions_cog, self.recipes_cog)
            )
        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary)
        back_btn.callback = back_callback
        self.add_item(back_btn)


# ----- Main Artisan View -----
class AddArtisanView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Gathering Profession", style=discord.ButtonStyle.secondary)
    async def gathering(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AddGathererView(self.professions_cog, self.recipes_cog)
        view.__post_init__()  # initialize buttons
        await interaction.response.send_message("Gathering Menu:", view=view, ephemeral=True)

    @discord.ui.button(label="Processing Profession", style=discord.ButtonStyle.secondary)
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AddProcessingView(self.professions_cog, self.recipes_cog)
        await interaction.response.send_message("Processing Menu:", view=view, ephemeral=True)

    @discord.ui.button(label="Crafting Profession", style=discord.ButtonStyle.secondary)
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AddCraftingView(self.professions_cog, self.recipes_cog)
        await interaction.response.send_message("Crafting Menu:", view=view, ephemeral=True)

    @discord.ui.button(label="View Current Professions", style=discord.ButtonStyle.secondary)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id if interaction.guild else None
        embeds = await self.professions_cog.format_artisan_registry(interaction.client, guild_id=guild_id)
        await interaction.response.send_message(embeds=embeds, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Back to home:",
            view=HomeView(self.professions_cog, self.recipes_cog)
        )
