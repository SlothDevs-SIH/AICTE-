"""Self sign-up, e-mail verification, choosing who you are, the public portal and the administrator's role requests."""
import hashlib
import logging
import os
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters import captcha, mailer
from app.api.deps import current_user, require
from app.core import roles as R
from app.core import ratelimit
from app.core.audit import write_audit
from app.core.config import get_settings
from app.core.crypto import encrypt
from app.core.errors import ApiError
from app.core.security import hash_password
from app.db.base import get_db
from app.db.models import Category, Complaint, ComplaintEvent, EmailToken, Institution, Region, Unit, User
from app.services import complaints as svc
from app.services.notifications import notify

log = logging.getLogger("samanvay.accounts")
router = APIRouter(tags=["accounts"])

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
TOKEN_HOURS = 24
RESEND_SECONDS = 60
PORTAL_DAILY_LIMIT = 10
PUBLIC_STATE = {
    "RECEIVED": "Received", "ASSIGNED": "Assigned to an officer", "UNDER_PROCESS": "Under review",
    "TRANSFERRED": "Passed to another unit", "ESCALATED": "Escalated to a senior officer",
    "DISPOSED": "Closed", "REOPENED": "Reopened",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def base_url(request: Request) -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or str(request.base_url)).rstrip("/")


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


def _check_password(pw: str, email: str) -> None:
    if len(pw) < 10:
        raise ApiError(422, "weak_password", "Use at least 10 characters.")
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        raise ApiError(422, "weak_password", "Use letters and at least one digit.")
    if pw.lower() == email.lower() or pw.lower() in ("password123", "1234567890"):
        raise ApiError(422, "weak_password", "That password is too easy to guess.")


def _send_verification(db: Session, user: User, request: Request) -> dict:
    raw = secrets.token_urlsafe(32)
    db.add(EmailToken(user_id=user.id, token_hash=_hash(raw), purpose="verify",
                      expires_at=_now() + timedelta(hours=TOKEN_HOURS)))
    db.commit()
    link = f"{base_url(request)}/verify?token={raw}"
    text = (f"Hello {user.name},\n\nConfirm your e-mail address to finish creating your SAMANVAY account:\n\n{link}\n\n"
            f"The link works once and expires in {TOKEN_HOURS} hours. If you did not sign up, ignore this message.\n")
    html = (f"<p>Hello {user.name},</p><p>Confirm your e-mail address to finish creating your SAMANVAY account:</p>"
            f"<p><a href=\"{link}\" style=\"background:#1a3fa8;color:#fff;padding:10px 18px;border-radius:8px;"
            f"text-decoration:none\">Verify my e-mail</a></p><p>Or open: {link}</p>"
            f"<p>The link works once and expires in {TOKEN_HOURS} hours. If you did not sign up, ignore this message.</p>")
    res = mailer.send(user.email, "Verify your e-mail for SAMANVAY", text, html)
    out = {"email_sent": res["sent"]}
    if not res["sent"]:
        out["mail_problem"] = res["error"]
        if os.environ.get("DEV_SHOW_VERIFY_LINK", "").lower() in ("1", "true", "yes"):
            out["dev_link"] = link  # testing only: the server has no way to send mail
    return out


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)
    captcha_token: str | None = Field(default=None, max_length=4000)


@router.post("/auth/register", status_code=202)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    ip = ratelimit.client_ip(request)
    ratelimit.check(f"register:ip:{ip}", 10, 3600, "sign-up attempts from your network")
    ratelimit.check(f"register:email:{email}", 4, 3600, "sign-up attempts for this address")
    if not EMAIL_RE.match(email):
        raise ApiError(422, "invalid_email", "Enter a valid e-mail address.")
    captcha.require(body.captcha_token, ip)
    _check_password(body.password, email)
    generic = {"message": "If the address can be used, a verification link is on its way. Open it, then sign in."}
    user = db.scalar(select(User).where(User.email == email))
    if user is not None and user.email_verified:
        return generic  # same answer as a new sign-up, so addresses cannot be probed
    if user is None:
        user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password),
                    role=R.NEW, is_active=True, email_verified=False)
        db.add(user)
        db.flush()
        write_audit(db, user.id, "ACCOUNT_CREATED", "user", user.id, {"email": email})
    else:  # an earlier sign-up that was never verified: the newest details win
        user.name, user.password_hash = body.name.strip(), hash_password(body.password)
    out = _send_verification(db, user, request)
    return {**generic, **out}


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


