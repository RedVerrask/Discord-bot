# utils/debug.py
import discord
from discord.ext import commands
from utils.data import load_json
from cogs.hub import (
    PROFILES_FILE, RECIPES_FILE, LEARNED_FILE,
    MARKET_FILE, TRADES_FILE, MAILBOX_FILE, REGISTRY_FILE
)

# ✅ Global helper for bot.py and other modules
def debug_log(message: str, logger=None, bot=None, **extra):
    """
    Lightweight debug logger used globally.
    Falls back to print if no logger is provided.
    """
    if logger:
        logger.info(f"[DEBUG] {message} | {extra}")
    else:
        print(f"[DEBUG] {message} | {extra}")


class Debug(commands.Cog):
    """Diagnostic tools for dev/testing only."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="debug", description="Run a full diagnostic check of all cogs/data.")
    async def debug(self, ctx: commands.Context):
        user_id = ctx.author.id

        e = discord.Embed(
            title="🛠 Debug Report",
            description=f"Diagnostics for **{ctx.author.display_name}** ({user_id})",
            color=discord.Color.purple()
        )

        # ---- Profile ----
        prof_cog = self.bot.get_cog("Profile")
        profiles = load_json(PROFILES_FILE, {})
        if prof_cog:
            profile = prof_cog.get_profile(user_id)
            e.add_field(name="👤 Profile", value=f"✅ Loaded | Name: {profile.get('character_name','—')}", inline=False)
        else:
            e.add_field(name="👤 Profile", value="⚠️ Cog not loaded", inline=False)

        # ---- Professions ----
        profs_cog = self.bot.get_cog("Professions")
        if profs_cog:
            mine = profs_cog.get_user_professions(user_id)
            e.add_field(name="🛠 Professions", value=f"✅ {len(mine)} selected", inline=False)
        else:
            e.add_field(name="🛠 Professions", value="⚠️ Cog not loaded", inline=False)

        # ---- Recipes ----
        recipes_cog = self.bot.get_cog("Recipes")
        learned = load_json(LEARNED_FILE, {})
        if recipes_cog:
            mine = recipes_cog.get_user_recipes(user_id)
            total = sum(len(v) for v in mine.values())
            e.add_field(name="📜 Recipes", value=f"✅ {total} learned", inline=False)
        else:
            e.add_field(name="📜 Recipes", value="⚠️ Cog not loaded", inline=False)

        # ---- Market ----
        market_cog = self.bot.get_cog("Market")
        market = load_json(MARKET_FILE, {})
        if market_cog:
            mine = market_cog.get_user_listings(user_id) if hasattr(market_cog, "get_user_listings") else []
            e.add_field(name="💰 Market", value=f"✅ {len(mine)} listings", inline=False)
        else:
            e.add_field(
                name="💰 Market",
                value=f"⚠️ Cog not loaded | {len(market) if isinstance(market, list) else len(market.keys())} raw entries",
                inline=False
            )

        # ---- Trades ----
        trades_cog = self.bot.get_cog("Trades")
        trades = load_json(TRADES_FILE, {})
        if trades_cog:
            mine = trades_cog.get_user_trades(user_id)
            e.add_field(name="📦 Trades", value=f"✅ {len(mine)} trades", inline=False)
        else:
            e.add_field(name="📦 Trades", value=f"⚠️ Cog not loaded | {len(trades)} raw entries", inline=False)

        # ---- Mailbox ----
        mail_cog = self.bot.get_cog("Mailbox")
        mail = load_json(MAILBOX_FILE, {})
        inbox = mail.get(str(user_id), [])
        if mail_cog:
            e.add_field(name="📬 Mailbox", value=f"✅ {len(inbox)} messages", inline=False)
        else:
            e.add_field(name="📬 Mailbox", value=f"⚠️ Cog not loaded | {len(inbox)} raw", inline=False)

        # ---- Registry ----
        reg = load_json(REGISTRY_FILE, {})
        e.add_field(name="📜 Registry", value=f"{len(reg)} recipes tracked", inline=False)

        await ctx.reply(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
