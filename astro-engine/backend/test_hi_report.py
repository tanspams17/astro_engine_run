"""Plain-assert tests for the Hindi Kundli Milan report. Run directly:
python3 test_hi_report.py  (PDF page-count check runs only if WeasyPrint loads)."""
import re
import sys

try:
    from . import hi_glossary as hg, hi_profiles as hp, hi_koota_text as ht, hi_report as hr
    from . import compatibility_engine as ce
except ImportError:
    import hi_glossary as hg, hi_profiles as hp, hi_koota_text as ht, hi_report as hr
    import compatibility_engine as ce


def _order(**kw):
    base = dict(tier="vedic_compat", name="Ava Morgan", partner_name="Rahul Nair",
                birth_date="1992-03-14", birth_time="08:30",
                partner_birth_date="1990-11-02", partner_birth_time="19:10",
                tz="Europe/London", lat=51.5, lon=-0.12, birth_place="London, UK",
                partner_birth_place="Kochi, India", partner_tz="Asia/Kolkata",
                partner_lat=9.93, partner_lon=76.26, gender="female", partner_gender="male",
                language="hi")
    base.update(kw)
    return base


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def test_static_hindi_text_has_no_english_letters():
    for mod in (hg, hp, ht):
        for name, val in vars(mod).items():
            if name.startswith("_") or not name.isupper() or name == "NAKSHATRA_LORD_ORDER":
                continue
            # engine keys (English dictionary keys) are allowed; only values are checked
            vals = val.values() if isinstance(val, dict) else [val]
            for s in _strings(list(vals)):
                bare = re.sub(r"\{[a-z_]+\}", "", s)  # format placeholders are allowed
                assert not re.search(r"[A-Za-z]", bare), f"{mod.__name__}.{name} has Latin letters: {s[:60]}"


def test_scores_match_english_engine_and_no_placeholders():
    for kw in (dict(), dict(gender="unspecified", partner_gender="unspecified"),
               dict(birth_time=None), dict(partner_birth_time=None),
               dict(gender="male", partner_gender="male"),
               dict(birth_date="1985-07-21", partner_birth_date="1988-01-09")):
        o = _order(**kw)
        ctx = hr.build_context(o)
        a_groom, _ = ce.assign_roles(o["gender"], o["partner_gender"])
        a, b = ctx["a"], ctx["b"]
        assert len(ctx["rows"]) == 8 and len(ctx["pages"]) == 8
        assert abs(sum(float(r["score"]) for r in ctx["rows"]) - float(ctx["total"])) < 1e-9
        for s in _strings(ctx):
            assert "{" not in s and "}" not in s, f"unformatted placeholder: {s[:80]}"
        assert ctx["band"] == hg.band_label(float(ctx["total"]))
        assert ctx["groom"] == (o["name"] if a_groom else o["partner_name"])


def test_unknown_time_is_noted_and_skips_lagna():
    ctx = hr.build_context(_order(birth_time=None))
    assert ctx["a"]["lagna"] == "ज्ञात नहीं" and len(ctx["time_notes"]) == 1
    assert "गणना नहीं की गई" in ctx["mangal"][0]["from_lagna"]


def test_dosha_and_mangal_branches_are_reachable():
    seen_mangal, seen_nadi, seen_bhakoot = set(), set(), set()
    import datetime as dt
    d0 = dt.date(1984, 1, 1)
    for i in range(0, 4200, 37):
        d = d0 + dt.timedelta(days=i)
        ctx = hr.build_context(_order(birth_date=d.isoformat(), partner_birth_date=(d0 + dt.timedelta(days=i * 3 % 4000 + 11)).isoformat()))
        seen_mangal.add(sum(m["present"] for m in ctx["mangal"]))
        seen_nadi.add(ctx["nadi_flag"])
        seen_bhakoot.add(ctx["bhakoot_flag"])
        assert ctx["mangal_text"] in (ht.MANGAL_BOTH, ht.MANGAL_NONE) or "केवल" in ctx["mangal_text"]
    assert seen_mangal == {0, 1, 2}, seen_mangal
    assert seen_nadi == {True, False} and seen_bhakoot == {True, False}


def test_pdf_page_count_if_weasyprint_available():
    try:
        from weasyprint import HTML  # noqa: F401
    except Exception:
        print("  (skipped: WeasyPrint unavailable here)")
        return
    import os, subprocess, tempfile
    out = os.path.join(tempfile.mkdtemp(), "hi.pdf")
    hr.generate(_order(), out)
    info = subprocess.run(["pdfinfo", out], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    assert 20 <= pages <= 24, pages


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