@router.post("/auth/verify-email")
def verify_email(body: TokenIn, db: Session = Depends(get_db)):
    row = db.scalar(select(EmailToken).where(EmailToken.token_hash == _hash(body.token), EmailToken.purpose == "verify"))
    bad = ApiError(400, "invalid_token", "This link is not valid, or it has expired. Ask for a new one.")
    if row is None or row.used or _aware(row.expires_at) < _now():
        raise bad
    user = db.get(User, row.user_id)
    if user is None:
        raise bad
    row.used = True
    user.email_verified = True
    write_audit(db, user.id, "EMAIL_VERIFIED", "user", user.id, {})
    if user.role == R.NEW and user.email.lower() in _admin_emails():
        user.role = R.ADMIN
        write_audit(db, user.id, "ADMIN_BOOTSTRAPPED", "user", user.id, {"via": "ADMIN_EMAILS"})
    db.commit()
    return {"verified": True, "email": user.email}


class ResendIn(BaseModel):
    email: str = Field(max_length=200)
    captcha_token: str | None = Field(default=None, max_length=4000)


@router.post("/auth/resend-verification", status_code=202)
def resend(body: ResendIn, request: Request, db: Session = Depends(get_db)):
    generic = {"message": "If that address is waiting for verification, a new link is on its way."}
    ratelimit.check(f"resend:ip:{ratelimit.client_ip(request)}", 12, 3600, "requests from your network")
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or user.email_verified:
        return generic
    last = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id).order_by(EmailToken.created_at.desc()).limit(1))
    if last and (_now() - _aware(last.created_at)).total_seconds() < RESEND_SECONDS:
        raise ApiError(429, "too_soon", f"Wait {RESEND_SECONDS} seconds before asking for another link.")
    return {**generic, **_send_verification(db, user, request)}


# ---------------------------------------------------------------- password reset

RESET_HOURS = 1


class ForgotIn(BaseModel):
    email: str = Field(max_length=200)
    captcha_token: str | None = Field(default=None, max_length=4000)


@router.post("/auth/forgot-password", status_code=202)
def forgot_password(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    generic = {"message": "If that address has an account, a link to choose a new password is on its way."}
    ip = ratelimit.client_ip(request)
    ratelimit.check(f"forgot:ip:{ip}", 10, 3600, "password-reset requests from your network")
    ratelimit.check(f"forgot:email:{body.email.strip().lower()}", 5, 3600, "password-reset requests for this address")
    captcha.require(body.captcha_token, ip)
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not user.is_active:
        return generic
    last = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id, EmailToken.purpose == "reset")
                     .order_by(EmailToken.created_at.desc()).limit(1))
    if last and (_now() - _aware(last.created_at)).total_seconds() < RESEND_SECONDS:
        raise ApiError(429, "too_soon", f"Wait {RESEND_SECONDS} seconds before asking for another link.")
    raw = secrets.token_urlsafe(32)
    db.add(EmailToken(user_id=user.id, token_hash=_hash(raw), purpose="reset", expires_at=_now() + timedelta(hours=RESET_HOURS)))
    write_audit(db, user.id, "PASSWORD_RESET_REQUESTED", "user", user.id, {})
    db.commit()
    link = f"{base_url(request)}/reset?token={raw}"
    text = (f"Hello {user.name},\n\nSomeone asked to reset the password of your SAMANVAY account. To choose a new one, open:\n\n{link}\n\n"
            f"The link works once and expires in {RESET_HOURS} hour. If it was not you, ignore this message: your password has not changed.\n")
    html = (f"<p>Hello {user.name},</p><p>Someone asked to reset the password of your SAMANVAY account.</p>"
            f"<p><a href=\"{link}\" style=\"background:#1a3fa8;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none\">Choose a new password</a></p>"
            f"<p>Or open: {link}</p><p>The link works once and expires in {RESET_HOURS} hour. If it was not you, ignore this message.</p>")
    res = mailer.send(user.email, "Reset your SAMANVAY password", text, html)
    out = dict(generic)
    if not res["sent"] and os.environ.get("DEV_SHOW_VERIFY_LINK", "").lower() in ("1", "true", "yes"):
        out["dev_link"] = link
    return out


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(max_length=200)


