"""Overlap summary: a deterministic template, optionally rewritten by a language model (BACKEND_PLAN 6.9).

The model output is accepted only if it mentions no case ID, unit or number that is not in the input.
Otherwise the template is returned and the response says so.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import llm
from app.db.models import Category, Complaint, Institution, Overlap, Unit


def facts(db: Session, o: Overlap) -> dict:
    a, b = db.get(Complaint, o.complaint_a_id), db.get(Complaint, o.complaint_b_id)
    cats = {c.id: c.name for c in db.scalars(select(Category))}
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    side = lambda c: {"case_id": c.case_id, "unit": units[c.unit_id], "category": cats[c.category_id],  # noqa: E731
                      "state": c.state.replace("_", " ").lower(), "last_action": c.last_action_text or "none recorded",
                      "received": c.received_on.isoformat()}
    return {"institution": db.get(Institution, o.institution_id).canonical_name, "severity": o.severity,
            "type": o.overlap_type, "a": side(a), "b": side(b),
            "reasons": o.receipt_json["layers"]["L4_rules"]["reasons"]}


def template(f: dict) -> str:
    a, b = f["a"], f["b"]
    return (f"{f['institution']} has two open cases handled by different units. "
            f"{a['unit']} case {a['case_id']} ({a['category']}, {a['state']}) — last action: {a['last_action']}. "
            f"{b['unit']} case {b['case_id']} ({b['category']}, {b['state']}) — last action: {b['last_action']}. "
            f"Flagged as {f['severity'].lower()} because: {'; '.join(f['reasons']).lower()}. "
            f"This is a suggestion for officer review; the units should coordinate before acting.")


def _grounded(text: str, f: dict) -> bool:
    allowed = " ".join(str(v) for side in (f["a"], f["b"]) for v in side.values()) + " " + f["institution"] + " " + " ".join(f["reasons"])
    for token in re.findall(r"SMV-\d{4}-\d{6}", text):
        if token not in allowed:
            return False
    for num in re.findall(r"\b\d+\b", text):
        if num not in allowed:
            return False
    return not re.search(r"\b(violat|fraud|guilty|illegal)", text, re.I)  # no accusations


def summarise(db: Session, o: Overlap) -> dict:
    f = facts(db, o)
    base = template(f)
    if llm.available():
        text = llm.complete("Rewrite these facts as two or three plain sentences for a government officer. "
                            "Use only the facts given. Do not accuse anyone. Do not add numbers or IDs.", base)
        if text and _grounded(text, f):
            return {"text": text.strip(), "kind": "AI-written", "reason": None}
        return {"text": base, "kind": "Template summary", "reason": "The model output did not pass the checks, so the template is shown."}
    return {"text": base, "kind": "Template summary", "reason": "AI summaries are switched off."}
