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
            "📖 Recipe Menu:",
            view=RecipesMainView(self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="✨ More Features", style=discord.ButtonStyle.secondary, custom_id="home_more")
    async def more_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚀 Upcoming Features",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="👤 Player Profiles",
            value="View your professions, tiers, and learned recipes.",
            inline=False
        )
        embed.add_field(
            name="💰 Market Manager",
            value="Submit and check player-driven item prices.",
            inline=False
        )
        embed.add_field(
            name="🔄 Trade Board",
            value="Offer, request, and search for items in the guild.",
            inline=False
        )
        embed.add_field(
            name="📜 Lore & Wiki Lookup",
            value="Pull info from Ashes Codex and other wikis.",
            inline=False
        )
        embed.add_field(
            name="🏆 Guild Stats",
            value="Track professions, recipes, and rankings.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ======================================================
# Tier Select View
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
# Gathering / Processing / Crafting Menus
# ======================================================
class AddGathererView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

        # Gathering Professions
        for prof in ["Mining", "Lumberjacking", "Fishing", "Herbalism", "Hunting"]:
            self.add_item(self._make_button(prof))

        # Back Button
        self.add_item(self._make_back_button())

    def _make_button(self, profession):
        button = discord.ui.Button(label=profession, style=discord.ButtonStyle.secondary)

        async def callback(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {profession} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, profession),
                ephemeral=True
            )

        button.callback = callback
        return button

    def _make_back_button(self):
        button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.danger)

        async def callback(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        button.callback = callback
        return button


class AddProcessingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

        # Processing Professions
        for prof in [
            "Stonemasonry", "Tanning", "Weaving", "Metalworking", "Farming",
            "Lumber Milling", "Alchemy", "Animal Husbandry", "Cooking"
        ]:
            self.add_item(self._make_button(prof))

        # Back Button
        self.add_item(self._make_back_button())

    def _make_button(self, profession):
        button = discord.ui.Button(label=profession, style=discord.ButtonStyle.secondary)

        async def callback(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {profession} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, profession),
                ephemeral=True
            )

        button.callback = callback
        return button

    def _make_back_button(self):
        button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.danger)

        async def callback(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        button.callback = callback
        return button


class AddCraftingView(discord.ui.View):
    def __init__(self, professions_cog, recipes_cog):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog

        # Crafting Professions
        for prof in [
            "Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
            "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"
        ]:
            self.add_item(self._make_button(prof))

        # Back Button
        self.add_item(self._make_back_button())

    def _make_button(self, profession):
        button = discord.ui.Button(label=profession, style=discord.ButtonStyle.secondary)

        async def callback(inter: discord.Interaction):
            await inter.response.send_message(
                f"Select your {profession} tier:",
                view=TierSelectView(self.professions_cog, self.recipes_cog, inter.user.id, profession),
                ephemeral=True
            )

        button.callback = callback
        return button

    def _make_back_button(self):
        button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.danger)

        async def callback(inter: discord.Interaction):
            await inter.response.edit_message(
                content="Returning to Artisan Menu:",
                view=AddArtisanView(self.professions_cog, self.recipes_cog)
            )

        button.callback = callback
        return button


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
        await interaction.response.send_message(
            "Gathering Menu:",
            view=AddGathererView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Processing Professions", style=discord.ButtonStyle.secondary, custom_id="artisan_processing")
    async def processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Processing Menu:",
            view=AddProcessingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Crafting Professions", style=discord.ButtonStyle.secondary, custom_id="artisan_crafting")
    async def crafting(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Crafting Menu:",
            view=AddCraftingView(self.professions_cog, self.recipes_cog),
            ephemeral=True
        )

    @discord.ui.button(label="View Current Professions", style=discord.ButtonStyle.success, custom_id="artisan_view_current")
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id if interaction.guild else None
        embeds = await self.professions_cog.format_artisan_registry(interaction.client, guild_id=guild_id)

        # Home Button
        home_button = discord.ui.Button(label="🏠 Home", style=discord.ButtonStyle.primary)

        async def back_home(inter):
            await inter.response.edit_message(
                content="Returning to Home:",
                view=HomeView(self.professions_cog, self.recipes_cog)
            )

        home_button.callback = back_home
        view = discord.ui.View(timeout=None)
        view.add_item(home_button)

        if not embeds:
            await interaction.response.send_message("⚠️ No profession data found.", ephemeral=True)
        else:
            await interaction.response.send_message(embeds=embeds, view=view, ephemeral=True)
