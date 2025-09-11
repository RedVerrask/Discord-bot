import logging
import discord
from discord.ext import commands
from typing import Dict, List
from cogs.professions import TIER_COLORS
from cogs.hub import refresh_hub  # live hub refresh

log = logging.getLogger("AshesBot")


class Profile(commands.Cog):
    """
    Profiles with dual classes, wishlist, learned recipes preview,
    and live Market sync (own listings + wishlist matches).
    """
    def __init__(self, bot):
        self.bot = bot
        # In-memory for now; migrate to DB later if desired
        self.profiles: Dict[str, Dict] = {}

    # ---------- storage helpers ----------
    def _ensure(self, user_id: int) -> Dict:
        uid = str(user_id)
        if uid not in self.profiles:
            self.profiles[uid] = {
                "class_primary": None,
                "class_secondary": None,
                "bio": None,
                "wishlist": [],
            }
        return self.profiles[uid]

    def get_profile(self, user_id: int) -> Dict:
        return self._ensure(user_id)

    # ---------- API ----------
    def add_wishlist_item(self, user_id: int, text: str) -> bool:
        p = self._ensure(user_id)
        s = (text or "").strip()
        if not s:
            return False
        if s not in p["wishlist"]:
            p["wishlist"].append(s)
            log.info(f"[wishlist] + {s} for {user_id}")
            return True
        return False

    def remove_wishlist_item(self, user_id: int, text: str) -> bool:
        p = self._ensure(user_id)
        before = len(p["wishlist"])
        p["wishlist"] = [t for t in p["wishlist"] if t != text]
        removed = len(p["wishlist"]) != before
        if removed:
            log.info(f"[wishlist] - {text} for {user_id}")
        return removed

    def set_classes(self, user_id: int, primary: str | None, secondary: str | None):
        p = self._ensure(user_id)
        p["class_primary"] = (primary or "").strip() or None
        p["class_secondary"] = (secondary or "").strip() or None
        log.info(f"[classes] {user_id} -> {p['class_primary']} / {p['class_secondary']}")

    # ---------- embed ----------
    def build_profile_embed(self, user: discord.Member | discord.User) -> discord.Embed:
        professions_cog = self.bot.get_cog("Professions")
        recipes_cog = self.bot.get_cog("Recipes")
        market_cog = self.bot.get_cog("Market")

        prof_data = self.get_profile(user.id)
        professions = professions_cog.get_user_professions(user.id) if professions_cog else []
        learned_recipes = recipes_cog.get_user_recipes(user.id) if recipes_cog else {}

        embed = discord.Embed(
            title=f"👤 {getattr(user, 'display_name', user.name)}",
            color=discord.Color.blurple()
        )

        # Classes
        cp = prof_data["class_primary"] or "*Not set*"
        cs = prof_data["class_secondary"] or "*Not set*"
        embed.add_field(name="🎭 Classes", value=f"Primary: **{cp}**\nSecondary: **{cs}**", inline=True)

        # Professions
        if professions:
            lines: List[str] = []
            for p in professions:
                tier = p.get("tier", "1")
                emoji = TIER_COLORS.get(str(tier), "⚪")
                lines.append(f"{emoji} **{p['name']}** (Tier {tier})")
            embed.add_field(name="🛠️ Professions", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="🛠️ Professions", value="*None selected*", inline=False)

        # Wishlist
        wishlist = prof_data["wishlist"]
        wishlist_text = "\n".join([f"• {w}" for w in wishlist]) if wishlist else "*Empty*"
        embed.add_field(name="📜 Wishlist", value=wishlist_text, inline=False)

        # Learned Recipes (compact)
        if learned_recipes:
            chunks = []
            for prof, arr in learned_recipes.items():
                names = ", ".join([r.get("name", "?") for r in arr][:8])
                if names:
                    chunks.append(f"**{prof}**: {names}")
            embed.add_field(name="📘 Learned Recipes", value="\n".join(chunks) or "*None*", inline=False)
        else:
            embed.add_field(name="📘 Learned Recipes", value="*No recipes learned yet*", inline=False)

        # Market (sync)
        if market_cog:
            my_listings = market_cog.get_user_listings(user.id)
            if my_listings:
                rows = []
                for m in my_listings[:8]:
                    rows.append(f"• {m['item']} — {m.get('price_str','?')} | {m['village']}")
                embed.add_field(name="💰 My Market Listings", value="\n".join(rows), inline=False)
            else:
                embed.add_field(name="💰 My Market Listings", value="*No active listings*", inline=False)

            # Wishlist matches
            if wishlist:
                matches = market_cog.find_matches_for_wishlist(wishlist)
                if matches:
                    first = matches[:6]
                    v = "\n".join([f"• {x.get('item','?')} — {x.get('price_str', x.get('price', '?'))} ({x.get('village','?')})" for x in first])
                    embed.add_field(name="🧭 Wishlist Matches on Market", value=v, inline=False)

        embed.set_footer(text="Use /home to navigate.")
        return embed

    # ---------- entry points ----------
    async def open_profile(self, interaction: discord.Interaction, user: discord.Member | discord.User):
        embed = self.build_profile_embed(user)
        await interaction.response.send_message(
            embed=embed,
            view=ProfileMenuView(self, user),
            ephemeral=True
        )


