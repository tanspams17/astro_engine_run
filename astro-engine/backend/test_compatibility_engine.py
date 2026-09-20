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
