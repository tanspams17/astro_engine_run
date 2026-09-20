# Compatibility Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add compatibility reports (Zodiac $24 / Vedic $30 / Combined $39) as a new standalone product on Arvelos, reusing the existing order/payment/delivery pipeline.

**Architecture:** Extend the existing `orders` table with a `product_type` flag and `partner_*` columns rather than a parallel system. A new `compatibility_engine.py` module does the actual astrological comparison (numerology/zodiac matching + classical Vedic Guna Milan scoring), consumed by `report_generator.py` to produce a new PDF report type. The existing `/api/orders` → `/api/pay` → webhook → `_fulfil` → email/download pipeline is unchanged; it just also handles orders that happen to have partner fields set.

**Tech Stack:** Same as the rest of the backend — FastAPI/Pydantic, SQLite, Jinja2+WeasyPrint for PDFs. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-21-compatibility-reports-design.md`

## Global Constraints

- USD only, Stripe only — no new payment provider, no currency field (per this session's earlier arbitrage fix; compatibility tiers use the same fixed-USD pricing model).
- No accounts/login — compatibility orders are one-time purchases like everything else, accessed by the same download-token pattern.
- Buyer is always one of the two people ("Your details" / "Your Partner's details"), never a third party.
- `name`/`birth_place`-style free text fields must go through the same `autoescape=True` Jinja2 template and the same `max_length` field caps already established this session — the partner's fields are just as much an injection surface as the primary person's.
- **Guna Milan accuracy caveat** (carried from the spec): the 8-koota lookup tables are implemented from the standard published Ashtakoota system, cross-checked against available sources during design, but not independently verified against a canonical Jyotish reference text. Flag this to the user again after implementation — recommend a spot-check against 2-3 known reference charts before this tier is trusted commercially.

---

## Task 1: Database schema + pricing

**Files:**
- Modify: `astro-engine/backend/orders.py`

**Interfaces:**
- Produces: `orders.PRICES` gains `zodiac_compat`, `vedic_compat`, `mixed_compat` keys (USD only). `orders.create_order()` gains a `product_type: str = "individual"` parameter and eight optional `partner_*` parameters. `orders.init_db()` adds the new columns via the existing `ALTER TABLE` migration pattern.

- [ ] **Step 1: Add new columns to the schema and migration**

In `orders.py`, add to the `orders` table's `CREATE TABLE` block in `SCHEMA` (for fresh databases) — insert after the existing `zodiac_insights_opt_in` line:
```sql
    product_type TEXT NOT NULL DEFAULT 'individual',  -- 'individual' | 'compatibility'
    partner_name TEXT,
    partner_birth_date TEXT,
    partner_birth_time TEXT,
    partner_birth_place TEXT,
    partner_lat REAL,
    partner_lon REAL,
    partner_tz TEXT,
    partner_gender TEXT,
```

Then in `init_db()`, extend the existing column-migration loop (for databases that already exist):
```python
def init_db():
    with _conn() as c:
        c.executescript(SCHEMA)
        columns = {row[1] for row in c.execute("PRAGMA table_info(orders)")}
        for column in ("fulfilment_error", "email_error", "phone",
                       "partner_name", "partner_birth_date", "partner_birth_time",
                       "partner_birth_place", "partner_tz", "partner_gender"):
            if column not in columns:
                c.execute(f"ALTER TABLE orders ADD COLUMN {column} TEXT")
        if "zodiac_insights_opt_in" not in columns:
            c.execute("ALTER TABLE orders ADD COLUMN zodiac_insights_opt_in"
                      " INTEGER NOT NULL DEFAULT 0")
        if "product_type" not in columns:
            c.execute("ALTER TABLE orders ADD COLUMN product_type TEXT NOT NULL DEFAULT 'individual'")
        if "partner_lat" not in columns:
            c.execute("ALTER TABLE orders ADD COLUMN partner_lat REAL")
        if "partner_lon" not in columns:
            c.execute("ALTER TABLE orders ADD COLUMN partner_lon REAL")
```

- [ ] **Step 2: Add the three new prices**

In `orders.py`, extend `PRICES`:
```python
PRICES = {  # minor units, fixed at order creation — never recomputed mid-checkout
    "western": {"USD": 1900},
    "vedic": {"USD": 1900},
    "mixed": {"USD": 2900},
    "zodiac_compat": {"USD": 2400},
    "vedic_compat": {"USD": 3000},
    "mixed_compat": {"USD": 3900},
}
```

- [ ] **Step 3: Extend `create_order()` to accept partner fields**

Add parameters and pass them through to the `INSERT`:
```python
def create_order(quiz_session_id: str | None, email: str, name: str,
                 tier: str, currency: str, birth_date: str, birth_time: str,
                 birth_place: str, lat: float, lon: float, tz: str,
                 focus_areas: list[str], marketing_opt_in: bool,
                 gender: str = "unspecified", amount_minor: int | None = None,
                 phone: str | None = None,
                 zodiac_insights_opt_in: bool = False,
                 product_type: str = "individual",
                 partner_name: str | None = None,
                 partner_birth_date: str | None = None,
                 partner_birth_time: str | None = None,
                 partner_birth_place: str | None = None,
                 partner_lat: float | None = None,
                 partner_lon: float | None = None,
                 partner_tz: str | None = None,
                 partner_gender: str | None = None) -> dict:
    if tier not in PRICES:
        raise ValueError(f"unknown tier {tier}")
    if currency not in PRICES[tier]:
        raise ValueError(f"unsupported currency {currency}")
    oid = f"ord_{secrets.token_urlsafe(10)}"
    amount = amount_minor if amount_minor is not None else PRICES[tier][currency]
    if amount < 0:
        raise ValueError("invalid amount")
    with _conn() as c:
        c.execute(
            "INSERT INTO orders (id, quiz_session_id, created_at, email, name,"
            " phone, tier, currency, amount_minor, birth_date, birth_time,"
            " gender, birth_place, lat, lon, tz, focus_areas,"
            " marketing_opt_in, zodiac_insights_opt_in, product_type,"
            " partner_name, partner_birth_date, partner_birth_time,"
            " partner_birth_place, partner_lat, partner_lon, partner_tz,"
            " partner_gender)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, quiz_session_id, _now(), email, name, phone, tier, currency,
             amount, birth_date, birth_time, gender, birth_place, lat, lon,
             tz, ",".join(focus_areas), int(marketing_opt_in),
             int(zodiac_insights_opt_in), product_type,
             partner_name, partner_birth_date, partner_birth_time,
             partner_birth_place, partner_lat, partner_lon, partner_tz,
             partner_gender))
        _upsert_customer(c, email, name, phone, marketing_opt_in,
                         zodiac_insights_opt_in)
    return get_order(oid)