# -------- Views --------
class ProfileMenuView(discord.ui.View):
    def __init__(self, cog: Profile, owner: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.cog = cog
        self.owner = owner

    @discord.ui.button(label="🎭 Set Classes", style=discord.ButtonStyle.primary)
    async def set_classes(self, itx: discord.Interaction, _: discord.ui.Button):
        if itx.user.id != self.owner.id:
            return await itx.response.send_message("⚠️ This menu isn't yours.", ephemeral=True)
        await itx.response.send_modal(SetClassesModal(self.cog, self.owner))

    @discord.ui.button(label="➕ Add to Wishlist", style=discord.ButtonStyle.success)
    async def wish_add(self, itx: discord.Interaction, _: discord.ui.Button):
        if itx.user.id != self.owner.id:
            return await itx.response.send_message("⚠️ This menu isn't yours.", ephemeral=True)
        await itx.response.send_modal(AddWishlistModal(self.cog, self.owner))


# -------- Modals --------
class SetClassesModal(discord.ui.Modal, title="🎭 Set Classes"):
    def __init__(self, cog: Profile, owner: discord.User):
        super().__init__()
        self.cog = cog
        self.owner = owner
        self.primary = discord.ui.TextInput(label="Primary Class", placeholder="e.g., Fighter", required=False, max_length=32)
        self.secondary = discord.ui.TextInput(label="Secondary Class", placeholder="e.g., Rogue", required=False, max_length=32)
        self.add_item(self.primary)
        self.add_item(self.secondary)

    async def on_submit(self, itx: discord.Interaction):
        self.cog.set_classes(self.owner.id, str(self.primary.value or ""), str(self.secondary.value or ""))
        await itx.response.send_message("✅ Classes updated.", ephemeral=True)
        await refresh_hub(itx, self.owner.id, section="profile")


class AddWishlistModal(discord.ui.Modal, title="➕ Add to Wishlist"):
    def __init__(self, cog: Profile, owner: discord.User):
        super().__init__()
        self.cog = cog
        self.owner = owner
        self.item = discord.ui.TextInput(label="Item name", placeholder="Exact or partial is fine", required=True, max_length=100)
        self.add_item(self.item)

    async def on_submit(self, itx: discord.Interaction):
        added = self.cog.add_wishlist_item(self.owner.id, str(self.item.value))
        msg = f"✅ Added **{self.item.value}** to wishlist." if added else "⚠️ It was already on your wishlist."
        await itx.response.send_message(msg, ephemeral=True)
        await refresh_hub(itx, self.owner.id, section="profile")


async def setup(bot):
    await bot.add_cog(Profile(bot))

