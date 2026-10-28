# SAMANVAY (working name) — Unified Complaint Coordination for AICTE

Team **SlothDevs** · Smart India Hackathon · AICTE (Regulation Bureau) problem statement: an integrated institution complaint monitoring and status dashboard.

**One line:** a single dashboard for all AICTE complaints that warns an officer *before* they act on a college another unit is already handling, explains why, and shows management which colleges need attention.

## Status

🔨 **Working prototype (simulated complaints; real AICTE colleges can be imported).** Every route in the backend plan is built, and 75 backend tests pass (on SQLite; the app was also run end to end against PostgreSQL 18, see below). Built: self sign-up with e-mail verification, then a choice of who you are (complainant with instant access; institution representative or AICTE staff after an administrator approves), a portal for complainants to file and follow complaints, sign-in for seven staff roles, dashboard with live updates and Ask the Dashboard, case tracking and lifecycle, escalation, overlap detection with a Match Receipt, the Action Gate, coordination threads, notifications and time-limit alerts, College 360 with an attention score, Management view, CSV import wizard, reports (CSV, monthly and quarterly), PDF joint brief, admin screen, and a tamper-evident audit chain. Different wording of the same issue is matched through a hand-written concept list (English, Hinglish, Devanagari), by default, and optionally by a Gemini reading of pairs the list cannot place (Admin switch plus `GEMINI_API_KEY`; unit-tested with a stand-in; on 2026-10-28 a connection test reached Gemini from the Render deployment and got a correct answer on one invented pair, so the end-to-end path on real cases is still unmeasured). A neural embedding model could not be downloaded on the build machine. Real AICTE colleges load with `python -m app.cli import-aicte` (the live fetch has not been run: the AICTE site was unreachable from the build machine; parsing is tested on a fixture). AICTE publishes no complaint records, so complaints stay simulated. Not built: neural embeddings, Hindi-script college-name matching, PostgreSQL, a background scheduler (an admin runs the time-limit check), PDF reports, and automated frontend tests. The language-model features (summary, Ask) are off and were never run against the real service. The exact list is in the "Designed vs. Built" tables of the two plans.

## Run it

Needs Python 3 and Node.js. From the repository root, in PowerShell:

```
cd frontend\app; npm install; npm run build; cd ..\..
cd backend; py -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # then set SECRET_KEY and PII_ENCRYPTION_KEY to long random values
.\.venv\Scripts\python -m app.cli seed
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000. If SQLAlchemy 2.1 fails to import on Windows (Application Control blocking a compiled file), install `sqlalchemy<2.1`; this repo pins that.

People create their own accounts on the sign-up tab. For trying the staff screens locally there are generated demo accounts, which are **switched off unless `DEMO_ACCOUNTS=true`** is set (put it in `backend/.env`; never on a public deployment, the password is published here). Emails: `officer.rb`, `supervisor.rb`, `officer.pgrc`, `supervisor.pgrc`, `regional.west`, `management`, `authority`, `admin`, `auditor`, each followed by `@demo.samanvay.in`. The password for all of them is `Demo@12345`. These exist only in the generated demo database.

Tests: `cd backend; .\.venv\Scripts\python -m pytest -q`. Evaluation on the planted scenarios: `python -m app.cli evaluate`.

## Plans and next steps

1. Read `MASTER_PLAN.md`, then the two companion plans.
2. Backend: `BACKEND_PLAN.md` §15, phase **B1**.
3. Frontend: `FRONTEND_PLAN.md` §7.1, phase **F1**.
4. Open items: add the PS number to `docs/PROBLEM_STATEMENT.md` and the plan headers (`MASTER_PLAN.md` V-M1); confirm the meaning of "pending" vs "under process" with AICTE officers (`BACKEND_PLAN.md` V-B9).

## Data

All data is synthetic. No real complaint or personal data is used or stored in this repository.



## Deploy on Render

The repository root has a `requirements.txt` and a `render.yaml`. In the Render service use: build command `pip install -r requirements.txt`, start command `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and set `SECRET_KEY` and `PII_ENCRYPTION_KEY` (any long random strings). The built front end is committed, so no Node step is needed. On first start the app creates its tables and loads the demo data; restarts keep what is there. Render's free tier wipes the disk on each deploy, so the data resets then. Optional: `GEMINI_API_KEY`.

### Database that survives deploys (PostgreSQL)

Render's free disk is wiped on every deploy, so with SQLite every account and complaint would disappear. Use a free hosted
PostgreSQL instead (Neon, neon.tech, does not expire; Render's own free database expires after 30 days):

1. Create a Neon project and copy its connection string (it starts with `postgresql://` and ends with `?sslmode=require`).
2. In Render, add it as `DATABASE_URL` and save. The app creates its tables on first start and adds any later columns by itself.
3. **Create the Neon project in the same region as the Render service** (for example both in Singapore or both in Frankfurt). The first start loads about 5,000 small statements; in the same region that takes seconds, across the world it can take many minutes. The server opens its port straight away and answers `503 starting` to API calls until the data is loaded (`/api/v1/readyz` shows `starting`, then `ready`; if it fails it shows the reason).

`postgres://` and `postgresql://` addresses are both accepted. The first start loads the simulated cases (a few seconds).
**Verified:** the full app (seeding, every read endpoint as four roles, audit chain, sign-up, verification, portal, password
reset) was run against a real PostgreSQL 18 engine (PGlite) on the build machine. It has **not** been run against Neon itself,
and the 75-test suite was only run on SQLite.

### Demo accounts

On any start without `DEMO_ACCOUNTS=true` the generated demo logins are switched off (they stay as names in the simulated case
history). The administrator is whoever signs up with an address listed in `ADMIN_EMAILS`.

### Sign-up e-mail (needed for new accounts)

New accounts must confirm their e-mail address by a link before they can sign in. The server needs a way to send mail.
Render's free tier blocks SMTP ports, so use an HTTPS mail service. The easiest free one is Brevo:

1. Create a Brevo account, add your own address under *Senders*, and confirm it from the link Brevo mails you.
2. Create an API key (SMTP and API, API keys).
3. In Render, add `BREVO_API_KEY` (the key), `MAIL_FROM` (that confirmed address) and optionally `MAIL_FROM_NAME`.
4. Add `ADMIN_EMAILS` with your own address. When that address signs up and verifies, it becomes the administrator
   (it can then approve staff and institution requests under Admin, Access requests).

`RESEND_API_KEY` or `SMTP_HOST` (with `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) work too. The link in the mail uses
`PUBLIC_BASE_URL`, or Render's own address when that is not set. With no mail service the sign-up screen says so; for
testing only, `DEV_SHOW_VERIFY_LINK=true` shows the link on screen. Password reset works by e-mail (link valid one hour, signs out every device). Not built: rate limiting of
sign-ups per address or network, CAPTCHA.

Optional: set `AICTE_AUTO_IMPORT=true` on the host to load the real AICTE-approved colleges at every start (needs the host to reach facilities.aicte-india.org). Or sign in as admin and press "Load real AICTE colleges". The live AICTE endpoint has not been verified from the build machine; the import reports per-state problems on the Admin page.
