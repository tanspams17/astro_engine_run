"""Regenerate the two large binary assets on the server (keeps transfer slim):
cities.json (from geonamescache + vendor/rg_cities1000.csv, both GeoNames-
derived — city data is (c) GeoNames.org, CC BY 4.0, credited in the frontend
footer) and pdf_templates/cover_emblem.png.

cities.json needs one extra build-only dep not used at runtime:
    pip install timezonefinder
"""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- cities.json ---
# Two tiers: a "primary" tier of well-known cities (population >= 15,000, from
# geonamescache, which carries an authoritative timezone) ranked by population
# so common places dedupe cleanly, plus a much larger "secondary" tier (every
# populated place >= 1,000 people in vendor/rg_cities1000.csv, ~144k rows) so
# small towns aren't simply missing from birthplace search. Secondary entries
# get their timezone computed offline via timezonefinder (no live geocoding
# API — avoids depending on a third-party service being reachable/rate-limit-
# safe from every visitor's browser) and are labelled with their state/
# province since collisions are common at this scale (e.g. many "Springfield"s).
import geonamescache
gc = geonamescache.GeonamesCache()
countries = {c['iso']: c['name'] for c in gc.get_countries().values()}
us_states = gc.get_us_states()

primary, seen = [], {}
rows = sorted(gc.get_cities().values(), key=lambda c: -c['population'])
for c in rows:
    if c['population'] < 15000:
        continue
    country = countries.get(c['countrycode'], c['countrycode'])
    base = f"{c['name']}, {country}"
    if base in seen:
        prev = seen[base]
        if c['countrycode'] == 'US' and prev['countrycode'] == 'US' \
           and c.get('admin1code') != prev['admin1code']:
            st, pst = us_states.get(c.get('admin1code'), {}).get('name'), \
                      us_states.get(prev['admin1code'], {}).get('name')
            if st and pst:
                prev['entry']['n'] = f"{prev['name']}, {pst}, {country}"
                entry = {'n': f"{c['name']}, {st}, {country}", 'a': round(c['latitude'], 4),
                         'o': round(c['longitude'], 4), 'z': c['timezone']}
                primary.append(entry)
                seen[entry['n']] = {'entry': entry, 'name': c['name'],
                                     'countrycode': 'US', 'admin1code': c.get('admin1code')}
        continue
    entry = {'n': base, 'a': round(c['latitude'], 4),
              'o': round(c['longitude'], 4), 'z': c['timezone']}
    primary.append(entry)
    seen[base] = {'entry': entry, 'name': c['name'],
                  'countrycode': c['countrycode'], 'admin1code': c.get('admin1code')}
primary_names = {p['n'] for p in primary}
print("cities.json primary tier:", len(primary))

from timezonefinder import TimezoneFinder
tf = TimezoneFinder()
rg_csv = os.path.join(HERE, 'vendor', 'rg_cities1000.csv')
secondary, sec_seen = [], set()
for r in csv.DictReader(open(rg_csv)):
    lat, lon = float(r['lat']), float(r['lon'])
    cc, name, admin1 = r['cc'], r['name'], r['admin1']
    country = countries.get(cc, cc)
    bare = f"{name}, {country}"
    if bare in primary_names:
        continue  # already covered by the authoritative primary-tier entry
    key = (name, admin1, cc)
    if key in sec_seen:
        continue
    sec_seen.add(key)
    tz = tf.timezone_at(lat=lat, lng=lon)
    if not tz:
        continue
    label = f"{name}, {admin1}, {country}" if admin1 else bare
    secondary.append({'n': label, 'a': round(lat, 4), 'o': round(lon, 4), 'z': tz})
print("cities.json secondary tier:", len(secondary))

out = primary + secondary
json.dump(out, open(f"{ROOT}/frontend/cities.json", "w"),
          ensure_ascii=False, separators=(',', ':'))
print("cities.json:", len(out), "cities total")

# --- cover_emblem.png ---
from gen_chakra_v2 import chakra_solid
from gen_emblems_v2 import S
from PIL import Image
chakra_solid().resize((S, S), Image.LANCZOS).save(
    f"{ROOT}/pdf_templates/cover_emblem.png")
print("cover_emblem.png regenerated")
