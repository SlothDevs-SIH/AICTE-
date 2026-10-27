"""Ask the Dashboard (BACKEND_PLAN 7.5): turns a short question into FILTERS only.

No SQL is ever built from text. Output is a dict of whitelisted filters that the client passes to the
normal /complaints endpoint, which applies the user's own permissions.
"""
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import llm
from app.db.models import Category, Region, Unit
from app.engine.institution import match_institution
from app.services.settings import get_setting

ALLOWED = {"unit", "region", "category", "state", "overdue", "escalated", "has_overlap", "q", "institution_id", "older_than_days"}
STATE_WORDS = {"pending": "RECEIVED", "received": "RECEIVED", "assigned": "ASSIGNED", "under process": "UNDER_PROCESS",
               "in process": "UNDER_PROCESS", "disposed": "DISPOSED", "closed": "DISPOSED", "transferred": "TRANSFERRED",
               "escalated": "ESCALATED", "reopened": "REOPENED"}


def parse_rules(db: Session, text: str) -> dict:
    t = text.casefold()
    f: dict = {}
    for u in db.scalars(select(Unit)):
        if re.search(rf"\b{re.escape(u.code.casefold())}\b", t):
            f["unit"] = u.code
    for r in db.scalars(select(Region)):
        if r.name.casefold() in t or any(s.casefold() in t for s in (r.states or [])):
            f["region"] = r.code
    for c in db.scalars(select(Category)):
        key = c.name.casefold()
        if key in t or any(w in t for w in key.split() if len(w) > 5):
            f["category"] = c.code
    for word, state in STATE_WORDS.items():
        if word in t:
            if state == "ESCALATED":
                f["escalated"] = "true"
            else:
                f["state"] = state
            break
    if re.search(r"overdue|beyond (the )?timeline|past (the )?(due|deadline)", t):
        f["overdue"] = "true"
    if re.search(r"overlap|conflict", t):
        f["has_overlap"] = "true"
    m = re.search(r"older than (\d+) days?|more than (\d+) days? old|over (\d+) days", t)
    if m:
        f["older_than_days"] = int(next(g for g in m.groups() if g))
    m = re.search(r"(?:at|for|of|in)\s+([A-Z][\w .&,'-]{4,})", text)
    if m:
        cands = match_institution(db, m.group(1).strip(" ?.,"))
        if cands:
            f["institution_id"] = cands[0].institution_id
    return f


def validate(db: Session, raw: dict) -> dict:
    """Drop unknown keys and values that are not in the reference tables."""
    units = {u.code for u in db.scalars(select(Unit))}
    regions = {r.code for r in db.scalars(select(Region))}
    cats = {c.code for c in db.scalars(select(Category))}
    states = set(STATE_WORDS.values())
    out: dict = {}
    for k, v in raw.items():
        if k not in ALLOWED:
            continue
        if k == "unit" and v in units: out[k] = v
        elif k == "region" and v in regions: out[k] = v
        elif k == "category" and v in cats: out[k] = v
        elif k == "state" and v in states: out[k] = v
        elif k in ("overdue", "escalated", "has_overlap") and str(v).lower() in ("true", "false"): out[k] = str(v).lower()
        elif k == "older_than_days" and isinstance(v, int) and 0 < v < 5000: out[k] = v
        elif k == "q" and isinstance(v, str) and len(v) < 100: out[k] = v
        elif k == "institution_id" and isinstance(v, str) and len(v) == 36: out[k] = v
    return out


def ask(db: Session, question: str) -> dict:
    used_ai = False
    filters: dict = {}
    if get_setting(db, "ai_llm_enabled") and llm.available():
        text = llm.complete(
            "Convert the user's question into JSON only, using only these keys: unit, region, category, state, "
            "overdue, escalated, has_overlap, older_than_days, q. No prose, no SQL.", question)
        if text:
            try:
                filters = validate(db, json.loads(text[text.index("{"): text.rindex("}") + 1]))
                used_ai = bool(filters)
            except (ValueError, json.JSONDecodeError):
                filters = {}
    if not filters:
        filters = validate(db, parse_rules(db, question))
        used_ai = False
    if not filters:
        return {"parsed_filters": {}, "used_ai": False, "needs_manual_filters": True,
                "explanation": "I could not turn that into filters. Please use the filters on the Complaints page."}
    return {"parsed_filters": filters, "used_ai": used_ai, "needs_manual_filters": False,
            "explanation": "Showing cases where " + ", ".join(f"{k.replace('_', ' ')} = {v}" for k, v in filters.items())}
