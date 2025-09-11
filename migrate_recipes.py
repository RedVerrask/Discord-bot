import json
from collections import defaultdict
from pathlib import Path

# Paths
DATA_DIR = Path("data")
OLD_FILE = DATA_DIR / "recipes.json"
NEW_FILE = DATA_DIR / "recipes_grouped.json"

def migrate_recipes():
    print("🔄 Migrating recipes.json -> recipes_grouped.json ...")

    with open(OLD_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    grouped = defaultdict(list)

    # Group recipes by profession
    for recipe in recipes:
        profession = recipe.get("profession", "Unknown")
        grouped[profession].append({
            "name": recipe["name"],
            "level": recipe["level"],
            "url": recipe["url"]
        })

    # Save grouped recipes
    with open(NEW_FILE, "w", encoding="utf-8") as f:
        json.dump(grouped, f, indent=2, ensure_ascii=False)

    print(f"✅ Migration complete! New file saved as: {NEW_FILE}")

if __name__ == "__main__":
    migrate_recipes()

