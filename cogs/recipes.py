import os
import json
import discord
from discord.ext import commands

RECIPES_FILE = "data/recipes.json"          # your big flat list lives here
LEARNED_FILE = "data/learned_recipes.json"  # { user_id: { profession: [ {name, link} ] } }

# ----------------------------
# Small JSON helpers
# ----------------------------
def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class Recipes(commands.Cog):
    """
    Recipes Cog that accepts a FLAT data/recipes.json:
      [
        {"name": "...", "profession": "Armorsmithing", "level": "0", "url": "https://..."},
        ...
      ]

    We normalize it at load time into:
      self.recipes_by_prof = {
        "Armorsmithing": [ {"name": "...", "url": "...", "level": "0"}, ... ],
        ...
      }

    Learned recipes persist in LEARNED_FILE as:
      { user_id: { profession: [ {"name": "...", "link": "..."} ] } }
    """
    def __init__(self, bot):
        self.bot = bot

        # normalized recipes
        self.recipes_by_prof: dict[str, list[dict]] = {}
        # quick name -> (profession, recipe_dict) index for lookups
        self._name_index: list[tuple[str, str, dict]] = []  # (name_lower, profession, rec)

        # learned storage
        self.learned: dict = _load_json(LEARNED_FILE, {})

        self._load_and_normalize()

    # ----------------------------
    # Load & normalize flat JSON
    # ----------------------------
    def _load_and_normalize(self):
        raw = _load_json(RECIPES_FILE, [])
        by_prof: dict[str, list[dict]] = {}

        # Accept both dict objects and defensive fallbacks
        for entry in raw if isinstance(raw, list) else []:
            if not isinstance(entry, dict):
                # ignore invalid
                continue
            name = str(entry.get("name", "")).strip()
            prof = str(entry.get("profession", "Unknown")).strip() or "Unknown"
            level = str(entry.get("level", "")).strip()
            url = entry.get("url") or entry.get("link") or None
            if not name:
                continue

            by_prof.setdefault(prof, []).append({
                "name": name,
                "level": level,
                "url": url,
            })

        # sort for nicer UX
        for prof, arr in by_prof.items():
            arr.sort(key=lambda r: r["name"].lower())

        self.recipes_by_prof = dict(sorted(by_prof.items(), key=lambda kv: kv[0].lower()))
        # build index
        self._name_index = []
        for prof, arr in self.recipes_by_prof.items():
            for rec in arr:
                self._name_index.append((rec["name"].lower(), prof, rec))

    # ----------------------------
    # Learned helpers
    # ----------------------------
    def _ensure_user_prof_bucket(self, user_id: int, profession: str):
        uid = str(user_id)
        if uid not in self.learned:
            self.learned[uid] = {}
        if profession not in self.learned[uid]:
            self.learned[uid][profession] = []

    def get_user_recipes(self, user_id: int) -> dict:
        return self.learned.get(str(user_id), {})

    def add_learned_recipe(self, user_id: int, profession: str, recipe_name: str, link: str | None):
        self._ensure_user_prof_bucket(user_id, profession)
        bucket = self.learned[str(user_id)][profession]
        if any(r.get("name") == recipe_name for r in bucket):
            return False
        bucket.append({"name": recipe_name, "link": link})
        _save_json(LEARNED_FILE, self.learned)
        return True

    def remove_learned_recipe(self, user_id: int, profession: str, recipe_name: str):
        uid = str(user_id)
        if uid in self.learned and profession in self.learned[uid]:
            before = len(self.learned[uid][profession])
            self.learned[uid][profession] = [r for r in self.learned[uid][profession] if r.get("name") != recipe_name]
            if len(self.learned[uid][profession]) != before:
                _save_json(LEARNED_FILE, self.learned)
                return True
        return False

    # ----------------------------
    # Lookup helpers
    # ----------------------------
    def get_recipe_link(self, recipe_name: str) -> str | None:
        name_l = recipe_name.lower()
        for n, _, rec in self._name_index:
            if n == name_l:
                return rec.get("url")
        # fallback: first partial match
        for n, _, rec in self._name_index:
            if name_l in n:
                return rec.get("url")
        return None

    def search_recipes(self, query: str, professions: list[str] | None = None, limit: int = 25) -> list[dict]:
        """
        Returns: [{name, profession, link, level}]
        - Case-insensitive substring search
        - Optional profession filter
        """
        if not query:
            return []
        q = query.lower().strip()
        results = []

        if professions:
            # filter limited professions first
            prof_set = {p.lower() for p in professions}
            for prof, arr in self.recipes_by_prof.items():
                if prof.lower() not in prof_set:
                    continue
                for rec in arr:
                    if q in rec["name"].lower():
                        results.append({
                            "name": rec["name"],
                            "profession": prof,
                            "link": rec.get("url"),
                            "level": rec.get("level", ""),
                        })
                        if len(results) >= limit:
                            return results
        else:
            # search global index
            for n, prof, rec in self._name_index:
                if q in n:
                    results.append({
                        "name": rec["name"],
                        "profession": prof,
                        "link": rec.get("url"),
                        "level": rec.get("level", ""),
                    })
                    if len(results) >= limit:
                        return results

        return results