```

- [ ] **Step 4: Verify migration runs cleanly**

Run: `cd astro-engine/backend && ARVELOS_DATA_DIR=/tmp/compat-migration-test python3 -c "import orders; orders.init_db(); print('ok')"`
Expected: prints `ok`, no exceptions. Then: `sqlite3 /tmp/compat-migration-test/arvelos.db ".schema orders"` should show all new columns.

- [ ] **Step 5: Commit**

```bash
git add astro-engine/backend/orders.py
git commit -m "Add compatibility order schema: product_type, partner fields, new tier prices"
```

---

## Task 2: Compatibility engine — Zodiac/numerology comparison

**Files:**
- Create: `astro-engine/backend/compatibility_engine.py`
- Test: `astro-engine/backend/test_compatibility_engine.py`

**Interfaces:**
- Consumes: `numerology.compute_numerology()` (existing), `numerology.FRIENDS` (existing), sign→element/modality maps (currently inline in `report_generator._balance_section` — this task promotes them to module-level constants in `compatibility_engine.py` so both files can use them without duplication).
- Produces: `zodiac_compare(num_a: dict, sun_sign_a: str, num_b: dict, sun_sign_b: str) -> list[dict]` returning report sections (`{"title": str, "body": str}`), same shape `report_generator.py` already uses everywhere.

- [ ] **Step 1: Write the failing test**

Create `astro-engine/backend/test_compatibility_engine.py`:
```python
"""Plain-assert test script (no pytest — matches this repo's existing
lightweight-tooling convention). Run directly: python3 test_compatibility_engine.py"""
import sys

try:
    from . import compatibility_engine as ce
except ImportError:
    import compatibility_engine as ce


def test_zodiac_compare_friendly_numbers():
    num_a = {"mulank": 1, "bhagyank": 3}   # 3 is in FRIENDS[1]
    num_b = {"mulank": 3, "bhagyank": 1}
    sections = ce.zodiac_compare(num_a, "Aries", num_b, "Leo")
    assert any("numerology" in s["title"].lower() for s in sections)
    numerology_section = next(s for s in sections if "numerology" in s["title"].lower())
    assert "harmoni" in numerology_section["body"].lower() or "friend" in numerology_section["body"].lower()


def test_zodiac_compare_same_element():
    num_a = {"mulank": 1, "bhagyank": 1}
    num_b = {"mulank": 1, "bhagyank": 1}
    sections = ce.zodiac_compare(num_a, "Aries", num_b, "Leo")  # both Fire
    zodiac_section = next(s for s in sections if "zodiac" in s["title"].lower())
    assert "fire" in zodiac_section["body"].lower()


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd astro-engine/backend && python3 test_compatibility_engine.py`
Expected: `ModuleNotFoundError: No module named 'compatibility_engine'`

- [ ] **Step 3: Write `compatibility_engine.py` (zodiac/numerology part)**

```python
"""
Compatibility engine — the calculation behind the compatibility report
tiers (zodiac_compat / vedic_compat / mixed_compat). Two independent
halves:

  zodiac_compare()  — numerology "friendly numbers" + zodiac element/
                       modality comparison. Descriptive, not scored —
                       Western tradition doesn't have a compatibility
                       number the way Vedic Guna Milan does.
  guna_milan()       — the classical 8-koota Ashtakoota system, scored
                       out of 36. See the module docstring on guna_milan()
                       for the accuracy caveat.

Both take already-computed chart/numerology data (from chart_engine.py /
numerology.py) for two people — this module does no astronomical
calculation of its own, only comparison.
"""
from __future__ import annotations

try:
    from .numerology import FRIENDS
except ImportError:
    from numerology import FRIENDS

ELEMENTS = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
            "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
            "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
            "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
MODES = {"Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal",
         "Capricorn": "Cardinal", "Taurus": "Fixed", "Leo": "Fixed",
         "Scorpio": "Fixed", "Aquarius": "Fixed", "Gemini": "Mutable",
         "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable"}

# Which elements naturally get along, classically: Fire+Air fan each
# other, Earth+Water nourish each other; same element is inherently
# harmonious; the two "quiet" pairs (Fire+Earth, Air+Water) read as
# more effortful, not incompatible.
ELEMENT_HARMONY = {
    frozenset({"Fire", "Fire"}): "a shared spark — you understand each other's need for momentum instinctively",
    frozenset({"Air", "Air"}): "a shared need for ideas and conversation — rarely a dull moment between you",
    frozenset({"Earth", "Earth"}): "a shared groundedness — stability comes naturally when you're together",
    frozenset({"Water", "Water"}): "a shared emotional depth — you read each other's feelings without needing to ask",
    frozenset({"Fire", "Air"}): "a classically easy pairing — Air feeds Fire, and this relationship tends to energize both of you",
    frozenset({"Earth", "Water"}): "a classically easy pairing — Water nourishes Earth, and this relationship tends to feel steadying for both of you",
    frozenset({"Fire", "Water"}): "a pairing that takes real effort — Fire and Water can put each other out or bring each other to the boil; worth naming rather than ignoring",
    frozenset({"Fire", "Earth"}): "a pairing of different paces — Fire wants to move, Earth wants to build; patience with the difference is the work here",
    frozenset({"Air", "Water"}): "a pairing of different languages — Air processes by talking it through, Water by feeling it through; translation takes practice",
    frozenset({"Air", "Earth"}): "a pairing of different priorities — Air chases ideas, Earth chases results; each has something real to teach the other",
}


