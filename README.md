# SAMANVAY (working name) — Unified Complaint Coordination for AICTE

Team **SlothDevs** · Smart India Hackathon · AICTE (Regulation Bureau) problem statement: an integrated institution complaint monitoring and status dashboard.

**One line:** a single dashboard for all AICTE complaints that warns an officer *before* they act on a college another unit is already handling, explains why, and shows management which colleges need attention.

## Status

🔨 **Working prototype of the core flow (synthetic data).** Built and tested: sign-in for seven roles, dashboard, case tracking and lifecycle, escalation, overlap detection with a Match Receipt, the Action Gate, College 360°, reports with CSV export, and a tamper-evident audit chain. 19 backend tests pass. Not built yet: bulk import, coordination threads, notifications, risk score and clusters, matching on different wording (language model), Hindi-script names, PDF briefs, automated frontend tests. The exact list is in the "Designed vs. Built" tables of the two plans.

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

Demo accounts are generated. Emails: `officer.rb`, `supervisor.rb`, `officer.pgrc`, `supervisor.pgrc`, `regional.west`, `management`, `authority`, `admin`, `auditor`, each followed by `@demo.samanvay.in`. The password for all of them is `Demo@12345`. These exist only in the generated demo database.

Tests: `cd backend; .\.venv\Scripts\python -m pytest -q`. Evaluation on the planted scenarios: `python -m app.cli evaluate`.

## Plans and next steps

1. Read `MASTER_PLAN.md`, then the two companion plans.
2. Backend: `BACKEND_PLAN.md` §15, phase **B1**.
3. Frontend: `FRONTEND_PLAN.md` §7.1, phase **F1**.
4. Open items: add the PS number to `docs/PROBLEM_STATEMENT.md` and the plan headers (`MASTER_PLAN.md` V-M1); confirm the meaning of "pending" vs "under process" with AICTE officers (`BACKEND_PLAN.md` V-B9).

## Data

All data is synthetic. No real complaint or personal data is used or stored in this repository.
