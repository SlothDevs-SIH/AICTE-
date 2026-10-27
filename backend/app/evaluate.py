"""Evaluation against the planted ground truth (BACKEND_PLAN 11.2).

Honest limits: these numbers are measured on synthetic data that we also generated, so they show the
rules behave as designed, not how they would perform on real AICTE data. No held-out split is used
yet (the thresholds were set before the data was generated and have not been tuned on it).
"""
import json
from pathlib import Path

from sqlalchemy import select

from app.db.base import session_factory
from app.db.models import Complaint, Institution, Overlap

ROOT = Path(__file__).resolve().parent.parent


def run() -> dict:
    truth = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))
    out = {}
    with session_factory()() as db:
        cases = {c.case_id: c for c in db.scalars(select(Complaint))}
        insts = {i.id: i for i in db.scalars(select(Institution))}
        ovs = list(db.scalars(select(Overlap)))
        pair = {frozenset((o.complaint_a_id, o.complaint_b_id)): o for o in ovs}

        v = [s for s in truth["scenarios"] if s["kind"] == "variant_overlap"]
        ok = sum(1 for s in v if s["resolved"])
        out["variant_name_resolved"] = {"hit": ok, "total": len(v), "rate": round(ok / len(v), 3)}
        v_pair = sum(1 for s in v if frozenset(cases[c].id for c in s["cases"]) in pair)
        out["variant_overlap_detected"] = {"hit": v_pair, "total": len(v)}

        w = [s for s in truth["scenarios"] if s["kind"] == "wording_overlap"]
        w_pair = sum(1 for s in w if frozenset(cases[c].id for c in s["cases"]) in pair)
        out["wording_overlap_detected"] = {"hit": w_pair, "total": len(w),
                                           "note": "found through institution + category rules, not wording"}

        c = [s for s in truth["scenarios"] if s["kind"] == "conflict_pair"]
        c_ok = sum(1 for s in c if (o := pair.get(frozenset(cases[x].id for x in s["cases"]))) and o.severity == "CONFLICT")
        out["conflict_detected"] = {"hit": c_ok, "total": len(c)}

        d = [s for s in truth["scenarios"] if s["kind"] == "decoy"]
        bad = 0
        for s in d:
            case = cases[s["case"]]
            inst = insts.get(case.institution_id) if case.institution_id else None
            if inst and inst.canonical_name == s["must_not_link_to"]:
                bad += 1
        out["decoy_false_merges"] = {"false_merges": bad, "total": len(d)}
        out["decoy_resolved_to_correct_twin"] = {"hit": sum(1 for s in d if s["resolved_ok"]), "total": len(d)}
        out["engine_version"] = ovs[0].engine_version if ovs else None
    print(json.dumps(out, indent=2))
    return out