def zodiac_compare(num_a: dict, sun_sign_a: str, num_b: dict, sun_sign_b: str) -> list[dict]:
    out = []

    friends_a = FRIENDS[num_a["mulank"]]
    numerology_friendly = (num_b["mulank"] in friends_a
                           or num_b["mulank"] == num_a["mulank"])
    out.append({
        "title": "Numerology — Your Core Numbers",
        "body": (f"Your Mulank is {num_a['mulank']}, theirs is {num_b['mulank']}. "
                 + ("These numbers are traditionally friendly with each other — a "
                    "harmonious pairing that tends to work with less friction than most."
                    if numerology_friendly else
                    "These numbers sit in mild tension in the traditional friend-number "
                    "system — not a red flag, but a pairing that rewards a bit more "
                    "deliberate communication than a naturally friendly pair would need.")),
    })

    elem_a, elem_b = ELEMENTS[sun_sign_a], ELEMENTS[sun_sign_b]
    harmony = ELEMENT_HARMONY[frozenset({elem_a, elem_b})]
    out.append({
        "title": "Zodiac — Elemental Compatibility",
        "body": (f"You're a {sun_sign_a} Sun ({elem_a}), they're a {sun_sign_b} Sun "
                 f"({elem_b}). {harmony.capitalize()}."),
    })

    mode_a, mode_b = MODES[sun_sign_a], MODES[sun_sign_b]
    if mode_a == mode_b:
        mode_text = (f"You're both {mode_a} signs, which means you tend to move through "
                     f"life the same way — {'both natural starters' if mode_a=='Cardinal' else ('both built for the long haul' if mode_a=='Fixed' else 'both comfortable adapting as you go')}. "
                     "Comfortable, though two people pulling the same direction can also mean "
                     "nobody's covering the other approach.")
    else:
        mode_text = (f"You're {mode_a}, they're {mode_b} — different operating rhythms "
                     "that, read well, cover each other's blind spots rather than clash.")
    out.append({"title": "Zodiac — How You Each Move Through Life", "body": mode_text})

    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd astro-engine/backend && python3 test_compatibility_engine.py`
Expected: `PASS test_zodiac_compare_friendly_numbers`, `PASS test_zodiac_compare_same_element`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add astro-engine/backend/compatibility_engine.py astro-engine/backend/test_compatibility_engine.py
git commit -m "Add zodiac/numerology compatibility comparison"
```

---

## Task 3: Compatibility engine — Vedic Guna Milan

**Files:**
- Modify: `astro-engine/backend/compatibility_engine.py`
- Modify: `astro-engine/backend/test_compatibility_engine.py`

**Interfaces:**
- Consumes: `chart_engine.NAKSHATRAS` (existing, 27-item ordered list), `chart_engine.SIGNS` (existing, 12-item ordered list), `chart_engine.VEDIC_SIGN_LORDS` (existing).
- Produces: `guna_milan(moon_sign_a: str, nakshatra_a: str, moon_sign_b: str, moon_sign_b: str) -> dict` returning `{"total": int, "max_total": 36, "kootas": [{"name": str, "score": float, "max": int, "note": str}, ...]}`.

- [ ] **Step 1: Write the failing test**

Append to `test_compatibility_engine.py` (before the `if __name__` block):
```python
def test_guna_milan_same_nakshatra_scores_high():
    # Same nakshatra + same rashi: Varna/Vashya/Yoni/Gana/Nadi degenerate
    # to their same-group cases; total should be well above half of 36.
    result = ce.guna_milan("Aries", "Ashwini", "Aries", "Ashwini")
    assert result["max_total"] == 36
    assert len(result["kootas"]) == 8
    assert sum(k["max"] for k in result["kootas"]) == 36
    assert result["total"] >= 18

def test_guna_milan_nadi_same_group_scores_zero_on_that_koota():
    # Ashwini and Ardra are both classically Aadi/Vata nadi — same nadi
    # is the one koota that scores 0 regardless of anything else.
    result = ce.guna_milan("Aries", "Ashwini", "Gemini", "Ardra")
    nadi = next(k for k in result["kootas"] if k["name"] == "Nadi")
    assert nadi["score"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd astro-engine/backend && python3 test_compatibility_engine.py`
Expected: `FAIL` or `AttributeError: module 'compatibility_engine' has no attribute 'guna_milan'`

- [ ] **Step 3: Add Guna Milan to `compatibility_engine.py`**

