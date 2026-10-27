"""Deterministic synthetic data (BACKEND_PLAN 11.1). Every row is_synthetic=True.

Deviation from MASTER_PLAN section 8 (recorded in the Designed vs Built table): the plan says
about 40 institutions; the planted scenarios need 60 distinct institutions to stay independent.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.crypto import encrypt
from app.core.roles import (
    ADMIN, AUDITOR, COMPETENT_AUTHORITY, MANAGEMENT, REGIONAL_OFFICER, UNIT_OFFICER, UNIT_SUPERVISOR,
)
from app.core.security import hash_password
from app.db.models import Category, Institution, InstitutionAlias, Region, Unit, User
from app.engine.normalize import normalize
from app.engine.overlap import scan_complaint
from app.services import complaints as svc

DEMO_PASSWORD = "Demo@12345"  # synthetic demo accounts only; never reused anywhere real

UNITS = [("RB", "Regulation Bureau", "bureau"), ("PGRC", "Public Grievance Redressal Cell", "cell"),
         ("RO-W", "Western Regional Office", "regional")]
REGIONS = [("NR", "Northern", ["Delhi", "Punjab", "Haryana", "Uttar Pradesh"]),
           ("WR", "Western", ["Maharashtra", "Gujarat", "Goa"]),
           ("SR", "Southern", ["Karnataka", "Tamil Nadu", "Kerala", "Telangana"]),
           ("ER", "Eastern", ["West Bengal", "Odisha", "Bihar"]),
           ("CR", "Central", ["Madhya Pradesh", "Chhattisgarh"])]
CATEGORIES = [("FEE_REFUND", "Fee refund", 2, 30), ("FAKE_FACULTY", "Fake or unqualified faculty", 4, 45),
              ("UNAPPROVED_INTAKE", "Unapproved intake", 5, 30), ("INFRASTRUCTURE", "Infrastructure shortfall", 3, 60),
              ("MISLEADING_AD", "Misleading advertisement", 3, 30), ("DOCUMENTS", "Withholding of documents", 2, 21),
              ("APPROVAL_LAPSE", "Affiliation or approval lapse", 5, 45), ("HARASSMENT", "Harassment", 4, 30)]
CITIES = {"WR": [("Pune", "Maharashtra"), ("Nagpur", "Maharashtra"), ("Nashik", "Maharashtra"),
                 ("Ahmedabad", "Gujarat"), ("Surat", "Gujarat"), ("Panaji", "Goa")],
          "NR": [("Lucknow", "Uttar Pradesh"), ("Noida", "Uttar Pradesh"), ("Ludhiana", "Punjab"),
                 ("Gurugram", "Haryana"), ("New Delhi", "Delhi")],
          "SR": [("Bengaluru", "Karnataka"), ("Mysuru", "Karnataka"), ("Coimbatore", "Tamil Nadu"),
                 ("Chennai", "Tamil Nadu"), ("Kochi", "Kerala"), ("Hyderabad", "Telangana")],
          "ER": [("Kolkata", "West Bengal"), ("Bhubaneswar", "Odisha"), ("Patna", "Bihar"), ("Durgapur", "West Bengal")],
          "CR": [("Bhopal", "Madhya Pradesh"), ("Indore", "Madhya Pradesh"), ("Raipur", "Chhattisgarh")]}
PREFIX = ["Shri Ramdeo", "Sant Gadge", "Maharaja Agrasen", "Vidya Bharati", "National", "Bharat", "Sardar Patel",
          "Netaji", "Dr. Ambedkar", "Rajiv Gandhi", "Kalam", "Tagore", "Sai Krupa", "Gyan Ganga", "Lakshmi Narayan",
          "Mahatma Gandhi", "Indira", "Jawahar", "Shivaji", "Annapurna", "Saraswati", "Aryabhatta", "Chanakya",
          "Vivekananda", "Subhas", "Raman", "Bhaskara", "Patanjali", "Kautilya", "Tulsi", "Ganga", "Yamuna",
          "Narmada", "Godavari", "Krishna", "Kaveri", "Himalaya", "Vindhya", "Aravali", "Nilgiri", "Sahyadri",
          "Deccan", "Malwa", "Konkan", "Awadh", "Magadh", "Kalinga", "Anand", "Prabhat", "Navjeevan", "Udaya",
          "Sunrise", "Horizon", "Pioneer", "Zenith", "Apex", "Orchid", "Lotus", "Banyan", "Peepal"]
KIND = ["Institute of Technology", "College of Engineering", "Institute of Management Studies",
        "Polytechnic", "Institute of Engineering and Technology", "School of Pharmacy"]
TITLES = {
    "FEE_REFUND": ["Refund of fees not returned after withdrawal", "Fee refund pending since admission cancelled"],
    "FAKE_FACULTY": ["Faculty without required qualification teaching", "Fake experience certificates of faculty"],
    "UNAPPROVED_INTAKE": ["Admissions above approved intake", "Seats filled beyond sanctioned strength"],
    "INFRASTRUCTURE": ["Laboratories not equipped as per norms", "Insufficient classrooms and library"],
    "MISLEADING_AD": ["Advertisement claims approval that is not granted", "Placement claims in advertisement are false"],
    "DOCUMENTS": ["Original certificates withheld by college", "Transfer certificate not issued"],
    "APPROVAL_LAPSE": ["Approval lapsed but admissions continuing", "Affiliation not renewed this year"],
    "HARASSMENT": ["Student harassed by staff member", "Ragging complaint not acted upon"],
}
ALT_TITLES = {  # same issue, different wording (planted for the not-yet-built L3 layer)
    "FEE_REFUND": "Money paid at admission still not given back",
    "FAKE_FACULTY": "Teachers do not hold the degrees they claim",
    "UNAPPROVED_INTAKE": "More students enrolled than AICTE allows",
    "INFRASTRUCTURE": "Labs and building facilities are inadequate",
    "MISLEADING_AD": "Hoardings promise recognition the college lacks",
    "DOCUMENTS": "College refuses to hand over my marksheets",
    "APPROVAL_LAPSE": "College running without current approval",
    "HARASSMENT": "Faculty member behaves abusively with students",
}
CONFLICT_ACTIONS = ["Show-cause notice issued", "Penalty proposed", "Closure order drafted", "Notice issued for withdrawal of approval"]


def variants(rng: random.Random, name: str, city: str) -> list[str]:
    out = []
    words = name.replace(",", "").split()
    abbr = (name.replace("Institute", "Inst.").replace("Technology", "Tech.").replace("Engineering", "Engg.")
            .replace("College", "Coll.").replace("Management", "Mgmt."))
    out.append(abbr)
    i = rng.randrange(3, max(4, len(name) - 3))
    out.append(name[:i] + name[i + 1:] if name[i] != " " else name)  # dropped letter typo
    out.append(" ".join(reversed(words[:2])) + " " + " ".join(words[2:]) if len(words) > 3 else name.upper())
    out.append(name.upper().replace(",", ""))
    out.append(f"{words[0]} {words[1]} {' '.join(words[2:])} ({city})")
    seen, res = {normalize(name)}, []
    for v in out:
        n = normalize(v)
        if n not in seen:
            seen.add(n)
            res.append(v)
    return res


def seed(db: Session, seed_value: int = 42, ground_truth_path: Path | None = None) -> dict:
    rng = random.Random(seed_value)
    today = date.today()
    units = {}
    for code, name, kind in UNITS:
        u = Unit(code=code, name=name, kind=kind)
        db.add(u)
        units[code] = u
    regions = {}
    for code, name, states in REGIONS:
        r = Region(code=code, name=name, states=states)
        db.add(r)
        regions[code] = r
    cats = {}
    for code, name, w, sla in CATEGORIES:
        c = Category(code=code, name=name, severity_weight=w, sla_days=sla)
        db.add(c)
        cats[code] = c
    db.flush()

    pw = hash_password(DEMO_PASSWORD)
    people = [
        ("officer.rb@demo.samanvay.in", "Anil Kulkarni (RB officer)", UNIT_OFFICER, "RB", None),
        ("officer2.rb@demo.samanvay.in", "Meera Nair (RB officer)", UNIT_OFFICER, "RB", None),
        ("supervisor.rb@demo.samanvay.in", "Rakesh Sharma (RB supervisor)", UNIT_SUPERVISOR, "RB", None),
        ("officer.pgrc@demo.samanvay.in", "Sunita Verma (PGRC officer)", UNIT_OFFICER, "PGRC", None),
        ("officer2.pgrc@demo.samanvay.in", "Imran Sheikh (PGRC officer)", UNIT_OFFICER, "PGRC", None),
        ("supervisor.pgrc@demo.samanvay.in", "Kavita Rao (PGRC supervisor)", UNIT_SUPERVISOR, "PGRC", None),
        ("regional.west@demo.samanvay.in", "Deepak Joshi (Western regional officer)", REGIONAL_OFFICER, "RO-W", "WR"),
        ("management@demo.samanvay.in", "Dr. Pooja Menon (Management)", MANAGEMENT, None, None),
        ("authority@demo.samanvay.in", "Dr. S. Raghavan (Competent Authority)", COMPETENT_AUTHORITY, None, None),
        ("admin@demo.samanvay.in", "System Admin", ADMIN, None, None),
        ("auditor@demo.samanvay.in", "Neha Iyer (Auditor)", AUDITOR, None, None),
    ]
    users = {}
    for email, name, role, ucode, rcode in people:
        u = User(email=email, name=name, password_hash=pw, role=role,
                 unit_id=units[ucode].id if ucode else None, region_id=regions[rcode].id if rcode else None)
        db.add(u)
        users[email.split("@")[0]] = u
    db.flush()

    # ---- institutions ----
    insts: list[Institution] = []
    used = set()

    def make_inst(region_code: str, decoy_of: Institution | None = None) -> Institution:
        city, state = rng.choice(CITIES[region_code]) if not decoy_of else (decoy_of.district, decoy_of.state)
        while True:
            if decoy_of:
                first = decoy_of.canonical_name.split(",")[0]
                words = first.split()
                kind = rng.choice([k for k in KIND if k not in first])
                name = f"{' '.join(words[:2])} {kind}, {city}"
            else:
                name = f"{rng.choice(PREFIX)} {rng.choice(KIND)}, {city}"
            if name not in used:
                used.add(name)
                break
        i = Institution(aicte_id=f"1-{rng.randrange(10**8, 10**9)}", canonical_name=name,
                        normalized_name=normalize(name), short_name=None, type="Engineering/Technology",
                        state=state, district=city, pincode=str(rng.randrange(400000, 800000)),
                        region_id=regions[region_code].id, address=f"{rng.randrange(1, 300)}, Main Road, {city}",
                        is_synthetic=True)
        db.add(i)
        db.flush()
        for v in variants(rng, name, city)[: rng.randrange(1, 4)] if not decoy_of else []:
            db.add(InstitutionAlias(institution_id=i.id, alias=v, normalized_alias=normalize(v), source="seed"))
        insts.append(i)
        return i

    rcodes = list(CITIES)
    group = {"variant": [], "wording": [], "conflict": [], "filler": []}
    for kind, n in (("variant", 20), ("wording", 15), ("conflict", 8), ("filler", 7)):
        for _ in range(n):
            group[kind].append(make_inst(rng.choice(rcodes)))
    decoys = [make_inst("WR", decoy_of=i) for i in group["variant"][:10]]
    db.flush()

    unit_ids = {c: u.id for c, u in units.items()}
    officers = {"RB": [users["officer.rb"], users["officer2.rb"]], "PGRC": [users["officer.pgrc"], users["officer2.pgrc"]],
                "RO-W": [users["regional.west"]]}
    refno = {"RB": 0, "PGRC": 0, "RO-W": 0}
    truth = {"seed": seed_value, "synthetic": True, "scenarios": []}

    def case(unit: str, inst: Institution, cat: str, title: str, raw: str | None, age: int,
             state: str = "UNDER_PROCESS", last: str | None = None, next_: str | None = None,
             due_delta: int | None = None, esc: int = 0, pii: bool = True, desc: str | None = None):
        refno[unit] += 1
        owner = rng.choice(officers[unit])
        c = svc.create_complaint(
            db, owner, unit_id=unit_ids[unit], reference_no=f"{unit}/{today.year}/{refno[unit]:04d}",
            category_id=cats[cat].id, title=title, description=desc or f"{title}. Reported against {raw or inst.canonical_name}.",
            institution_id=None, institution_text_raw=raw or inst.canonical_name, aicte_id_raw=None,
            received_on=today - timedelta(days=age), case_id=None)
        return c, owner

    # Institutions are resolved through the real matcher so the data tests the engine.
    from app.engine.institution import resolve

    def attach(c, owner, inst: Institution, state, last, next_, due_delta, esc):
        iid, cands, status = resolve(db, c.institution_text_raw, None)
        c.institution_id = iid
        c.owner_user_id = owner.id
        if state != "RECEIVED":
            c.state = "UNDER_PROCESS" if state in ("UNDER_PROCESS", "ESCALATED", "DISPOSED") else state
            svc.add_event(db, c, "ASSIGNED", owner, "Assigned to officer", "RECEIVED", "ASSIGNED")
            svc.add_event(db, c, "STATE_CHANGED", owner, last or "Under examination", "ASSIGNED", "UNDER_PROCESS")
        if last:
            c.last_action_text = last
            c.last_action_at = svc.now() - timedelta(days=rng.randrange(1, 12))
        c.next_action_text = next_ or "Seek reply from the institution"
        c.next_action_due_on = today + timedelta(days=rng.randrange(3, 20))
        if due_delta is not None:
            c.due_on = c.expected_disposal_on = today + timedelta(days=due_delta)
        if state == "ESCALATED":
            c.state, c.escalation_level = "ESCALATED", esc
            sup = users["supervisor.rb"] if c.unit_id == unit_ids["RB"] else users["supervisor.pgrc"]
            c.escalated_to_user_id = (sup if esc == 2 else users["authority"]).id
            svc.add_event(db, c, "ESCALATED", owner, "Escalated: no reply from institution after two reminders",
                          "UNDER_PROCESS", "ESCALATED", {"level": esc})
        if state == "DISPOSED":
            c.state = "DISPOSED"
            svc.add_event(db, c, "STATE_CHANGED", owner, "Disposed after institution complied", "UNDER_PROCESS", "DISPOSED")
        c.complainant_name_enc = encrypt(rng.choice(["Rohan Patil", "Asha Kulkarni", "Vikram Singh", "Priya Nair", "Faizal Khan"]))
        c.complainant_phone_enc = encrypt(f"9{rng.randrange(10**8, 10**9)}")
        c.complainant_email_enc = encrypt(f"user{rng.randrange(1000, 9999)}@example.invalid")
        db.flush()
        scan_complaint(db, c, owner.id)
        return status

    cat_codes = list(cats)
    # 20 true overlaps with spelling variants only
    for inst in group["variant"]:
        cat = rng.choice(cat_codes)
        al = [a for a in db.query(InstitutionAlias).filter_by(institution_id=inst.id)]
        raw2 = rng.choice([a.alias for a in al]) if al and rng.random() < 0.5 else variants(rng, inst.canonical_name, inst.district)[0]
        c1, o1 = case("RB", inst, cat, rng.choice(TITLES[cat]), None, rng.randrange(20, 90))
        attach(c1, o1, inst, "UNDER_PROCESS", "Reply sought from institution", None, rng.randrange(5, 40), 0)
        c2, o2 = case("PGRC", inst, cat, rng.choice(TITLES[cat]), raw2, rng.randrange(5, 60))
        st = attach(c2, o2, inst, "UNDER_PROCESS", "Forwarded for comments", None, rng.randrange(5, 40), 0)
        truth["scenarios"].append({"kind": "variant_overlap", "institution": inst.canonical_name, "cases": [c1.case_id, c2.case_id],
                                   "typed_name": raw2, "expected_same_institution": True, "expected_overlap": "O2",
                                   "resolved": c2.institution_id == inst.id, "resolution_status": st})
    # 15 different wording of the same issue
    for inst in group["wording"]:
        cat = rng.choice(cat_codes)
        c1, o1 = case("RB", inst, cat, rng.choice(TITLES[cat]), None, rng.randrange(20, 80))
        attach(c1, o1, inst, "UNDER_PROCESS", "Under examination", None, rng.randrange(5, 40), 0)
        c2, o2 = case("PGRC", inst, cat, ALT_TITLES[cat], None, rng.randrange(5, 50))
        attach(c2, o2, inst, "UNDER_PROCESS", "Under examination", None, rng.randrange(5, 40), 0)
        truth["scenarios"].append({"kind": "wording_overlap", "institution": inst.canonical_name, "cases": [c1.case_id, c2.case_id],
                                   "expected_same_institution": True, "expected_overlap": "O2",
                                   "note": "same issue, different words; wording match (L3) is not built, so only the institution and category rules apply"})
    # 8 conflicting-action pairs
    for inst in group["conflict"]:
        cat = rng.choice(cat_codes)
        act = rng.choice(CONFLICT_ACTIONS)
        c1, o1 = case("RB", inst, cat, rng.choice(TITLES[cat]), None, rng.randrange(30, 90))
        attach(c1, o1, inst, "UNDER_PROCESS", act, "Await institution reply to notice", rng.randrange(5, 30), 0)
        c2, o2 = case("PGRC", inst, rng.choice(cat_codes), rng.choice(TITLES[cat]), None, rng.randrange(5, 40))
        attach(c2, o2, inst, "UNDER_PROCESS", "Under examination", None, rng.randrange(5, 30), 0)
        truth["scenarios"].append({"kind": "conflict_pair", "institution": inst.canonical_name, "cases": [c1.case_id, c2.case_id],
                                   "expected_overlap_severity": "CONFLICT", "expected_gate_for_pgrc": "CONFLICT"})
    # 10 decoys: look-alike names in the same city that must NOT merge
    for base, twin in zip(group["variant"][:10], decoys):
        cat = rng.choice(cat_codes)
        c, o = case("RO-W", twin, cat, rng.choice(TITLES[cat]), None, rng.randrange(10, 50))
        attach(c, o, twin, "UNDER_PROCESS", "Under examination", None, rng.randrange(5, 30), 0)
        truth["scenarios"].append({"kind": "decoy", "case": c.case_id, "typed_name": twin.canonical_name,
                                   "must_not_link_to": base.canonical_name, "expected_institution": twin.canonical_name,
                                   "resolved_ok": c.institution_id == twin.id})
    # filler: single-unit institutions (no overlap by construction)
    filler_units = ["RB", "PGRC"]
    while sum(refno.values()) < 250:
        inst = rng.choice(group["filler"] + group["variant"][10:] + group["wording"][:0])
        # keep each filler institution within one unit so no unplanned overlap appears
        unit = filler_units[insts.index(inst) % 2] if inst in group["filler"] else None
        if unit is None:
            continue
        cat = rng.choice(cat_codes)
        c, o = case(unit, inst, cat, rng.choice(TITLES[cat]), None, rng.randrange(1, 200))
        attach(c, o, inst, rng.choice(["RECEIVED", "UNDER_PROCESS", "UNDER_PROCESS", "DISPOSED"]), "Routine action recorded", None,
               rng.randrange(-20, 60), 0)
    db.flush()
    # SLA scenarios on existing open cases: 12 approaching, 8 beyond, 6 escalated (levels 2 and 3)
    from sqlalchemy import select
    from app.db.models import Complaint
    open_cases = [c for c in db.scalars(select(Complaint).where(Complaint.state == "UNDER_PROCESS"))]
    rng.shuffle(open_cases)
    for c in open_cases[:12]:
        c.due_on = c.expected_disposal_on = today + timedelta(days=rng.randrange(1, 6))
    for c in open_cases[12:20]:
        c.due_on = c.expected_disposal_on = today - timedelta(days=rng.randrange(2, 40))
    for k, c in enumerate(open_cases[20:26]):
        lvl = 2 if k < 3 else 3
        c.state, c.escalation_level = "ESCALATED", lvl
        sup = users["supervisor.rb"] if c.unit_id == unit_ids["RB"] else users["supervisor.pgrc"]
        c.escalated_to_user_id = (sup if lvl == 2 else users["authority"]).id
        svc.add_event(db, c, "ESCALATED", users["officer.rb"], "Escalated: delay beyond prescribed timeline", "UNDER_PROCESS", "ESCALATED", {"level": lvl})
    truth["counts"] = {"approaching_sla": 12, "beyond_sla": 8, "escalated": 6}
    write_audit(db, None, "SEED_COMPLETED", "system", "seed", {"seed": seed_value, "synthetic": True})
    db.commit()
    if ground_truth_path:
        ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
        ground_truth_path.write_text(json.dumps(truth, indent=2, default=str), encoding="utf-8")
    return truth
