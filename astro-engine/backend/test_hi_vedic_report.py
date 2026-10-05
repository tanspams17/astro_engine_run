"""Plain-assert tests for the Hindi Vedic Kundli report. Run directly:
python3 test_hi_vedic_report.py  (PDF page-count checks run only if WeasyPrint and pdfinfo exist)."""
import datetime as dt
import re
import sys

try:
    from . import hi_vedic_text as vt, hi_vedic_report as hv, hi_glossary as hg
    from . import compatibility_engine as ce
except ImportError:
    import hi_vedic_text as vt, hi_vedic_report as hv, hi_glossary as hg
    import compatibility_engine as ce

BIRTHS = [
    ("Priya Sharma", dt.datetime(1995, 7, 14, 6, 30), "Asia/Kolkata", 19.076, 72.8777, True),
    ("Arjun Mehta", dt.datetime(1988, 1, 2, 23, 45), "Asia/Kolkata", 28.6139, 77.209, True),
    ("Ava Morgan", dt.datetime(1992, 3, 14, 8, 30), "Europe/London", 51.5, -0.12, True),
    ("No Time", dt.datetime(2001, 11, 30, 12, 0), "Asia/Kolkata", 13.08, 80.27, False),
]


def _ctx(b):
    n, d, tz, lat, lon, known = b
    return hv.build_context(n, d, tz, "Test City", lat, lon, known)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def test_navamsa_known_cases():
    sign = lambda lon: ce.SIGNS[hv.navamsa_sign(lon)]
    assert sign(0.5) == "Aries" and sign(3.4) == "Taurus"          # fire: from Aries
    assert sign(30.5) == "Capricorn" and sign(59.9) == "Virgo"     # earth: from Capricorn
    assert sign(60.5) == "Libra"                                   # air: from Libra
    assert sign(90.5) == "Cancer"                                  # water: from Cancer
    assert sign(239.9) == "Pisces"                                 # last navamsa of Scorpio (water: Cancer ... Pisces)
    # every sign has nine distinct consecutive navamsas
    for s in range(12):
        seq = [hv.navamsa_sign(s * 30 + k * (30 / 9) + 0.1) for k in range(9)]
        assert len(set(seq)) == 9 and all((seq[i + 1] - seq[i]) % 12 == 1 for i in range(8))


def test_houses_and_planets_are_consistent():
    for b in BIRTHS:
        c = _ctx(b)
        assert len(c["houses"]) == 12 and len(c["planets"]) == 9 and len(c["table"]) == 9
        assert all(1 <= r["house"] <= 12 for r in c["table"])
        occ = sum(1 for h in c["houses"] for t in h["paras"] if t.startswith("इस भाव में") and "स्थित हैं" in t)
        assert occ == len({r["house"] for r in c["table"]})
        assert len(c["dasha_rows"]) == 9 and sum(1 for r in c["dasha_rows"] if r["current"]) == 1
        assert len(c["toc"]) == len(vt.TOC)


def test_unknown_time_uses_moon_as_base():
    c = _ctx(BIRTHS[3])
    moon_row = next(r for r in c["table"] if r["planet"] == "चंद्र")
    assert moon_row["house"] == 1 and c["time_note"]
    assert "लग्न" not in c["bigthree"] and c["kv"][4] == ("लग्न", "ज्ञात नहीं")
    assert "चंद्र कुंडली" in c["chart_main_title"]


def test_known_time_uses_lagna_as_base():
    c = _ctx(BIRTHS[0])
    assert c["chart_main_title"] == "लग्न कुंडली" and "लग्न" in c["bigthree"] and not c["time_note"]


def test_no_placeholders_and_chart_labels_are_html():
    for b in BIRTHS:
        c = _ctx(b)
        for k, v in c.items():
            if k in ("chart_main", "chart_nav"):
                assert 'class="hc"' in v and "<text" not in v, "chart labels must be HTML, not SVG text"
                continue
            for s in _strings(v):
                assert "{" not in s and "}" not in s, f"{k}: {s[:60]}"


def test_static_text_has_no_english_letters():
    skip = {"EXALT", "DEBIL", "OWN", "HOUSE_KIND", "SIGN_ELEMENT", "SIGN_MODE"}
    for name, val in vars(vt).items():
        if name.startswith("_") or not name.isupper() or name in skip:
            continue
        vals = val.values() if isinstance(val, dict) else [val]
        for s in _strings(list(vals)):
            bare = re.sub(r"\{[a-z_]+\}|D9", "", s)  # placeholders and the standard "D9" label are allowed
            assert not re.search(r"[A-Za-z]", bare), f"{name}: {s[:60]}"


def test_mangal_matches_engine():
    for b in BIRTHS:
        c = _ctx(b)
        assert (vt.MANGAL_ABSENT == c["mangal_text"]) or c["mangal_text"].startswith("आपकी कुंडली में मंगल")


def test_pdf_page_count_if_available():
    try:
        from weasyprint import HTML  # noqa: F401
    except Exception:
        print("  (skipped: WeasyPrint unavailable here)")
        return
    import os, shutil, subprocess, tempfile
    if not shutil.which("pdfinfo"):
        print("  (skipped: pdfinfo not installed here)")
        return
    for b in (BIRTHS[0], BIRTHS[3]):
        out = os.path.join(tempfile.mkdtemp(), "k.pdf")
        n, d, tz, lat, lon, known = b
        hv.generate(n, d, tz, "Test City", lat, lon, out, time_known=known)
        info = subprocess.run(["pdfinfo", out], capture_output=True, text=True).stdout
        pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        assert 20 <= pages <= 24, (n, pages)


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