Append these tables and the `guna_milan()` function to `compatibility_engine.py`:
```python
try:
    from .chart_engine import NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS
except ImportError:
    from chart_engine import NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS

# ---------------------------------------------------------------- Guna Milan
#
# The classical 8-koota Ashtakoota marriage-matching system, scored out of
# 36. Implemented from the standard published tables (cross-checked against
# available references during design — see the design spec's accuracy
# caveat, carried into this session's report to the user: this should be
# spot-checked against a couple of known reference charts before being
# trusted commercially).
#
# Several classical rules (Varna, Gana, Vashya) are traditionally
# direction-dependent (scored differently for "groom" vs "bride"). This
# product has no gendered framing, so each such koota is scored using the
# more favorable of the two directions — a documented simplification, not
# an oversight.

VARNA = {  # rashi -> varna rank, 4=Brahmin (highest) .. 1=Shudra
    "Cancer": 4, "Scorpio": 4, "Pisces": 4,
    "Aries": 3, "Leo": 3, "Sagittarius": 3,
    "Taurus": 2, "Virgo": 2, "Capricorn": 2,
    "Gemini": 1, "Libra": 1, "Aquarius": 1,
}

VASHYA_GROUP = {  # rashi -> vashya group
    "Aries": "chatushpada", "Taurus": "chatushpada", "Leo": "chatushpada",
    "Gemini": "manava", "Virgo": "manava", "Libra": "manava", "Aquarius": "manava",
    "Cancer": "jalachara", "Pisces": "jalachara",
    "Sagittarius": "manava", "Capricorn": "jalachara",
    "Scorpio": "keeta",
}
# group-pair -> points out of 2 (symmetric)
VASHYA_SCORE = {
    frozenset({"manava"}): 2, frozenset({"chatushpada"}): 2,
    frozenset({"jalachara"}): 2, frozenset({"keeta"}): 2,
    frozenset({"manava", "chatushpada"}): 1, frozenset({"manava", "jalachara"}): 1,
    frozenset({"chatushpada", "jalachara"}): 0.5, frozenset({"keeta", "manava"}): 1,
    frozenset({"keeta", "chatushpada"}): 0, frozenset({"keeta", "jalachara"}): 0.5,
}

GANA = {  # nakshatra -> temperament
    "Ashwini": "Deva", "Mrigashira": "Deva", "Punarvasu": "Deva", "Pushya": "Deva",
    "Hasta": "Deva", "Swati": "Deva", "Anuradha": "Deva", "Shravana": "Deva", "Revati": "Deva",
    "Bharani": "Manushya", "Rohini": "Manushya", "Ardra": "Manushya",
    "Purva Phalguni": "Manushya", "Uttara Phalguni": "Manushya",
    "Purva Ashadha": "Manushya", "Uttara Ashadha": "Manushya",
    "Purva Bhadrapada": "Manushya", "Uttara Bhadrapada": "Manushya",
    "Krittika": "Rakshasa", "Ashlesha": "Rakshasa", "Magha": "Rakshasa",
    "Chitra": "Rakshasa", "Vishakha": "Rakshasa", "Jyeshtha": "Rakshasa",
    "Mula": "Rakshasa", "Dhanishta": "Rakshasa", "Shatabhisha": "Rakshasa",
}
GANA_SCORE = {
    frozenset({"Deva"}): 6, frozenset({"Manushya"}): 6, frozenset({"Rakshasa"}): 6,
    frozenset({"Deva", "Manushya"}): 5,
    frozenset({"Manushya", "Rakshasa"}): 1,
    frozenset({"Deva", "Rakshasa"}): 0,
}

NADI = {  # nakshatra -> constitution group; same group = 0 (Nadi dosha)
    "Ashwini": "Vata", "Ardra": "Vata", "Punarvasu": "Vata", "Uttara Phalguni": "Vata",
    "Hasta": "Vata", "Jyeshtha": "Vata", "Mula": "Vata", "Shatabhisha": "Vata",
    "Purva Bhadrapada": "Vata",
    "Bharani": "Pitta", "Krittika": "Pitta", "Pushya": "Pitta", "Purva Phalguni": "Pitta",
    "Chitra": "Pitta", "Anuradha": "Pitta", "Purva Ashadha": "Pitta", "Dhanishta": "Pitta",
    "Uttara Bhadrapada": "Pitta",
    "Rohini": "Kapha", "Mrigashira": "Kapha", "Ashlesha": "Kapha", "Magha": "Kapha",
    "Swati": "Kapha", "Vishakha": "Kapha", "Uttara Ashadha": "Kapha", "Shravana": "Kapha",
    "Revati": "Kapha",
}

YONI = {  # nakshatra -> animal (14 yonis across 27 nakshatras)
    "Ashwini": "Horse", "Shatabhisha": "Horse",
    "Bharani": "Elephant", "Revati": "Elephant",
    "Krittika": "Sheep", "Pushya": "Sheep",
    "Rohini": "Serpent", "Mrigashira": "Serpent",
    "Ardra": "Dog", "Mula": "Dog",
    "Punarvasu": "Cat", "Ashlesha": "Cat",
    "Magha": "Rat", "Purva Phalguni": "Rat",
    "Uttara Phalguni": "Cow", "Uttara Bhadrapada": "Cow",
    "Hasta": "Buffalo", "Swati": "Buffalo",
    "Chitra": "Tiger", "Vishakha": "Tiger",
    "Anuradha": "Deer", "Jyeshtha": "Deer",
    "Purva Ashadha": "Monkey", "Shravana": "Monkey",
    "Uttara Ashadha": "Mongoose",
    "Dhanishta": "Lion", "Purva Bhadrapada": "Lion",
}
YONI_ENEMIES = {  # classical natural-enemy yoni pairs -> score 0
    frozenset({"Cow", "Tiger"}), frozenset({"Elephant", "Lion"}),
    frozenset({"Horse", "Buffalo"}), frozenset({"Dog", "Deer"}),
    frozenset({"Sheep", "Monkey"}), frozenset({"Serpent", "Mongoose"}),
    frozenset({"Rat", "Cat"}),
}

# Classical planetary friendship (natural, not situational) — Sun/Moon/
# Mars/Jupiter are mutually friendly, Mercury is neutral to most,
# Venus-Saturn are friendly to each other but not to the Sun/Moon axis.
PLANET_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"},
    "Mars": {"Sun", "Moon", "Jupiter"}, "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
}
PLANET_ENEMIES = {
    "Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"},
    "Mercury": {"Moon", "Mars"}, "Jupiter": {"Mercury", "Venus"},
    "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"},
}


def _varna_score(sign_a: str, sign_b: str) -> tuple[float, str]:
    va, vb = VARNA[sign_a], VARNA[sign_b]
    diff = abs(va - vb)
    if diff == 0:
        return 1, "Same varna."
    if diff == 1:
        return 0.5, "Adjacent varna — a mild difference in temperament, not a real mismatch."
    return 0, "A significant varna difference — traditionally the widest caste-temperament gap."


def _vashya_score(sign_a: str, sign_b: str) -> tuple[float, str]:
    ga, gb = VASHYA_GROUP[sign_a], VASHYA_GROUP[sign_b]
    score = VASHYA_SCORE[frozenset({ga, gb})]
    return score, f"{ga.title()} / {gb.title()} vashya groups."


def _tara_score(nak_a: str, nak_b: str) -> tuple[float, str]:
    ia, ib = NAKSHATRAS.index(nak_a), NAKSHATRAS.index(nak_b)
    # Tara category = ((count from one nakshatra to the other, inclusive) - 1) % 9 + 1,
    # simplifies to (index difference % 9) + 1 since 9 divides 27 evenly.
    # Categories 3, 5, 7 (Vipat, Pratyak, Vadha) are the classically inauspicious taras.
    bad = {3, 5, 7}
    d1 = ((ib - ia) % 9) + 1
    d2 = ((ia - ib) % 9) + 1
    good = sum(1 for d in (d1, d2) if d not in bad)
    return (3 if good == 2 else 1.5 if good == 1 else 0), "Based on birth-star distance, both directions."


def _yoni_score(nak_a: str, nak_b: str) -> tuple[float, str]:
    ya, yb = YONI[nak_a], YONI[nak_b]
    if ya == yb:
        return 4, f"Same yoni ({ya})."
    if frozenset({ya, yb}) in YONI_ENEMIES:
        return 0, f"{ya}/{yb} are classically opposed yonis."
    return 2, f"{ya}/{yb} — neutral yoni pairing."


def _graha_maitri_score(sign_a: str, sign_b: str) -> tuple[float, str]:
    lord_a, lord_b = VEDIC_SIGN_LORDS[sign_a], VEDIC_SIGN_LORDS[sign_b]
    if lord_a == lord_b:
        return 5, f"Same rashi lord ({lord_a})."
    a_friend = lord_b in PLANET_FRIENDS.get(lord_a, set())
    b_friend = lord_a in PLANET_FRIENDS.get(lord_b, set())
    a_enemy = lord_b in PLANET_ENEMIES.get(lord_a, set())
    b_enemy = lord_a in PLANET_ENEMIES.get(lord_b, set())
    if a_friend or b_friend:
        return 5, f"Rashi lords {lord_a}/{lord_b} are natural friends."
    if a_enemy and b_enemy:
        return 0, f"Rashi lords {lord_a}/{lord_b} are natural enemies."
    return 3, f"Rashi lords {lord_a}/{lord_b} are neutral."


def _gana_score(nak_a: str, nak_b: str) -> tuple[float, str]:
    ga, gb = GANA[nak_a], GANA[nak_b]
    return GANA_SCORE[frozenset({ga, gb})], f"{ga}/{gb} gana."


def _bhakoot_score(sign_a: str, sign_b: str) -> tuple[float, str]:
    ia, ib = SIGNS.index(sign_a), SIGNS.index(sign_b)
    dist = ((ib - ia) % 12) + 1
    dosha_distances = {2, 12, 6, 8, 5, 9}
    ok = dist not in dosha_distances
    return (7 if ok else 0), f"{dist}th-sign relationship."


def _nadi_score(nak_a: str, nak_b: str) -> tuple[float, str]:
    if NADI[nak_a] == NADI[nak_b]:
        return 0, f"Same nadi ({NADI[nak_a]}) — the one koota Vedic tradition weighs most heavily."
    return 8, f"Different nadi ({NADI[nak_a]}/{NADI[nak_b]})."


def guna_milan(moon_sign_a: str, nakshatra_a: str,
               moon_sign_b: str, nakshatra_b: str) -> dict:
    checks = [
        ("Varna", 1, _varna_score(moon_sign_a, moon_sign_b)),
        ("Vashya", 2, _vashya_score(moon_sign_a, moon_sign_b)),
        ("Tara", 3, _tara_score(nakshatra_a, nakshatra_b)),
        ("Yoni", 4, _yoni_score(nakshatra_a, nakshatra_b)),
        ("Graha Maitri", 5, _graha_maitri_score(moon_sign_a, moon_sign_b)),
        ("Gana", 6, _gana_score(nakshatra_a, nakshatra_b)),
        ("Bhakoot", 7, _bhakoot_score(moon_sign_a, moon_sign_b)),
        ("Nadi", 8, _nadi_score(nakshatra_a, nakshatra_b)),
    ]
    kootas = [{"name": name, "max": max_pts, "score": score, "note": note}
             for name, max_pts, (score, note) in checks]
    return {"total": sum(k["score"] for k in kootas), "max_total": 36, "kootas": kootas}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd astro-engine/backend && python3 test_compatibility_engine.py`
