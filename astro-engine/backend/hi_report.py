"""Hindi Kundli Milan (vedic_compat) report: context builder and PDF render.
Calculation is shared with the English report; only content, template and
fonts differ."""
from __future__ import annotations

import datetime as dt
import os

from jinja2 import Environment, FileSystemLoader

try:
    from . import hi_glossary as hg, hi_profiles as hp, hi_koota_text as ht
    from . import compatibility_engine as ce
    from .chart_engine import compute_charts, NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS
except ImportError:
    import hi_glossary as hg, hi_profiles as hp, hi_koota_text as ht
    import compatibility_engine as ce
    from chart_engine import compute_charts, NAKSHATRAS, SIGNS, VEDIC_SIGN_LORDS

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "pdf_templates")

_BAND_ORDER = ["full", "high", "mid", "zero"]


def _band(score: float, max_pts: float) -> str:
    ratio = score / max_pts
    return "full" if ratio >= 1 else "high" if ratio >= 0.6 else "mid" if ratio > 0 else "zero"


def _pick(info: dict, band: str) -> str:
    if band in info:
        return info[band]
    i = _BAND_ORDER.index(band)
    for b in _BAND_ORDER[i + 1:] + _BAND_ORDER[:i][::-1]:
        if b in info:
            return info[b]
    raise KeyError(band)


def _person(name: str, birth: dt.datetime, tz: str, lat: float, lon: float,
            time_known: bool) -> dict:
    vc = compute_charts("vedic", birth, tz, lat, lon)["vedic"]
    moon, mars = vc.get("Moon"), vc.get("Mars")
    nak = vc.moon_nakshatra
    current = next((d for d in vc.dashas if d.current), None)
    lagna = vc.ascendant.sign if (time_known and vc.ascendant) else None
    vashya = ce._vashya_group(moon.sign, moon.sign_degree)
    nadi = ce.NADI_NAME[ce._nadi_index(nak)]
    return {
        "name": name, "time_known": time_known,
        "moon_sign": moon.sign, "moon_deg": moon.sign_degree,
        "nak": nak, "pada": vc.moon_nakshatra_pada,
        "nak_lord": hp.NAKSHATRA_LORD_ORDER[NAKSHATRAS.index(nak) % 9],
        "rashi_lord": VEDIC_SIGN_LORDS[moon.sign],
        "mars_sign": mars.sign, "lagna": lagna,
        "varna": ce.VARNA_NAME[ce.VARNA[moon.sign]], "vashya": vashya,
        "yoni": ce.YONI[nak], "gana": ce.GANA[nak], "nadi": nadi,
        "dasha_lord": current.lord if current else None,
        "dasha_end": dt.date.fromisoformat(current.end) if current else None,
    }


def _koota_values(k: dict) -> tuple[str, str, str, str]:
    """Hindi (groom value, groom note, bride value, bride note) for a koota row."""
    n, g, b = k["name"], k["groom"], k["bride"]
    if n == "Varna":
        return hg.VARNA[g], hp.VARNA[g], hg.VARNA[b], hp.VARNA[b]
    if n == "Vashya":
        return hg.VASHYA[g], hp.VASHYA[g], hg.VASHYA[b], hp.VASHYA[b]
    if n == "Tara":
        def tara(x):
            i = int(x)
            return hg.TARA[i - 1], ("कम अनुकूल" if i in hg.TARA_INAUSPICIOUS else "अनुकूल")
        (tg, ng), (tb, nb) = tara(g), tara(b)
        return tg, ng, tb, nb
    if n == "Yoni":
        return hg.YONI[g], hp.YONI[g], hg.YONI[b], hp.YONI[b]
    if n == "Graha Maitri":
        return hg.PLANETS[g], hp.PLANET[g], hg.PLANETS[b], hp.PLANET[b]
    if n == "Gana":
        return hg.GANA[g], hp.GANA[g], hg.GANA[b], hp.GANA[b]
    if n == "Bhakoot":
        return (f"{g}वीं राशि", "कन्या की राशि, वर की राशि से गिनने पर",
                f"{b}वीं राशि", "वर की राशि, कन्या की राशि से गिनने पर")
    return hg.NADI[g], hp.NADI[g], hg.NADI[b], hp.NADI[b]


