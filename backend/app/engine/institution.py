"""Institution matching: L1 (exact ID / exact name or alias) and L2 (fuzzy). BACKEND_PLAN 6.2."""
from dataclasses import dataclass, field

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Institution, InstitutionAlias
from app.engine.normalize import normalize

AUTO_LINK = 0.92  # at or above: treated as the same institution (still shown with evidence)
SUGGEST = 0.78  # between SUGGEST and AUTO_LINK: offered to the officer to confirm


@dataclass
class Candidate:
    institution_id: str
    name: str
    score: float
    layer: str
    evidence: dict = field(default_factory=dict)


def match_institution(
    db: Session, text: str | None, aicte_id: str | None = None,
    state: str | None = None, limit: int = 5,
) -> list[Candidate]:
    out: dict[str, Candidate] = {}
    if aicte_id:
        inst = db.scalar(select(Institution).where(Institution.aicte_id == aicte_id.strip()))
        if inst:
            out[inst.id] = Candidate(
                inst.id, inst.canonical_name, 1.0, "L1",
                {"rule": "exact AICTE ID", "aicte_id": inst.aicte_id},
            )
    if text and text.strip():
        norm = normalize(text)
        rows = [
            (i.id, i.canonical_name, i.normalized_name, "canonical name", i.state)
            for i in db.scalars(select(Institution))
        ]
        names = {r[0]: r for r in rows}
        for a in db.scalars(select(InstitutionAlias)):
            base = names.get(a.institution_id)
            if base:
                rows.append((a.institution_id, base[1], a.normalized_alias, f"alias {a.alias!r}", base[4]))
        for iid, cname, nname, via, inst_state in rows:
            if not nname:
                continue
            if nname == norm:
                score, layer, rule = 0.99, "L1", f"exact normalised {via}"
            else:
                score = max(fuzz.token_sort_ratio(norm, nname), fuzz.ratio(norm, nname)) / 100
                layer, rule = "L2", f"fuzzy match on {via}"
                # a different distinguishing word (e.g. Pune vs Nagpur) caps the score
                a_set, b_set = set(norm.split()), set(nname.split())
                if score >= SUGGEST and a_set ^ b_set and not (a_set <= b_set or b_set <= a_set):
                    score = min(score, 0.88)
                if state and inst_state and state.casefold() == inst_state.casefold():
                    score = min(1.0, score + 0.02)
            prev = out.get(iid)
            if prev is not None and (prev.score >= score or (prev.layer == "L1" and prev.score == 1.0)):
                continue
            out[iid] = Candidate(
                iid, cname, round(score, 3), layer,
                {"rule": rule, "input": text, "normalised_input": norm, "matched_on": nname},
            )
    ranked = sorted(out.values(), key=lambda c: -c.score)
    return [c for c in ranked if c.score >= SUGGEST][:limit]


def resolve(db: Session, text: str | None, aicte_id: str | None, state: str | None = None):
    """Return (institution_id or None, candidates, status). Never guesses below AUTO_LINK."""
    cands = match_institution(db, text, aicte_id, state)
    if cands and cands[0].score >= AUTO_LINK:
        second = cands[1].score if len(cands) > 1 else 0
        if cands[0].score - second >= 0.03 or cands[0].layer == "L1":
            return cands[0].institution_id, cands, "linked"
    return None, cands, ("needs_review" if cands else "unmatched")
