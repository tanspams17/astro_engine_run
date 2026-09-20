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
    from .chart_engine import NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS
except ImportError:
    from numerology import FRIENDS
    from chart_engine import NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS

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