def _mangal_row(p: dict) -> dict:
    r = ce.mangal_dosha(p["mars_sign"], p["lagna"], p["moon_sign"])
    def line(house, by):
        if house is None:
            return "जन्म समय ज्ञात नहीं, इसलिए गणना नहीं की गई"
        return f"मंगल {ht.HOUSE_ORDINAL[house]} भाव में ({'मांगलिक स्थिति' if by else 'मांगलिक स्थिति नहीं'})"
    return {"name": p["name"], "present": r["present"], "mars": hg.SIGNS[p["mars_sign"]],
            "from_lagna": line(r["from_lagna"], r["by_lagna"]),
            "from_moon": line(r["from_moon"], r["by_moon"])}


def build_context(order: dict) -> dict:
    ta = bool(order["birth_time"])
    tb = bool(order["partner_birth_time"])
    a_birth = dt.datetime.strptime(order["birth_date"] + " " + (order["birth_time"] or "12:00"), "%Y-%m-%d %H:%M")
    b_birth = dt.datetime.strptime(order["partner_birth_date"] + " " + (order["partner_birth_time"] or "12:00"), "%Y-%m-%d %H:%M")
    a = _person(order["name"], a_birth, order["tz"], order["lat"], order["lon"], ta)
    b = _person(order["partner_name"], b_birth, order["partner_tz"], order["partner_lat"], order["partner_lon"], tb)
    a["birth"], b["birth"] = a_birth, b_birth
    a["place"], b["place"] = order["birth_place"], order["partner_birth_place"]

    a_groom, basis = ce.assign_roles(order.get("gender"), order.get("partner_gender"))
    guna = ce.guna_milan(a["moon_sign"], a["nak"], b["moon_sign"], b["nak"],
                         moon_deg_a=a["moon_deg"], moon_deg_b=b["moon_deg"], a_is_groom=a_groom)
    groom, bride = (a, b) if a_groom else (b, a)
    roles_text = (ht.ROLES_GENDER if basis == "gender" else ht.ROLES_ORDER).format(
        groom=groom["name"], bride=bride["name"])

    total = guna["total"]
    band = hg.band_label(total)

    rows, pages, tips, strengths = [], [], [], []
    for k in guna["kootas"]:
        hi_name, mx = hg.KOOTA[k["name"]]
        bnd = _band(k["score"], k["max"])
        info = ht.KOOTA_INFO[k["name"]]
        gv, gn, bv, bn = _koota_values(k)
        dist = "/".join(str(x) for x in sorted((int(k["groom"]), int(k["bride"])))) if k["name"] == "Bhakoot" else ""
        text = _pick(info, bnd).format(score=hg.fmt(k["score"]), dist=dist,
                                       groom_nadi=hg.NADI.get(k["groom"], ""), bride_nadi=hg.NADI.get(k["bride"], ""))
        low = k["score"] / k["max"] < 0.6
        ev = info["everyday"] + " " + (ht.EVERYDAY_LOW if low else ht.EVERYDAY_POS)
        rows.append({"name": hi_name, "max": mx, "score": hg.fmt(k["score"]), "groom": gv, "bride": bv, "band": bnd})
        pages.append({"name": hi_name, "max": mx, "score": hg.fmt(k["score"]), "band": bnd,
                      "meaning": info["meaning"], "scoring": ht.SCORING[k["name"]], "groom_val": gv, "groom_note": gn,
                      "bride_val": bv, "bride_note": bn, "result": text, "everyday": ev})
        (tips if low else strengths).append((hi_name, ht.TIPS[k["name"]]))

    mangal = [_mangal_row(a), _mangal_row(b)]
    flags = [m["present"] for m in mangal]
    if all(flags):
        mangal_text = ht.MANGAL_BOTH
    elif not any(flags):
        mangal_text = ht.MANGAL_NONE
    else:
        mangal_text = ht.MANGAL_ONE.format(name=(mangal[0] if flags[0] else mangal[1])["name"])

    dasha_text = (ht.DASHA_BOTH_SAME if a["dasha_lord"] == b["dasha_lord"] else ht.DASHA_DIFF)
    unknown = [p["name"] for p in (a, b) if not p["time_known"]]
    time_notes = [ht.TIME_UNKNOWN_NOTE.format(who=n) for n in unknown]

    def person_view(p):
        return {
            "name": p["name"], "date": hg.hi_date(p["birth"]),
            "time": p["birth"].strftime("%H:%M") if p["time_known"] else "ज्ञात नहीं",
            "place": p["place"], "rashi": hg.SIGNS[p["moon_sign"]],
            "nak": hg.NAKSHATRAS[p["nak"]], "pada": p["pada"], "nak_lord": hg.PLANETS[p["nak_lord"]],
            "rashi_lord": hg.PLANETS[p["rashi_lord"]],
            "lagna": hg.SIGNS[p["lagna"]] if p["lagna"] else "ज्ञात नहीं",
            "rashi_text": hp.RASHI[p["moon_sign"]], "nak_text": hp.NAKSHATRA[p["nak"]],
            "symbols": [("वर्ण", hg.VARNA[p["varna"]], hp.VARNA[p["varna"]]),
                        ("वश्य", hg.VASHYA[p["vashya"]], hp.VASHYA[p["vashya"]]),
                        ("योनि", hg.YONI[p["yoni"]], hp.YONI[p["yoni"]]),
                        ("गण", hg.GANA[p["gana"]], hp.GANA[p["gana"]]),
                        ("नाड़ी", hg.NADI[p["nadi"]], hp.NADI[p["nadi"]]),
                        ("राशि स्वामी", hg.PLANETS[p["rashi_lord"]], hp.PLANET[p["rashi_lord"]])],
            "dasha": hg.PLANETS[p["dasha_lord"]] if p["dasha_lord"] else "",
            "dasha_text": hp.DASHA.get(p["dasha_lord"], ""),
            "dasha_end": hg.hi_date(p["dasha_end"]) if p["dasha_end"] else "",
        }

    faq = list(ht.FAQ)
    faq.append(("इस रिपोर्ट में वर और कन्या पक्ष कैसे तय किया गया?", roles_text))

    return {
        "a": person_view(a), "b": person_view(b),
        "groom": groom["name"], "bride": bride["name"], "roles_text": roles_text,
        "generated": hg.hi_date(dt.date.today()),
        "total": hg.fmt(total), "max": 36, "band": band, "summary": ht.SUMMARY[band],
        "summary_everyday": ht.SUMMARY_EVERYDAY[band],
        "rows": rows, "pages": pages, "intro": ht.INTRO,
        "tips": tips, "strengths": strengths,
        "bhakoot_nadi_intro": ht.BHAKOOT_NADI_INTRO,
        "bhakoot": ht.BHAKOOT_PRESENT if guna["bhakoot_dosha"] else ht.BHAKOOT_ABSENT,
        "nadi": ht.NADI_PRESENT if guna["nadi_dosha"] else ht.NADI_ABSENT,
        "bhakoot_flag": guna["bhakoot_dosha"], "nadi_flag": guna["nadi_dosha"],
        "dosha_caution": ht.DOSHA_CAUTION,
        "mangal_intro": ht.MANGAL_INTRO, "mangal": mangal, "mangal_text": mangal_text,
        "mangal_note": ht.MANGAL_NOTE, "time_notes": time_notes,
        "dasha_intro": ht.DASHA_INTRO, "dasha_text": dasha_text,
        "toc": ht.TOC, "closing_quote": ht.CLOSING_QUOTE,
        "faq": faq, "glossary": ht.GLOSSARY, "closing": ht.CLOSING, "disclaimer": ht.DISCLAIMER,
        "bands": [("31 से 36", "अति उत्तम"), ("21 से 30", "उत्तम"), ("17 से 20", "साधारण"), ("0 से 16", "अल्प मेल")],
    }


def generate(order: dict, out_path: str) -> str:
    from weasyprint import HTML
    ctx = build_context(order)
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    html = env.get_template("compatibility_report_hi.html").render(**ctx)
    HTML(string=html, base_url=TEMPLATE_DIR).write_pdf(out_path)
    return out_path
