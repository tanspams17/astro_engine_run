"""Regenerate the two large binary assets on the server (keeps transfer slim):
cities.json (from geonamescache) and pdf_templates/cover_emblem.png."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- cities.json ---
import geonamescache
gc = geonamescache.GeonamesCache()
countries = {c['iso']: c['name'] for c in gc.get_countries().values()}
out, seen = [], set()
rows = sorted(gc.get_cities().values(), key=lambda c: -c['population'])
for c in rows:
    if c['population'] < 15000:
        continue
    n = f"{c['name']}, {countries.get(c['countrycode'], c['countrycode'])}"
    if n in seen:
        continue
    seen.add(n)
    out.append({'n': n, 'a': round(c['latitude'], 4),
                'o': round(c['longitude'], 4), 'z': c['timezone']})
json.dump(out, open(f"{ROOT}/frontend/cities.json", "w"),
          ensure_ascii=False, separators=(',', ':'))
print("cities.json:", len(out), "cities")

# --- cover_emblem.png ---
from gen_chakra_v2 import chakra_solid
from gen_emblems_v2 import S
from PIL import Image
chakra_solid().resize((S, S), Image.LANCZOS).save(
    f"{ROOT}/pdf_templates/cover_emblem.png")
print("cover_emblem.png regenerated")
