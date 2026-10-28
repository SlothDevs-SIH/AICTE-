"""Overlap rules (L4) and Match Receipt. BACKEND_PLAN 6.5 / 6.8.

Types built here:
  O1  same institution, different units, both open            -> RELATED
  O2  O1 and the same complaint category                       -> RELATED
  O3  a regulatory action is recorded/planned on either case   -> CONFLICT
  O4  O1 and the complaint texts describe the same issue (concept lexicon, any wording)
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.db.models import Category, Complaint, Overlap
from app.services.intelligence import issue_similarity, same_issue

ENGINE_VERSION = "rules-1.0"
OPEN_STATES = ("RECEIVED", "ASSIGNED", "UNDER_PROCESS", "ESCALATED", "REOPENED", "TRANSFERRED")
ACTION_WORDS = ("penalty", "closure", "show cause", "show-cause", "withdraw", "notice", "debar")


def has_action(c: Complaint) -> bool:
    text = " ".join(filter(None, [c.last_action_text, c.next_action_text])).casefold()
    return any(w in text for w in ACTION_WORDS)


def classify(a: Complaint, b: Complaint) -> tuple[str, str, float, list[str]] | None:
    """Return (type, severity, score, reasons) for two open complaints at one institution."""
    if a.unit_id == b.unit_id:
        return None
    reasons = ["Same institution", "Handled by different units", "Both cases still open"]
    kind, sev, score = "O1", "RELATED", 0.55
    if a.category_id == b.category_id:
        reasons.append("Same complaint category")
        kind, score = "O2", 0.7
    sim, why = same_issue(a, b)
    if why["shared_concepts"]:
        names = ", ".join(s["concept"] for s in why["shared_concepts"])
        reasons.append(f"Same issue in the complaint text ({names}), even if worded differently")
        if kind == "O1":
            kind = "O4"
        score = min(0.85, score + 0.15)
    if has_action(a) or has_action(b):
        reasons.append("A regulatory action is recorded or planned on one of the cases")
        kind, sev, score = "O3", "CONFLICT", 0.9
    return kind, sev, score, reasons


def scan_complaint(db: Session, c: Complaint, actor_id: str | None = None) -> list[Overlap]:
    """Compare a complaint with the other open complaints at its institution."""
    if not c.institution_id or c.state not in OPEN_STATES:
        return []
    others = db.scalars(
        select(Complaint).where(
            Complaint.institution_id == c.institution_id,
            Complaint.id != c.id,
            Complaint.state.in_(OPEN_STATES),
        )
    ).all()
    cats = {x.id: x.name for x in db.scalars(select(Category))}
    created: list[Overlap] = []
    for o in others:
        res = classify(c, o)
        if res is None:
            continue
        kind, sev, score, reasons = res
        a, b = sorted((c, o), key=lambda x: x.id)
        if db.scalar(
            select(Overlap).where(Overlap.complaint_a_id == a.id, Overlap.complaint_b_id == b.id)
        ):
            continue
        receipt = {
            "layers": {
                "L1_institution": {
                    "matched": True,
                    "institution_id": c.institution_id,
                    "how": "both cases are linked to the same institution record",
                },
                "L2_fuzzy_name": {
                    "inputs": [a.institution_text_raw, b.institution_text_raw],
                    "how": "the institution name typed on each case was matched to the registry",
                },
                "L3_issue": {
                    "used": True,
                    "concept_score": same_issue(a, b)[0],
                    "concepts": same_issue(a, b)[1],
                    "lexical_score": issue_similarity(a, b)[0],
                    "formula": "each complaint text is read for known problem concepts (fee refund, faculty "
                    "qualification, approval lapse and so on) from a hand-written list in English, Hinglish and "
                    "Devanagari. Shared concepts raise the score and are listed here. This is not a language "
                    "model: a problem described in a way the list does not know is not seen. The plain "
                    "word-overlap score is shown for information only",
                },
                "L4_rules": {"type": kind, "severity": sev, "reasons": reasons},
            },
            "categories": [cats.get(a.category_id), cats.get(b.category_id)],
            "note": "Suggested overlap for officer review. The system does not act on it.",
        }
        ov = Overlap(
            complaint_a_id=a.id, complaint_b_id=b.id, institution_id=c.institution_id,
            overlap_type=kind, severity=sev, match_score=score, receipt_json=receipt,
            status="SUGGESTED", detected_at=datetime.now(UTC), engine_version=ENGINE_VERSION,
        )
        db.add(ov)
        db.flush()
        write_audit(db, actor_id, "OVERLAP_SUGGESTED", "overlap", ov.id,
                    {"type": kind, "severity": sev, "a": a.case_id, "b": b.case_id})
        created.append(ov)
    return created


def gate_check(db: Session, institution_id: str, complaint_id: str | None, unit_id: str | None) -> dict:
    """What an officer is shown before taking a regulatory action (MASTER_PLAN 4.4)."""
    q = select(Complaint).where(
        Complaint.institution_id == institution_id, Complaint.state.in_(OPEN_STATES)
    )
    if complaint_id:
        q = q.where(Complaint.id != complaint_id)
    others = [c for c in db.scalars(q) if c.unit_id != unit_id]
    conflict = {c.id for c in others if has_action(c) or c.state == "ESCALATED"}
    result = "CONFLICT" if conflict else ("RELATED" if others else "CLEAR")
    return {
        "result": result,
        "other_cases": [
            {
                "id": c.id, "case_id": c.case_id, "unit_id": c.unit_id, "state": c.state,
                "title": c.title, "last_action_text": c.last_action_text,
                "reason": "a regulatory action is recorded or the case is escalated"
                if c.id in conflict else "open case at the same institution",
            }
            for c in others
        ],
    }
