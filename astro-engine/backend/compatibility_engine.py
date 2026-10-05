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
    frozenset({"Fire", "Fire"}): "a shared spark: you understand each other's need for momentum instinctively",
    frozenset({"Air", "Air"}): "a shared need for ideas and conversation, with rarely a dull moment between you",
    frozenset({"Earth", "Earth"}): "a shared groundedness, where stability comes naturally when you're together",
    frozenset({"Water", "Water"}): "a shared emotional depth: you read each other's feelings without needing to ask",
    frozenset({"Fire", "Air"}): "a classically easy pairing. Air feeds Fire, and this relationship tends to energize both of you",
    frozenset({"Earth", "Water"}): "a classically easy pairing. Water nourishes Earth, and this relationship tends to feel steadying for both of you",
    frozenset({"Fire", "Water"}): "a pairing that takes real effort. Fire and Water can put each other out or bring each other to the boil, which is worth naming rather than ignoring",
    frozenset({"Fire", "Earth"}): "a pairing of different paces. Fire wants to move, Earth wants to build; patience with the difference is the work here",
    frozenset({"Air", "Water"}): "a pairing of different languages. Air processes by talking it through, Water by feeling it through; translation takes practice",
    frozenset({"Air", "Earth"}): "a pairing of different priorities. Air chases ideas, Earth chases results; each has something real to teach the other",
}


def _article(sign: str) -> str:
    return "an" if sign[0] in "AEIOU" else "a"


# Numeric scoring so the Western side has a headline number of its own,
# the same way Guna Milan does for the Vedic side. Not a classical
# tradition (Western astrology doesn't score compatibility numerically the
# way Vedic matching does) — a transparent, documented point system over
# the same two comparisons already described in prose below.
ELEMENT_SCORE = {
    frozenset({"Fire", "Fire"}): 5, frozenset({"Air", "Air"}): 5,
    frozenset({"Earth", "Earth"}): 5, frozenset({"Water", "Water"}): 5,
    frozenset({"Fire", "Air"}): 4, frozenset({"Earth", "Water"}): 4,
    frozenset({"Fire", "Water"}): 2, frozenset({"Fire", "Earth"}): 2,
    frozenset({"Air", "Water"}): 2, frozenset({"Air", "Earth"}): 2,
}


def zodiac_compare(name_a: str, num_a: dict, sun_sign_a: str,
                   name_b: str, num_b: dict, sun_sign_b: str) -> tuple[list[dict], dict]:
    out = []

    friends_a = FRIENDS[num_a["mulank"]]
    same_mulank = num_b["mulank"] == num_a["mulank"]
    numerology_friendly = same_mulank or num_b["mulank"] in friends_a
    numerology_score = 5 if same_mulank else (4 if numerology_friendly else 2)
    out.append({
        "title": "Numerology: Core Numbers",
        "body": (f"{name_a}'s Mulank is {num_a['mulank']}, {name_b}'s is {num_b['mulank']}. "
                 + ("These numbers are traditionally friendly with each other, a "
                    "harmonious pairing that tends to work with less friction than most."
                    if numerology_friendly else
                    "These numbers sit in mild tension in the traditional friend-number "
                    "system. It isn't a red flag, but the pairing rewards a bit more "
                    "deliberate communication than a naturally friendly pair would need.")),
    })

    elem_a, elem_b = ELEMENTS[sun_sign_a], ELEMENTS[sun_sign_b]
    harmony = ELEMENT_HARMONY[frozenset({elem_a, elem_b})]
    elemental_score = ELEMENT_SCORE[frozenset({elem_a, elem_b})]
    out.append({
        "title": "Zodiac: Elemental Compatibility",
        "body": (f"{name_a} is {_article(sun_sign_a)} {sun_sign_a} Sun ({elem_a}), "
                 f"{name_b} is {_article(sun_sign_b)} {sun_sign_b} Sun ({elem_b}). "
                 f"{harmony[0].upper() + harmony[1:]}."),
    })

    mode_a, mode_b = MODES[sun_sign_a], MODES[sun_sign_b]
    if mode_a == mode_b:
        mode_text = (f"{name_a} and {name_b} are both {mode_a} signs, which means they tend "
                     f"to move through life the same way: "
                     f"{'both natural starters' if mode_a=='Cardinal' else ('both built for the long haul' if mode_a=='Fixed' else 'both comfortable adapting as you go')}. "
                     "Comfortable, though two people pulling the same direction can also mean "
                     "nobody's covering the other approach.")
    else:
        mode_text = (f"{name_a} is {mode_a}, {name_b} is {mode_b}. These are different operating "
                     "rhythms that, read well, cover each other's blind spots rather than clash.")
    out.append({"title": "Zodiac: How They Each Move Through Life", "body": mode_text})

    score = {
        "total": numerology_score + elemental_score, "max": 10,
        "rows": [
            {"label": "Numerology (Mulank)", "value": f"{numerology_score}/5"},
            {"label": "Elemental harmony", "value": f"{elemental_score}/5"},
        ],
    }
    return out, score


