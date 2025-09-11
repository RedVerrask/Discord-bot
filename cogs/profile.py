import logging
import discord
from discord.ext import commands
from cogs.professions import TIER_COLORS

log = logging.getLogger("AshesBot")


class Profile(commands.Cog):
    """
    Profiles with dual classes, wishlist, learned recipes preview,
    and live Market sync (own listings + wishlist matches).
    """
    def __init__(self, bot):
        self.bot = bot
        # In-memory (migrate to DB later)
        self.profiles: dict[str, dict] = {}  # {user_id: {class_primary, class_secondary, bio, wishlist: [..]}}

    # ---------- storage helpers ----------
    def _ensure(self, user_id: int) -> dict:
        uid = str(user_id)
        if uid not in self.profiles:
            self.profiles[uid] = {
                "class_primary": None,
                "class_secondary": None,
                "bio": None,
                "wishlist": [],
            }
        return self.profiles[uid]

    def get_profile(self, user_id: int) -> dict:
        return self._ensure(user_id)

    # ---------- public API ----------
    def add_wishlist_item(self, user_id: int, text: str) -> bool:
        p = self._ensure(user_id)
        text = (text or "").strip()
        if not text:
            return False
        if text not in p["wishlist"]:
            p["wishlist"].append(text)
            log.info(f"[wishlist] + {text} for {user_id}")
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
            lines = []
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

        # Learned Recipes (compact preview)
        if learned_recipes:
            chunks = []
            for prof, arr in learned_recipes.items():
                names = ", ".join([r.get("name", "?") for r in arr][:8])  # cap
                if names:
                    chunks.append(f"**{prof}**: {names}")
            embed.add_field(name="📘 Learned Recipes", value="\n".join(chunks) or "*None*", inline=False)
        else:
            embed.add_field(name="📘 Learned Recipes", value="*No recipes learned yet*", inline=False)

        # Market (sync: live listings)
        if market_cog:
            my_listings = market_cog.get_user_listings(user.id)
            if my_listings:
                rows = []
                for m in my_listings[:8]:
                    rows.append(f"• {m['item']} — {m.get('price_str','?')}  |  {m['village']}")
                embed.add_field(name="💰 My Market Listings", value="\n".join(rows), inline=False)
            else:
                embed.add_field(name="💰 My Market Listings", value="*No active listings*", inline=False)

            # Wishlist matches on market
            if wishlist:
                matches = market_cog.find_matches_for_wishlist(wishlist)
                if matches:
                    first = matches[:6]
                    v = "\n".join([f"• {x['item']} — {x['price_str']}  ({x['village']})" for x in first])
                    embed.add_field(name="🧭 Wishlist Matches on Market", value=v, inline=False)

        embed.set_footer(text="Manage via the buttons below.")
        return embed

    # ---------- entry points ----------
    async def open_profiles_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "📂 **Profiles**",
            view=ProfilesMenuView(self, interaction.user),
            ephemeral=True
        )

    async def open_profile(self, interaction: discord.Interaction, user: discord.Member | discord.User):
        embed = self.build_profile_embed(user)
        await interaction.response.send_message(
            embed=embed,
            view=ProfileMenuView(self, user),
            ephemeral=True
        )


