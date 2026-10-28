"""Outgoing e-mail (sign-up verification).

Providers, first one configured wins:
  BREVO_API_KEY   Brevo (free tier, sends to any address once the sender address is verified). Plain HTTPS.
  RESEND_API_KEY  Resend. Plain HTTPS.
  SMTP_HOST       any SMTP server (SMTP_PORT, SMTP_USER, SMTP_PASSWORD).
MAIL_FROM is the sender address, MAIL_FROM_NAME its display name.

Free hosts such as Render block outgoing SMTP ports, so use one of the HTTPS providers there.
With no provider configured nothing leaves the machine: the message is logged and kept in OUTBOX (tests read it).
"""
import logging
import os
import smtplib
from email.message import EmailMessage

import httpx

log = logging.getLogger("samanvay.mail")
OUTBOX: list[dict] = []  # the latest messages that were not sent anywhere (no provider configured)
_last_error: str | None = None


def provider() -> str | None:
    if os.environ.get("BREVO_API_KEY"):
        return "brevo"
    if os.environ.get("RESEND_API_KEY"):
        return "resend"
    if os.environ.get("SMTP_HOST"):
        return "smtp"
    return None


def last_error() -> str | None:
    return _last_error


def _sender() -> tuple[str, str]:
    return os.environ.get("MAIL_FROM", "no-reply@samanvay.invalid"), os.environ.get("MAIL_FROM_NAME", "SAMANVAY")


def _clean(msg: str) -> str:
    for k in ("BREVO_API_KEY", "RESEND_API_KEY", "SMTP_PASSWORD"):
        if os.environ.get(k):
            msg = msg.replace(os.environ[k], "***")
    return msg[:300]


def send(to: str, subject: str, text: str, html: str | None = None) -> dict:
    """Send one message. Returns {"sent": bool, "provider": str | None, "error": str | None}; never raises."""
    global _last_error
    prov = provider()
    addr, name = _sender()
    if prov is None:
        OUTBOX.append({"to": to, "subject": subject, "text": text, "html": html})
        del OUTBOX[:-50]
        log.info("mail not sent (no provider configured): to=%s subject=%s", to, subject)
        return {"sent": False, "provider": None, "error": "No e-mail provider is configured on the server."}
    try:
        if prov == "brevo":
            r = httpx.post("https://api.brevo.com/v3/smtp/email", timeout=20,
                           headers={"api-key": os.environ["BREVO_API_KEY"], "accept": "application/json"},
                           json={"sender": {"name": name, "email": addr}, "to": [{"email": to}], "subject": subject,
                                 "textContent": text, **({"htmlContent": html} if html else {})})
            r.raise_for_status()
        elif prov == "resend":
            r = httpx.post("https://api.resend.com/emails", timeout=20,
                           headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
                           json={"from": f"{name} <{addr}>", "to": [to], "subject": subject, "text": text,
                                 **({"html": html} if html else {})})
            r.raise_for_status()
        else:
            m = EmailMessage()
            m["From"], m["To"], m["Subject"] = f"{name} <{addr}>", to, subject
            m.set_content(text)
            if html:
                m.add_alternative(html, subtype="html")
            port = int(os.environ.get("SMTP_PORT", "587"))
            if port == 465:
                srv = smtplib.SMTP_SSL(os.environ["SMTP_HOST"], port, timeout=20)
            else:
                srv = smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=20)
                srv.starttls()
            with srv:
                if os.environ.get("SMTP_USER"):
                    srv.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
                srv.send_message(m)
        _last_error = None
        return {"sent": True, "provider": prov, "error": None}
    except Exception as e:  # noqa: BLE001 - a mail failure must never break sign-up
        detail = getattr(getattr(e, "response", None), "text", "") or ""
        _last_error = _clean(f"{type(e).__name__}: {e} {detail}".strip())
        log.warning("mail failed via %s: %s", prov, _last_error)
        return {"sent": False, "provider": prov, "error": _last_error}