@router.post("/auth/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    from app.db.models import RefreshToken

    row = db.scalar(select(EmailToken).where(EmailToken.token_hash == _hash(body.token), EmailToken.purpose == "reset"))
    bad = ApiError(400, "invalid_token", "This link is not valid, or it has expired. Ask for a new one.")
    if row is None or row.used or _aware(row.expires_at) < _now():
        raise bad
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise bad
    _check_password(body.password, user.email)
    row.used = True
    user.password_hash = hash_password(body.password)
    user.email_verified = True  # they just proved they read this mailbox
    user.failed_logins, user.locked_until = 0, None
    for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))):
        t.revoked = True  # every device is signed out
    write_audit(db, user.id, "PASSWORD_RESET", "user", user.id, {})
    db.commit()
    return {"reset": True}


# ---------------------------------------------------------------- who am I

def _inst_name(db: Session, iid: str | None) -> str | None:
    i = db.get(Institution, iid) if iid else None
    return i.canonical_name if i else None


def me_payload(db: Session, user: User) -> dict:
    req = user.request_json or None
    return {
        "id": user.id, "email": user.email, "name": user.name, "role": user.role,
        "unit_id": user.unit_id, "region_id": user.region_id, "email_verified": user.email_verified,
        "institution_id": user.institution_id, "institution_name": _inst_name(db, user.institution_id),
        "request": req,
    }


class RoleIn(BaseModel):
    account_type: str  # complainant | institution | staff
    institution_id: str | None = None
    role: str | None = None
    unit_code: str | None = None
    region_code: str | None = None
    note: str | None = Field(default=None, max_length=500)


@router.post("/me/role")
def choose_role(body: RoleIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != R.NEW:
        raise ApiError(409, "role_already_set", "Your account type is already set. An administrator can change it.")
    note = (body.note or "").strip() or None
    if body.account_type == "complainant":
        user.role = R.COMPLAINANT
        user.request_json = None
        write_audit(db, user.id, "ROLE_CHOSEN", "user", user.id, {"role": R.COMPLAINANT})
        db.commit()
        return me_payload(db, user)
    if body.account_type == "institution":
        inst = db.get(Institution, body.institution_id) if body.institution_id else None
        if inst is None:
            raise ApiError(422, "institution_required", "Choose your institution from the list.")
        req = {"type": "institution", "institution_id": inst.id, "institution_name": inst.canonical_name,
               "note": note, "status": "pending", "requested_at": _now().isoformat()}
    elif body.account_type == "staff":
        if body.role not in R.REQUESTABLE_STAFF:
            raise ApiError(422, "role_required", "Choose the role you hold at AICTE.")
        unit = region = None
        if body.role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR):
            unit = db.scalar(select(Unit).where(Unit.code == (body.unit_code or "")))
            if unit is None:
                raise ApiError(422, "unit_required", "Choose your Bureau or Cell.")
        if body.role == R.REGIONAL_OFFICER:
            region = db.scalar(select(Region).where(Region.code == (body.region_code or "")))
            if region is None:
                raise ApiError(422, "region_required", "Choose your region.")
        req = {"type": "staff", "role": body.role, "unit_code": unit.code if unit else None,
               "region_code": region.code if region else None, "note": note, "status": "pending",
               "requested_at": _now().isoformat()}
    else:
        raise ApiError(422, "invalid_account_type", "Choose complainant, institution or AICTE staff.")
    user.role, user.request_json = R.PENDING, req
    write_audit(db, user.id, "ROLE_REQUESTED", "user", user.id, {k: v for k, v in req.items() if k != "note"})
    for admin in db.scalars(select(User).where(User.role == R.ADMIN, User.is_active.is_(True))):
        notify(db, admin.id, "ROLE_REQUEST", "user", user.id, f"{user.name} asked for access as {req.get('role') or 'institution representative'}.", dedupe_hours=1)
    db.commit()
    return me_payload(db, user)


