import requests
from bs4 import BeautifulSoup
import json

def scrape_all_recipes(max_pages=100):
    recipes = []
    base = "https://ashescodex.com/artisan/recipe-tracker"
    for page in range(1, max_pages + 1):
        params = {'page': page}
        print(f"Fetching page {page}...")
        r = requests.get(base, params=params)
        if r.status_code != 200:
            print("No more pages or error:", r.status_code)
            break

        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('tbody tr')
        if not rows:
            print("No recipes found on this page; stopping.")
            break

        for tr in rows:
            cols = tr.find_all('td')
            if len(cols) < 3:
                continue
            name_link = cols[1].find('a')
            profession = cols[2].get_text(strip=True)
            level = cols[3].get_text(strip=True) if len(cols) > 3 else ""
            if name_link:
                name = name_link.get_text(strip=True)
                href = name_link.get('href')
                url = f"https://ashescodex.com{href}"
                recipes.append({
                    "name": name,
                    "profession": profession,
                    "level": level,
                    "url": url
                })
        print(f"Page {page}: collected {len(rows)} rows")

    with open('recipes.json', 'w', encoding='utf-8') as f:
        json.dump(recipes, f, indent=4, ensure_ascii=False)
    print(f"Wrote {len(recipes)} recipes to recipes.json")

if __name__ == '__main__':
    scrape_all_recipes()