Expected: all 4 tests `PASS`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add astro-engine/backend/compatibility_engine.py astro-engine/backend/test_compatibility_engine.py
git commit -m "Add Vedic Guna Milan (Ashtakoota) compatibility scoring"
```

---

## Task 4: Backend API — accept compatibility orders

**Files:**
- Modify: `astro-engine/backend/app.py`

**Interfaces:**
- Consumes: `orders.create_order()` (extended in Task 1), `orders.PRICES` (extended in Task 1).
- Produces: `OrderIn` accepts optional partner fields; `/api/orders` creates compatibility orders when `tier` is one of the three `*_compat` values.

- [ ] **Step 1: Extend `OrderIn` with partner fields + a validator**

In `app.py`, modify `OrderIn`:
```python
COMPAT_TIERS = {"zodiac_compat", "vedic_compat", "mixed_compat"}


class OrderIn(BaseModel):
    quiz_session_id: str | None = Field(default=None, max_length=64)
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=32)
    tier: str = Field(pattern="^(western|vedic|mixed|zodiac_compat|vedic_compat|mixed_compat)$")
    currency: str = Field(pattern="^USD$")
    coupon_code: str | None = Field(default=None, max_length=40)
    birth_date: str = Field(max_length=10)
    birth_time: str | None = Field(default=None, max_length=5)
    gender: str = Field(default="unspecified", pattern="^(male|female|unspecified)$")
    birth_place: str = Field(max_length=200)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str = Field(max_length=64)
    focus_areas: list[str] = Field(default_factory=list, max_length=8)
    marketing_opt_in: bool = False
    zodiac_insights_opt_in: bool = False

    partner_name: str | None = Field(default=None, min_length=1, max_length=80)
    partner_birth_date: str | None = Field(default=None, max_length=10)
    partner_birth_time: str | None = Field(default=None, max_length=5)
    partner_birth_place: str | None = Field(default=None, max_length=200)
    partner_lat: float | None = Field(default=None, ge=-90, le=90)
    partner_lon: float | None = Field(default=None, ge=-180, le=180)
    partner_tz: str | None = Field(default=None, max_length=64)
    partner_gender: str | None = Field(default="unspecified", pattern="^(male|female|unspecified)$")

    @model_validator(mode="after")
    def _partner_fields_match_tier(self):
        is_compat = self.tier in COMPAT_TIERS
        required = (self.partner_name, self.partner_birth_date, self.partner_birth_place,
                   self.partner_lat, self.partner_lon, self.partner_tz)
        if is_compat and any(v is None for v in required):
            raise ValueError("partner details are required for a compatibility report")
        if not is_compat and any(v is not None for v in required):
            raise ValueError("partner details are only accepted for a compatibility report")
        return self
