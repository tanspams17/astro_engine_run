"""
Arvelos numerology engine — Chaldean system (matches the market-standard
'fortune report' calculations: Mulank, Bhagyank, name numbers, Lo Shu grid,
Kua number, personal year/month cycles).
Requires only date of birth + name — no birth time.
"""
from __future__ import annotations

import datetime as dt

CHALDEAN = {
    "A": 1, "I": 1, "J": 1, "Q": 1, "Y": 1,
    "B": 2, "K": 2, "R": 2,
    "C": 3, "G": 3, "L": 3, "S": 3,
    "D": 4, "M": 4, "T": 4,
    "E": 5, "H": 5, "N": 5, "X": 5,
    "U": 6, "V": 6, "W": 6,
    "O": 7, "Z": 7,
    "F": 8, "P": 8,
}
VOWELS = set("AEIOU")
KARMIC_DEBT = {13, 14, 16, 19}

NUMBER_PLANETS = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury",
                  6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}

# friendships between numbers (classical Vedic numerology)
FRIENDS = {1: {1, 2, 3, 5, 6, 9}, 2: {1, 2, 3, 5}, 3: {1, 2, 3, 5, 6, 9},
           4: {1, 5, 6, 7}, 5: {1, 2, 3, 5, 6}, 6: {1, 4, 5, 6, 7},
           7: {1, 4, 5, 6, 7}, 8: {3, 5, 6}, 9: {1, 2, 3, 5, 9}}

LUCKY = {  # per mulank: colours, days, dates-of-month, avoid-numbers
    1: dict(colours="Gold, orange, copper", days="Sunday, Monday",
            dates="1st, 10th, 19th, 28th", avoid="8, 4"),
    2: dict(colours="White, cream, sea-green", days="Monday, Friday",
            dates="2nd, 11th, 20th, 29th", avoid="8, 9"),
    3: dict(colours="Yellow, violet, purple", days="Thursday, Friday",
            dates="3rd, 12th, 21st, 30th", avoid="4, 8"),
    4: dict(colours="Electric blue, grey, khaki", days="Saturday, Sunday",
            dates="4th, 13th, 22nd, 31st", avoid="8, 9"),
    5: dict(colours="Green, light grey, white", days="Wednesday, Friday",
            dates="5th, 14th, 23rd", avoid="none in particular"),
    6: dict(colours="Blue, rose, pink", days="Friday, Thursday",
            dates="6th, 15th, 24th", avoid="4, 8"),
    7: dict(colours="Grey, white, pale green", days="Monday, Sunday",
            dates="7th, 16th, 25th", avoid="2, 8, 9"),
    8: dict(colours="Dark blue, black, purple", days="Saturday",
            dates="8th, 17th, 26th", avoid="1, 2, 9"),
    9: dict(colours="Red, crimson, rose", days="Tuesday, Thursday",
            dates="9th, 18th, 27th", avoid="4, 8"),
}

MANTRAS = {  # planet of the mulank -> beej mantra (transliterated)
    "Sun": "Om Hraam Hreem Hraum Sah Suryaya Namah",
    "Moon": "Om Shraam Shreem Shraum Sah Chandraya Namah",
    "Jupiter": "Om Graam Greem Graum Sah Gurave Namah",
    "Rahu": "Om Bhraam Bhreem Bhraum Sah Rahave Namah",
    "Mercury": "Om Braam Breem Braum Sah Budhaya Namah",
    "Venus": "Om Draam Dreem Draum Sah Shukraya Namah",
    "Ketu": "Om Sraam Sreem Sraum Sah Ketave Namah",
    "Saturn": "Om Praam Preem Praum Sah Shanaye Namah",
    "Mars": "Om Kraam Kreem Kraum Sah Bhaumaya Namah",
}

KUA_DIRECTIONS = {
    1: dict(success="Southeast", health="East", harmony="South", growth="North"),
    2: dict(success="Northeast", health="West", harmony="Northwest", growth="Southwest"),
    3: dict(success="South", health="North", harmony="Southeast", growth="East"),
    4: dict(success="North", health="South", harmony="East", growth="Southeast"),
    6: dict(success="West", health="Northeast", harmony="Southwest", growth="Northwest"),
    7: dict(success="Northwest", health="Southwest", harmony="Northeast", growth="West"),
    8: dict(success="Southwest", health="Northwest", harmony="West", growth="Northeast"),
    9: dict(success="East", health="Southeast", harmony="North", growth="South"),
}

