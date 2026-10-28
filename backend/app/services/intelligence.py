"""Issue matching, clusters and the institution risk score (BACKEND_PLAN 6.3, 7.1, 7.2).

`issue_similarity` is LEXICAL (word overlap) and shown for information only. `same_issue` uses the hand-written
concept lexicon in engine/concepts.py, which does see that "money not returned" and "refund pending" are one
concept. Neither is a neural embedding: a local embedding model could not be downloaded on this machine.
"""
import re
from datetime import date, timedelta
from statistics import median

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Complaint, Institution, Overlap
from app.engine.concepts import concept_similarity
from app.engine.normalize import normalize
from app.services.settings import get_setting

OPEN = ("RECEIVED", "ASSIGNED", "UNDER_PROCESS", "ESCALATED", "REOPENED", "TRANSFERRED")
STOP = {"the", "a", "an", "is", "are", "not", "to", "in", "on", "at", "for", "by", "with", "has", "have",
        "was", "were", "be", "been", "college", "institute", "students", "student", "complaint", "case"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", normalize(text)) if w not in STOP and len(w) > 2}


def issue_similarity(a: Complaint, b: Complaint) -> tuple[float, dict]:
    ta, tb = f"{a.title} {a.description}", f"{b.title} {b.description}"
    wa, wb = _words(ta), _words(tb)
    jacc = len(wa & wb) / len(wa | wb) if wa | wb else 0.0
    fz = fuzz.token_set_ratio(normalize(a.title), normalize(b.title)) / 100
    score = round(0.5 * jacc + 0.5 * fz * (1 if wa & wb else 0.5), 3)
    return score, {"method": "lexical (word overlap + fuzzy title)", "shared_words": sorted(wa & wb),
                   "word_overlap": round(jacc, 3), "title_similarity": round(fz, 3)}


def same_issue(a: Complaint, b: Complaint) -> tuple[float, dict]:
    """Concept-level similarity of two complaints: same problem, whatever the words (engine.concepts)."""
    return concept_similarity(f"{a.title}. {a.description}", f"{b.title}. {b.description}")


def clusters(db: Session, institution_id: str | None = None) -> list[dict]:
    min_size = int(get_setting(db, "cluster_min_size"))
    window = int(get_setting(db, "cluster_window_days"))
    since = date.today() - timedelta(days=window)
    q = select(Complaint).where(Complaint.institution_id.is_not(None), Complaint.state.in_(OPEN),
                                Complaint.received_on >= since)
    if institution_id:
        q = q.where(Complaint.institution_id == institution_id)
    groups: dict[tuple, list[Complaint]] = {}
    for c in db.scalars(q):
        groups.setdefault((c.institution_id, c.category_id), []).append(c)
    insts = {i.id: i for i in db.scalars(select(Institution))}
    cats = {c.id: c.name for c in db.scalars(select(Category))}
    out = []
    for (iid, cid), cs in groups.items():
        if len(cs) < min_size:
            continue
        cs.sort(key=lambda c: c.received_on)
        out.append({"institution_id": iid, "institution": insts[iid].canonical_name, "category": cats[cid],
                    "size": len(cs), "first": cs[0].received_on.isoformat(), "last": cs[-1].received_on.isoformat(),
                    "days": (cs[-1].received_on - cs[0].received_on).days + 1,
                    "label": f"{len(cs)} similar complaints in {(cs[-1].received_on - cs[0].received_on).days + 1} days",
                    "cases": [c.case_id for c in cs], "severity": "SYSTEMIC"})
    return sorted(out, key=lambda r: -r["size"])


def risk_score(db: Session, inst: Institution, today: date | None = None) -> dict:
    today = today or date.today()
    w = get_setting(db, "risk_weights")
    cats = {c.id: c for c in db.scalars(select(Category))}
    cs = list(db.scalars(select(Complaint).where(Complaint.institution_id == inst.id)))
    open_cs = [c for c in cs if c.state in OPEN]
    year = today - timedelta(days=365)
    recent_open = [c for c in open_cs if c.received_on >= year]
    ages = [(today - c.received_on).days for c in open_cs]
    units = {c.unit_id for c in open_cs}
    seen: dict[str, int] = {}
    repeats = 0
    for c in sorted(cs, key=lambda c: c.received_on):
        if seen.get(c.category_id):
            repeats += 1
        seen[c.category_id] = seen.get(c.category_id, 0) + 1
    maxw = max([c.severity_weight for c in cats.values()] or [1])
    sev = (sum(cats[c.category_id].severity_weight for c in open_cs) / len(open_cs) / maxw) if open_cs else 0
    conflicts = len(list(db.scalars(select(Overlap).where(
        Overlap.institution_id == inst.id, Overlap.severity == "CONFLICT",
        Overlap.status.in_(("SUGGESTED", "CONFIRMED", "LINKED"))))))
    last90 = sum(1 for c in cs if (today - c.received_on).days <= 90)
    prev90 = sum(1 for c in cs if 90 < (today - c.received_on).days <= 180)
    comp = {
        "volume": min(len(recent_open) / 10, 1),
        "ageing": min((median(ages) if ages else 0) / 180, 1),
        "multi_unit": min(max(len(units) - 1, 0) / 2, 1),
        "repeat": (repeats / len(cs)) if cs else 0,
        "severity": sev,
        "open_conflicts": min(conflicts / 3, 1),
        "trend": max(0.0, min(((last90 - prev90) / prev90) if prev90 else (1.0 if last90 > 1 else 0.0), 1)),
    }
    score = round(100 * sum(w[k] * comp[k] for k in comp), 1)
    return {"institution_id": inst.id, "institution": inst.canonical_name, "score": score,
            "components": [{"name": k, "value": round(v, 3), "weight": w[k], "points": round(100 * w[k] * v, 1)}
                           for k, v in comp.items()],
            "open_cases": len(open_cs), "note": "Score is a ranking aid based on complaint data only."}


def ranking(db: Session, limit: int = 20) -> list[dict]:
    # only colleges that have an open case can rank, so a registry of thousands of real colleges stays fast
    with_open = select(Complaint.institution_id).where(Complaint.institution_id.is_not(None),
                                                       Complaint.state.in_(OPEN)).distinct()
    rows = [risk_score(db, i) for i in db.scalars(select(Institution).where(Institution.id.in_(with_open)))]
    rows = [r for r in rows if r["open_cases"] > 0]
    return sorted(rows, key=lambda r: -r["score"])[:limit]