```

Add `model_validator` to the pydantic import line near the top of `app.py`:
```python
from pydantic import BaseModel, EmailStr, Field, model_validator
```

- [ ] **Step 2: Update `create_order()` endpoint to validate + pass through partner fields**

In `app.py`'s `create_order` endpoint, after the existing birth-date/tz validation block, add the same validation for the partner when present, and pass `product_type`/partner fields to `orders.create_order()`:
```python
@app.post("/api/orders")
def create_order(o: OrderIn):
    try:
        dt.datetime.strptime(
            o.birth_date + " " + (o.birth_time or "12:00"),
            "%Y-%m-%d %H:%M")
        from zoneinfo import ZoneInfo
        ZoneInfo(o.tz)
    except Exception:
        raise HTTPException(400, "invalid birth date/time/timezone")

    is_compat = o.tier in COMPAT_TIERS
    if is_compat:
        try:
            dt.datetime.strptime(
                o.partner_birth_date + " " + (o.partner_birth_time or "12:00"),
                "%Y-%m-%d %H:%M")
            from zoneinfo import ZoneInfo
            ZoneInfo(o.partner_tz)
        except Exception:
            raise HTTPException(400, "invalid partner birth date/time/timezone")

    focus = [f for f in o.focus_areas
             if f in ("personality", "love", "career", "growth")]
    try:
        amount_minor = _apply_coupon(orders.PRICES[o.tier][o.currency], o.coupon_code)
    except ValueError:
        amount_minor = orders.PRICES[o.tier][o.currency]
    order = orders.create_order(
        o.quiz_session_id, o.email, o.name, o.tier, o.currency,
        o.birth_date, o.birth_time or "", o.birth_place, o.lat, o.lon,
        o.tz, focus, o.marketing_opt_in, o.gender,
        amount_minor=amount_minor, phone=o.phone,
        zodiac_insights_opt_in=o.zodiac_insights_opt_in,
        product_type="compatibility" if is_compat else "individual",
        partner_name=o.partner_name, partner_birth_date=o.partner_birth_date,
        partner_birth_time=o.partner_birth_time, partner_birth_place=o.partner_birth_place,
        partner_lat=o.partner_lat, partner_lon=o.partner_lon, partner_tz=o.partner_tz,
        partner_gender=o.partner_gender)
    session = None
    if amount_minor > 0:
        adapter = get_adapter()
        try:
            session = adapter.create_order(order["amount_minor"], order["currency"],
                                           order["tier"], order["email"],
                                           order_id=order["id"])
        except Exception:
            logger.exception("Gateway create_order failed for order %s (%s)",
                             order["id"], order["currency"])
            raise HTTPException(502, "payment gateway unavailable — please try again shortly")
        if session.checkout_url:
            orders.set_payment_session(order["id"], session.session_id)
    return {"order_id": order["id"], "payment_session_id": session.session_id if session else None,
            "amount_minor": order["amount_minor"],
            "currency": order["currency"], "checkout_url": session.checkout_url if session else None}
```

- [ ] **Step 3: Extend `/api/prices` to expose the new tiers (already automatic)**

No code change needed — `/api/prices` already returns `orders.PRICES` directly, which now includes the three new keys from Task 1.

- [ ] **Step 4: Extend `_fulfil()` to call the right report builder**

In `app.py`'s `_fulfil()` function, branch on `order["product_type"]`:
```python
def _fulfil(order_id: str):
    order = orders.get_order(order_id)
    if not order or order["status"] != "paid":
        return
    pdf_path = os.path.join(REPORT_DIR, f"{order_id}.pdf")
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if order.get("product_type") == "compatibility":
            generate_compatibility_report(order, pdf_path)
        else:
            time_known = bool(order["birth_time"])
            birth = dt.datetime.strptime(
                order["birth_date"] + " " + (order["birth_time"] or "12:00"),
                "%Y-%m-%d %H:%M")
            generate_report(
                order["name"], birth, order["tz"], order["birth_place"],
                order["lat"], order["lon"], order["tier"],
                [f for f in order["focus_areas"].split(",") if f], pdf_path,
                time_known=time_known, gender=order.get("gender", "unspecified"))
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise RuntimeError("report generator did not create a PDF")
    except Exception as exc:
        logger.exception("Report generation failed for paid order %s", order_id)
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            orders.mark_fulfilment_failed(order_id, str(exc))
        except Exception:
            logger.exception("Could not record fulfilment failure for order %s", order_id)
        return

    try:
        token = orders.mark_delivered(order_id, pdf_path)
    except Exception:
        logger.exception("Could not mark generated report delivered for order %s", order_id)
        return

    try:
        tier_name = COMPAT_TIER_NAMES[order["tier"]] if order.get("product_type") == "compatibility" else TIER_NAMES[order["tier"]]
        send_report_email(order["email"], order["name"], tier_name, token)
    except Exception as exc:
        logger.exception("Report email delivery failed for order %s", order_id)
        with orders._conn() as connection:
            connection.execute("UPDATE orders SET email_error=? WHERE id=?",
                               (str(exc), order_id))
```

Add the import for `generate_compatibility_report` and `COMPAT_TIER_NAMES` near the top of `app.py`, alongside the existing `report_generator` import:
```python
try:
    from .report_generator import generate_report, TIER_NAMES, generate_compatibility_report, COMPAT_TIER_NAMES
except ImportError:
    from report_generator import generate_report, TIER_NAMES, generate_compatibility_report, COMPAT_TIER_NAMES
