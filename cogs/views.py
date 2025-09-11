import discord
from cogs.professions_menu import ProfessionsMenu
from cogs.profile import ProfileMenuView
from cogs.recipes import RecipesMainView
from cogs.market import MarketMenu
class HomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👤 Profile", style=discord.ButtonStyle.primary)
    async def profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        profile_cog = interaction.client.get_cog("Profile")
        if not profile_cog:
            return await interaction.response.send_message("⚠️ Profile system not loaded.", ephemeral=True)
        from cogs.profile import ProfileMenuView
        await interaction.response.send_message(
            embed=profile_cog.build_profile_embed(interaction.user),
            view=ProfileMenuView(profile_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="🛠️ Professions", style=discord.ButtonStyle.secondary)
    async def professions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        professions_cog = interaction.client.get_cog("Professions")
        if not professions_cog:
            return await interaction.response.send_message("⚠️ Professions system not loaded.", ephemeral=True)
        from cogs.professions_menu import ProfessionsMenu
        await interaction.response.send_message(
            "🛠️ **Professions Menu**",
            view=ProfessionsMenu(professions_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="📜 Recipes", style=discord.ButtonStyle.secondary)
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        recipes_cog = interaction.client.get_cog("Recipes")
        if not recipes_cog:
            return await interaction.response.send_message("⚠️ Recipes system not loaded.", ephemeral=True)
        from cogs.recipes import RecipesMainView
        await interaction.response.send_message(
            "📖 **Recipe Browser**",
            view=RecipesMainView(recipes_cog, interaction.user),  # ← pass user
            ephemeral=True
        )

    @discord.ui.button(label="💰 Market", style=discord.ButtonStyle.success)
    async def market_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        market_cog = interaction.client.get_cog("Market")
        if not market_cog:
            return await interaction.response.send_message("⚠️ Market system not loaded.", ephemeral=True)
        from cogs.market import MarketMenu
        await interaction.response.send_message(
            "💰 **Market Listings**",
            view=MarketMenu(market_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="⚔️ Gear Lookup", style=discord.ButtonStyle.secondary)
    async def gear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚔️ Gear Lookup",
            description="Coming soon! You'll be able to search gear stats, rarity, and sources here.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📖 Lore Drops", style=discord.ButtonStyle.secondary)
    async def lore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 Lore Drop",
            description="Did you know?\n\nThe **Riverlands** were once home to House Kordath...",
            color=discord.Color.gold()
        )
        embed.set_footer(text="More lore integrations coming soon!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
