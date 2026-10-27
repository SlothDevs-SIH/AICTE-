"""Import Wizard (BACKEND_PLAN 10): upload CSV, map columns, dry-run, commit (idempotent).

A bad row is reported by row number and never aborts the file.
"""
import csv
import hashlib
import io
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.errors import ApiError
from app.db.models import Category, Complaint, ImportJob, User
from app.engine.institution import resolve
from app.engine.overlap import OPEN_STATES
from app.services import complaints as svc

FIELDS = ["reference_no", "title", "description", "category", "institution_text", "aicte_id", "received_on"]
REQUIRED = ["reference_no", "title", "category"]
MAX_ROWS = 5000
GUESS = {
    "reference_no": ["reference", "ref", "ref_no", "file_no", "case_no", "reference_no"],
    "title": ["title", "subject", "complaint", "heading"],
    "description": ["description", "details", "text", "remarks"],
    "category": ["category", "type", "nature"],
    "institution_text": ["institution", "college", "institute", "name", "institution_name"],
    "aicte_id": ["aicte_id", "permanent_id", "aicte", "id"],
    "received_on": ["received", "date", "received_on", "date_of_receipt"],
}


def create_job(db: Session, user: User, unit_id: str, filename: str, data: bytes, max_mb: int) -> ImportJob:
    if len(data) > max_mb * 1024 * 1024:
        raise ApiError(413, "file_too_large", f"File is larger than {max_mb} MB.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(422, "bad_encoding", "The file must be a UTF-8 CSV.") from None
    rows = list(csv.DictReader(io.StringIO(text), restkey="_extra"))
    if not rows:
        raise ApiError(422, "empty_file", "The file has no data rows.")
    if len(rows) > MAX_ROWS:
        raise ApiError(422, "too_many_rows", f"At most {MAX_ROWS} rows per file.")
    cols = [c for c in rows[0].keys() if c != "_extra" and c is not None]
    sha = hashlib.sha256(data).hexdigest()
    job = ImportJob(unit_id=unit_id, filename=filename[:255], sha256=sha, columns_json=cols,
                    raw_rows_json=rows, rows_total=len(rows), created_by=user.id,
                    mapping_json={f: next((c for c in cols if c.strip().lower().replace(" ", "_") in GUESS[f]), None)
                                  for f in FIELDS})
    db.add(job)
    db.flush()
    write_audit(db, user.id, "IMPORT_UPLOADED", "import", job.id, {"filename": filename, "rows": len(rows)})
    return job


def duplicate_file(db: Session, job: ImportJob) -> bool:
    return db.scalar(select(ImportJob).where(ImportJob.sha256 == job.sha256, ImportJob.id != job.id,
                                             ImportJob.status == "COMMITTED")) is not None


def _parse_row(db: Session, job: ImportJob, i: int, raw: dict, cats: dict):
    m = job.mapping_json or {}
    get = lambda f: (raw.get(m[f]) or "").strip() if m.get(f) else ""  # noqa: E731
    errs = []
    if raw.get("_extra"):
        errs.append("row has more cells than the header (a comma inside a value needs quotes)")
    for f in REQUIRED:
        if not get(f):
            errs.append(f"{f} is missing")
    cat = cats.get(get("category").casefold())
    if get("category") and not cat:
        errs.append(f"unknown category '{get('category')}'")
    received = None
    if get("received_on"):
        try:
            received = date.fromisoformat(get("received_on")[:10])
        except ValueError:
            errs.append(f"received_on '{get('received_on')}' is not a date (use YYYY-MM-DD)")
    if not get("institution_text") and not get("aicte_id"):
        errs.append("needs an institution name or AICTE ID")
    return {"row": i + 2, "errors": errs, "values": {
        "reference_no": get("reference_no"), "title": get("title"), "description": get("description"),
        "category_id": cat.id if cat else None, "institution_text": get("institution_text"),
        "aicte_id": get("aicte_id"), "received_on": received}}


def _cats(db: Session) -> dict:
    out = {}
    for c in db.scalars(select(Category)):
        out[c.name.casefold()] = c
        out[c.code.casefold()] = c
    return out


def dry_run(db: Session, job: ImportJob) -> dict:
    cats = _cats(db)
    ok, bad, seen = 0, [], set()
    matches = {"linked": 0, "needs_review": 0, "unmatched": 0}
    would_overlap = 0
    existing = {r for (r,) in db.execute(select(Complaint.reference_no).where(Complaint.unit_id == job.unit_id))}
    for i, raw in enumerate(job.raw_rows_json):
        p = _parse_row(db, job, i, raw, cats)
        ref = p["values"]["reference_no"]
        if ref and ref in seen:
            p["errors"].append("duplicate reference_no inside this file")
        if ref and ref in existing:
            p["errors"].append("reference_no already exists for this unit")
        seen.add(ref)
        if p["errors"]:
            bad.append({"row": p["row"], "errors": p["errors"]})
            continue
        iid, cands, status = resolve(db, p["values"]["institution_text"], p["values"]["aicte_id"] or None)
        matches[status] += 1
        if iid:
            would_overlap += db.query(Complaint).filter(
                Complaint.institution_id == iid, Complaint.unit_id != job.unit_id,
                Complaint.state.in_(OPEN_STATES)).count() > 0
        ok += 1
    job.rows_ok, job.rows_error, job.status = ok, len(bad), "DRY_RUN"
    job.report_json = {"rows_total": job.rows_total, "rows_ok": ok, "rows_error": len(bad), "errors": bad[:200],
                       "institution_matches": matches, "rows_that_would_raise_overlap_alerts": would_overlap,
                       "duplicate_file": duplicate_file(db, job)}
    return job.report_json


def commit(db: Session, job: ImportJob, user: User) -> dict:
    if job.status == "COMMITTED":
        return job.report_json  # idempotent: a second commit changes nothing
    if job.status != "DRY_RUN":
        raise ApiError(409, "dry_run_required", "Run the dry run before committing.")
    cats = _cats(db)
    created = skipped = 0
    for i, raw in enumerate(job.raw_rows_json):
        p = _parse_row(db, job, i, raw, cats)
        v = p["values"]
        if p["errors"] or db.scalar(select(Complaint).where(Complaint.unit_id == job.unit_id,
                                                           Complaint.reference_no == v["reference_no"])):
            skipped += 1
            continue
        iid, _, _ = resolve(db, v["institution_text"], v["aicte_id"] or None)
        c = svc.create_complaint(db, user, unit_id=job.unit_id, reference_no=v["reference_no"],
                                 category_id=v["category_id"], title=v["title"], description=v["description"],
                                 institution_id=iid, institution_text_raw=v["institution_text"] or None,
                                 aicte_id_raw=v["aicte_id"] or None, received_on=v["received_on"])
        c.source, c.import_job_id = "import", job.id
        created += 1
    job.status = "COMMITTED"
    job.report_json = {**(job.report_json or {}), "created": created, "skipped": skipped}
    write_audit(db, user.id, "IMPORT_COMMITTED", "import", job.id, {"created": created, "skipped": skipped})
    return job.report_json
