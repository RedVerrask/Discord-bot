import discord
from discord.ext import commands
import json
import os
class MarketMenu(discord.ui.View):
    def __init__(self, market_cog, user):
        super().__init__(timeout=None)
        self.market_cog = market_cog
        self.user = user

    @discord.ui.button(label="📜 Browse Market", style=discord.ButtonStyle.primary)
    async def browse_market(self, interaction: discord.Interaction, button: discord.ui.Button):
        listings = self.market_cog.get_all_listings()
        if not listings:
            return await interaction.response.send_message("⚠️ There are no active market listings.", ephemeral=True)

        per_page = 5

        async def render(i: discord.Interaction, page: int, first: bool):
            total_pages = max(1, (len(listings) + per_page - 1) // per_page)
            start, end = page * per_page, page * per_page + per_page
            page_listings = listings[start:end]

            embed = discord.Embed(
                title=f"💰 Market Listings (Page {page+1}/{total_pages})",
                description="Current player-submitted prices",
                color=discord.Color.gold()
            )
            for entry in page_listings:
                embed.add_field(
                    name=f"🛒 {entry['item']} — {entry['price']}g",
                    value=f"📍 **Village**: {entry['village']}\n"
                            f"👤 **Seller**: {entry['seller']}\n"
                            f"[🔗 View on Ashes Codex]({entry['link']})",
                    inline=False
                )

            view = discord.ui.View(timeout=None)

            if page > 0:
                prev_btn = discord.ui.Button(label="⬅ Prev", style=discord.ButtonStyle.secondary)
                async def prev_cb(ii): await render(ii, page-1, False)
                prev_btn.callback = prev_cb
                view.add_item(prev_btn)

            if end < len(listings):
                next_btn = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.secondary)
                async def next_cb(ii): await render(ii, page+1, False)
                next_btn.callback = next_cb
                view.add_item(next_btn)

            close_btn = discord.ui.Button(label="❌ Close", style=discord.ButtonStyle.danger)
            async def close_cb(ii): await ii.response.edit_message(content="Menu closed.", view=None, embed=None)
            close_btn.callback = close_cb
            view.add_item(close_btn)

            if first:
                await i.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await i.response.edit_message(embed=embed, view=view)

        await render(interaction, 0, True)
