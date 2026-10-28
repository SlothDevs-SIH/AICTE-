"""Concept matching: do two complaints describe the same kind of problem, whatever words they use?

This is a curated, hand-written lexicon (English, Hinglish and Devanagari phrases grouped into concepts), not
a language model. It can see that "money still not given back" and "fee refund pending" are the same concept.
It can only recognise concepts that are in the list below, and a human can read and edit every entry, which is
why each match can be explained to an officer. Phrases are regular-expression stems.
"""
import re

# concept id -> (label, [phrase stems])
CONCEPTS: dict[str, tuple[str, list[str]]] = {
    "fee_refund": ("Fee refund", [
        r"refund", r"money (?:paid|deposited|taken)", r"(?:given|paid|sent|handed) back", r"not returned",
        r"fees? (?:return|back|wapas)", r"return(?:ing|ed)? (?:of )?(?:the )?(?:fee|money|amount|deposit)",
        r"reimburs", r"caution (?:money|deposit)", r"paise? wapas", r"वापसी", r"रिफंड", r"शुल्क वापस", r"पैसे वापस"]),
    "excess_fee": ("Excess fee", [
        r"excess(?:ive)? fee", r"extra (?:fee|money|charge)", r"overcharg", r"capitation", r"donation",
        r"illegal (?:fee|charge)", r"charging more", r"fee hike", r"अतिरिक्त शुल्क", r"ज्यादा फीस"]),
    "faculty_qualification": ("Faculty qualification", [
        r"fake (?:faculty|experience|teacher)", r"unqualified", r"without (?:the )?(?:required )?qualification",
        r"(?:do|does) not (?:hold|have) (?:the )?(?:degree|qualification|phd)", r"degrees? (?:they|he|she) claim",
        r"faculty (?:qualification|credential)", r"teachers? (?:do|does)? ?not hold", r"fake (?:degree|phd|certificate) of (?:faculty|teacher)",
        r"योग्यता", r"फर्जी शिक्षक"]),
    "intake_excess": ("Admissions above approved intake", [
        r"above (?:the )?(?:approved|sanctioned) (?:intake|strength|seats)", r"beyond (?:the )?(?:approved|sanctioned)",
        r"more students (?:enrolled|admitted|taken)", r"(?:enrolled|admitted) more", r"seats? (?:filled|exceed)",
        r"exceed(?:s|ed|ing)? (?:the )?(?:intake|sanctioned|approved)", r"extra (?:seats|admissions|batch)", r"unapproved (?:intake|seats|batch)",
        r"स्वीकृत सीट"]),
    "infrastructure": ("Infrastructure", [
        r"\blabs?\b", r"laborator", r"librar", r"classroom", r"infrastructure", r"building", r"facilit(?:y|ies) (?:are|is)? ?inadequate",
        r"inadequate", r"insufficient", r"not equipped", r"equipment", r"workshop", r"toilet", r"drinking water", r"प्रयोगशाला", r"पुस्तकालय"]),
    "misleading_claims": ("Misleading advertisement", [
        r"advertis", r"hoarding", r"brochure", r"promis(?:e|es|ed|ing)", r"false claim", r"misleading", r"placement claim",
        r"claims? (?:approval|recognition|placement)", r"100% placement", r"guarantee", r"विज्ञापन", r"झूठा दावा"]),
    "documents_withheld": ("Documents withheld", [
        r"original (?:certificate|document|marksheet|mark sheet)", r"certificates? withheld", r"withh?eld", r"marksheets?",
        r"mark sheets?", r"transfer certificate", r"\btc\b", r"migration certificate", r"refus(?:e|es|ed|ing) to (?:hand|give|return|release|issue)",
        r"not (?:issue|issued|issuing|release|released|giving)", r"hand over", r"degree (?:certificate )?not (?:given|issued)",
        r"मूल दस्तावेज", r"प्रमाण ?पत्र रोक"]),
    "approval_lapse": ("Approval or affiliation lapse", [
        r"approval (?:lapse|expired|not renewed|withdrawn|cancel)", r"lapsed", r"affiliation", r"not renewed", r"without (?:current |valid )?approval",
        r"no (?:current|valid) approval", r"unrecogni[sz]ed", r"recognition", r"not approved", r"\beoa\b", r"मान्यता", r"अनुमोदन"]),
    "harassment": ("Harassment", [
        r"harass", r"ragging", r"bully", r"abus(?:e|es|ed|ive|ively)", r"misbehav", r"threat", r"humiliat", r"molest",
        r"intimidat", r"रैगिंग", r"उत्पीड़न", r"परेशान"]),
    "salary_unpaid": ("Staff salary unpaid", [
        r"salar", r"wages?", r"unpaid", r"not (?:been )?paid", r"stipend", r"pay ?slip", r"वेतन", r"तनख्वाह", r"पगार"]),
    "examination": ("Examination and results", [
        r"\bexams?\b", r"examination", r"\bresults?\b", r"revaluation", r"re-?evaluation", r"backlog", r"परीक्षा", r"परिणाम"]),
}

_COMPILED = {cid: (label, [re.compile(p, re.IGNORECASE) for p in phrases]) for cid, (label, phrases) in CONCEPTS.items()}


def concepts_in(text: str) -> dict[str, list[str]]:
    """Return {concept_id: [matched phrases]} for the concepts found in the text."""
    out: dict[str, list[str]] = {}
    for cid, (_, pats) in _COMPILED.items():
        hits = [m.group(0).lower() for p in pats if (m := p.search(text))]
        if hits:
            out[cid] = sorted(set(hits))
    return out


def concept_similarity(text_a: str, text_b: str) -> tuple[float, dict]:
    """Share of concepts the two texts have in common (0 to 1), with the reasons."""
    ca, cb = concepts_in(text_a), concepts_in(text_b)
    shared = sorted(set(ca) & set(cb))
    union = set(ca) | set(cb)
    score = round(len(shared) / len(union), 3) if union else 0.0
    return score, {
        "method": "concept lexicon (hand-written; not a language model)",
        "shared_concepts": [{"concept": CONCEPTS[c][0], "a_words": ca[c], "b_words": cb[c]} for c in shared],
        "a_concepts": [CONCEPTS[c][0] for c in ca], "b_concepts": [CONCEPTS[c][0] for c in cb],
    }