# ==========================================================
# Top-level Recipes Menu (buttons)
# ==========================================================
class RecipesMainView(discord.ui.View):
    def __init__(self, recipes_cog: Recipes, user: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

    @discord.ui.button(label="📗 Learn Recipes", style=discord.ButtonStyle.success)
    async def learn_recipes(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(LearnRecipeModal(self.recipes_cog, interaction.user))

    @discord.ui.button(label="📘 Learned Recipes", style=discord.ButtonStyle.primary)
    async def learned_recipes(self, interaction: discord.Interaction, _: discord.ui.Button):
        view = LearnedRecipesView(self.recipes_cog, interaction.user)
        await view.send_embed(interaction)

    @discord.ui.button(label="🔍 Search Recipes", style=discord.ButtonStyle.secondary)
    async def search_recipes(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(SearchRecipeModal(self.recipes_cog))


# ==========================================================
# Learn Recipe: modal -> dropdown (limited to user's professions)
# ==========================================================
class LearnRecipeModal(discord.ui.Modal, title="📗 Learn a Recipe"):
    def __init__(self, recipes_cog: Recipes, user: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

        self.query = discord.ui.TextInput(
            label="Recipe Name",
            placeholder="Partial or full (e.g., 'Dagger')",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        # fetch professions from Professions cog
        prof_cog = interaction.client.get_cog("Professions")
        user_profs = []
        if prof_cog:
            # Expecting list of dicts with "name"
            try:
                user_profs = [p["name"] for p in prof_cog.get_user_professions(self.user.id)]
            except Exception:
                user_profs = []
        if not user_profs:
            return await interaction.response.send_message(
                "⚠️ You need to set your professions first.",
                ephemeral=True
            )

        matches = self.recipes_cog.search_recipes(self.query.value, professions=user_profs, limit=25)
        if not matches:
            return await interaction.response.send_message(
                "⚠️ No matching recipes found within your professions.",
                ephemeral=True
            )

        # Build dropdown (Discord max 25 options)
        options = [
            discord.SelectOption(
                label=m["name"][:100],
                value=m["name"][:100],
                description=(m["profession"][:97] + "...") if len(m["profession"]) > 97 else m["profession"]
            )
            for m in matches[:25]
        ]

        select = discord.ui.Select(placeholder="Select a recipe to learn…", options=options)
        view = discord.ui.View(timeout=120)

        async def on_pick(i: discord.Interaction):
            picked_name = select.values[0]
            # Find chosen entry for profession & link
            chosen = next((m for m in matches if m["name"] == picked_name), None)
            if not chosen:
                return await i.response.send_message("⚠️ Selection not found anymore.", ephemeral=True)

            ok = self.recipes_cog.add_learned_recipe(
                self.user.id, chosen["profession"], chosen["name"], chosen.get("link")
            )
            if ok:
                await i.response.send_message(f"✅ Learned **{chosen['name']}**!", ephemeral=True)
            else:
                await i.response.send_message(f"⚠️ You already learned **{chosen['name']}**.", ephemeral=True)

        select.callback = on_pick
        view.add_item(select)

        await interaction.response.send_message(
            content=f"Found **{len(matches)}** result(s). Pick one:",
            view=view,
            ephemeral=True
        )


# ==========================================================
# Learned Recipes: yours + button to view others
# ==========================================================
class LearnedRecipesView(discord.ui.View):
    def __init__(self, recipes_cog: Recipes, user: discord.Member | discord.User):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.user = user

    async def send_embed(self, interaction: discord.Interaction):
        data = self.recipes_cog.get_user_recipes(self.user.id)

        embed = discord.Embed(
            title=f"📘 {getattr(self.user, 'display_name', self.user.name)}'s Learned Recipes",
            color=discord.Color.blue()
        )

        if not data:
            embed.description = "*You haven’t learned any recipes yet.*"
        else:
            # compact per profession
            for prof, arr in data.items():
                if not arr:
                    continue
                lines = [f"• [{r['name']}]({r.get('link')})" if r.get("link") else f"• {r['name']}" for r in arr]
                # cap the field length to avoid hitting embed limits
                chunk = "\n".join(lines[:20])
                embed.add_field(name=prof, value=chunk or "*None*", inline=False)

        view = discord.ui.View(timeout=None)
        view.add_item(ViewOthersRecipesButton(self.recipes_cog))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ViewOthersRecipesButton(discord.ui.Button):
    def __init__(self, recipes_cog: Recipes):
        super().__init__(label="👥 View Others' Recipes", style=discord.ButtonStyle.secondary)
        self.recipes_cog = recipes_cog

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("⚠️ Guild not found.", ephemeral=True)

        # only show members that actually have learned recipes
        active_ids = []
        for uid, prof_map in (self.recipes_cog.learned or {}).items():
            if any(prof_map.get(p) for p in prof_map.keys()):
                try:
                    active_ids.append(int(uid))
                except ValueError:
                    continue

        options: list[discord.SelectOption] = []
        for uid in sorted(active_ids):
            m = guild.get_member(uid)
            if m and not m.bot:
                label = m.display_name
                options.append(discord.SelectOption(label=label[:100], value=str(uid)))

        if not options:
            return await interaction.response.send_message(
                "⚠️ No guild members have learned recipes yet.",
                ephemeral=True
            )

        select = discord.ui.Select(placeholder="Select a member…", options=options[:25])
        view = discord.ui.View(timeout=120)

        async def on_pick(i: discord.Interaction):
            target_id = int(select.values[0])
            target = guild.get_member(target_id)
            data = self.recipes_cog.get_user_recipes(target_id)

            embed = discord.Embed(
                title=f"📘 {getattr(target, 'display_name', target_id)}'s Learned Recipes",
                color=discord.Color.teal()
            )
            if not data:
                embed.description = "*This player hasn’t learned any recipes yet.*"
            else:
                for prof, arr in data.items():
                    if not arr:
                        continue
                    lines = [f"• [{r['name']}]({r.get('link')})" if r.get("link") else f"• {r['name']}" for r in arr]
                    embed.add_field(name=prof, value="\n".join(lines[:20]) or "*None*", inline=False)

            await i.response.send_message(embed=embed, ephemeral=True)

        select.callback = on_pick
        view.add_item(select)
        await interaction.response.send_message("Choose a member:", view=view, ephemeral=True)


# ==========================================================
# Generic Search Modal (all professions)
# ==========================================================
class SearchRecipeModal(discord.ui.Modal, title="🔍 Search Recipes"):
    def __init__(self, recipes_cog: Recipes):
        super().__init__(timeout=None)
        self.recipes_cog = recipes_cog
        self.query = discord.ui.TextInput(
            label="Search",
            placeholder="e.g., 'Phoenix Cloak'",
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        matches = self.recipes_cog.search_recipes(self.query.value, professions=None, limit=25)

        embed = discord.Embed(
            title=f"🔍 Results for “{self.query.value}”",
            color=discord.Color.purple()
        )

        if not matches:
            embed.description = "No recipes found."
        else:
            for m in matches:
                line = f"**{m['name']}** — *{m['profession']}*"
                if m.get("link"):
                    line += f"\n[Open on Ashes Codex]({m['link']})"
                if m.get("level"):
                    line += f"\nLevel: {m['level']}"
                embed.add_field(name="\u200b", value=line, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================================
# Extension setup
# ==========================================================
async def setup(bot):
    await bot.add_cog(Recipes(bot))
