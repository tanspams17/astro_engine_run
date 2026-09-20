"""Plain-assert test script (no pytest — matches this repo's existing
lightweight-tooling convention). Run directly: python3 test_compatibility_engine.py"""
import sys

try:
    from . import compatibility_engine as ce
except ImportError:
    import compatibility_engine as ce


def test_zodiac_compare_friendly_numbers():
    num_a = {"mulank": 1, "bhagyank": 3}   # 3 is in FRIENDS[1]
    num_b = {"mulank": 3, "bhagyank": 1}
    sections = ce.zodiac_compare(num_a, "Aries", num_b, "Leo")
    assert any("numerology" in s["title"].lower() for s in sections)
    numerology_section = next(s for s in sections if "numerology" in s["title"].lower())
    assert "harmoni" in numerology_section["body"].lower() or "friend" in numerology_section["body"].lower()


def test_zodiac_compare_same_element():
    num_a = {"mulank": 1, "bhagyank": 1}
    num_b = {"mulank": 1, "bhagyank": 1}
    sections = ce.zodiac_compare(num_a, "Aries", num_b, "Leo")  # both Fire
    zodiac_section = next(s for s in sections if "zodiac" in s["title"].lower())
    assert "fire" in zodiac_section["body"].lower()


def test_guna_milan_same_nakshatra_scores_high():
    # Same nakshatra + same rashi: Varna/Vashya/Yoni/Gana degenerate to
    # their same-group cases; total should be well above half of 36.
    result = ce.guna_milan("Aries", "Ashwini", "Aries", "Ashwini")
    assert result["max_total"] == 36
    assert len(result["kootas"]) == 8
    assert sum(k["max"] for k in result["kootas"]) == 36
    assert result["total"] >= 18


def test_guna_milan_nadi_same_group_scores_zero_on_that_koota():
    # Ashwini and Ardra are both classically Aadi/Vata nadi — same nadi
    # is the one koota that scores 0 regardless of anything else.
    result = ce.guna_milan("Aries", "Ashwini", "Gemini", "Ardra")
    nadi = next(k for k in result["kootas"] if k["name"] == "Nadi")
    assert nadi["score"] == 0


def test_guna_milan_varna_not_tautological():
    # Regression check for the bug caught in plan self-review: Varna must
    # actually discriminate, not always return full score.
    hi = ce.guna_milan("Cancer", "Ashwini", "Cancer", "Ashwini")  # same varna
    lo = ce.guna_milan("Cancer", "Ashwini", "Gemini", "Ashwini")  # Brahmin vs Shudra
    hi_varna = next(k for k in hi["kootas"] if k["name"] == "Varna")["score"]
    lo_varna = next(k for k in lo["kootas"] if k["name"] == "Varna")["score"]
    assert hi_varna == 1
    assert lo_varna == 0


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
