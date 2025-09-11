import os
import json
import logging
import discord
from discord.ext import commands
from typing import Dict, List, Tuple, Any
from cogs.hub import refresh_hub
from cogs.professions import PROFESSION_ALIASES

logger = logging.getLogger("AshesBot")

RECIPES_FILE = "data/recipes.json"          # flat or grouped accepted
LEARNED_FILE = "data/learned_recipes.json"  # { user_id: { profession: [ {name, link} ] } }


def _load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _norm_prof(name: str) -> str:
    return PROFESSION_ALIASES.get(name, name)


class Recipes(commands.Cog):
    """
    Accepts FLAT data/recipes.json:
      [{"name": "...", "profession": "Armor Smithing", "level": "0", "url": "https://..."}]
    Or grouped { "Armor Smithing": [ { ... }, ... ] }

    Normalizes into:
      self.recipes_by_prof = { "Armor Smithing": [ {name, url, level}, ... ] }
    """
    def __init__(self, bot):
        self.bot = bot
        self.recipes_by_prof: Dict[str, List[Dict]] = {}
        self._name_index: List[Tuple[str, str, Dict]] = []  # (name_lower, profession, rec)
        self.learned: Dict[str, Dict[str, List[Dict[str, str]]]] = _load_json(LEARNED_FILE, {})
        self._load_and_normalize()

    def _load_and_normalize(self):
        raw = _load_json(RECIPES_FILE, [])
        by_prof: Dict[str, List[Dict]] = {}

        if isinstance(raw, dict):
            # grouped
            for prof, lst in raw.items():
                prof_n = _norm_prof(prof)
                for entry in lst or []:
                    if not isinstance(entry, dict):
                        continue
                    name = str(entry.get("name", "")).strip()
                    if not name:
                        continue
                    level = str(entry.get("level", "")).strip()
                    url = entry.get("url") or entry.get("link") or None
                    by_prof.setdefault(prof_n, []).append({"name": name, "level": level, "url": url})
        elif isinstance(raw, list):
            # flat
            for entry in raw:
                if not isinstance(entry, dict):
                    by_prof.setdefault("Unknown", []).append({"name": str(entry), "level": "", "url": None})
                    continue
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                prof = _norm_prof(str(entry.get("profession", "Unknown")).strip() or "Unknown")
                level = str(entry.get("level", "")).strip()
                url = entry.get("url") or entry.get("link") or None
                by_prof.setdefault(prof, []).append({"name": name, "level": level, "url": url})

        for prof, arr in by_prof.items():
            arr.sort(key=lambda r: r["name"].lower())

        self.recipes_by_prof = dict(sorted(by_prof.items(), key=lambda kv: kv[0].lower()))
        self._name_index = []
        for prof, arr in self.recipes_by_prof.items():
            for rec in arr:
                self._name_index.append((rec["name"].lower(), prof, rec))

        logger.info(f"[recipes] Loaded: {sum(len(v) for v in self.recipes_by_prof.values())} recipes across {len(self.recipes_by_prof)} professions.")

    # ---------- learned storage ----------
    def _ensure_user_prof_bucket(self, user_id: int, profession: str):
        uid = str(user_id)
        if uid not in self.learned:
            self.learned[uid] = {}
        if profession not in self.learned[uid]:
            self.learned[uid][profession] = []

    def get_user_recipes(self, user_id: int) -> Dict[str, List[Dict[str, str]]]:
        return self.learned.get(str(user_id), {})

    def add_learned_recipe(self, user_id: int, profession: str, recipe_name: str, link: str | None):
        profession = _norm_prof(profession)
        self._ensure_user_prof_bucket(user_id, profession)
        bucket = self.learned[str(user_id)][profession]
        if any(r.get("name") == recipe_name for r in bucket):
            return False
        bucket.append({"name": recipe_name, "link": link})
        _save_json(LEARNED_FILE, self.learned)
        return True

    def remove_learned_recipe(self, user_id: int, profession: str, recipe_name: str):
        profession = _norm_prof(profession)
        uid = str(user_id)
        if uid in self.learned and profession in self.learned[uid]:
            before = len(self.learned[uid][profession])
            self.learned[uid][profession] = [r for r in self.learned[uid][profession] if r.get("name") != recipe_name]
            if len(self.learned[uid][profession]) != before:
                _save_json(LEARNED_FILE, self.learned)
                return True
        return False

    # ---------- lookup + search ----------
    def get_recipe_link(self, recipe_name: str) -> str | None:
        name_l = (recipe_name or "").lower()
        if not name_l:
            return None
        for n, _, rec in self._name_index:
            if n == name_l:
                return rec.get("url")
        for n, _, rec in self._name_index:
            if name_l in n:
                return rec.get("url")
        return None

    def search_recipes(self, query: str, professions: List[str] | None = None, limit: int = 25) -> List[Dict]:
        if not query:
            return []
        q = query.lower().strip()
        results: List[Dict] = []

        if professions:
            prof_set = { _norm_prof(p).lower() for p in professions }
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

    # ---------- commands ----------
    @commands.hybrid_command(name="learnrecipe", description="Save a recipe you learned")
    async def learn_recipe_cmd(self, ctx: commands.Context, profession: str, recipe_name: str):
        link = self.get_recipe_link(recipe_name)
        ok = self.add_learned_recipe(ctx.author.id, profession, recipe_name, link)
        if ok:
            await ctx.reply(f"✅ Learned **{recipe_name}** ({_norm_prof(profession)}).", ephemeral=True)
            if getattr(ctx, "interaction", None):
                await refresh_hub(ctx.interaction, ctx.author.id, section="recipes")
                await refresh_hub(ctx.interaction, ctx.author.id, section="profile")
        else:
            await ctx.reply("⚠️ You already learned that recipe.", ephemeral=True)

    @commands.hybrid_command(name="unlearnrecipe", description="Remove a learned recipe")
    async def unlearn_recipe_cmd(self, ctx: commands.Context, profession: str, recipe_name: str):
        ok = self.remove_learned_recipe(ctx.author.id, profession, recipe_name)
        if ok:
            await ctx.reply(f"🗑️ Removed **{recipe_name}** ({_norm_prof(profession)}).", ephemeral=True)
            if getattr(ctx, "interaction", None):
                await refresh_hub(ctx.interaction, ctx.author.id, section="recipes")
                await refresh_hub(ctx.interaction, ctx.author.id, section="profile")
        else:
            await ctx.reply("⚠️ Not found in your learned list.", ephemeral=True)

    @commands.hybrid_command(name="searchrecipe", description="Search the recipe catalog")
    async def search_recipe_cmd(self, ctx: commands.Context, query: str, profession: str | None = None):
        profs = [_norm_prof(profession)] if profession else None
        hits = self.search_recipes(query, professions=profs, limit=25)
        if not hits:
            return await ctx.reply("🔎 No matches.", ephemeral=True)
        lines = []
        for h in hits[:10]:
            lvl = f" (Lv {h['level']})" if h.get("level") else ""
            link = f" — <{h['link']}>" if h.get("link") else ""
            lines.append(f"• **{h['name']}** — *{h['profession']}*{lvl}{link}")
        embed = discord.Embed(title=f"🔎 Results for “{query}”", description="\n".join(lines), color=discord.Color.green())
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Recipes(bot))
