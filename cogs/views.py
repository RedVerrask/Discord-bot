import discord
from .professions import Professions
from .recipes import Recipes, RecipesMainView  # import your Recipes and RecipesMainView classes

# ----- Home View -----
class HomeView(discord.ui.View):
    def __init__(self, professions_cog: "Professions", recipes_cog: "Recipes"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        
    # Add this button for Artisan menu
    @discord.ui.button(label="Artisan", style=discord.ButtonStyle.primary)
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Artisan Menu:",
            view=AddArtisanView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Recipe Menu:",
            view=RecipesMainView(self.recipes_cog),
            ephemeral=True
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

# ----- Gathering Professions -----
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary)
    async def add_mining(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select your Mining tier:",
            view=TierSelectView(self.professions_cog, interaction.user.id, "Mining"),
            ephemeral=True
        )

    @discord.ui.button(label="Lumberjacking", style=discord.ButtonStyle.secondary)
    async def add_lumberjacking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select your Lumberjacking tier:",
            view=TierSelectView(self.professions_cog, interaction.user.id, "Lumberjacking"),
            ephemeral=True
        )

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary)
    async def add_fishing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select your Fishing tier:",
            view=TierSelectView(self.professions_cog, interaction.user.id, "Fishing"),
            ephemeral=True
        )

    @discord.ui.button(label="Herbalism", style=discord.ButtonStyle.secondary)
    async def add_herbalism(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select your Herbalism tier:",
            view=TierSelectView(self.professions_cog, interaction.user.id, "Herbalism"),
            ephemeral=True
        )

    @discord.ui.button(label="Hunting", style=discord.ButtonStyle.secondary)
    async def add_hunting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select your Hunting tier:",
            view=TierSelectView(self.professions_cog, interaction.user.id, "Hunting"),
            ephemeral=True
        )

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Back to home:",
            view=HomeView(self.professions_cog, self.recipes_cog)
        )

# ----- Processing Professions -----
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

# ----- Crafting Professions -----
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

# ----- Main Add Artisan Menu -----
class AddArtisanView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

    @discord.ui.button(label="Gathering Profession", style=discord.ButtonStyle.secondary)
    async def gathering(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Gathering Menu:",
            view=AddGathererView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Processing Profession", style=discord.ButtonStyle.secondary)
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Processing Menu:",
            view=AddProcessingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Crafting Profession", style=discord.ButtonStyle.secondary)
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Crafting Menu:",
            view=AddCraftingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

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