LO_SHU_POSITIONS = {  # number -> (row, col) in classical Lo Shu square
    4: (0, 0), 9: (0, 1), 2: (0, 2),
    3: (1, 0), 5: (1, 1), 7: (1, 2),
    8: (2, 0), 1: (2, 1), 6: (2, 2),
}
LO_SHU_ELEMENT = {1: "Water", 2: "Earth", 3: "Wood", 4: "Wood", 5: "Earth",
                  6: "Metal", 7: "Metal", 8: "Earth", 9: "Fire"}


def reduce_digits(n: int, keep_master: bool = False) -> int:
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def _name_value(name: str, letters: str | None = None) -> int:
    total = 0
    for ch in name.upper():
        if not ch.isalpha():
            continue
        if letters == "vowels" and ch not in VOWELS:
            continue
        if letters == "consonants" and ch in VOWELS:
            continue
        total += CHALDEAN.get(ch, 0)
    return total


def kua_number(year: int, gender: str) -> int:
    y = reduce_digits(sum(int(d) for d in str(year)[-2:]))
    if year < 2000:
        k = 10 - y if gender != "female" else reduce_digits(y + 5)
    else:
        k = 9 - y if gender != "female" else reduce_digits(y + 6)
    if k == 0:
        k = 9
    if k == 5:
        k = 2 if gender != "female" else 8
    return k


def lo_shu_grid(dob: dt.date, mulank: int, bhagyank: int, kua: int) -> dict:
    digits = [int(d) for d in dob.strftime("%d%m%Y")]
    digits = [d for d in digits if d != 0]
    # complete grid: DOB digits + driver/conductor/kua (common practice)
    digits += [mulank, bhagyank, kua]
    counts = {n: digits.count(n) for n in range(1, 10)}
    present = {n: c for n, c in counts.items() if c > 0}
    missing = [n for n, c in counts.items() if c == 0]
    return {"counts": counts, "present": present, "missing": missing}


def personal_year(dob: dt.date, year: int) -> int:
    return reduce_digits(dob.day + dob.month + sum(int(d) for d in str(year)))


def personal_month(dob: dt.date, year: int, month: int) -> int:
    return reduce_digits(personal_year(dob, year) + month)


def compute_numerology(name: str, dob: dt.date,
                       gender: str = "unspecified") -> dict:
    mulank_raw = dob.day
    mulank = reduce_digits(dob.day)
    bhagyank_raw = sum(int(d) for d in dob.strftime("%d%m%Y"))
    bhagyank = reduce_digits(bhagyank_raw)
    # name-derived numbers; fall back to birth numbers for degenerate
    # inputs (e.g. initials with no vowels) so downstream never sees 0
    name_no = reduce_digits(_name_value(name)) or mulank
    soul = reduce_digits(_name_value(name, "vowels")) or bhagyank
    personality = reduce_digits(_name_value(name, "consonants")) or mulank
    kua = kua_number(dob.year, gender)
    grid = lo_shu_grid(dob, mulank, bhagyank, kua)

    karmic = dob.day if dob.day in KARMIC_DEBT else None
    lucky = LUCKY[mulank]
    planet = NUMBER_PLANETS[mulank]

    # friendly/unfriendly numbers for the mulank
    friends = sorted(FRIENDS[mulank])
    name_harmonious = name_no in FRIENDS[mulank] or name_no == mulank

    return {
        "mulank": mulank, "mulank_day": mulank_raw,
        "bhagyank": bhagyank, "name_number": name_no,
        "soul_urge": soul, "personality_number": personality,
        "kua": kua, "kua_directions": KUA_DIRECTIONS[kua],
        "grid": grid, "karmic_debt": karmic,
        "ruling_planet": planet, "mantra": MANTRAS[planet],
        "lucky": lucky, "friend_numbers": friends,
        "name_harmonious": name_harmonious,
    }


def next_12_months(dob: dt.date, start: dt.date | None = None) -> list[dict]:
    """[{year, month, label, personal_month}] for the next 12 calendar months."""
    start = start or dt.date.today()
    out = []
    y, m = start.year, start.month
    for _ in range(12):
        out.append({"year": y, "month": m,
                    "label": dt.date(y, m, 1).strftime("%B %Y"),
                    "pm": personal_month(dob, y, m)})
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out
