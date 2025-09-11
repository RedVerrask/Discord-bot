import discord
from cogs.professions_menu import ProfessionsMenu
from cogs.profile import ProfileMenuView
from cogs.recipes import RecipesMainView
from cogs.market import MarketMenu

class HomeView(discord.ui.View):
    def __init__(self, professions_cog=None, recipes_cog=None, market_cog=None):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.recipes_cog = recipes_cog
        self.market_cog = market_cog

    @discord.ui.button(label="👤 Profile", style=discord.ButtonStyle.primary, custom_id="home_profile")
    async def profile_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.profile import ProfileMenuView
        profile_cog = interaction.client.get_cog("Profile")
        await interaction.response.send_message(
            embed=profile_cog.build_profile_embed(interaction.user),
            view=ProfileMenuView(profile_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="🛠️ Professions", style=discord.ButtonStyle.secondary, custom_id="home_professions")
    async def professions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.professions_menu import ProfessionsMenu
        await interaction.response.send_message(
            "🛠️ **Professions Menu**",
            view=ProfessionsMenu(self.professions_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="📜 Recipes", style=discord.ButtonStyle.secondary, custom_id="home_recipes")
    async def recipes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.recipes import RecipesMainView
        await interaction.response.send_message(
            "📖 **Recipe Browser**",
            view=RecipesMainView(self.recipes_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="💰 Market", style=discord.ButtonStyle.success, custom_id="home_market")
    async def market_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.market import MarketMenu
        market_cog = interaction.client.get_cog("Market")
        await interaction.response.send_message(
            "💰 **Market Listings**",
            view=MarketMenu(market_cog, interaction.user),
            ephemeral=True
        )

    @discord.ui.button(label="⚔️ Gear Lookup", style=discord.ButtonStyle.secondary, custom_id="home_gear")
    async def gear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚔️ Gear Lookup",
            description="Coming soon! You'll be able to search gear stats, rarity, and sources here.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📖 Lore Drops", style=discord.ButtonStyle.secondary, custom_id="home_lore")
    async def lore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 Lore Drop",
            description="Did you know?\n\nThe **Riverlands** were once home to House Kordath...",
            color=discord.Color.gold()
        )
        embed.set_footer(text="More lore integrations coming soon!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
