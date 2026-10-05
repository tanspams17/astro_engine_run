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
    sections, score = ce.zodiac_compare("Ava", num_a, "Aries", "Rahul", num_b, "Leo")
    assert any("numerology" in s["title"].lower() for s in sections)
    numerology_section = next(s for s in sections if "numerology" in s["title"].lower())
    assert "harmoni" in numerology_section["body"].lower() or "friend" in numerology_section["body"].lower()
    assert "Ava" in numerology_section["body"] and "Rahul" in numerology_section["body"]
    assert 0 < score["total"] <= score["max"]


def test_zodiac_compare_same_element():
    num_a = {"mulank": 1, "bhagyank": 1}
    num_b = {"mulank": 1, "bhagyank": 1}
    sections, score = ce.zodiac_compare("Ava", num_a, "Aries", "Rahul", num_b, "Leo")  # both Fire
    zodiac_section = next(s for s in sections if "zodiac" in s["title"].lower())
    assert "fire" in zodiac_section["body"].lower()
    assert "Ava" in zodiac_section["body"] and "Rahul" in zodiac_section["body"]
    # same mulank + same element should score at the top of the scale
    assert score["total"] == score["max"]


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


def _k(result, name):
    return next(k for k in result["kootas"] if k["name"] == name)


def test_guna_milan_varna_is_directional():
    # Groom's varna must be equal or higher than the bride's to score.
    ok = ce.guna_milan("Cancer", "Ashwini", "Gemini", "Ashwini")            # Brahmin groom, Shudra bride
    bad = ce.guna_milan("Gemini", "Ashwini", "Cancer", "Ashwini")           # Shudra groom, Brahmin bride
    same = ce.guna_milan("Cancer", "Ashwini", "Cancer", "Ashwini")
    assert _k(ok, "Varna")["score"] == 1
    assert _k(bad, "Varna")["score"] == 0
    assert _k(same, "Varna")["score"] == 1
    # swapping who is groom flips it
    flipped = ce.guna_milan("Cancer", "Ashwini", "Gemini", "Ashwini", a_is_groom=False)
    assert _k(flipped, "Varna")["score"] == 0


def test_nadi_groups_krittika_and_mrigashira():
    # Regression: Krittika is Antya and Mrigashira is Madhya (they were swapped).
    assert ce.NADI_NAME[ce._nadi_index("Krittika")].startswith("Antya")
    assert ce.NADI_NAME[ce._nadi_index("Mrigashira")].startswith("Madhya")
    assert _k(ce.guna_milan("Aries", "Krittika", "Taurus", "Rohini"), "Nadi")["score"] == 0   # both Antya
    assert _k(ce.guna_milan("Taurus", "Mrigashira", "Aries", "Bharani"), "Nadi")["score"] == 0  # both Madhya
    assert _k(ce.guna_milan("Aries", "Krittika", "Taurus", "Mrigashira"), "Nadi")["score"] == 8


def test_nadi_and_gana_groups_are_even():
    for k in range(3):
        assert sum(1 for n in ce.NAKSHATRAS if ce._nadi_index(n) == k) == 9
    for g in ce.GANA_ORDER:
        assert list(ce.GANA.values()).count(g) == 9


def test_yoni_matrix_symmetric_with_classical_enemies():
    m = ce.YONI_MATRIX
    assert all(m[i][j] == m[j][i] for i in range(14) for j in range(14))
    zeros = {frozenset({ce.YONI_ORDER[i], ce.YONI_ORDER[j]})
             for i in range(14) for j in range(i + 1, 14) if m[i][j] == 0}
    assert zeros == {frozenset(p) for p in [("Cow", "Tiger"), ("Elephant", "Lion"), ("Horse", "Buffalo"),
                                            ("Dog", "Deer"), ("Sheep", "Monkey"), ("Serpent", "Mongoose"),
                                            ("Rat", "Cat")]}
    assert all(m[i][i] == 4 for i in range(14))


