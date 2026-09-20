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