```

- [ ] **Step 5: Extend `order_status()` to report the tier correctly for compatibility orders (no change needed)**

`order_status()` already returns `order["tier"]` generically — the frontend already maps tier→label via `TIER_LABEL`, which Task 7 extends. No backend change here.

- [ ] **Step 6: Verify the app still boots and imports cleanly**

Run: `cd astro-engine/backend && python3 -m py_compile app.py orders.py compatibility_engine.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add astro-engine/backend/app.py
git commit -m "Accept compatibility orders through /api/orders"
```

---

## Task 5: GDPR extension

**Files:**
- Modify: `astro-engine/backend/gdpr_tools.py`

**Interfaces:**
- Modifies: `_SCRUB_ORDER_FIELDS` dict (existing).

- [ ] **Step 1: Add partner fields to the scrub set**

In `gdpr_tools.py`:
```python
_SCRUB_ORDER_FIELDS = {
    "name": "[deleted]", "email": "[deleted]", "phone": None, "birth_date": "[deleted]",
    "birth_time": "", "gender": "unspecified", "birth_place": "[deleted]",
    "lat": 0.0, "lon": 0.0, "tz": "UTC", "focus_areas": "",
    "marketing_opt_in": 0, "zodiac_insights_opt_in": 0,
    "download_token": None, "pdf_path": None,
    "partner_name": None, "partner_birth_date": None, "partner_birth_time": None,
    "partner_birth_place": None, "partner_lat": None, "partner_lon": None,
    "partner_tz": None, "partner_gender": None,
}
```

- [ ] **Step 2: Verify**

Run: `cd astro-engine/backend && python3 -m py_compile gdpr_tools.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add astro-engine/backend/gdpr_tools.py
git commit -m "Scrub partner fields on GDPR delete"
```

---

## Task 6: Report generation (PDF)

**Files:**
- Modify: `astro-engine/backend/report_generator.py`
- Create: `astro-engine/pdf_templates/compatibility_report.html`

**Interfaces:**
- Consumes: `compatibility_engine.zodiac_compare()`, `compatibility_engine.guna_milan()` (Tasks 2-3), `numerology.compute_numerology()` (existing), `chart_engine.compute_charts()` (existing, called once per person).
- Produces: `report_generator.generate_compatibility_report(order: dict, out_path: str) -> str`, `report_generator.COMPAT_TIER_NAMES: dict`.

- [ ] **Step 1: Add `COMPAT_TIER_NAMES` and the context builder to `report_generator.py`**

```python
COMPAT_TIER_NAMES = {"zodiac_compat": "Zodiac Compatibility Report",
                     "vedic_compat": "Vedic Compatibility Report",
                     "mixed_compat": "Combined Compatibility Report"}


def build_compatibility_report_context(order: dict) -> dict:
    try:
        from .numerology import compute_numerology
        from .chart_engine import compute_charts
        from .compatibility_engine import zodiac_compare, guna_milan
    except ImportError:
        from numerology import compute_numerology
        from chart_engine import compute_charts
        from compatibility_engine import zodiac_compare, guna_milan

    tier = order["tier"]
    a_birth = dt.datetime.strptime(
        order["birth_date"] + " " + (order["birth_time"] or "12:00"), "%Y-%m-%d %H:%M")
    b_birth = dt.datetime.strptime(
        order["partner_birth_date"] + " " + (order["partner_birth_time"] or "12:00"),
        "%Y-%m-%d %H:%M")

    needs_western = tier in ("zodiac_compat", "mixed_compat")
    needs_vedic = tier in ("vedic_compat", "mixed_compat")
    systems = []
    if needs_western:
        systems.append("western")
    if needs_vedic:
        systems.append("vedic")
    a_charts = compute_charts("mixed" if len(systems) == 2 else systems[0],
                              a_birth, order["tz"], order["lat"], order["lon"])
    b_charts = compute_charts("mixed" if len(systems) == 2 else systems[0],
                              b_birth, order["partner_tz"], order["partner_lat"], order["partner_lon"])

    sections = []

    if needs_western:
        num_a = compute_numerology(order["name"], a_birth.date(), order.get("gender", "unspecified"))
        num_b = compute_numerology(order["partner_name"], b_birth.date(),
                                   order.get("partner_gender", "unspecified"))
        sun_a = a_charts["western"].get("Sun").sign
        sun_b = b_charts["western"].get("Sun").sign
        sections.append({"h1": "Zodiac & Numerology Compatibility", "no": "01"})
        sections += zodiac_compare(num_a, sun_a, num_b, sun_b)

    guna = None
    if needs_vedic:
        vc_a, vc_b = a_charts["vedic"], b_charts["vedic"]
        guna = guna_milan(vc_a.get("Moon").sign, vc_a.moon_nakshatra,
                          vc_b.get("Moon").sign, vc_b.moon_nakshatra)
        sections.append({"h1": "Vedic Guna Milan (Ashtakoota Matching)",
                         "no": "02" if needs_western else "01"})
        sections.append({"guna": guna, "title": "Your Compatibility Score"})
        for k in guna["kootas"]:
            sections.append({"title": f"{k['name']} ({k['score']}/{k['max']})", "body": k["note"]})

    return {
        "tier": tier, "tier_name": COMPAT_TIER_NAMES[tier],
        "name": order["name"], "partner_name": order["partner_name"],
        "generated": dt.date.today().strftime("%d %B %Y"),
        "sections": sections, "guna_summary": guna,
    }


def generate_compatibility_report(order: dict, out_path: str) -> str:
    ctx = build_compatibility_report_context(order)
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    tpl = env.get_template("compatibility_report.html")
    html = tpl.render(**ctx)
    from weasyprint import HTML
    HTML(string=html, base_url=TEMPLATE_DIR).write_pdf(out_path)
    return out_path