# ---------------------------------------------------------------- Guna Milan
#
# The classical 8-koota Ashtakoota system, scored out of 36, using the
# widely published tables. Varna, Vashya, Gana and Yoni are directional, so
# the caller says who is the groom (var) and who the bride (kanya); see
# assign_roles(). Conventions where published sources differ: Vashya uses the
# Astroyogi table, Gana the Saravali matrix, Graha Maitri the 5/4/3/1/0.5/0
# scheme. Cross-checked against an independent open-source implementation
# (see test_compatibility_engine.py).

VARNA = {  # rashi -> varna rank, 4=Brahmin (highest) .. 1=Shudra
    "Cancer": 4, "Scorpio": 4, "Pisces": 4,
    "Aries": 3, "Leo": 3, "Sagittarius": 3,
    "Taurus": 2, "Virgo": 2, "Capricorn": 2,
    "Gemini": 1, "Libra": 1, "Aquarius": 1,
}
VARNA_NAME = {4: "Brahmin", 3: "Kshatriya", 2: "Vaishya", 1: "Shudra"}

VASHYA_ORDER = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
# rows: bride's group, columns: groom's group, in VASHYA_ORDER
VASHYA_MATRIX = [
    [2, 1, 1, 1.5, 1],
    [1, 2, 1.5, 0, 1],
    [1, 1.5, 2, 1, 1],
    [0, 0, 0, 2, 0],
    [1, 1, 1, 0, 2],
]


def _vashya_group(sign: str, sign_degree: float | None) -> str:
    deg = sign_degree or 0.0
    if sign in ("Aries", "Taurus"):
        return "Chatushpada"
    if sign in ("Gemini", "Virgo", "Libra", "Aquarius"):
        return "Manava"
    if sign in ("Cancer", "Pisces"):
        return "Jalachara"
    if sign == "Leo":
        return "Vanachara"
    if sign == "Scorpio":
        return "Keeta"
    if sign == "Sagittarius":
        return "Manava" if deg < 15 else "Chatushpada"
    return "Chatushpada" if deg < 15 else "Jalachara"  # Capricorn


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
GANA_ORDER = ["Deva", "Manushya", "Rakshasa"]
# rows: bride's gana, columns: groom's gana
GANA_MATRIX = [[6, 6, 0], [5, 6, 0], [1, 0, 6]]

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
YONI_ORDER = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat",
              "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
# Symmetric 14x14: 4 same, 3 friendly, 2 neutral, 1 unfriendly, 0 sworn enemies.
YONI_MATRIX = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 1, 3, 2, 1],
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],
    [1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],
]

MAITRI_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
# Symmetric: 5 same/mutual friends, 4 friend+neutral, 3 neutral, 1 friend+enemy,
# 0.5 neutral+enemy, 0 mutual enemies.
MAITRI_MATRIX = [
    [5, 5, 5, 4, 5, 0, 0],
    [5, 5, 4, 1, 4, 0.5, 0.5],
    [5, 4, 5, 0.5, 5, 3, 0.5],
    [4, 1, 0.5, 5, 0.5, 5, 4],
    [5, 4, 5, 0.5, 5, 0.5, 3],
    [0, 0.5, 3, 5, 0.5, 5, 5],
    [0, 0.5, 0.5, 4, 3, 5, 5],
]

NADI_NAME = ["Adi (Vata)", "Madhya (Pitta)", "Antya (Kapha)"]


def _nadi_index(nakshatra: str) -> int:
    # Nadi runs Adi, Madhya, Antya, Antya, Madhya, Adi and repeats every 6 stars.
    return [0, 1, 2, 2, 1, 0][NAKSHATRAS.index(nakshatra) % 6]


def assign_roles(gender_a: str | None, gender_b: str | None) -> tuple[bool, str]:
    """(a_is_groom, basis). Gender decides when it distinguishes the two
    people; otherwise the first person entered is the groom."""
    ga, gb = gender_a or "unspecified", gender_b or "unspecified"
    if ga == "male" and gb != "male":
        return True, "gender"
    if ga == "female" and gb != "female":
        return False, "gender"
    if gb == "male" and ga != "male":
        return False, "gender"
    if gb == "female" and ga != "female":
        return True, "gender"
    return True, "order"


def _varna(groom_sign, bride_sign):
    vg, vb = VARNA[groom_sign], VARNA[bride_sign]
    score = 1 if vg >= vb else 0
    return score, VARNA_NAME[vg], VARNA_NAME[vb]


def _vashya(groom_sign, groom_deg, bride_sign, bride_deg):
    gg, gb = _vashya_group(groom_sign, groom_deg), _vashya_group(bride_sign, bride_deg)
    return VASHYA_MATRIX[VASHYA_ORDER.index(gb)][VASHYA_ORDER.index(gg)], gg, gb


def _tara(groom_nak, bride_nak):
    ig, ib = NAKSHATRAS.index(groom_nak), NAKSHATRAS.index(bride_nak)
    d_bride_to_groom = ((ig - ib) % 9) + 1
    d_groom_to_bride = ((ib - ig) % 9) + 1
    bad = {3, 5, 7}  # Vipat, Pratyak, Vadha
    good = sum(1 for d in (d_bride_to_groom, d_groom_to_bride) if d not in bad)
    return (3 if good == 2 else 1.5 if good == 1 else 0), d_groom_to_bride, d_bride_to_groom


