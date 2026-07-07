"""
Arvelos report generator.
Assembles chart data + content library into a styled PDF via WeasyPrint.
"""
from __future__ import annotations

import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

import content_library as cl
import content_vedic as cv
from chart_engine import Chart, compute_charts

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "pdf_templates")

TIER_NAMES = {"western": "Western Report", "vedic": "Vedic Report",
              "mixed": "Mixed Report — Western + Vedic"}


# ------------------------------------------------------------ assembly


def _placement_rows(chart: Chart) -> list[dict]:
    rows = []
    for p in chart.placements:
        rows.append({
            "planet": p.planet,
            "sign": p.sign,
            "degree": f"{p.sign_degree:.1f}°",
            "house": cl._ordinal(p.house),
            "retro": "R" if p.retrograde else "",
            "nakshatra": p.nakshatra or "",
        })
    return rows


def _core_three(chart: Chart) -> list[dict]:
    """Rising, Sun, Moon feature sections."""
    out = []
    asc = chart.ascendant
    sun = chart.get("Sun")
    moon = chart.get("Moon")
    if asc:
        out.append({"title": f"Your Rising Sign — {asc.sign}",
                    "body": cl.RISING_SIGNS[asc.sign]})
    if sun:
        out.append({"title": f"Your Sun — {sun.sign}",
                    "body": cl.SUN_SIGNS[sun.sign]})
    if moon:
        out.append({"title": f"Your Moon — {moon.sign}",
                    "body": cl.MOON_SIGNS[moon.sign]})
    return out


def _planet_sections(chart: Chart, with_houses: bool = True) -> list[dict]:
    out = []
    skip = {"Sun", "Moon"}
    for p in chart.placements:
        if p.planet in skip:
            continue
        body = cl.planet_in_sign(p.planet, p.sign)
        if with_houses:
            body += " " + cl.planet_in_house(p.planet, p.house)
        if p.retrograde:
            body += (" This planet was retrograde at your birth — its themes "
                     "tend to be processed inwardly first, and mature later "
                     "and more thoroughly than average.")
        if chart.system == "vedic" and p.nakshatra:
            body += f" It occupies the nakshatra {p.nakshatra}."
        out.append({"title": f"{p.planet} in {p.sign}", "body": body})
    return out