```

- [ ] **Step 2: Create the PDF template**

Create `astro-engine/pdf_templates/compatibility_report.html` — reuses the same visual language as `report.html` (same fonts/colors) but a simpler structure:
```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 20mm 18mm; }
  body { font-family: Georgia, serif; color: #241505; }
  .cover { text-align: center; padding-top: 40mm; }
  .cover .brand { font-size: 14pt; letter-spacing: 0.2em; color: #d4920a; text-transform: uppercase; }
  .cover h1 { font-size: 30pt; margin: 8mm 0; }
  .cover .names { font-size: 18pt; color: #5a3c1a; margin-top: 6mm; }
  .cover .sub { font-size: 11pt; color: #7a6a52; margin-top: 4mm; }
  h1.section { font-size: 18pt; color: #5a3c1a; border-bottom: 1pt solid #d4920a; padding-bottom: 3mm; margin-top: 14mm; }
  .section-body { margin: 6mm 0; }
  .section-body h2 { font-size: 13pt; margin-bottom: 2mm; }
  .section-body p { font-size: 10.5pt; line-height: 1.5; }
  .guna-total { text-align: center; font-size: 22pt; color: #d4920a; margin: 8mm 0; }
  .guna-total .max { font-size: 12pt; color: #7a6a52; }
  table.kootas { width: 100%; border-collapse: collapse; margin: 6mm 0; }
  table.kootas th, table.kootas td { border: 0.5pt solid #d9cbb0; padding: 2mm 3mm; font-size: 9.5pt; text-align: left; }
</style>
</head>
<body>
<div class="cover">
  <div class="brand">Arvelos</div>
  <h1>{{ tier_name }}</h1>
  <div class="names">{{ name }} &amp; {{ partner_name }}</div>
  <div class="sub">Prepared {{ generated }}</div>
</div>

{% if guna_summary %}
<h1 class="section">Guna Milan Score</h1>
<div class="guna-total">{{ guna_summary.total }} <span class="max">/ {{ guna_summary.max_total }}</span></div>
<table class="kootas">
  <tr><th>Koota</th><th>Score</th><th>Note</th></tr>
  {% for k in guna_summary.kootas %}
  <tr><td>{{ k.name }}</td><td>{{ k.score }}/{{ k.max }}</td><td>{{ k.note }}</td></tr>
  {% endfor %}
</table>
{% endif %}

{% for s in sections %}
  {% if s.h1 is defined %}
    <h1 class="section">{{ s.h1 }}</h1>
  {% elif s.guna is defined %}
    {# already rendered above #}
  {% else %}
    <div class="section-body">
      {% if s.title %}<h2>{{ s.title }}</h2>{% endif %}
      {% if s.body %}<p>{{ s.body }}</p>{% endif %}
    </div>
  {% endif %}
{% endfor %}

</body>
</html>
```

- [ ] **Step 3: Verify template renders without WeasyPrint (Jinja-only smoke test)**

Run:
```bash
cd astro-engine/backend && python3 -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('../pdf_templates'), autoescape=True)
tpl = env.get_template('compatibility_report.html')
out = tpl.render(tier_name='Combined Compatibility Report', name='<script>alert(1)</script>Alex',
    partner_name='Sam', generated='today', sections=[{'h1':'Test'},{'title':'X','body':'Y'}],
    guna_summary={'total':22,'max_total':36,'kootas':[{'name':'Nadi','score':8,'max':8,'note':'ok'}]})
assert '&lt;script&gt;' in out, 'name not escaped!'
print('PASS: template renders and escapes correctly')
"
```
Expected: `PASS: template renders and escapes correctly`

- [ ] **Step 4: Commit**

```bash
git add astro-engine/backend/report_generator.py astro-engine/pdf_templates/compatibility_report.html
git commit -m "Add compatibility report PDF generation"
```

---

## Task 7: Frontend — new Compatibility section

**Files:**
- Modify: `astro-engine/frontend/index.html`

**Interfaces:**
- Consumes: existing `applyCoupon()`, `scrollIntoViewSettled()`, `showOrderState()`, city-autocomplete helpers (`searchCities`, `selectCity` pattern) — reused for both the primary and partner place fields.

- [ ] **Step 1: Add the pricing cards + two-person form markup**

Insert a new `<section id="compatibility">` after the existing `<section id="order">` closing tag (before `</main>`), following the exact same card/form visual pattern already in the file (reuse `.pricing-grid`, `.price-card`, `.order-layout`, `.card.order-card`, `.field-grid` classes already defined) — three cards (Zodiac $24 / Vedic $30 / Combined $39), and a form with two `.field-grid` blocks labeled "Your details" and "Your Partner's details", each with name/DOB/time/"don't know exact time"/place fields (place fields get their own autocomplete wiring — id-suffixed `_a`/`_b` to avoid collisions with the existing single-person `bplace` input and with each other).

- [ ] **Step 2: Add `TIER_LABEL` entries and wire tier selection**

Extend the existing `TIER_LABEL` map:
```js
const TIER_LABEL = {western:"Western", vedic:"Vedic", mixed:"Mixed",
  zodiac_compat:"Zodiac Compatibility", vedic_compat:"Vedic Compatibility",
  mixed_compat:"Combined Compatibility"};
```

Add a `chooseCompatTier(t)` function mirroring `chooseTier()` but scrolling to the new compatibility form section instead of `#order`, and a `payCompat()` function mirroring `pay()` but reading both field groups and sending the extra `partner_*` fields alongside the existing ones in the `/api/orders` POST body — reusing the exact same request/response handling, `showOrderState()` calls, and `poll()` function already defined (no duplication needed there — `poll()` and delivery/download handling are entirely generic already).

- [ ] **Step 3: Test locally**

Start the app locally (`ARVELOS_DATA_DIR=/tmp/compat-frontend-test ARVELOS_FRONTEND=$(pwd)/../frontend uvicorn app:app --port 8820`), open in the browser tool, click each of the three new compatibility cards, verify the form reveals with both field groups, fill in a test pair of birth details, verify the order posts successfully and a PDF is generated end-to-end using the free coupon path.

- [ ] **Step 4: Commit**

```bash
git add astro-engine/frontend/index.html
git commit -m "Add Compatibility section to the frontend"
```

---

## Task 8: End-to-end verification + regression check

**Files:** none (verification only)

- [ ] **Step 1: Run the unit test script**

Run: `cd astro-engine/backend && python3 test_compatibility_engine.py`
Expected: all tests `PASS`.

- [ ] **Step 2: Negative-test the API** (matching this session's established pattern)

Via curl against a locally running instance: compatibility order missing partner fields → expect `422`; individual order with partner fields present → expect `422`; unknown tier → expect `422`; oversized `partner_birth_place` → expect `422`.

- [ ] **Step 3: Full order→pay→PDF→download flow for all three new tiers**

Using the `ASTRO100` free-coupon path (as used throughout this session), create and pay one order per new tier, poll to `delivered`, download the PDF, confirm it's a valid non-empty PDF containing both names.

- [ ] **Step 4: Regression check the existing single-person flow**

Create and pay one order on each of the original three tiers (western/vedic/mixed), confirm unaffected by this change.

- [ ] **Step 5: GDPR scrub check**

Log a GDPR delete request against one of the test compatibility orders' email, approve it, confirm the partner fields are scrubbed from the row.

---

## Task 9: Deploy

- [ ] **Step 1: Push to `origin/main`**
- [ ] **Step 2: SSH deploy** — `git fetch && git reset --hard origin/main && docker compose up -d --build` (rebuild required — backend files changed)
- [ ] **Step 3: Re-run Task 8's verification against production** (`https://astro.arvelos.cloud`), using real but clearly-test data, then log GDPR delete requests for any test orders created against production, per this session's established practice.