# ============================
# Menu shown when pressing "Profiles" on Home
# ============================
class ProfilesMenuView(discord.ui.View):
    def __init__(self, cog: Profile, user: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.cog = cog
        self.user = user

    @discord.ui.button(label="👤 My Profile", style=discord.ButtonStyle.primary, custom_id="profiles_my")
    async def my_profile(self, itx: discord.Interaction, _: discord.ui.Button):
        await self.cog.open_profile(itx, itx.user)

    @discord.ui.button(label="👥 View Others' Profiles", style=discord.ButtonStyle.secondary, custom_id="profiles_others")
    async def others(self, itx: discord.Interaction, _: discord.ui.Button):
        guild = itx.guild
        if not guild:
            return await itx.response.send_message("⚠️ Guild-only feature.", ephemeral=True)

        recipes = self.cog.bot.get_cog("Recipes")
        market = self.cog.bot.get_cog("Market")

        active_ids: set[int] = set()
        # users who edited profile (classes or wishlist)
        for uid, p in self.cog.profiles.items():
            if p.get("class_primary") or p.get("class_secondary") or p.get("wishlist"):
                active_ids.add(int(uid))

        # users with learned recipes
        if getattr(recipes, "learned", None):
            for uid, rec in recipes.learned.items():
                if rec:
                    active_ids.add(int(uid))

        # users with market listings
        if market:
            for entry in market.market:
                active_ids.add(int(entry["seller_id"]))

        options: list[discord.SelectOption] = []
        for uid in sorted(active_ids):
            m = guild.get_member(uid)
            if m and not m.bot:
                options.append(discord.SelectOption(label=m.display_name, value=str(uid)))

        if not options:
            return await itx.response.send_message("⚠️ Nobody has set up a profile yet.", ephemeral=True)

        select = discord.ui.Select(placeholder="Choose a member…", options=options, custom_id="profiles_others_dd")
        view = discord.ui.View(timeout=None)

        async def on_pick(sitx: discord.Interaction):
            target = guild.get_member(int(select.values[0]))
            if not target:
                return await sitx.response.send_message("⚠️ Member not found.", ephemeral=True)
            embed = self.cog.build_profile_embed(target)
            back = discord.ui.Button(label="⬅ Back to Profiles", style=discord.ButtonStyle.secondary, custom_id="profiles_back")

            async def back_cb(i):
                await self.cog.open_profiles_menu(i)

            back.callback = back_cb
            v2 = discord.ui.View(timeout=None)
            v2.add_item(back)
            await sitx.response.send_message(embed=embed, view=v2, ephemeral=True)

        select.callback = on_pick
        view.add_item(select)
        await itx.response.send_message("Select a member:", view=view, ephemeral=True)


# ============================
# Actions under a profile embed
# ============================
class ProfileMenuView(discord.ui.View):
    def __init__(self, cog: Profile, owner: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.cog = cog
        self.owner = owner

    def _mine(self, user: discord.User) -> bool:
        return user.id == self.owner.id

    @discord.ui.button(label="🎭 Set Classes", style=discord.ButtonStyle.primary, custom_id="profile_set_classes")
    async def set_classes(self, itx: discord.Interaction, _: discord.ui.Button):
        if not self._mine(itx.user):
            return await itx.response.send_message("⚠️ This menu isn't yours.", ephemeral=True)
        await itx.response.send_modal(SetClassesModal(self.cog, self.owner))

    @discord.ui.button(label="➕ Add to Wishlist", style=discord.ButtonStyle.success, custom_id="profile_wish_add")
    async def wish_add(self, itx: discord.Interaction, _: discord.ui.Button):
        if not self._mine(itx.user):
            return await itx.response.send_message("⚠️ This menu isn't yours.", ephemeral=True)
        await itx.response.send_modal(AddWishlistModal(self.cog, self.owner))

    @discord.ui.button(label="🗑️ Remove from Wishlist", style=discord.ButtonStyle.danger, custom_id="profile_wish_del")
    async def wish_del(self, itx: discord.Interaction, _: discord.ui.Button):
        if not self._mine(itx.user):
            return await itx.response.send_message("⚠️ This menu isn't yours.", ephemeral=True)
        prof = self.cog.get_profile(self.owner.id)
        if not prof["wishlist"]:
            return await itx.response.send_message("Your wishlist is empty.", ephemeral=True)

        opts = [discord.SelectOption(label=w, value=w) for w in prof["wishlist"][:25]]
        sel = discord.ui.Select(placeholder="Pick an item to remove…", options=opts, custom_id="profile_wish_del_dd")
        v = discord.ui.View(timeout=None)

        async def del_cb(sitx: discord.Interaction):
            item = sel.values[0]
            removed = self.cog.remove_wishlist_item(self.owner.id, item)
            msg = f"✅ Removed **{item}** from wishlist." if removed else "⚠️ Not found."
            await sitx.response.send_message(msg, ephemeral=True)

        sel.callback = del_cb
        v.add_item(sel)
        await itx.response.send_message(view=v, ephemeral=True)

    @discord.ui.button(label="📫 Mailbox", style=discord.ButtonStyle.secondary, custom_id="profile_mail")
    async def mailbox(self, itx: discord.Interaction, _: discord.ui.Button):
        mbox = self.cog.bot.get_cog("Mailbox")
        if not mbox:
            return await itx.response.send_message("📫 Mailbox is not enabled.", ephemeral=True)
        await mbox.open_mailbox(itx, self.owner.id)


# --------- Modals ----------
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


async def setup(bot):
    await bot.add_cog(Profile(bot))
