import discord

class ProfessionsMenu(discord.ui.View):
    def __init__(self, professions_cog, user):
        super().__init__(timeout=None)
        self.professions_cog = professions_cog
        self.user = user

    # ================================
    # Profession Category Buttons
    # ================================
    @discord.ui.button(label="⛏️ Gathering", style=discord.ButtonStyle.primary, custom_id="prof_gathering")
    async def gathering_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_profession_dropdown(interaction, "Gathering", [
            "Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"
        ])

    @discord.ui.button(label="⚙️ Processing", style=discord.ButtonStyle.primary, custom_id="prof_processing")
    async def processing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_profession_dropdown(interaction, "Processing", [
            "Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
            "Metalworking", "Stonemasonry", "Tanning", "Weaving"
        ])

    @discord.ui.button(label="🛠️ Crafting", style=discord.ButtonStyle.primary, custom_id="prof_crafting")
    async def crafting_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_profession_dropdown(interaction, "Crafting", [
            "Arcane Engineering", "Armor Smithing", "Carpentry", "Jewelry",
            "Leatherworking", "Scribing", "Tailoring", "Weapon Smithing"
        ])

    # ================================
    # Remove Profession Button
    # ================================
    @discord.ui.button(label="❌ Remove Profession", style=discord.ButtonStyle.danger, custom_id="prof_remove")
    async def remove_profession_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        professions = self.professions_cog.get_user_professions(interaction.user.id)

        if not professions:
            await interaction.response.send_message(
                "⚠️ You don't have any professions to remove.",
                ephemeral=True
            )
            return

        options = [
            discord.SelectOption(label=p["name"], value=p["name"])
            for p in professions
        ]

        view = discord.ui.View(timeout=None)
        dropdown = discord.ui.Select(
            placeholder="Select a profession to remove...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="prof_remove_dropdown"
        )

        async def dropdown_callback(select_interaction: discord.Interaction):
            profession = dropdown.values[0]
            self.professions_cog.remove_user_profession(select_interaction.user.id, profession)
            embed = discord.Embed(
                title="✅ Profession Removed",
                description=f"You have removed **{profession}**.",
                color=discord.Color.red()
            )
            await select_interaction.response.send_message(embed=embed, ephemeral=True)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        @discord.ui.button(label="📜 View Current Professions", style=discord.ButtonStyle.success, custom_id="prof_view_current")
        async def view_current_professions(self, interaction: discord.Interaction, button: discord.ui.Button):
            guild_id = interaction.guild.id if interaction.guild else None
            embeds = await self.professions_cog.format_artisan_registry(interaction.client, guild_id=guild_id)

            if not embeds:
                await interaction.response.send_message(
                    "⚠️ No profession data found.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(embeds=embeds, ephemeral=True)


        # Back button
        back_button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.secondary)
        async def back_callback(back_interaction: discord.Interaction):
            await back_interaction.response.edit_message(
                content="🛠️ Back to Professions Menu",
                view=ProfessionsMenu(self.professions_cog, interaction.user)
            )
        back_button.callback = back_callback
        view.add_item(back_button)

        await interaction.response.send_message(
            content="Select a profession to remove:",
            view=view,
            ephemeral=True
        )

    # ================================
    # Tier Legend Button
    # ================================
    @discord.ui.button(label="📜 Tier Legend", style=discord.ButtonStyle.secondary, custom_id="prof_tier_legend")
    async def tier_legend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.professions_cog.get_tier_legend()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================================
    # Home Button
    # ================================
    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.success, custom_id="prof_home")
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.views import HomeView
        await interaction.response.edit_message(
            content="🏠 Returning to Home Menu",
            view=HomeView()
        )

    # ================================
    # Profession Dropdown Selector
    # ================================
    async def _show_profession_dropdown(self, interaction, category, professions):
        """Display a dropdown to choose a profession."""
        options = [
            discord.SelectOption(label=prof, value=prof)
            for prof in professions
        ]

        view = discord.ui.View(timeout=None)

        dropdown = discord.ui.Select(
            placeholder=f"Select your {category} profession...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="prof_select_dropdown"
        )

        async def dropdown_callback(select_interaction: discord.Interaction):
            profession = dropdown.values[0]
            await self._show_tier_selection(select_interaction, profession)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        # Back Button
        back_button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.danger)
        async def back_callback(inter):
            await inter.response.edit_message(
                content="🛠️ Back to Professions Menu",
                view=ProfessionsMenu(self.professions_cog, interaction.user)
            )
        back_button.callback = back_callback
        view.add_item(back_button)

        await interaction.response.edit_message(
            content=f"**{category} Professions** — choose one below:",
            view=view
        )

    # ================================
    # Tier Selection View
    # ================================
    async def _show_tier_selection(self, interaction, profession):
        """Show dropdown for selecting artisan tier."""
        tiers = [
            discord.SelectOption(label="Novice", value="1"),
            discord.SelectOption(label="Apprentice", value="2"),
            discord.SelectOption(label="Journeyman", value="3"),
            discord.SelectOption(label="Master", value="4"),
            discord.SelectOption(label="Grandmaster", value="5"),
        ]

        view = discord.ui.View(timeout=None)

        dropdown = discord.ui.Select(
            placeholder=f"Select your tier for {profession}",
            options=tiers,
            min_values=1,
            max_values=1,
            custom_id="prof_tier_dropdown"
        )

        async def dropdown_callback(select_interaction: discord.Interaction):
            tier = dropdown.values[0]
            success = self.professions_cog.set_user_profession(
                select_interaction.user.id, profession, tier
            )

            if not success:
                await select_interaction.response.send_message(
                    "⚠️ You can only have **2 professions** at a time.\n"
                    "Remove one before selecting a new one.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="✅ Profession Added",
                description=f"You are now **Tier {tier}** in **{profession}**!",
                color=discord.Color.green()
            )
            await select_interaction.response.send_message(embed=embed, ephemeral=True)

        dropdown.callback = dropdown_callback
        view.add_item(dropdown)

        # Back Button
        back_button = discord.ui.Button(label="⬅ Back", style=discord.ButtonStyle.danger)
        async def back_callback(inter):
            await inter.response.edit_message(
                content="🛠️ Back to Professions Menu",
                view=ProfessionsMenu(self.professions_cog, interaction.user)
            )
        back_button.callback = back_callback
        view.add_item(back_button)

        await interaction.response.edit_message(
            content=f"**Set Tier for {profession}**:",
            view=view
        )
