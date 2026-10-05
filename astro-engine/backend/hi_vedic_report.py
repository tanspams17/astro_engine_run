"""Hindi Vedic Kundli report (tier `vedic`): context builder and PDF render.
Calculation is shared with the English report; the content is native Hindi."""
from __future__ import annotations

import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

try:
    from . import hi_glossary as hg, hi_profiles as hp, hi_vedic_text as vt
    from . import compatibility_engine as ce
    from .chart_engine import compute_charts, monthly_transits, SIGNS, NAKSHATRAS, VEDIC_SIGN_LORDS
except ImportError:
    import hi_glossary as hg, hi_profiles as hp, hi_vedic_text as vt
    import compatibility_engine as ce
    from chart_engine import compute_charts, monthly_transits, SIGNS, NAKSHATRAS, VEDIC_SIGN_LORDS

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "pdf_templates")
ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
ABBR = {"Sun": "सू", "Moon": "चं", "Mars": "मं", "Mercury": "बु", "Jupiter": "गु",
        "Venus": "शु", "Saturn": "श", "Rahu": "रा", "Ketu": "के"}
FIRE, EARTH, AIR, WATER = (0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)


def navamsa_sign(longitude: float) -> int:
    """Navamsa (D9) sign index: nine parts of 3°20' per sign, counted from
    Aries for fire signs, Capricorn for earth, Libra for air, Cancer for water."""
    sign = int(longitude // 30) % 12
    part = int((longitude % 30) // (30 / 9))
    start = 0 if sign in FIRE else 9 if sign in EARTH else 6 if sign in AIR else 3
    return (start + part) % 12


_HC = [(.5, .25), (.25, .12), (.10, .25), (.25, .5), (.10, .75), (.25, .88),
       (.5, .75), (.75, .88), (.90, .75), (.75, .5), (.90, .25), (.75, .12)]
_S = 70  # chart edge in mm


def html_north_chart(base_idx: int, placed: list) -> str:
    """North Indian diamond chart. Lines are SVG; labels are HTML because
    WeasyPrint's SVG text mis-shapes Devanagari vowel signs."""
    by_house: dict[int, list[str]] = {}
    for planet, si in placed:
        by_house.setdefault((si - base_idx) % 12, []).append(ABBR[planet])
    line = 'stroke="#43277a" stroke-width="1.5" fill="none"'
    svg = ('<svg viewBox="0 0 420 420" xmlns="http://www.w3.org/2000/svg">'
           '<rect x="4" y="4" width="412" height="412" fill="#f6f3fc" stroke="#c9b458" stroke-width="3"/>'
           f'<rect x="12" y="12" width="396" height="396" {line}/>'
           f'<line x1="12" y1="12" x2="408" y2="408" {line}/><line x1="408" y1="12" x2="12" y2="408" {line}/>'
           f'<polygon points="210,12 408,210 210,408 12,210" {line}/></svg>')
    cells = []
    for h in range(12):
        cx, cy = _HC[h][0] * _S, _HC[h][1] * _S
        left, top = cx - 10, cy - 6.5 + (3.2 if _HC[h][1] < 0.2 else 0)
        names = " ".join(by_house.get(h, []))
        cells.append(f'<div class="hc" style="left:{left:.1f}mm;top:{top:.1f}mm">'
                     f'<span class="sn">{(base_idx + h) % 12 + 1}</span><br>{names}</div>')
    return f'<div class="nchart">{svg}{"".join(cells)}</div>'


def _dignity(planet: str, sign: str) -> str:
    if EXALT.get(planet) == sign:
        return "exalted"
    if DEBIL.get(planet) == sign:
        return "debilitated"
    if sign in vt.OWN.get(planet, []):
        return "own"
    return "neutral"


EXALT, DEBIL = vt.EXALT, vt.DEBIL


def _deg(d: float) -> str:
    return f"{int(d)}° {int((d % 1) * 60):02d}′"


def build_context(name: str, birth: dt.datetime, tz: str, place: str, lat: float,
                  lon: float, time_known: bool = True) -> dict:
    vc = compute_charts("vedic", birth, tz, lat, lon)["vedic"]
    moon = vc.get("Moon")
    base_idx = int(vc.ascendant.longitude // 30) if time_known else int(moon.longitude // 30)
    base_sign = SIGNS[base_idx]

    pl = {}
    for p in vc.placements:
        if p.planet not in ORDER:
            continue
        si = int(p.longitude // 30) % 12
        pl[p.planet] = {"p": p, "sign": SIGNS[si], "si": si, "house": (si - base_idx) % 12 + 1,
                        "dig": _dignity(p.planet, SIGNS[si])}

    def hi_sign(s):
        return hg.SIGNS[s]

    # ---------------- planet table + planet sections
    table, planets = [], []
    for name_en in ORDER:
        d = pl[name_en]
        p = d["p"]
        status = [vt.DIGNITY_LABEL[d["dig"]]] if d["dig"] != "neutral" else []
        if p.retrograde:
            status.append("वक्री")
        table.append({"planet": hg.PLANETS[name_en], "sign": hi_sign(d["sign"]), "deg": _deg(p.sign_degree),
                      "house": d["house"], "nak": f"{hg.NAKSHATRAS[p.nakshatra]} ({p.nakshatra_pada})",
                      "status": ", ".join(status)})
        elem, mode = vt.SIGN_ELEMENT[d["sign"]], vt.SIGN_MODE[d["sign"]]
        paras = [vt.PLANET[name_en][0],
                 f"{hg.PLANETS[name_en]} आपकी कुंडली में {hi_sign(d['sign'])} राशि में, {hg.NAKSHATRAS[p.nakshatra]} नक्षत्र के पद {p.nakshatra_pada} में और {vt.ORD_SHORT[d['house']]} भाव में स्थित है। "
                 f"{hi_sign(d['sign'])} {elem} तत्व की राशि है, जो {vt.ELEMENT[elem]} से जुड़ी है, और {vt.MODE[mode]} {mode} प्रकृति की मानी जाती है। "
                 f"{vt.BHAVA[d['house']][2]} से जुड़े क्षेत्र इस ग्रह के कारकत्व ({vt.PLANET[name_en][1]}) से रंगे रहते हैं।"]
        if vt.DIGNITY_TEXT[d["dig"]]:
            paras.append(vt.DIGNITY_TEXT[d["dig"]])
        if p.retrograde:
            paras.append(vt.RETRO_TEXT)
        planets.append({
            "title": f"{hg.PLANETS[name_en]}: {hi_sign(d['sign'])}, {vt.ORD_SHORT[d['house']]} भाव",
            "paras": paras,
            "easy": f"{hg.PLANETS[name_en]} {vt.PLANET[name_en][1]} का ग्रह है, और आपके यहाँ यह {vt.BHAVA[d['house']][2]} वाले क्षेत्र में काम करता है.".replace("है.", "है।"),
        })

    # ---------------- houses
    houses = []
    for i in range(1, 13):
        si = (base_idx + i - 1) % 12
        sign = SIGNS[si]
        lord = VEDIC_SIGN_LORDS[sign]
        j = pl[lord]["house"]
        occupants = [n for n in ORDER if pl[n]["house"] == i]
        bname, theme, short = vt.BHAVA[i]
        if occupants:
            occ = f"इस भाव में {', '.join(hg.PLANETS[n] for n in occupants)} स्थित हैं। " + " ".join(
                f"{hg.PLANETS[n]} ({vt.PLANET[n][1]}) के विषय इस भाव के क्षेत्र में सक्रिय रहते हैं।" for n in occupants)
        else:
            occ = "इस भाव में कोई ग्रह स्थित नहीं है; फल मुख्यतः भाव-स्वामी की स्थिति से देखा जाता है।"
        if j == i:
            lord_text = f"इस भाव के स्वामी {hg.PLANETS[lord]} स्वयं इसी भाव में स्थित हैं, जो इस भाव के विषयों को बल देने वाली स्थिति मानी जाती है।"
        else:
            lord_text = (f"इस भाव के स्वामी {hg.PLANETS[lord]} {vt.ORD_SHORT[j]} भाव ({hi_sign(pl[lord]['sign'])}) में स्थित हैं, "
                         f"जो {vt.BHAVA[j][2]} से संबंधित है। इसलिए {short} के विषयों में {vt.BHAVA[j][2]} की भूमिका दिखाई देती है।")
        extra = vt.HOUSE_CATEGORY[vt.HOUSE_KIND[j]]
        if vt.DIGNITY_TEXT[pl[lord]["dig"]]:
            extra += " " + vt.DIGNITY_TEXT[pl[lord]["dig"]]
        houses.append({
            "title": f"{vt.ORD[i]} भाव: {bname}",
            "meta": f"राशि: {hi_sign(sign)} · भाव स्वामी: {hg.PLANETS[lord]}",
            "paras": [theme, occ, lord_text + " " + extra],
            "easy": f"{short} की चाबी {hg.PLANETS[lord]} के हाथ में है, जो आपके {vt.BHAVA[j][2]} वाले क्षेत्र में बैठे हैं।",
        })

    # ---------------- charts
    place_list = [(n, pl[n]["si"]) for n in ORDER]
    chart_main = html_north_chart(base_idx, place_list)
    nav_base = navamsa_sign(vc.ascendant.longitude if time_known else moon.longitude)
    chart_nav = html_north_chart(nav_base, [(n, navamsa_sign(pl[n]["p"].longitude)) for n in ORDER])

    # ---------------- dasha
    today = dt.date.today()
    bd = birth.date()
    dasha_rows, current, nxt = [], None, None
    for k, d in enumerate(vc.dashas):
        s, e = dt.date.fromisoformat(d.start), dt.date.fromisoformat(d.end)
        dasha_rows.append({"lord": hg.PLANETS[d.lord], "start": hg.hi_date(s), "end": hg.hi_date(e),
                           "years": round((e - s).days / 365.25, 1),
                           "age": f"{int((s - bd).days / 365.25)} से {int((e - bd).days / 365.25)} वर्ष",
                           "current": d.current})
        if d.current:
            current = d
            if k + 1 < len(vc.dashas):
                nxt = vc.dashas[k + 1]
    dasha_now, dasha_next = [], []
    if current:
        cl = current.lord
        dasha_now = [vt.DASHA_NOW.format(lord=hg.PLANETS[cl], end=hg.hi_date(dt.date.fromisoformat(current.end))),
                     vt.DASHA_LONG[cl],
                     f"आपकी कुंडली में {hg.PLANETS[cl]} {hi_sign(pl[cl]['sign'])} राशि में, {vt.ORD_SHORT[pl[cl]['house']]} भाव में स्थित हैं; "
                     f"इसलिए इस काल में {vt.BHAVA[pl[cl]['house']][2]} के क्षेत्र विशेष रूप से सक्रिय रहते हैं।"]
    if nxt:
        dasha_now.append(vt.DASHA_NEXT.format(lord=hg.PLANETS[nxt.lord], start=hg.hi_date(dt.date.fromisoformat(nxt.start))))

    # ---------------- special: mangal + sade sati
    mars = pl["Mars"]
    md = ce.mangal_dosha(mars["sign"], base_sign if time_known else None, moon_sign := SIGNS[pl["Moon"]["si"]])
    where = []
    if md["by_lagna"]:
        where.append(f"लग्न से {vt.ORD_SHORT[md['from_lagna']]} भाव में")
    if md["by_moon"]:
        where.append(f"चंद्र राशि से {vt.ORD_SHORT[md['from_moon']]} भाव में")
    mangal_text = vt.MANGAL_PRESENT.format(where=" और ".join(where)) if md["present"] else vt.MANGAL_ABSENT
    tr = monthly_transits(moon.longitude)[0]
    sh = tr["saturn_house"]
    sade_text = vt.SADE_SATI.get(sh) or vt.DHAIYA.get(sh) or vt.SADE_NONE

    # ---------------- remedies
    seen, remedies = set(), []
    focus = []
    if time_known:
        focus.append(("लग्न स्वामी", VEDIC_SIGN_LORDS[base_sign]))
    focus.append(("चंद्र राशि स्वामी", VEDIC_SIGN_LORDS[moon_sign]))
    if current:
        focus.append(("वर्तमान महादशा स्वामी", current.lord))
    for why, pn in focus:
        if pn in seen:
            continue
        seen.add(pn)
        mantra, day, dana, practice = vt.REMEDY[pn]
        remedies.append({"why": why, "planet": hg.PLANETS[pn], "mantra": mantra, "day": day, "dana": dana, "practice": practice})

    nak = vc.moon_nakshatra
    lagna_hi = hg.SIGNS[base_sign] if time_known else "ज्ञात नहीं"
    kv = [("नाम", name), ("जन्म तिथि", hg.hi_date(birth)),
          ("जन्म समय", birth.strftime("%H:%M") if time_known else "ज्ञात नहीं"), ("जन्म स्थान", place),
          ("लग्न", lagna_hi), ("चंद्र राशि", hg.SIGNS[moon_sign]), ("राशि स्वामी", hg.PLANETS[VEDIC_SIGN_LORDS[moon_sign]]),
          ("जन्म नक्षत्र (पद)", f"{hg.NAKSHATRAS[nak]} ({vc.moon_nakshatra_pada})"),
          ("नक्षत्र स्वामी", hg.PLANETS[hp.NAKSHATRA_LORD_ORDER[NAKSHATRAS.index(nak) % 9]]),
          ("सूर्य राशि (निरयन)", hg.SIGNS[pl["Sun"]["sign"]]),
          ("वर्तमान महादशा", hg.PLANETS[current.lord] if current else "")]

    return {
        "name": name, "generated": hg.hi_date(today), "time_known": time_known,
        "birth_line": f"{hg.hi_date(birth)}" + (f", {birth.strftime('%H:%M')}" if time_known else "") + f", {place}",
        "bigthree": " · ".join(([f"{lagna_hi} लग्न"] if time_known else []) +
                               [f"{hg.SIGNS[moon_sign]} चंद्र राशि", f"{hg.NAKSHATRAS[nak]} नक्षत्र"]),
        "intro": vt.INTRO, "time_note": "" if time_known else vt.TIME_UNKNOWN,
        "kv": kv, "chart_main": chart_main, "chart_nav": chart_nav,
        "chart_main_title": "लग्न कुंडली" if time_known else "चंद्र कुंडली (चंद्र राशि को लग्न मानकर)",
        "chart_help": vt.CHART_HELP, "chart_abbr": vt.CHART_ABBR_NOTE, "nav_note": vt.NAVAMSA_NOTE,
        "chart_everyday": vt.EVERYDAY_CHART, "table": table, "table_note": vt.TABLE_NOTE,
        "houses": houses, "planets": planets,
        "dasha_intro": vt.DASHA_INTRO, "dasha_rows": dasha_rows, "dasha_now": dasha_now, "dasha_next": dasha_next,
        "dasha_everyday": vt.DASHA_EVERYDAY,
        "mangal_rule": vt.MANGAL_RULE, "mangal_text": mangal_text, "sade_text": sade_text,
        "sade_note": vt.SADE_NOTE, "sade_everyday": vt.SADE_EVERYDAY,
        "rashi": hg.SIGNS[moon_sign], "rashi_text": hp.RASHI[moon_sign],
        "nak": hg.NAKSHATRAS[nak], "pada": vc.moon_nakshatra_pada, "nak_text": hp.NAKSHATRA[nak],
        "remedies": remedies, "remedy_note": vt.REMEDY_NOTE,
        "toc": vt.TOC, "faq": vt.FAQ, "glossary": vt.GLOSSARY,
        "closing": vt.CLOSING, "closing_quote": vt.CLOSING_QUOTE, "disclaimer": vt.DISCLAIMER,
    }


def generate(name, birth, tz, place, lat, lon, out_path, time_known=True) -> str:
    from weasyprint import HTML
    ctx = build_context(name, birth, tz, place, lat, lon, time_known)
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    html = env.get_template("kundli_report_hi.html").render(**ctx)
    HTML(string=html, base_url=TEMPLATE_DIR).write_pdf(out_path)
    return out_path
