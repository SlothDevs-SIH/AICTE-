# SAMANVAY (working name) — Unified Complaint Coordination for AICTE

Team **SlothDevs** · Smart India Hackathon · AICTE (Regulation Bureau) problem statement: an integrated institution complaint monitoring and status dashboard.

**One line:** a single dashboard for all AICTE complaints that warns an officer *before* they act on a college another unit is already handling, explains why, and shows management which colleges need attention.

## Status

📋 **Planning complete (M0). Nothing is built yet.** The plans below are the source of truth for the build.

| Document | What it covers |
|---|---|
| [`MASTER_PLAN.md`](MASTER_PLAN.md) | Problem, users, principles, features and USPs, flows, data plan, phases, risks, demo script, presentation outline |
| [`backend/BACKEND_PLAN.md`](backend/BACKEND_PLAN.md) | Data model, API, overlap engine, Action Gate, audit hash chain, risk score, import, tests, evaluation |
| [`frontend/FRONTEND_PLAN.md`](frontend/FRONTEND_PLAN.md) | Screens, components, UI rules, accessibility, tests, performance budgets |
| [`CLAUDE.md`](CLAUDE.md) | Rules for any Claude session working in this repo (including the git authorship rule) |

## Where to start building

1. Read `MASTER_PLAN.md`, then the two companion plans.
2. Backend: `BACKEND_PLAN.md` §15, phase **B1**.
3. Frontend: `FRONTEND_PLAN.md` §7.1, phase **F1**.
4. Open item: paste the official problem-statement text into `docs/PROBLEM_STATEMENT.md` and re-map requirement IDs (`MASTER_PLAN.md` V-M1).

## Data

All data is synthetic. No real complaint or personal data is used or stored in this repository.