@router.post("/me/role/cancel")
def cancel_request(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role not in (R.PENDING,) and not (user.role == R.NEW and user.request_json):
        raise ApiError(409, "nothing_to_cancel", "You have no open request.")
    user.role, user.request_json = R.NEW, None
    write_audit(db, user.id, "ROLE_REQUEST_CANCELLED", "user", user.id, {})
    db.commit()
    return me_payload(db, user)


# ---------------------------------------------------------------- administrator

@router.get("/admin/role-requests")
def role_requests(db: Session = Depends(get_db), _: User = Depends(require(R.ADMIN))):
    rows = db.scalars(select(User).where(User.role == R.PENDING).order_by(User.created_at))
    return {"items": [{"user_id": u.id, "name": u.name, "email": u.email, "request": u.request_json,
                       "created_at": u.created_at.isoformat() if u.created_at else None} for u in rows]}


class ApproveIn(BaseModel):
    role: str | None = None
    unit_code: str | None = None
    region_code: str | None = None


@router.post("/admin/role-requests/{uid}/approve")
def approve_request(uid: str, body: ApproveIn, db: Session = Depends(get_db), admin: User = Depends(require(R.ADMIN))):
    u = db.get(User, uid)
    if u is None or u.role != R.PENDING or not u.request_json:
        raise ApiError(404, "not_found", "There is no open request for this person.")
    req = u.request_json
    if req.get("type") == "institution":
        u.role, u.institution_id = R.INSTITUTION_REP, req["institution_id"]
    else:
        role = body.role or req["role"]
        if role not in R.ALL_ROLES:
            raise ApiError(422, "invalid_role", "Unknown role.")
        unit_code, region_code = body.unit_code or req.get("unit_code"), body.region_code or req.get("region_code")
        unit = db.scalar(select(Unit).where(Unit.code == unit_code)) if unit_code else None
        region = db.scalar(select(Region).where(Region.code == region_code)) if region_code else None
        if role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR) and unit is None:
            raise ApiError(422, "unit_required", "This role needs a Bureau or Cell.")
        if role == R.REGIONAL_OFFICER and region is None:
            raise ApiError(422, "region_required", "This role needs a region.")
        u.role, u.unit_id, u.region_id = role, unit.id if unit else None, region.id if region else None
    u.request_json = None
    write_audit(db, admin.id, "ROLE_APPROVED", "user", u.id, {"role": u.role})
    notify(db, u.id, "ROLE_DECISION", "user", u.id, f"Your access was approved: {u.role.replace('_', ' ')}.", dedupe_hours=0)
    db.commit()
    return {"user_id": u.id, "role": u.role}


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/admin/role-requests/{uid}/reject")
def reject_request(uid: str, body: RejectIn, db: Session = Depends(get_db), admin: User = Depends(require(R.ADMIN))):
    u = db.get(User, uid)
    if u is None or u.role != R.PENDING or not u.request_json:
        raise ApiError(404, "not_found", "There is no open request for this person.")
    u.request_json = {**u.request_json, "status": "rejected", "reason": body.reason.strip()}
    u.role = R.NEW
    write_audit(db, admin.id, "ROLE_REJECTED", "user", u.id, {"reason": body.reason.strip()})
    notify(db, u.id, "ROLE_DECISION", "user", u.id, f"Your request was not approved: {body.reason.strip()}", dedupe_hours=0)
    db.commit()
    return {"user_id": u.id, "role": u.role}


# ---------------------------------------------------------------- public portal

def _public_user(user: User = Depends(current_user)) -> User:
    if user.role not in R.PUBLIC_ROLES:
        raise ApiError(403, "forbidden", "This page is for complainants and institution representatives.")
    return user


class PortalComplaintIn(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=4000)
    category_id: str
    institution_id: str | None = None
    institution_text: str | None = Field(default=None, max_length=300)
    aicte_id: str | None = Field(default=None, max_length=40)


def _portal_row(c: Complaint, cats: dict, insts: dict) -> dict:
    return {"id": c.id, "case_id": c.case_id, "title": c.title, "category": cats.get(c.category_id),
            "institution": insts.get(c.institution_id) or c.institution_text_raw, "state": c.state,
            "status": PUBLIC_STATE.get(c.state, c.state), "received_on": c.received_on.isoformat(),
            "expected_disposal_on": c.expected_disposal_on.isoformat() if c.expected_disposal_on else None,
            "updated_at": c.last_action_at.isoformat() if c.last_action_at else None}


def _maps(db: Session) -> tuple[dict, dict]:
    return ({c.id: c.name for c in db.scalars(select(Category))},
            {i.id: i.canonical_name for i in db.scalars(select(Institution))})


