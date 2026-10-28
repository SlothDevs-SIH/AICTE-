"""Concept matching must pair the same issue in different words, and must not pair different issues."""
from app.engine.concepts import concept_similarity, concepts_in
from app.seed import ALT_TITLES, TITLES


def test_every_planted_different_wording_pair_is_matched():
    missed = [cat for cat, alt in ALT_TITLES.items()
              if concept_similarity(TITLES[cat][0], alt)[0] == 0 and concept_similarity(TITLES[cat][1], alt)[0] == 0]
    assert missed == []


def test_different_issues_are_not_matched():
    bad = []
    for ca, alt in ALT_TITLES.items():
        for cb, titles in TITLES.items():
            if ca != cb and any(concept_similarity(t, alt)[0] > 0 for t in titles):
                bad.append((ca, cb))
    # A hoarding that promises recognition the college lacks is genuinely about approval too.
    assert bad == [("MISLEADING_AD", "APPROVAL_LAPSE")], bad


def test_hinglish_and_devanagari_phrases():
    assert "fee_refund" in concepts_in("शुल्क वापसी अभी तक नहीं मिली")
    assert "fee_refund" in concepts_in("college is not giving fees wapas")
    assert "harassment" in concepts_in("रैगिंग की शिकायत")


def test_complaint_search_finds_a_college_by_part_of_its_name_or_a_misspelling(client, tokens):
    h = tokens["officer.rb"]
    row = client.get("/api/v1/complaints?limit=1&has_overlap=true", headers=h).json()["items"][0]
    name = row["institution"]
    words = name.split()
    partial = " ".join(reversed(words[:2]))                  # words in the wrong order
    typo = name.replace("a", "e", 2)                          # two wrong letters
    for q in (partial, typo):
        got = client.get("/api/v1/complaints", params={"q": q, "limit": 200}, headers=h).json()["items"]
        assert row["id"] in [r["id"] for r in got], q


def test_receipt_reasons_are_given():
    score, why = concept_similarity("Fee refund pending", "Money paid at admission still not given back")
    assert score > 0 and why["shared_concepts"][0]["concept"] == "Fee refund"
    assert "not a language model" in why["method"]
