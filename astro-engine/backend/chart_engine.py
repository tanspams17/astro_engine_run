"""
Arvelos chart engine.
Swiss Ephemeris wrapper: tropical (Western) + sidereal/Lahiri (Vedic).
Computes planetary placements, houses, aspects, nakshatras, Vimshottari dashas.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo

import swisseph as swe

# ---------------------------------------------------------------- constants

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

WESTERN_PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

# Vedic uses the classical nine grahas
VEDIC_PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
    "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE,  # Ketu derived
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Vimshottari dasha: lord and length in years, keyed by nakshatra index % 9
DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
    ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]
DASHA_TOTAL_YEARS = 120

ASPECTS = [
    ("Conjunction", 0, 8), ("Sextile", 60, 5), ("Square", 90, 7),
    ("Trine", 120, 7), ("Opposition", 180, 8),
]

VEDIC_SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus",
    "Scorpio": "Mars", "Sagittarius": "Jupiter", "Capricorn": "Saturn",
    "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# ---------------------------------------------------------------- dataclasses


@dataclass
class Placement:
    planet: str
    longitude: float          # 0-360 in the relevant zodiac
    sign: str
    sign_degree: float        # degree within sign, 0-30
    house: int
    retrograde: bool
    nakshatra: str | None = None
    nakshatra_pada: int | None = None


@dataclass
class Aspect:
    planet_a: str
    planet_b: str
    aspect: str
    orb: float


@dataclass
class DashaPeriod:
    lord: str
    start: str   # ISO date
    end: str     # ISO date
    current: bool = False


@dataclass
class Chart:
    system: str                      # "western" | "vedic"
    ascendant: Placement | None
    placements: list[Placement]
    house_cusps: list[float]
    aspects: list[Aspect] = field(default_factory=list)
    moon_nakshatra: str | None = None
    moon_nakshatra_pada: int | None = None
    dashas: list[DashaPeriod] = field(default_factory=list)
    ayanamsa: float | None = None

    def to_dict(self):
        return asdict(self)

    def get(self, planet: str) -> Placement | None:
        for p in self.placements:
            if p.planet == planet:
                return p
        return None


# ---------------------------------------------------------------- helpers


def _julian_day_ut(birth_dt_local: dt.datetime, tz_name: str) -> float:
    """Local birth datetime + IANA tz -> Julian day in UT."""
    local = birth_dt_local.replace(tzinfo=ZoneInfo(tz_name))
    ut = local.astimezone(dt.timezone.utc)
    hour = ut.hour + ut.minute / 60 + ut.second / 3600
    return swe.julday(ut.year, ut.month, ut.day, hour)


def _sign_of(lon: float) -> tuple[str, float]:
    idx = int(lon // 30) % 12
    return SIGNS[idx], lon % 30


def _nakshatra_of(sidereal_lon: float) -> tuple[str, int]:
    span = 360 / 27          # 13°20'
    idx = int(sidereal_lon // span) % 27
    pada = int((sidereal_lon % span) // (span / 4)) + 1
    return NAKSHATRAS[idx], pada


def _house_of(lon: float, cusps: list[float]) -> int:
    """House index (1-12) for a longitude given 12 cusps."""
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a <= b:
            if a <= lon < b:
                return i + 1
        else:  # wraps 360
            if lon >= a or lon < b:
                return i + 1
    return 12


def _whole_sign_cusps(asc_lon: float) -> list[float]:
    start = (int(asc_lon // 30) * 30) % 360
    return [(start + 30 * i) % 360 for i in range(12)]


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


# ---------------------------------------------------------------- engine


def compute_western_chart(birth_dt_local: dt.datetime, tz_name: str,
                          lat: float, lon: float) -> Chart:
    jd = _julian_day_ut(birth_dt_local, tz_name)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    cusps, ascmc = swe.houses(jd, lat, lon, b"P")  # Placidus
    asc_lon = ascmc[0]
    cusp_list = list(cusps[:12])

    placements = []
    for name, pid in WESTERN_PLANETS.items():
        pos, _ = swe.calc_ut(jd, pid, flags)
        plon, speed = pos[0], pos[3]
        sign, deg = _sign_of(plon)
        placements.append(Placement(
            planet=name, longitude=plon, sign=sign, sign_degree=deg,
            house=_house_of(plon, cusp_list), retrograde=speed < 0,
        ))

    asc_sign, asc_deg = _sign_of(asc_lon)
    ascendant = Placement(planet="Ascendant", longitude=asc_lon,
                          sign=asc_sign, sign_degree=asc_deg, house=1,
                          retrograde=False)

    aspects = []
    names = list(WESTERN_PLANETS.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pa = next(p for p in placements if p.planet == names[i])
            pb = next(p for p in placements if p.planet == names[j])
            d = _angle_diff(pa.longitude, pb.longitude)
            for aname, angle, orb in ASPECTS:
                if abs(d - angle) <= orb:
                    aspects.append(Aspect(names[i], names[j], aname,
                                          round(abs(d - angle), 2)))
                    break

    return Chart(system="western", ascendant=ascendant,
                 placements=placements, house_cusps=cusp_list,
                 aspects=aspects)


def compute_vedic_chart(birth_dt_local: dt.datetime, tz_name: str,
                        lat: float, lon: float,
                        report_date: dt.date | None = None) -> Chart:
    jd = _julian_day_ut(birth_dt_local, tz_name)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    ayanamsa = swe.get_ayanamsa_ut(jd)

    # sidereal ascendant via tropical asc minus ayanamsa
    _, ascmc = swe.houses(jd, lat, lon, b"P")
    asc_lon = (ascmc[0] - ayanamsa) % 360
    cusp_list = _whole_sign_cusps(asc_lon)  # whole-sign houses

    placements = []
    for name, pid in VEDIC_PLANETS.items():
        pos, _ = swe.calc_ut(jd, pid, flags)
        plon, speed = pos[0] % 360, pos[3]
        sign, deg = _sign_of(plon)
        nak, pada = _nakshatra_of(plon)
        placements.append(Placement(
            planet=name, longitude=plon, sign=sign, sign_degree=deg,
            house=_house_of(plon, cusp_list),
            retrograde=(speed < 0 and name not in ("Sun", "Moon", "Rahu")),
            nakshatra=nak, nakshatra_pada=pada,
        ))
    # Ketu = Rahu + 180
    rahu = next(p for p in placements if p.planet == "Rahu")
    klon = (rahu.longitude + 180) % 360
    ksign, kdeg = _sign_of(klon)
    knak, kpada = _nakshatra_of(klon)
    placements.append(Placement(
        planet="Ketu", longitude=klon, sign=ksign, sign_degree=kdeg,
        house=_house_of(klon, cusp_list), retrograde=False,
        nakshatra=knak, nakshatra_pada=kpada,
    ))

    asc_sign, asc_deg = _sign_of(asc_lon)
    anak, apada = _nakshatra_of(asc_lon)
    ascendant = Placement(planet="Ascendant", longitude=asc_lon,
                          sign=asc_sign, sign_degree=asc_deg, house=1,
                          retrograde=False, nakshatra=anak,
                          nakshatra_pada=apada)

    moon = next(p for p in placements if p.planet == "Moon")
    dashas = _vimshottari_dashas(moon.longitude, birth_dt_local,
                                 report_date or dt.date.today())

    swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)  # reset side effects
    return Chart(system="vedic", ascendant=ascendant, placements=placements,
                 house_cusps=cusp_list,
                 moon_nakshatra=moon.nakshatra,
                 moon_nakshatra_pada=moon.nakshatra_pada,
                 dashas=dashas, ayanamsa=ayanamsa)


def _vimshottari_dashas(moon_sidereal_lon: float,
                        birth_dt_local: dt.datetime,
                        today: dt.date) -> list[DashaPeriod]:
    """Full mahadasha timeline from birth, flagging the current one."""
    span = 360 / 27
    nak_idx = int(moon_sidereal_lon // span) % 27
    frac_elapsed = (moon_sidereal_lon % span) / span

    seq_start = nak_idx % 9
    first_lord, first_years = DASHA_SEQUENCE[seq_start]
    balance_years = first_years * (1 - frac_elapsed)

    YEAR = 365.25
    periods = []
    cursor = birth_dt_local.date()
    end = cursor + dt.timedelta(days=balance_years * YEAR)
    periods.append([first_lord, cursor, end])
    cursor = end
    for k in range(1, 9):
        lord, years = DASHA_SEQUENCE[(seq_start + k) % 9]
        end = cursor + dt.timedelta(days=years * YEAR)
        periods.append([lord, cursor, end])
        cursor = end

    out = []
    for lord, start, end in periods:
        out.append(DashaPeriod(
            lord=lord, start=start.isoformat(), end=end.isoformat(),
            current=(start <= today < end),
        ))
    return out


def monthly_transits(natal_moon_lon_sidereal: float,
                     start: dt.date | None = None) -> list[dict]:
    """Jupiter/Saturn sidereal positions for each of the next 12 months,
    expressed as houses counted from the natal Moon sign, + Sade Sati flag."""
    start = start or dt.date.today()
    moon_sign = int(natal_moon_lon_sidereal // 30) % 12
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    out = []
    y, m = start.year, start.month
    for _ in range(12):
        jd = swe.julday(y, m, 15, 12.0)  # mid-month
        jup = swe.calc_ut(jd, swe.JUPITER, flags)[0][0] % 360
        sat = swe.calc_ut(jd, swe.SATURN, flags)[0][0] % 360
        jup_sign, sat_sign = int(jup // 30), int(sat // 30)
        jup_house = (jup_sign - moon_sign) % 12 + 1
        sat_house = (sat_sign - moon_sign) % 12 + 1
        out.append({
            "year": y, "month": m,
            "jupiter_sign": SIGNS[jup_sign], "jupiter_house": jup_house,
            "saturn_sign": SIGNS[sat_sign], "saturn_house": sat_house,
            "sade_sati": sat_house in (12, 1, 2),
        })
        m += 1
        if m == 13:
            m, y = 1, y + 1
    swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)
    return out


def compute_charts(system: str, birth_dt_local: dt.datetime, tz_name: str,
                   lat: float, lon: float) -> dict[str, Chart]:
    """system: 'western' | 'vedic' | 'mixed'"""
    charts = {}
    if system in ("western", "mixed"):
        charts["western"] = compute_western_chart(
            birth_dt_local, tz_name, lat, lon)
    if system in ("vedic", "mixed"):
        charts["vedic"] = compute_vedic_chart(
            birth_dt_local, tz_name, lat, lon)
    return charts