def test_yoni_scores():
    assert _k(ce.guna_milan("Aries", "Ashwini", "Aries", "Shatabhisha"), "Yoni")["score"] == 4   # Horse/Horse
    assert _k(ce.guna_milan("Aries", "Ashwini", "Virgo", "Hasta"), "Yoni")["score"] == 0         # Horse/Buffalo
    assert _k(ce.guna_milan("Aries", "Ashwini", "Taurus", "Rohini"), "Yoni")["score"] == 3       # Horse/Serpent


def test_gana_is_directional():
    # groom Rakshasa (Krittika), bride Deva (Ashwini) -> 0; groom Deva, bride Rakshasa -> 1
    assert _k(ce.guna_milan("Taurus", "Krittika", "Aries", "Ashwini"), "Gana")["score"] == 0
    assert _k(ce.guna_milan("Aries", "Ashwini", "Taurus", "Krittika"), "Gana")["score"] == 1
    assert _k(ce.guna_milan("Aries", "Ashwini", "Gemini", "Punarvasu"), "Gana")["score"] == 6


def test_bhakoot_dosha_distances():
    for bride, expected in [("Taurus", 0), ("Gemini", 7), ("Leo", 0), ("Virgo", 0),
                            ("Libra", 7), ("Scorpio", 0), ("Sagittarius", 0), ("Pisces", 0)]:
        # Aries groom with each bride sign: 2,3,5,6,7,8,9,12
        assert _k(ce.guna_milan("Aries", "Ashwini", bride, "Ashwini"), "Bhakoot")["score"] == expected, bride


def test_graha_maitri():
    assert _k(ce.guna_milan("Taurus", "Ashwini", "Libra", "Ashwini"), "Graha Maitri")["score"] == 5  # same lord
    assert _k(ce.guna_milan("Leo", "Ashwini", "Taurus", "Ashwini"), "Graha Maitri")["score"] == 0   # Sun/Venus
    assert _k(ce.guna_milan("Cancer", "Ashwini", "Gemini", "Ashwini"), "Graha Maitri")["score"] == 1  # Moon/Mercury


def test_vashya_uses_degree_for_split_signs():
    manava = ce._vashya_group("Sagittarius", 10)
    chatush = ce._vashya_group("Sagittarius", 20)
    assert (manava, chatush) == ("Manava", "Chatushpada")
    assert (ce._vashya_group("Capricorn", 5), ce._vashya_group("Capricorn", 25)) == ("Chatushpada", "Jalachara")
    assert ce._vashya_group("Leo", 0) == "Vanachara"


def test_scores_never_exceed_maximums():
    for gi, gn in enumerate(ce.NAKSHATRAS):
        for bn in ce.NAKSHATRAS:
            r = ce.guna_milan(ce.SIGNS[gi % 12], gn, ce.SIGNS[(gi * 5 + 3) % 12], bn)
            assert r["total"] <= 36
            assert all(0 <= k["score"] <= k["max"] for k in r["kootas"])


def test_assign_roles():
    assert ce.assign_roles("male", "female") == (True, "gender")
    assert ce.assign_roles("female", "male") == (False, "gender")
    assert ce.assign_roles("unspecified", "female") == (True, "gender")
    assert ce.assign_roles("unspecified", "male") == (False, "gender")
    assert ce.assign_roles("female", "unspecified") == (False, "gender")
    assert ce.assign_roles("male", "male") == (True, "order")
    assert ce.assign_roles("unspecified", "unspecified") == (True, "order")


def test_mangal_dosha():
    assert ce.mangal_dosha("Aries", "Aries", "Cancer")["by_lagna"] is True      # 1st from lagna
    assert ce.mangal_dosha("Taurus", "Aries", "Cancer")["by_lagna"] is True     # 2nd
    assert ce.mangal_dosha("Gemini", "Aries", "Cancer")["by_lagna"] is False    # 3rd
    assert ce.mangal_dosha("Libra", "Aries", "Cancer")["by_lagna"] is True      # 7th
    r = ce.mangal_dosha("Cancer", None, "Aries")                                # unknown birth time
    assert r["from_lagna"] is None and r["by_moon"] is True and r["present"] is True  # 4th from Moon


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