def _yoni(groom_nak, bride_nak):
    yg, yb = YONI[groom_nak], YONI[bride_nak]
    return YONI_MATRIX[YONI_ORDER.index(yb)][YONI_ORDER.index(yg)], yg, yb


def _graha_maitri(groom_sign, bride_sign):
    lg, lb = VEDIC_SIGN_LORDS[groom_sign], VEDIC_SIGN_LORDS[bride_sign]
    return MAITRI_MATRIX[MAITRI_ORDER.index(lb)][MAITRI_ORDER.index(lg)], lg, lb


def _gana(groom_nak, bride_nak):
    gg, gb = GANA[groom_nak], GANA[bride_nak]
    return GANA_MATRIX[GANA_ORDER.index(gb)][GANA_ORDER.index(gg)], gg, gb


def _bhakoot(groom_sign, bride_sign):
    ig, ib = SIGNS.index(groom_sign), SIGNS.index(bride_sign)
    dist = ((ib - ig) % 12) + 1
    # 2/12, 5/9 and 6/8 relationships are the classical Bhakoot dosha.
    return (0 if dist in (2, 12, 5, 9, 6, 8) else 7), dist, ((ig - ib) % 12) + 1


def _nadi(groom_nak, bride_nak):
    ng, nb = _nadi_index(groom_nak), _nadi_index(bride_nak)
    return (0 if ng == nb else 8), NADI_NAME[ng], NADI_NAME[nb]


def guna_milan(moon_sign_a: str, nakshatra_a: str,
               moon_sign_b: str, nakshatra_b: str,
               moon_deg_a: float | None = None, moon_deg_b: float | None = None,
               a_is_groom: bool = True) -> dict:
    """Ashtakoota score for two people. a/b are the two people as entered;
    a_is_groom says which of them takes the groom (var) side."""
    if a_is_groom:
        gs, gn, gd, bs, bn, bd = moon_sign_a, nakshatra_a, moon_deg_a, moon_sign_b, nakshatra_b, moon_deg_b
    else:
        gs, gn, gd, bs, bn, bd = moon_sign_b, nakshatra_b, moon_deg_b, moon_sign_a, nakshatra_a, moon_deg_a
    varna, vg, vb = _varna(gs, bs)
    vashya, ag, ab = _vashya(gs, gd, bs, bd)
    tara, t_gb, t_bg = _tara(gn, bn)
    yoni, yg, yb = _yoni(gn, bn)
    maitri, lg, lb = _graha_maitri(gs, bs)
    gana, nag, nab = _gana(gn, bn)
    bhakoot, d_gb, d_bg = _bhakoot(gs, bs)
    nadi, ng, nb = _nadi(gn, bn)
    rows = [
        ("Varna", 1, varna, vg, vb, f"Groom {vg}, bride {vb}."),
        ("Vashya", 2, vashya, ag, ab, f"Groom {ag}, bride {ab} vashya group."),
        ("Tara", 3, tara, str(t_gb), str(t_bg), "Based on birth-star distance, counted both ways."),
        ("Yoni", 4, yoni, yg, yb, f"Groom {yg}, bride {yb}."),
        ("Graha Maitri", 5, maitri, lg, lb, f"Moon-sign lords: groom {lg}, bride {lb}."),
        ("Gana", 6, gana, nag, nab, f"Groom {nag}, bride {nab} gana."),
        ("Bhakoot", 7, bhakoot, str(d_gb), str(d_bg), f"Moon signs are in a {d_gb}/{d_bg} relationship."),
        ("Nadi", 8, nadi, ng, nb, f"Groom {ng}, bride {nb} nadi."),
    ]
    kootas = [{"name": n, "max": m, "score": sc, "groom": g, "bride": b, "note": note}
              for n, m, sc, g, b, note in rows]
    return {"total": sum(k["score"] for k in kootas), "max_total": 36, "kootas": kootas,
            "a_is_groom": a_is_groom,
            "bhakoot_dosha": bhakoot == 0, "nadi_dosha": nadi == 0}


MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}


def mangal_dosha(mars_sign: str, lagna_sign: str | None, moon_sign: str) -> dict:
    """Standard rule: Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house counted
    from the Lagna (when birth time is known) or from the Moon sign."""
    im = SIGNS.index(mars_sign)
    out = {}
    for label, ref in (("lagna", lagna_sign), ("moon", moon_sign)):
        if ref is None:
            out[label] = None
            continue
        out[label] = ((im - SIGNS.index(ref)) % 12) + 1
    present_l = out["lagna"] in MANGLIK_HOUSES if out["lagna"] else False
    present_m = out["moon"] in MANGLIK_HOUSES
    return {"present": present_l or present_m, "from_lagna": out["lagna"],
            "from_moon": out["moon"], "by_lagna": present_l, "by_moon": present_m}
