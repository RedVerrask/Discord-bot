import discord
from .professions import Professions


# ----- Home View -----
class HomeView(discord.ui.View):
    def __init__(self, professions_cog: "Professions"):  # quotes = forward reference
        super().__init__(timeout=None)
        self.professions_cog = professions_cog

    @discord.ui.button(label="Artisan", style=discord.ButtonStyle.secondary)
    async def artisan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Artisan Menu:", view=AddArtisanView(self.professions_cog), ephemeral=True)

    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Recipe Menu:", ephemeral=True)


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
            discord.SelectOption(label="Novice", description="Just starting out"),
            discord.SelectOption(label="Apprentice", description="Learning the ropes"),
            discord.SelectOption(label="Journeyman", description="Skilled worker"),
            discord.SelectOption(label="Master", description="Expert level"),
            discord.SelectOption(label="Grandmaster", description="The very best"),
        ]
    )
    async def select_tier(self, interaction: discord.Interaction, select: discord.ui.Select):
        tier = select.values[0]
        self.professions_cog.set_user_profession(self.user_id, self.profession, tier)
        await interaction.response.send_message(
            f"✅ You are now a **{tier} {self.profession}**!", ephemeral=True
        )


# ----- Gathering Professions -----
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog: "Professions"):
        
        super().__init__(timeout=None)
        self.professions_cog = professions_cog

    @discord.ui.button(label="Mining", style=discord.ButtonStyle.secondary)
    async def add_mining(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Mining tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Mining"), ephemeral=True)

    @discord.ui.button(label="Lumberjacking", style=discord.ButtonStyle.secondary)
    async def add_lumberjacking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Lumberjacking tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Lumberjacking"), ephemeral=True)

    @discord.ui.button(label="Fishing", style=discord.ButtonStyle.secondary)
    async def add_fishing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Fishing tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Fishing"), ephemeral=True)

    @discord.ui.button(label="Herbalism", style=discord.ButtonStyle.secondary)
    async def add_herbalism(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Herbalism tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Herbalism"), ephemeral=True)

    @discord.ui.button(label="Hunting", style=discord.ButtonStyle.secondary)
    async def add_hunting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Hunting tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Hunting"), ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update the current message with the HomeView instead of sending a new message
        await interaction.response.edit_message(content="Back to home:", view=HomeView(self.professions_cog))



# ----- Processing Professions -----
class AddProcessingView(discord.ui.View):
    def __init__(self, professions_cog: "Professions"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog

    @discord.ui.button(label="Stonemasonry", style=discord.ButtonStyle.secondary)
    async def add_stonemasonry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Stonemasonry tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Stonemasonry"), ephemeral=True)

    @discord.ui.button(label="Tanning", style=discord.ButtonStyle.secondary)
    async def add_tanning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Tanning tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Tanning"), ephemeral=True)

    @discord.ui.button(label="Weaving", style=discord.ButtonStyle.secondary)
    async def add_weaving(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Weaving tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Weaving"), ephemeral=True)

    @discord.ui.button(label="Metalworking", style=discord.ButtonStyle.secondary)
    async def add_metalworking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Metalworking tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Metalworking"), ephemeral=True)

    @discord.ui.button(label="Farming", style=discord.ButtonStyle.secondary)
    async def add_farming(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Farming tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Farming"), ephemeral=True)

    @discord.ui.button(label="Lumber Milling", style=discord.ButtonStyle.secondary)
    async def add_lumber_milling(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Lumber Milling tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Lumber Milling"), ephemeral=True)

    @discord.ui.button(label="Alchemy", style=discord.ButtonStyle.secondary)
    async def add_alchemy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Alchemy tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Alchemy"), ephemeral=True)

    @discord.ui.button(label="Animal Husbandry", style=discord.ButtonStyle.secondary)
    async def add_animal_husbandry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Animal Husbandry tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Animal Husbandry"), ephemeral=True)

    @discord.ui.button(label="Cooking", style=discord.ButtonStyle.secondary)
    async def add_cooking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Cooking tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Cooking"), ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update the current message with the HomeView instead of sending a new message
        await interaction.response.edit_message(content="Back to home:", view=HomeView(self.professions_cog))


# ----- Crafting Professions -----
class AddCraftingView(discord.ui.View):
    def __init__(self, professions_cog: "Professions"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog

    @discord.ui.button(label="Arcane Engineering", style=discord.ButtonStyle.secondary)
    async def add_arcane(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Arcane Engineering tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Arcane Engineering"), ephemeral=True)

    @discord.ui.button(label="Armor Smithing", style=discord.ButtonStyle.secondary)
    async def add_armor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Armor Smithing tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Armor Smithing"), ephemeral=True)

    @discord.ui.button(label="Carpentry", style=discord.ButtonStyle.secondary)
    async def add_carpentry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Carpentry tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Carpentry"), ephemeral=True)

    @discord.ui.button(label="Jewelry", style=discord.ButtonStyle.secondary)
    async def add_jewelry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Jewelry tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Jewelry"), ephemeral=True)

    @discord.ui.button(label="Leatherworking", style=discord.ButtonStyle.secondary)
    async def add_leatherworking(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Leatherworking tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Leatherworking"), ephemeral=True)

    @discord.ui.button(label="Scribing", style=discord.ButtonStyle.secondary)
    async def add_scribing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Scribing tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Scribing"), ephemeral=True)

    @discord.ui.button(label="Tailoring", style=discord.ButtonStyle.secondary)
    async def add_tailoring(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Tailoring tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Tailoring"), ephemeral=True)

    @discord.ui.button(label="Weapon Smithing", style=discord.ButtonStyle.secondary)
    async def add_weapon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your Weapon Smithing tier:", view=TierSelectView(self.professions_cog, interaction.user.id, "Weapon Smithing"), ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update the current message with the HomeView instead of sending a new message
        await interaction.response.edit_message(content="Back to home:", view=HomeView(self.professions_cog))


# ----- Main Add Artisan Menu -----
class AddArtisanView(discord.ui.View):
    def __init__(self, professions_cog: "Professions"):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog

    @discord.ui.button(label="Gathering Profession", style=discord.ButtonStyle.secondary)
    async def gathering(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Gathering Menu:", view=AddGathererView(self.professions_cog), ephemeral=True)

    @discord.ui.button(label="Processing Profession", style=discord.ButtonStyle.secondary)
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Processing Menu:", view=AddProcessingView(self.professions_cog), ephemeral=True)

    @discord.ui.button(label="Crafting Profession", style=discord.ButtonStyle.secondary)
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Crafting Menu:", view=AddCraftingView(self.professions_cog), ephemeral=True)

    @discord.ui.button(label="View Current Professions", style=discord.ButtonStyle.secondary)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.professions_cog.format_artisan_registry(interaction.client)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Back to home:", view=HomeView(self.professions_cog))