def _house_sections(chart: Chart) -> list[dict]:
    from chart_engine import SIGNS
    by_house: dict[int, list[str]] = {}
    for p in chart.placements:
        by_house.setdefault(p.house, []).append(p.planet)
    out = []
    for h in range(1, 13):
        title, desc = cl.HOUSES[h]
        cusp_sign = SIGNS[int(chart.house_cusps[h - 1] // 30) % 12]
        occupants = by_house.get(h, [])
        style = (f"The sign on this house's cusp is {cusp_sign}, so this "
                 f"arena of your life tends to run in a {cusp_sign} style — "
                 f"{cl.SIGN_EXPRESSIONS[cusp_sign]}.")
        if occupants:
            occ = ", ".join(occupants)
            body = (f"This house governs {desc}. {style} In your chart it "
                    f"holds {occ} — this is an active arena for you, "
                    f"energized by the themes of "
                    f"{'that planet' if len(occupants)==1 else 'those planets'} "
                    f"described above. Expect this part of life to demand — "
                    f"and reward — more of your attention than average.")
        else:
            body = (f"This house governs {desc}. {style} No planets occupy it "
                    f"in your chart — which doesn't mean the area is empty in "
                    f"your life, only that it runs quietly on that cusp-sign "
                    f"style rather than being a major center of gravity.")
        out.append({"title": f"{cl._ordinal(h)} House — {title}", "body": body})
    return out


def _aspect_sections(chart: Chart) -> list[dict]:
    out = []
    majors = [a for a in chart.aspects if a.orb <= 5][:8]
    for a in majors:
        out.append({
            "title": f"{a.planet_a} {a.aspect.lower()} {a.planet_b}",
            "body": (f"Your {a.planet_a} and {a.planet_b} "
                     f"{cl.ASPECT_MEANINGS[a.aspect]}."),
        })
    return out


def _focus_sections(charts: dict[str, Chart], focus_areas: list[str]) -> list[dict]:
    chart = charts.get("western") or charts.get("vedic")
    out = []
    for area in focus_areas:
        if area not in cl.FOCUS_INTROS:
            continue
        parts = [cl.FOCUS_INTROS[area]]
        if area == "personality":
            asc, sun, moon = chart.ascendant, chart.get("Sun"), chart.get("Moon")
            parts.append(
                f"Your outer layer is {asc.sign} rising, your core is a {sun.sign} "
                f"Sun, and your emotional engine is a {moon.sign} Moon. Read together: "
                f"the world first meets the {asc.sign} in you, is then held (or "
                f"challenged) by the {sun.sign} underneath, and the private weather "
                f"is {moon.sign}. When these three feel at odds, it isn't inconsistency "
                f"— it's layering, and self-knowledge is mostly learning which layer "
                f"is speaking.")
        elif area == "love":
            venus, moon = chart.get("Venus"), chart.get("Moon")
            seventh = [p.planet for p in chart.placements if p.house == 7]
            parts.append(cl.planet_in_sign("Venus", venus.sign) + " " +
                         cl.planet_in_house("Venus", venus.house))
            parts.append(
                f"Your Moon in {moon.sign} sets what you need to feel emotionally "
                f"safe with a partner — reread that section with relationships in "
                f"mind.")
            if seventh:
                parts.append(
                    f"Your 7th house of partnership holds {', '.join(seventh)}: "
                    f"relationships are a genuinely active arena in this chart, "
                    f"a place where major themes of your life get worked out.")
            else:
                parts.append(
                    "Your 7th house of partnership holds no planets — partnership "
                    "in your chart is shaped more by who you choose than by heavy "
                    "internal weather, which is quieter but also freer.")
        elif area == "career":
            tenth = [p.planet for p in chart.placements if p.house == 10]
            saturn, mars = chart.get("Saturn"), chart.get("Mars")
            if tenth:
                parts.append(
                    f"Your 10th house of career holds {', '.join(tenth)} — public "
                    f"work is a major center of gravity in this chart, and those "
                    f"planets' themes (see their sections) describe the flavor of "
                    f"work that will feel like yours.")
            else:
                parts.append(
                    "Your 10th house of career holds no planets, which often "
                    "describes careers built deliberately rather than compulsively "
                    "— direction comes from choice and cumulative skill rather "
                    "than a single burning drive.")
            parts.append(
                f"Saturn — where you meet discipline — sits in {saturn.sign} in your "
                f"{cl._ordinal(saturn.house)} house: effort invested there compounds "
                f"more slowly but more durably than anywhere else in your chart. "
                f"Mars in {mars.sign} describes your working drive: "
                f"{cl.SIGN_EXPRESSIONS[mars.sign]}.")
        elif area == "growth":
            saturn = chart.get("Saturn")
            hard = [a for a in chart.aspects
                    if a.aspect in ("Square", "Opposition")][:3]
            parts.append(
                f"Saturn marks the chart's main growth edge. Yours, in {saturn.sign} "
                f"in the {cl._ordinal(saturn.house)} house, points to the arena where "
                f"life keeps setting the same exam until you pass it — and where "
                f"passing it builds something nothing can take away.")
            for a in hard:
                parts.append(f"Your {a.planet_a}–{a.planet_b} "
                             f"{a.aspect.lower()}: these two functions "
                             f"{cl.ASPECT_MEANINGS[a.aspect]}. Friction like this "
                             f"is the chart's gym equipment — resistance that "
                             f"builds strength when worked deliberately.")
            v = charts.get("vedic")
            if v:
                rahu, ketu = v.get("Rahu"), v.get("Ketu")
                if rahu and ketu:
                    parts.append(
                        f"In the Vedic chart, growth is read on the Rahu–Ketu axis. "
                        f"Ketu in {ketu.sign} ({cl._ordinal(ketu.house)} house) marks "
                        f"what you already carry with ease; Rahu in {rahu.sign} "
                        f"({cl._ordinal(rahu.house)} house) marks the unfamiliar "
                        f"territory this life keeps pulling you toward. Growth, in "
                        f"this reading, is the deliberate walk from the first "
                        f"toward the second.")
        out.append({"title": f"Focus: {area.title()}",
                    "body": "\n\n".join(parts)})
    return out


def _vedic_sections(chart: Chart) -> list[dict]:
    out = [{"title": "Reading Your Vedic Chart", "body": cv.VEDIC_INTRO}]
    nak = chart.moon_nakshatra
    if nak:
        symbol, lord, passage = cv.NAKSHATRAS[nak]
        out.append({
            "title": f"Your Birth Star — {nak}",
            "body": (cv.NAKSHATRA_INTRO + f"\n\nYours is {nak} — symbol: "
                     f"{symbol}; ruled by {lord}; pada {chart.moon_nakshatra_pada}. "
                     f"\n\n{passage}"),
        })
    current = next((d for d in chart.dashas if d.current), None)
    if current:
        timeline = "\n".join(
            f"{'▶ ' if d.current else '   '}{d.lord}: {d.start[:7]} → {d.end[:7]}"
            for d in chart.dashas)
        out.append({
            "title": f"Your Current Chapter — {current.lord} Mahadasha "
                     f"(until {current.end[:7]})",
            "body": (cv.DASHA_INTRO + "\n\n" + cv.DASHA_LORDS[current.lord] +
                     "\n\nYour full mahadasha timeline:\n" + timeline),
        })
        idx = chart.dashas.index(current)
        if idx + 1 < len(chart.dashas):
            nxt = chart.dashas[idx + 1]
            out.append({
                "title": f"The Chapter After — {nxt.lord} Mahadasha "
                         f"(from {nxt.start[:7]})",
                "body": ("For orientation, here is the chapter that follows "
                         "your current one. " + cv.DASHA_LORDS[nxt.lord] +
                         " Knowing what's next isn't about bracing for it — "
                         "it's about finishing the current chapter's work "
                         "so the next one starts on solid ground."),
            })
    return out


def _synthesis_section(charts: dict[str, Chart]) -> dict:
    w, v = charts["western"], charts["vedic"]
    lines = [cv.SYNTHESIS_INTRO, ""]
    for name in ("Ascendant", "Sun", "Moon", "Mercury", "Venus", "Mars",
                 "Jupiter", "Saturn"):
        wp = w.ascendant if name == "Ascendant" else w.get(name)
        vp = v.ascendant if name == "Ascendant" else v.get(name)
        if not wp or not vp:
            continue
        if wp.sign == vp.sign:
            lines.append(f"• {name}: {wp.sign} in BOTH systems — a reinforced "
                         f"signal; treat this placement's description as "
                         f"doubly weighted for you.")
        else:
            lines.append(f"• {name}: {wp.sign} (Western) / {vp.sign} (Vedic) "
                         f"— read the Western as the inner experience, the "
                         f"Vedic as the life-pattern lens.")
    return {"title": "Synthesis — Two Lenses, One Person",
            "body": "\n".join(lines)}


def _balance_section(chart: Chart) -> dict:
    """Element & modality balance, computed from placements."""
    ELEMENTS = {"Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
                "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
                "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
                "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water"}
    MODES = {"Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal",
             "Capricorn": "Cardinal", "Taurus": "Fixed", "Leo": "Fixed",
             "Scorpio": "Fixed", "Aquarius": "Fixed", "Gemini": "Mutable",
             "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable"}
    ELEM_MEANING = {
        "Fire": "initiative, enthusiasm, and the confidence to act",
        "Earth": "practicality, patience, and the ability to build things that last",
        "Air": "ideas, communication, and social intelligence",
        "Water": "feeling, intuition, and emotional depth",
    }
    MODE_MEANING = {
        "Cardinal": "starting things — leadership and initiation",
        "Fixed": "sustaining things — persistence and loyalty",
        "Mutable": "adapting things — flexibility and learning",
    }
    core = [p for p in chart.placements
            if p.planet in ("Sun", "Moon", "Mercury", "Venus", "Mars",
                            "Jupiter", "Saturn")]
    elems: dict[str, int] = {}
    modes: dict[str, int] = {}
    for p in core:
        elems[ELEMENTS[p.sign]] = elems.get(ELEMENTS[p.sign], 0) + 1
        modes[MODES[p.sign]] = modes.get(MODES[p.sign], 0) + 1
    dom_e = max(elems, key=elems.get)
    dom_m = max(modes, key=modes.get)
    missing = [e for e in ("Fire", "Earth", "Air", "Water") if e not in elems]
    body = (
        f"Counting your seven classical planets across the four elements: "
        + ", ".join(f"{v} in {k}" for k, v in sorted(elems.items(), key=lambda x: -x[1]))
        + f". Your strongest element is {dom_e}, which weights your chart "
        f"toward {ELEM_MEANING[dom_e]}.")
    if missing:
        m = missing[0]
        body += (f" You have no classical planets in {m} — not a deficiency, "
                 f"but a muscle that develops through conscious practice "
                 f"rather than instinct: {ELEM_MEANING[m]}.")
    body += (f"\n\nBy modality, your chart leans {dom_m} — your natural mode "
             f"is {MODE_MEANING[dom_m]}. Knowing your dominant mode explains "
             f"a lot about where your energy goes effortlessly and which "
             f"phases of a project you tend to hand off, avoid, or need "
             f"structure for.")
    return {"title": "Your Elemental Balance", "body": body}


# ------------------------------------------------------------ numerology


def _numerology_sections(num: dict, no) -> list[dict]:
    import content_numerology as cn
    from chart_graphics import lo_shu_svg
    out = [{"h1": "Your Numbers — Numerological Analysis", "no": no}]
    out.append({"title": f"Mulank {num['mulank']} — Your Psychic Number",
                "body": (cn.MULANK_INTRO + f"\n\nYours is {num['mulank']}, "
                         + cn.NUMBER_ESSENCE[num['mulank']])})
    if num["karmic_debt"]:
        out.append({"title": f"Born on the {num['karmic_debt']}th — "
                             "A Karmic Number",
                    "body": cn.KARMIC_DEBT_TEXT[num["karmic_debt"]]})
    out.append({"title": f"Bhagyank {num['bhagyank']} — Your Destiny Number",
                "body": (cn.BHAGYANK_INTRO + f"\n\nYours is {num['bhagyank']}, "
                         + cn.NUMBER_ESSENCE[num['bhagyank']])})
    friendly = (num["bhagyank"] in cn_friends(num["mulank"])
                or num["bhagyank"] == num["mulank"])
    from numerology import NUMBER_PLANETS
    out.append({"title": f"The {num['mulank']}–{num['bhagyank']} Combination",
                "body": cn.COMBO_TEXT.format(
                    m=num["mulank"], mp=NUMBER_PLANETS[num["mulank"]],
                    b=num["bhagyank"], bp=NUMBER_PLANETS[num["bhagyank"]],
                    verdict=cn.COMBO_FRIENDLY if friendly else cn.COMBO_NEUTRAL)})
    out.append({"title": f"Name Number {num['name_number']}",
                "body": (cn.NAME_INTRO + f"\n\nYours is {num['name_number']}, "
                         + cn.NUMBER_ESSENCE[num['name_number']] + "\n\n"
                         + ("Your name number is harmonious with your birth "
                            "numbers — the name you use works with you."
                            if num["name_harmonious"] else
                            "Your name number sits in mild tension with your "
                            "birth numbers. Nothing alarming — many successful "
                            "people have this — but if you ever use a short "
                            "form or pen name, one aligned with your Mulank's "
                            "friend numbers ("
                            + ", ".join(map(str, num["friend_numbers"]))
                            + ") is the traditional preference."))})
    out.append({"title": f"Soul Urge {num['soul_urge']} · Personality "
                         f"{num['personality_number']}",
                "body": (cn.SOUL_INTRO + " "
                         + cn.NUMBER_ESSENCE[num['soul_urge']] + "\n\n"
                         + cn.PERSONALITY_INTRO + " "
                         + cn.NUMBER_ESSENCE[num['personality_number']])})

    # Lo Shu grid
    out.append({"h1": "Your Lo Shu Fortune Grid", "no": None})
    out.append({"body": ("The Lo Shu grid maps the digits of your birth date "
                         "(plus your core numbers) onto the ancient 3×3 "
                         "magic square. Repeated numbers show concentrated "
                         "strengths; missing numbers show qualities that "
                         "develop through conscious practice rather than "
                         "instinct."), "title": ""})
    out.append({"chart": lo_shu_svg(num["grid"]["counts"]),
                "cap": "Your Lo Shu grid — numbers present in your birth data, with their classical elements"})
    strengths = [f"{n} appears {c}×" for n, c in num["grid"]["present"].items() if c >= 2]
    if strengths:
        out.append({"title": "Concentrated numbers",
                    "body": ("In your grid: " + "; ".join(strengths) + ". "
                             "Repetition amplifies a number's qualities — "
                             "review the essences above for your repeated "
                             "numbers; they act as double-strength traits.")})
    if num["grid"]["missing"]:
        body = "\n\n".join(cn.MISSING_NUMBER[n] for n in num["grid"]["missing"])
        out.append({"title": "Missing numbers — and what to do about them",
                    "body": body + "\n\n" + cn.GRID_PLANE_NOTE})

    # lucky things + directions card
    kd = num["kua_directions"]
    out.append({"h1": "Your Lucky Things & Directions", "no": None})
    out.append({"gold": True, "title": "Quick Reference — Keep This Page",
                "kv": [
                    ("Ruling planet", num["ruling_planet"]),
                    ("Lucky colours", num["lucky"]["colours"]),
                    ("Strong days", num["lucky"]["days"]),
                    ("Favourable dates", num["lucky"]["dates"]),
                    ("Friendly numbers", ", ".join(map(str, num["friend_numbers"]))),
                    ("Numbers to be careful with", num["lucky"]["avoid"]),
                    (f"Kua number", f"{num['kua']}"),
                    ("Direction of success", kd["success"]),
                    ("Direction of health/vitality", kd["health"]),
                    ("Direction of harmony", kd["harmony"]),
                    ("Direction of growth", kd["growth"]),
                    ("Your mantra", num["mantra"]),
                ]})
    out.append({"title": "",
                "body": ("How to use this page: favour your colours and days "
                         "for important starts; face your success direction "
                         "for focused work when practical; the mantra is "
                         "traditionally recited on your strong days — 11 or "
                         "108 repetitions, entirely optional. None of this "
                         "is superstition-as-obligation; treat it as a "
                         "personal rhythm the tradition offers you.")})
    return out


def cn_friends(m):
    from numerology import FRIENDS
    return FRIENDS[m]


def _monthly_sections(num: dict, moon_sidereal_lon: float,
                      dashas) -> list[dict]:
    import content_numerology as cn
    from numerology import next_12_months
    from chart_engine import monthly_transits
    months = next_12_months(dt.date.fromisoformat(num["_dob"]))
    transits = monthly_transits(moon_sidereal_lon)
    cur_dasha = next((d.lord for d in dashas if d.current), None) if dashas else None

    out = [{"h1": "Month by Month — Your Next 12 Months", "no": None},
           {"title": "", "body": cn.MONTHLY_INTRO +
            (f"\n\nBackdrop for the whole year: you are in a {cur_dasha} "
             f"mahadasha — reread that chapter's description; every month "
             f"below plays out against it." if cur_dasha else "")}]
    sade_flagged = False
    for mo, tr in zip(months, transits):
        pm = cn.PERSONAL_MONTH[mo["pm"]]
        jn = (cn.JUPITER_NOTE_GOOD if tr["jupiter_house"] in cn.JUPITER_GOOD
              else cn.JUPITER_NOTE_HARD).format(h=cl._ordinal(tr["jupiter_house"]))
        sn = (cn.SATURN_NOTE_GOOD if tr["saturn_house"] in cn.SATURN_GOOD
              else cn.SATURN_NOTE_HARD).format(h=cl._ordinal(tr["saturn_house"]))
        transit_txt = f"Sky context: {jn} {sn}"
        if tr["sade_sati"] and not sade_flagged:
            transit_txt += " " + cn.SADE_SATI_NOTE
            sade_flagged = True
        out.append({"month": {
            "label": mo["label"], "pm": mo["pm"], "theme": pm["theme"],
            "positive": pm["positive"], "negative": pm["negative"],
            "tips": pm["tips"], "transit": transit_txt}})
    return out


# ------------------------------------------------------------ render


def build_report_context(name: str, birth_dt_local: dt.datetime,
                         tz_name: str, place_label: str, lat: float,
                         lon: float, tier: str, focus_areas: list[str],
                         time_known: bool = True,
                         gender: str = "unspecified") -> dict:
    from numerology import compute_numerology
    from chart_graphics import (north_indian_chart, western_wheel,
                                lo_shu_svg, cover_zodiac_ring, SIGNS as GS)
    charts = compute_charts(tier, birth_dt_local, tz_name, lat, lon)
    primary = charts.get("western") or charts.get("vedic")
    num = compute_numerology(name, birth_dt_local.date(), gender)
    num["_dob"] = birth_dt_local.date().isoformat()

    sections = []
    toc = []
    sec_no = [0]

    def h1(title, desc):
        sec_no[0] += 1
        toc.append({"title": title, "desc": desc})
        return {"h1": title, "no": f"{sec_no[0]:02d}"}

    # 01 how to read
    sections.append(h1("How to Read This Report",
                       "No astrology knowledge assumed — start here"))
    sections.append({"title": "", "body": cl.HOW_TO_READ + (
        "" if time_known else
        "\n\nA note on your birth time: you indicated it isn't precisely "
        "known. Everything based on your birth date — all numerology, sun "
        "sign, monthly forecast, and (almost always) moon sign and nakshatra "
        "— is unaffected. We've omitted the rising sign and house placements, "
        "which are the only elements that need an exact clock time, rather "
        "than guess them.")})

    # 02 snapshot
    sections.append(h1("Your Details at a Glance",
                       "Birth data, core signs and core numbers"))
    vc0 = charts.get("vedic")
    kv = [("Name", name),
          ("Date of birth", birth_dt_local.strftime("%d %B %Y")),
          ("Time of birth", birth_dt_local.strftime("%H:%M") if time_known
           else "Not precisely known"),
          ("Place of birth", place_label),
          ("Sun sign (Western)", charts.get("western").get("Sun").sign
           if "western" in charts else "—"),
          ("Moon sign" + (" (Vedic)" if vc0 else ""),
           (vc0 or primary).get("Moon").sign),
          ("Mulank (psychic number)", str(num["mulank"])),
          ("Bhagyank (destiny number)", str(num["bhagyank"])),
          ("Name number", str(num["name_number"])),
          ("Kua number", str(num["kua"]))]
    if vc0 and vc0.moon_nakshatra:
        kv.insert(6, ("Birth star (nakshatra)",
                      f"{vc0.moon_nakshatra}, pada {vc0.moon_nakshatra_pada}"))
    if time_known and primary.ascendant:
        kv.insert(4, ("Rising sign", primary.ascendant.sign))
    sections.append({"kv": kv, "title": ""})

    # 03+ charts
    if "western" in charts:
        wc = charts["western"]
        sections.append(h1("Your Western Birth Chart",
                           "Tropical zodiac — the psychological lens"))
        wheel_pl = [(p.planet, p.longitude) for p in wc.placements]
        sections.append({"chart": western_wheel(
            wheel_pl, wc.ascendant.longitude if time_known else None),
            "cap": "Your Western chart wheel — planets in the tropical zodiac"
                   + (", Ascendant marked" if time_known else "")})
        sections += _core_three(wc) if time_known else _core_three_no_asc(wc)
        sections.append({"table": _placement_rows(wc), "houses": time_known,
                         "title": "Planetary Placements (Western / Tropical)"})
        sections.append(_balance_section(wc))
        sections += _planet_sections(wc, with_houses=time_known)
        if time_known:
            sections.append(h1("House by House",
                               "The twelve arenas of your life"))
            sections += _house_sections(wc)
            if wc.aspects:
                sections.append(h1("Major Aspects",
                                   "How your planets talk to each other"))
                sections += _aspect_sections(wc)

    if "vedic" in charts:
        vc = charts["vedic"]
        sections.append(h1("Your Vedic Birth Chart",
                           "Sidereal zodiac, Lahiri — the Jyotish lens"))
        asc_idx = (int(vc.ascendant.longitude // 30) if time_known
                   else int(vc.get("Moon").longitude // 30))
        diamond_pl = [(p.planet, int(p.longitude // 30))
                      for p in vc.placements]
        cap = ("North-Indian style chart" +
               (" (lagna kundali)" if time_known else
                " drawn from your Moon sign (chandra kundali) — the "
                "traditional approach when birth time is unknown"))
        sections.append({"chart": north_indian_chart(asc_idx, diamond_pl),
                         "cap": cap})
        sections += _vedic_sections(vc)
        if time_known:
            sections += _core_three(vc)
        sections.append({"table": _placement_rows(vc), "houses": time_known,
                         "title": "Planetary Placements (Vedic / Sidereal, Lahiri)"})
        sections += _planet_sections(vc, with_houses=time_known)
        if time_known and tier != "mixed":
            sections.append(h1("House by House (Whole Sign)",
                               "The twelve arenas, Vedic style"))
            sections += _house_sections(vc)

    if tier == "mixed" and "western" in charts and "vedic" in charts:
        sections.append(h1("Synthesis — Two Lenses, One Person",
                           "Where the systems agree about you"))
        sections.append(_synthesis_section(charts))

    # numerology block
    num_secs = _numerology_sections(num, None)
    # register its h1s in toc
    for s in num_secs:
        if "h1" in s:
            sec_no[0] += 1
            s["no"] = f"{sec_no[0]:02d}"
            toc.append({"title": s["h1"], "desc": {
                "Your Numbers — Numerological Analysis":
                    "Mulank, Bhagyank, name, soul urge — Chaldean system",
                "Your Lo Shu Fortune Grid":
                    "Your birth digits on the ancient magic square",
                "Your Lucky Things & Directions":
                    "Colours, days, dates, directions, mantra — quick reference",
            }.get(s["h1"], "")})
    sections += num_secs

    # monthly
    moon_lon = (charts.get("vedic") or primary).get("Moon").longitude
    monthly = _monthly_sections(
        num, moon_lon, charts["vedic"].dashas if "vedic" in charts else None)
    for s in monthly:
        if "h1" in s:
            sec_no[0] += 1
            s["no"] = f"{sec_no[0]:02d}"
            toc.append({"title": s["h1"],
                        "desc": "Personal-month cycle + real Jupiter/Saturn "
                                "transits, month by month"})
    sections += monthly

    if focus_areas:
        sections.append(h1("Your Focus Areas",
                           "The sections you asked us to go deeper on"))
        sections += _focus_sections(charts, focus_areas)

    return {
        "tier": tier, "tier_name": TIER_NAMES[tier], "name": name,
        "birth_line": ((birth_dt_local.strftime("%d %B %Y, %H:%M")
                        if time_known else
                        birth_dt_local.strftime("%d %B %Y")) +
                       f" — {place_label}"),
        "generated": dt.date.today().strftime("%d %B %Y"),
        "sections": sections, "toc": toc, "num": num,
        "closing": cl.CLOSING,
        "cover_ring": cover_zodiac_ring(),
        "asc_sign": (primary.ascendant.sign
                     if time_known and primary.ascendant else ""),
        "sun_sign": primary.get("Sun").sign,
        "moon_sign": (charts.get("vedic") or primary).get("Moon").sign,
    }


def _core_three_no_asc(chart: Chart) -> list[dict]:
    out = []
    sun, moon = chart.get("Sun"), chart.get("Moon")
    out.append({"title": f"Your Sun — {sun.sign}",
                "body": cl.SUN_SIGNS[sun.sign]})
    out.append({"title": f"Your Moon — {moon.sign}",
                "body": cl.MOON_SIGNS[moon.sign]})
    return out


def render_pdf(context: dict, out_path: str) -> str:
    from weasyprint import HTML
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template("report.html")
    html = tpl.render(**context)
    HTML(string=html, base_url=TEMPLATE_DIR).write_pdf(out_path)
    return out_path


def generate_report(name, birth_dt_local, tz_name, place_label, lat, lon,
                    tier, focus_areas, out_path, time_known=True,
                    gender="unspecified") -> str:
    ctx = build_report_context(name, birth_dt_local, tz_name, place_label,
                               lat, lon, tier, focus_areas,
                               time_known=time_known, gender=gender)
    return render_pdf(ctx, out_path)