@router.post("/portal/complaints", status_code=201)
def portal_file(body: PortalComplaintIn, db: Session = Depends(get_db), user: User = Depends(_public_user)):
    from app.engine.institution import resolve

    since = _now() - timedelta(hours=24)
    today = db.scalar(select(func.count()).select_from(Complaint).where(
        Complaint.submitted_by_id == user.id, Complaint.created_at >= since)) or 0
    if today >= PORTAL_DAILY_LIMIT:
        raise ApiError(429, "daily_limit", f"You can file {PORTAL_DAILY_LIMIT} complaints a day. Try again tomorrow.")
    if not (body.institution_id or (body.institution_text or "").strip() or (body.aicte_id or "").strip()):
        raise ApiError(422, "institution_required", "Tell us which institution this is about.")
    if db.get(Category, body.category_id) is None:
        raise ApiError(422, "unknown_category", "Choose a category.")
    unit = db.scalar(select(Unit).where(Unit.code == "PGRC")) or db.scalar(select(Unit).order_by(Unit.code))
    inst_id = body.institution_id if body.institution_id and db.get(Institution, body.institution_id) else None
    if not inst_id:
        inst_id, _cands, _status = resolve(db, body.institution_text, body.aicte_id)
    c = svc.create_complaint(
        db, user, unit_id=unit.id, reference_no=f"PORTAL-{uuid.uuid4().hex[:10].upper()}", category_id=body.category_id,
        title=body.title.strip(), description=body.description.strip(), institution_id=inst_id,
        institution_text_raw=(body.institution_text or "").strip() or None, aicte_id_raw=(body.aicte_id or "").strip() or None,
        is_synthetic=False)
    c.source, c.submitted_by_id = "portal", user.id
    c.complainant_name_enc, c.complainant_email_enc = encrypt(user.name), encrypt(user.email)
    db.commit()
    cats, insts = _maps(db)
    return _portal_row(c, cats, insts)


@router.get("/portal/my/complaints")
def portal_mine(db: Session = Depends(get_db), user: User = Depends(_public_user)):
    cats, insts = _maps(db)
    rows = db.scalars(select(Complaint).where(Complaint.submitted_by_id == user.id).order_by(Complaint.created_at.desc()))
    return {"items": [_portal_row(c, cats, insts) for c in rows]}


@router.get("/portal/my/complaints/{cid}")
def portal_mine_one(cid: str, db: Session = Depends(get_db), user: User = Depends(_public_user)):
    c = db.get(Complaint, cid)
    if c is None or c.submitted_by_id != user.id:
        raise ApiError(404, "not_found", "Complaint not found.")
    cats, insts = _maps(db)
    steps = []
    for ev in db.scalars(select(ComplaintEvent).where(ComplaintEvent.complaint_id == c.id).order_by(ComplaintEvent.occurred_at)):
        if ev.kind in ("RECEIVED", "STATE_CHANGED", "ESCALATED", "DE_ESCALATED", "TRANSFERRED"):  # no internal remarks reach the public
            steps.append({"at": ev.occurred_at.isoformat(), "status": PUBLIC_STATE.get(ev.to_state or "", "Received")})
    return {**_portal_row(c, cats, insts), "description": c.description, "timeline": steps}


@router.get("/portal/institution/complaints")
def portal_institution(db: Session = Depends(get_db), user: User = Depends(require(R.INSTITUTION_REP))):
    if not user.institution_id:
        raise ApiError(409, "no_institution", "Your account is not linked to an institution yet.")
    cats, _ = _maps(db)
    rows = list(db.scalars(select(Complaint).where(Complaint.institution_id == user.institution_id).order_by(Complaint.received_on.desc())))
    open_states = ("RECEIVED", "ASSIGNED", "UNDER_PROCESS", "ESCALATED", "REOPENED", "TRANSFERRED")
    return {"institution": _inst_name(db, user.institution_id),
            "open": sum(1 for c in rows if c.state in open_states), "closed": sum(1 for c in rows if c.state == "DISPOSED"),
            "items": [{"case_id": c.case_id, "category": cats.get(c.category_id), "state": c.state,
                       "status": PUBLIC_STATE.get(c.state, c.state), "received_on": c.received_on.isoformat(),
                       "expected_disposal_on": c.expected_disposal_on.isoformat() if c.expected_disposal_on else None}
                      for c in rows]}  # no titles, descriptions or complainant details
