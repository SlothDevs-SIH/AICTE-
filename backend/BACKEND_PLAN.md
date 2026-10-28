# SAMANVAY Backend — Plan & Build Record

**Team:** SlothDevs (SIH) · **Solution (working name):** SAMANVAY · **Problem statement:** AICTE (Regulation Bureau) — integrated institution complaint monitoring and status dashboard · **PS number:** not supplied yet (MASTER_PLAN V-M1) · **Official text:** [`../docs/PROBLEM_STATEMENT.md`](../docs/PROBLEM_STATEMENT.md)
**Parent document:** [`../MASTER_PLAN.md`](../MASTER_PLAN.md) (product). Sibling: [`../frontend/FRONTEND_PLAN.md`](../frontend/FRONTEND_PLAN.md). This document is the source of truth for the API, data and engine. When they disagree, fix all three in the same commit.
**Document date:** 2026-10-27 (v1.1 — reconciled with the official problem statement)
**Backend phase:** **B0 — Planning: ✅ this document.** Nothing is built. Next: **B1 — Foundations.**

> ⚠️ **Honesty rule:** a "✅" must point to a file and a test that passed. Everything here is **📋 Planned** until code exists. Numbers in §11 are **targets**, replaced by measured values in Appendix B as they are measured.

---

## ⚠️ Verification & Discrepancy Log — Read First

| # | Item | Detail | Resolution / action | Status |
|---|---|---|---|---|
| V-B1 | No library versions are pinned in this plan | Versions change; any number written now would be a guess | At B1, resolve versions into the lockfile (`uv.lock`) and record them in Appendix A | ⏳ B1 |
| V-B2 | Embedding model choice for Hindi text | The commonly used small English model `all-MiniLM-L6-v2` is **English-focused**; Hindi/Hinglish quality is unproven | Evaluate a multilingual small model against the Hindi/Hinglish portion of the ground truth at B4; pick by measured recall, keep the fallback regardless | ⏳ B4 |
| V-B3 | Devanagari transliteration library | Needed for U5 name matching; library quality for institution names is unknown | Evaluate on the planted Hindi variants at B3; if weak, fall back to a hand-built alias list plus the multilingual embedding for names | ⏳ B3 |
| V-B4 | SQLite vs PostgreSQL behaviour differences | Case-folding, JSON functions and locking differ | Write the schema with portable types; run the test suite against both from B3; document differences | ⏳ B3 |
| V-B5 | Hash chain needs a single writer | Concurrent writers can fork the chain | Serialise appends (SQLite: single writer already; PostgreSQL: advisory lock); concurrency test at B3 | ⏳ B3 |
| V-B6 | LLM provider and key are undecided | We do not know which provider the team will use | LLM is behind an adapter; template summary is the default; provider chosen later | ⏳ Open |
| V-B7 | Threshold values in §6 are starting points | They have not been measured | Tune on the **development split** only; report on the **held-out split** (§11) | ⏳ B3 |
| V-B8 | Requirement IDs | Earlier working IDs `R-xx` were replaced by the official IDs (`OBJ`, `KF`, `INN`, `OUT`, `TU`); the comparison found gaps (MASTER_PLAN V-M7), all fixed here: Escalated status, case tracking fields, system Case ID, extra reports, Competent Authority role, live stream | Done; coverage matrix in MASTER_PLAN §1.3 | ✅ Resolved 2026-10-27 |
| V-B9 | Meaning of "pending" vs "under process" | The statement lists both without defining them. Our definition: **pending** = received or assigned but no officer action yet; **under process** = at least one action taken and not yet disposed; **escalated** and **transferred** counted separately (§3.3) | Confirm with AICTE officers; definitions live in one place (`app/services/dashboard.py`) and are tested | ⏳ Confirm |

---

## 1. Backend Identity & Scope

| Field | Planned value (to be resolved in the lockfile at B1) |
|---|---|
| Language / runtime | Python 3.12 |
| Web framework | FastAPI (OpenAPI generated automatically) with Pydantic v2 models |
| ORM / migrations | SQLAlchemy 2.x, Alembic |
| Database | SQLite (prototype), PostgreSQL + pgvector (target). Schema stays portable |
| Matching | `rapidfuzz` (string similarity), a Devanagari transliteration library (V-B3), a small sentence-embedding model (V-B2) |
| Password hashing | Argon2 |
| Sessions | Short-lived signed access token + refresh token (prototype); OIDC is roadmap |
| PDF export | A server-side PDF library (to be chosen at B5) |
| Package manager | `uv` with a committed lockfile |
| Quality tools | `ruff`, `mypy --strict`, `pytest`, `hypothesis` |
| Packaging | Docker image; Docker Compose with the frontend |

**The backend owns:** all business logic, role enforcement, masking, the Overlap Engine, the Action Gate, the audit chain, risk and cluster computation, reports, imports, and the canonical API contract.
**It does not own:** layout or presentation. It returns canonical data; the frontend formats it.

---

## 2. Architecture

### 2.1 Layers

```
 HTTP (FastAPI routers)           app/api/v1/*        thin: parse → call service → shape response
   │
 Services (business logic)        app/services/*      complaints, institutions, overlaps, gate,
   │                                                   coordination, imports, reports, risk, ask
 Engine (pure functions)          app/engine/*        normalise, institution match, issue match,
   │                                                   rules, scoring, receipts — no DB, no I/O
 Adapters (optional, swappable)   app/adapters/*      embeddings, llm, pdf, clock
   │
 Persistence                      app/db/*            models, repositories, migrations
 Cross-cutting                    app/core/*          config, security, roles, masking, audit, errors
```

**Rules:**
1. The **Engine** is pure: given inputs it returns outputs. This makes it easy to test against the ground truth and to run offline.
2. Routers never contain business logic.
3. Every state-changing service call writes an audit entry **in the same database transaction**.
4. Adapters are the only place that touches the network or model files; each has a **fallback implementation**.

### 2.2 Request flow (Action Gate example)

```
 POST /api/v1/gate/check  {complaint_or_institution, action_type}
   → auth + role check
   → gate service loads open/recent cases for the institution (and look-alike institutions)
   → engine scores each candidate pair, applies rules → result {CLEAR | RELATED | CONFLICT}
   → store gate_checks row (snapshot of what was shown)
   → audit entry (GATE_CHECKED)
   → response: result, candidates, Match Receipts, allowed choices
 POST /api/v1/gate/{check_id}/decision {choice, justification?}
   → audit entry (GATE_DECISION) → perform choice (request coordination / link / proceed)
```

### 2.3 API contract rules
- Versioned prefix `/api/v1`. Generated OpenAPI is exported to a committed file (`openapi.json`) by a CLI command; the frontend generates types from it; CI fails on drift (as in the frontend plan §2.3).
- JSON only. Timestamps are UTC ISO-8601. IDs are opaque integers or UUIDs (decide at B1; UUIDs preferred so IDs are not guessable).
- **Error envelope:** `{ "error": { "code": "...", "message": "...", "details": {...}, "request_id": "..." } }`. Stable `code` values are part of the contract.
- **Pagination:** `limit` (max 200) + `cursor`. **Sorting:** `sort=field,-field` with a whitelist.
- Unimplemented routes return `501` with `code = "not_implemented"` and `planned_phase = "Bx"`, so the frontend can show "planned" honestly from day one.
- Every response carries `X-Request-ID` (accepted from the client or generated).

---

## 3. Data Model

Types are described logically; at B1 they are written as portable SQLAlchemy types. All tables have `id`, `created_at`, `updated_at`. All demo rows have `is_synthetic = true`.

### 3.1 Reference tables

| Table | Key columns | Notes |
|---|---|---|
| `units` | `code` (RB, PGRC, REG-W, …), `name`, `kind` | The handling units |
| `regions` | `code`, `name`, `states[]` | Regional offices / zones |
| `categories` | `code`, `name`, `severity_weight`, `sla_days` | Complaint categories (8 initially) |
| `users` | `email`, `name`, `password_hash`, `role`, `unit_id`, `region_id`, `is_active` | Roles: `unit_officer`, `unit_supervisor`, `regional_officer`, `management`, `competent_authority`, `admin`, `auditor`. Whether an officer belongs to RB, PGRC or another Bureau/Cell comes from `unit_id`, not from the role |

### 3.2 Institutions

| Table | Key columns | Notes |
|---|---|---|
| `institutions` | `aicte_id` (nullable, unique when present), `canonical_name`, `normalized_name`, `short_name`, `type`, `state`, `district`, `pincode`, `region_id`, `address` | The registry |
| `institution_aliases` | `institution_id`, `alias`, `normalized_alias`, `source` (`seed`, `import`, `officer_confirmed`), `confirmed_by`, `confirmed_at` | **Alias Memory (U4).** Unique on (`institution_id`, `normalized_alias`) |

Indexes: `normalized_name`, `normalized_alias`, (`state`,`district`), `aicte_id`.

### 3.3 Complaints

| Table | Key columns | Notes |
|---|---|---|
| `complaints` | `case_id` (system-generated, globally unique, e.g. `SMV-2026-000123`), `reference_no` (the unit's own number, unique per unit), `unit_id`, `institution_id` (nullable until resolved), `institution_text_raw`, `aicte_id_raw`, `category_id`, `title`, `description`, `language_hint`, `received_on`, `due_on` (SLA due date), `expected_disposal_on`, `state`, `owner_user_id`, `escalation_level` (0–3), `escalated_to_user_id`, `last_action_text`, `last_action_at`, `last_action_by`, `next_action_text`, `next_action_due_on`, `priority`, `source` (`manual`, `import`), `import_job_id`, `complainant_name_enc`, `complainant_phone_enc`, `complainant_email_enc`, `is_synthetic` | Personal fields are **encrypted at rest** and masked in responses by role |
| `complaint_events` | `complaint_id`, `kind`, `from_state`, `to_state`, `actor_user_id`, `remark`, `payload_json`, `occurred_at` | The workflow history (KF5). `kind`: `RECEIVED`, `ASSIGNED`, `STATE_CHANGED`, `TRANSFERRED`, `ESCALATED`, `DE_ESCALATED`, `REMINDER_SENT`, `NEXT_ACTION_SET`, `REMARK`, `ACTION_TAKEN`, `OVERLAP_LINKED`, `COORDINATION_REQUESTED`, … |
| `attachments` | `complaint_id`, `filename`, `content_type`, `size_bytes`, `sha256`, `storage_key` | Prototype stores metadata and a small file in local storage |
| `complaint_actions` | `complaint_id`, `action_type`, `status` (`PROPOSED`,`DONE`,`WITHDRAWN`), `proposed_by`, `proposed_at`, `done_at`, `details` | Regulatory actions (notice, penalty, closure…); used by the Gate and by O4 |

**Complaint states and transitions**

| From | To | Who | Condition |
|---|---|---|---|
| — | `RECEIVED` | system/unit officer | on creation |
| `RECEIVED` | `ASSIGNED` | unit officer / supervisor | owner set |
| `ASSIGNED` | `UNDER_PROCESS` | owner | first action or remark |
| `UNDER_PROCESS` | `TRANSFERRED` | owner | target unit set, remark required |
| `TRANSFERRED` | `ASSIGNED` | receiving unit | accepted into the receiving unit's queue (new `unit_id`, new `reference_no` allowed, original kept in events) |
| `UNDER_PROCESS` | `DISPOSED` | owner | disposal reason required; Gate runs for the `CLOSE_CASE` action |
| `UNDER_PROCESS` | `ESCALATED` | owner, supervisor or system (if auto-escalation is on) | level (2 or 3) and reason required; `escalation_level` and `escalated_to_user_id` set; event `ESCALATED` |
| `ESCALATED` | `ESCALATED` (higher level) | escalated-to user | Level 2 → 3 only; reason required |
| `ESCALATED` | `UNDER_PROCESS` | escalated-to user | instructions recorded; returns to the owner; event `DE_ESCALATED` |
| `ESCALATED` | `DISPOSED` | escalated-to user (Level 2 or 3) | disposal reason required; Gate runs for the `CLOSE_CASE` action |
| `DISPOSED` | `REOPENED` | supervisor | reason required |
| `REOPENED` | `UNDER_PROCESS` | owner | — |

Illegal transitions return `409 invalid_transition`. **Tracking fields (KF2.7–KF2.9):** `last_action_*` is derived automatically from the latest `ACTION_TAKEN`, `STATE_CHANGED`, `TRANSFERRED` or `ESCALATED` event and stored for fast listing; `next_action_*` is set by the owner (event `NEXT_ACTION_SET`), and an `UNDER_PROCESS` case without a next action shows a hint; `expected_disposal_on` defaults to `due_on` and the owner may change it with a remark.
**Dashboard counters (KF4, defined once, in `app/services/dashboard.py`):** *total received* = all cases in scope; *pending* = `RECEIVED` or `ASSIGNED` with no officer action yet; *under process* = `UNDER_PROCESS`; *escalated* = `ESCALATED`; *disposed* = `DISPOSED`; *transferred* = cases with a `TRANSFERRED` event in the selected period; *beyond timeline* = computed (below). The definitions are our interpretation (V-B9).
**"On hold for coordination"** is a flag on the complaint, not a state, so the normal lifecycle is not disturbed. **"Overdue"** is computed (`due_on < today` and state not `DISPOSED`), not stored.

### 3.4 Overlaps, gate, coordination

| Table | Key columns | Notes |
|---|---|---|
| `overlaps` | `complaint_a_id`, `complaint_b_id` (ordered so a < b), `institution_id`, `overlap_type` (O1…O6), `severity` (`CONFLICT`,`RELATED`,`SYSTEMIC`), `match_score`, `receipt_json`, `status` (`SUGGESTED`,`CONFIRMED`,`DISMISSED`,`LINKED`,`UNLINKED`), `detected_at`, `decided_by`, `decided_at`, `decision_reason`, `engine_version` | Unique on (`complaint_a_id`,`complaint_b_id`). `receipt_json` is the Match Receipt (§6.8) |
| `link_groups` | `institution_id`, `created_by`, `note` | A set of linked complaints |
| `link_group_members` | `link_group_id`, `complaint_id` | A complaint is in at most one active group |
| `gate_checks` | `actor_user_id`, `institution_id`, `complaint_id` (nullable), `action_type`, `result` (`CLEAR`,`RELATED`,`CONFLICT`), `snapshot_json`, `choice`, `justification`, `decided_at` | Stores exactly what the officer was shown |
| `coordination_threads` | `institution_id`, `opened_by`, `status` (`OPEN`,`RESOLVED`,`EXPIRED`), `due_at`, `outcome` (`PROCEED_TOGETHER`,`DEFER_TO_A`,`DEFER_TO_B`,`NOT_RELATED`) | |
| `coordination_thread_complaints` | `thread_id`, `complaint_id` | Cases held for discussion |
| `coordination_messages` | `thread_id`, `author_user_id`, `body`, `posted_at` | |
| `notifications` | `user_id`, `kind`, `ref_type`, `ref_id`, `message`, `read_at` | In-app only in the prototype |

### 3.5 Intelligence and operations

| Table | Key columns | Notes |
|---|---|---|
| `complaint_embeddings` | `complaint_id`, `model_name`, `model_version`, `vector` (blob/JSON in SQLite; `vector` type in PostgreSQL), `text_hash` | Recomputed when `text_hash` changes. Absent when embeddings are disabled |
| `clusters` | `institution_id`, `category_id`, `size`, `first_at`, `last_at`, `status` | U7 |
| `cluster_members` | `cluster_id`, `complaint_id` | |
| `risk_snapshots` | `institution_id`, `computed_at`, `score`, `components_json`, `engine_version` | History so trends are visible |
| `import_mappings` | `unit_id`, `name`, `mapping_json`, `created_by` | Saved column mappings (U8) |
| `import_jobs` | `unit_id`, `filename`, `sha256`, `mapping_id`, `status` (`UPLOADED`,`DRY_RUN`,`COMMITTED`,`FAILED`), `rows_total`, `rows_ok`, `rows_error`, `report_json`, `created_by` | Duplicate file (same `sha256`) is flagged |
| `settings` | `key`, `value_json`, `updated_by` | Thresholds, SLA days, alert budget, AI switches (§6.6) |
| `audit_log` | `seq`, `occurred_at`, `actor_user_id`, `action`, `entity_type`, `entity_id`, `payload_json`, `prev_hash`, `entry_hash` | Hash-chained (§8) |

### 3.6 Data protection in the model
- `complainant_*` fields are encrypted with a key from the environment (prototype: symmetric encryption; key never in the repo). Search on complainant fields is **not** supported (by design).
- Responses apply masking by role (§9.3). Revealing writes a `PII_REVEALED` audit entry with the reason.

---

## 4. Roles and Permissions (summary; full matrix in §9.2)

Roles: `unit_officer` (RB, PGRC or any other Bureau/Cell, decided by the user's unit), `unit_supervisor`, `regional_officer`, `management`, `competent_authority`, `admin`, `auditor`.
Scope rules: officers see **all institutions' overlap summaries** (needed for coordination) but only **their own unit's case details**, unless a coordination thread or link group gives them access to the specific counterpart case. Regional officers additionally see cases in their region. Management sees aggregates and case summaries. Supervisors see their whole unit's queue. The Competent Authority sees all case details read-only and acts on Level 3 escalations. Auditors see audit data and everything read-only.

> **Design note:** this resolves a real tension. The Gate must tell an RB officer that PGRC has a related case (otherwise the product is pointless), but it should not expose a PGRC complainant's details. So the Gate shows **case summary fields** (unit, category, state, owner, dates, match receipt) and hides description text and personal data until the other unit shares the case through coordination.

---

## 5. API Surface (all under `/api/v1`)

Role abbreviations: **O** = `unit_officer`, `unit_supervisor` or `regional_officer`; **SUP** = `unit_supervisor`; **M** = `management`; **CA** = `competent_authority`; **A** = `admin`; **U** = `auditor`; **ALL** = any authenticated user.

### 5.1 System and auth

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/healthz` | public | Liveness |
| GET | `/readyz` | public | Readiness (database, optional adapters) |
| GET | `/meta` | ALL | Version, build, environment, phase, adapter status, component registry |
| POST | `/auth/login` | public | Email + password → access/refresh tokens (rate-limited) |
| POST | `/auth/refresh` | public | Refresh |
| POST | `/auth/logout` | ALL | Revoke refresh token |
| GET | `/me` | ALL | Current user, role, unit, region |
| GET | `/stream` | ALL (scoped) | **Live updates (F-31):** Server-Sent Events carrying `counters_changed`, `case_changed`, `overlap_created` and `notification` events for the caller's scope, with a heartbeat every 15 s. If the stream fails the client falls back to polling `/dashboard/summary` every `live_poll_seconds` |

### 5.2 Institutions

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/institutions` | ALL | Search by text/ID/state/district (uses the matching engine for text) |
| GET | `/institutions/suggest?text=` | O,A | Ranked institution matches for typed text, with scores (used at intake) |
| GET | `/institutions/{id}` | ALL | Record with aliases |
| POST | `/institutions` | A | Create |
| PATCH | `/institutions/{id}` | A | Update |
| POST | `/institutions/{id}/aliases` | O,A | Add an alias (source `officer_confirmed`) |
| DELETE | `/institutions/{id}/aliases/{alias_id}` | A | Remove alias |
| GET | `/institutions/{id}/360` | ALL | Timeline across units, owners, open overlaps, latest risk |
| GET | `/institutions/{id}/risk` | M,A,U | Current score with components and history |

### 5.3 Complaints

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/complaints` | ALL | List with filters: `institution_id`, `aicte_id`, `unit`, `region`, `category`, `state`, `overdue`, `received_from/to`, `owner`, `q`, `case_id`, `reference_no`, `escalated`, `has_overlap`; masked by role |
| POST | `/complaints` | O | Create (then runs the overlap scan) |
| GET | `/complaints/{id}` | ALL (scope rules §4) | Detail |
| PATCH | `/complaints/{id}` | O (owner/supervisor) | Edit allowed fields |
| POST | `/complaints/{id}/transition` | O | Change state (validated) |
| POST | `/complaints/{id}/transfer` | O | Transfer to another unit (remark required) |
| POST | `/complaints/{id}/escalate` | O | `{level: 2|3, to_user_id?, reason}`; sets status `ESCALATED`; notifies the recipient (F-29) |
| POST | `/complaints/{id}/next-action` | O (owner/supervisor) | `{text, due_on}` — sets the next action required (KF2.8) |
| GET | `/escalations` | SUP, CA, M, A | Escalated cases: supervisor → their unit at Level 2; Competent Authority → Level 3; management and admin → all |
| POST | `/complaints/{id}/remarks` | O | Add a remark |
| POST | `/complaints/{id}/attachments` | O | Add an attachment |
| POST | `/complaints/{id}/reveal-pii` | O,M | Body `{reason}`; returns unmasked personal fields; audited |
| GET | `/complaints/{id}/events` | ALL (scope rules) | Workflow history |
| GET | `/complaints/{id}/overlaps` | ALL (scope rules) | Overlaps involving this complaint |

### 5.4 Overlaps, Gate, coordination

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/overlaps` | O,M,A,U | Queue: filter by `status`, `severity`, `institution_id`, `unit` |
| GET | `/overlaps/{id}` | O,M,A,U | Both case summaries + Match Receipt |
| POST | `/overlaps/{id}/decision` | O | `{decision: CONFIRM|DISMISS|LINK|UNLINK, reason, save_alias?}` |
| POST | `/overlaps/{id}/summary` | O,M | Generate AI summary (falls back to template) |
| GET | `/overlaps/{id}/brief.pdf` | O,M,A | Joint Case Brief (U9) |
| POST | `/gate/check` | O | `{institution_id | complaint_id, action_type}` → result |
| POST | `/gate/{check_id}/decision` | O | `{choice: REQUEST_COORDINATION|LINK|PROCEED, justification?}` |
| GET | `/coordination` | O,M | My threads |
| POST | `/coordination` | O | Open a thread for given complaints |
| GET | `/coordination/{id}` | participants,M,A,U | Thread with messages |
| POST | `/coordination/{id}/messages` | participants | Post a note |
| POST | `/coordination/{id}/resolve` | participants | `{outcome, note}` |
| GET | `/notifications` | ALL | My notifications |
| POST | `/notifications/{id}/read` | ALL | Mark read |

### 5.5 Monitoring, reports, intelligence

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/dashboard/summary` | ALL (scoped) | Counters: total received, pending, under process, disposed, transferred, **escalated**, **beyond timeline**; by unit (definitions in §3.3) |
| GET | `/dashboard/by-institution` | ALL (scoped) | **Institution-wise case status (KF4.7):** per institution the counts by status and unit |
| GET | `/dashboard/ageing` | ALL (scoped) | Age buckets for open cases |
| GET | `/dashboard/workload` | M,O | Open cases per unit and per owner |
| GET | `/reports/{kind}` | M,A,O | `kind`: `by_unit`, `by_region`, `by_status`, `by_institution`, `institution_history` (needs `institution_id`), `ageing`, `disposal_rate`, `overlaps`, `performance` (needs `period=monthly|quarterly` and a date range); `format=json|csv|pdf` |
| GET | `/clusters` | M,A,O | Systemic clusters |
| GET | `/risk/ranking` | M,A,U | Institutions ranked by score with components |
| POST | `/ask` | O,M | `{question}` → `{parsed_filters, explanation, used_ai}`; **returns filters only**, the client then calls the normal list endpoint |

### 5.6 Import, audit, admin

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/imports` | A,O | Upload file → `import_job` (`UPLOADED`), returns detected columns and sample rows |
| POST | `/imports/{id}/map` | A,O | Save or choose a column mapping |
| POST | `/imports/{id}/dry-run` | A,O | Report of rows to create, rows with errors, suggested institution matches, overlaps that would be flagged |
| POST | `/imports/{id}/commit` | A | Create the records (idempotent) |
| GET | `/imports/{id}` | A,O | Status and report |
| GET | `/audit` | U,A | Filter by `actor`, `entity`, `action`, `from/to` |
| GET | `/audit/verify` | U,A | Re-compute the chain; `{intact, entries_checked, first_broken_seq?, head_hash}` |
| GET | `/admin/settings` | A | Thresholds etc. |
| PUT | `/admin/settings/{key}` | A | Update (audited) |
| GET | `/admin/users` | A | List users |
| POST | `/admin/users` | A | Create |
| PATCH | `/admin/users/{id}` | A | Role/unit/active |
| GET | `/admin/scenarios` | A | List demo scenarios |
| POST | `/admin/scenarios/{id}/load` | A | Load a scenario (synthetic data only; refuses if non-synthetic data would be touched) |
| POST | `/admin/ai/{feature}` | A | Enable/disable `embeddings`, `llm` |

---

## 6. The Overlap Engine

The engine lives in `app/engine/` as **pure functions**. Its inputs are plain data; its output is a **Match Receipt**. All numbers below are **starting values** (V-B7), stored in `settings`, and tuned on the development split only.

### 6.1 Text normalisation (shared by L2 and L3)

Applied in this order (each step has a unit test):
1. Unicode NFKC normalisation; lowercase.
2. Replace punctuation and repeated whitespace with single spaces.
3. **Script handling (U5):** transliterate Devanagari to Latin; keep a copy of the original.
4. **Abbreviation expansion** from a maintained dictionary (e.g. `inst`→`institute`, `engg`→`engineering`, `tech`→`technology`, `univ`→`university`, `coll`→`college`, `mgmt`→`management`, `pharm`→`pharmacy`, `sci`→`science`).
5. **Spelling variants** map (e.g. `vishwakarma`, `vishvakarma`, `viswakarma`), built from the registry's aliases plus a small seed list.
6. Drop **stop words** (`of`, `the`, `and`, `for`) and generic words with low information (`institute`, `college`) **only for the "core name" comparison**, not for the full-name comparison.
7. Produce: `full_tokens`, `core_tokens`, `acronym` (initials of the full tokens), `sorted_core`.

### 6.2 Institution matching (L1 + L2)

Inputs: a text (and optional ID, state, district, pincode) and the registry. Output: a ranked list of `(institution_id, S_inst, evidence)`.

**L1 — exact ID.** If `aicte_id` is present and equals a registry ID → `S_inst = 1.0`, evidence `ID_EXACT`. If an ID is present but unknown → evidence `ID_UNKNOWN` (no score from L1).

**L1b — alias hit.** If the normalised text equals a normalised alias of an institution → `S_inst = 0.98`, evidence `ALIAS_EXACT` (this is Alias Memory).

**L2 — fuzzy.** For each candidate institution (pre-filtered by state/district when known, otherwise by cheap token-overlap):
- `name_set` = token-set similarity of `core_tokens` (0–1)
- `name_sort` = token-sort similarity of the full names (0–1)
- `jw` = Jaro–Winkler of joined `sorted_core` (0–1)
- `acr` = 1.0 if the text equals the candidate's acronym, else 0
- `name_score = max(acr, 0.45·name_set + 0.30·name_sort + 0.25·jw)`
- `loc_score` = 1.0 if district matches, 0.6 if only state matches, 0.3 if unknown, 0 if state conflicts
- `S_inst = 0.75·name_score + 0.25·loc_score`, capped at 0.97 (only ID/alias can reach above).

**Decision bands (starting values):**

| `S_inst` | Meaning | Behaviour |
|---|---|---|
| ≥ 0.90 **and** a second signal (location agrees, or alias, or ID) | Strong match | Offered first in the picker; overlap scanning treats it as the same institution |
| 0.75 – 0.90 | Possible | Shown in the picker with its score; scanning treats as *look-alike* (severity capped at RELATED) |
| < 0.75 | No match | Not offered |

**Two-signal rule (guards against false merges, risk R1):** a name-only match is never "strong". **The engine never merges institution records automatically.** At intake it only *suggests*; an officer picks. Duplicate records are an admin task.

### 6.3 Issue matching (L3)

For two complaints on the same (or look-alike) institution:
- `cat` = 1.0 same category, 0.5 same category family, else 0.
- `kw` = Jaccard overlap of normalised content tokens (stop words removed, light stemming).
- `emb` = cosine similarity of the two complaint embeddings (when available), rescaled so that the model's typical "unrelated" level maps to 0.

**With embeddings:** `S_issue = 0.55·emb + 0.25·cat + 0.20·kw`
**Fallback (no embeddings):** `S_issue = 0.55·cat + 0.45·kw`

The Match Receipt records **which formula was used**, so the officer can see "meaning matching: unavailable".

### 6.4 State compatibility (L4 inputs)
- `both_open` — both complaints not `DISPOSED`
- `recent_closed` — one closed within `recent_days` (default 90)
- `conflicting_actions` — one has a `PROPOSED`/`DONE` penalty-type action while the other has a `PROPOSED`/`DONE` closure-type action or exoneration on the same institution and issue
- `same_unit` — both held by the same unit

### 6.5 Rules (L4) — severity assignment

Rules are data (a small ordered table in `settings`), evaluated top-down, first match wins:

| # | Condition | Type | Severity |
|---|---|---|---|
| 1 | `conflicting_actions` and `S_issue ≥ 0.5` and institution strong | O4 | CONFLICT |
| 2 | different units, `both_open`, institution strong, `S_issue ≥ T_issue_high` (0.70) | O1 | CONFLICT |
| 3 | different units, `both_open`, institution strong, `S_issue ≥ T_issue_low` (0.40) | O2 | RELATED |
| 4 | different units, `both_open`, institution look-alike, `S_issue ≥ T_issue_high` | O2 | RELATED |
| 5 | different units, `recent_closed`, institution strong, `S_issue ≥ T_issue_high` | O3 | RELATED |
| 6 | `same_unit`, institution strong, `S_issue ≥ 0.85`, same complainant hash or near-identical text | O5 | RELATED |
| else | — | none | no overlap record |

A scan on intake compares the new complaint against candidates limited to: strong or look-alike institutions, complaints received within a window (default 24 months), and states open/recently closed. Complexity is bounded by the institution filter, so a scan stays fast at 10,000+ complaints.

### 6.6 Configuration (all in `settings`)

`T_inst_strong` (0.90), `T_inst_possible` (0.75), `T_issue_high` (0.70), `T_issue_low` (0.40), `recent_days` (90), `pending_reminder_days` (7), `escalation_grace_days` (3), `auto_escalate` (false), `live_poll_seconds` (15), `scan_window_months` (24), `alert_budget_per_officer_per_day` (20), `coordination_sla_working_days` (3), `embeddings_enabled`, `llm_enabled`, `cluster_min_size` (3), `cluster_window_days` (180), `cluster_sim_threshold` (0.70), risk weights (§7.2).

Changes via `PUT /admin/settings/{key}` are audited and take effect on the next scan. The **engine version** string is stored on every overlap so results can be traced to the configuration used.

### 6.7 Overlap lifecycle
`SUGGESTED` → officer decision → `CONFIRMED` / `DISMISSED` / `LINKED`. `LINKED` adds both complaints to a link group. `UNLINKED` reverses a link (audit entry; link group updated). A dismissed pair is **not re-suggested** unless either complaint's text, institution or state changes materially (the engine compares a stored `evidence_hash`).

### 6.8 Match Receipt (U2)

`receipt_json` has a fixed schema, validated before storage:

```json
{
  "engine_version": "…",
  "institution": {
    "score": 0.94,
    "signals": [
      {"kind": "ALIAS_EXACT|ID_EXACT|NAME_FUZZY|LOCATION", "value": 0.94, "note": "…"}
    ],
    "strength": "STRONG|POSSIBLE"
  },
  "issue": {
    "score": 0.81,
    "formula": "WITH_EMBEDDINGS|FALLBACK",
    "parts": {"embedding": 0.78, "category": 1.0, "keywords": 0.55}
  },
  "state": {"both_open": true, "recent_closed": false, "conflicting_actions": false, "same_unit": false},
  "rule": {"id": 2, "type": "O1", "severity": "CONFLICT"},
  "match_score": 0.88,
  "text_reason": "Both cases concern the same institution (name match 0.94, same district) and the same issue (fee refund), and both are open in different units."
}
```

`text_reason` is built from a template over the structured fields (never free-form), so it is always consistent with the numbers. `match_score = 0.5·S_inst + 0.35·S_issue + 0.15·state_factor` is for **sorting only**; severity comes from the rules. The UI labels it "match score", not "probability" (principle P6).

### 6.9 AI-written summary (F-19) — guardrails
- The LLM receives **only** the structured receipt and the case summary fields (no personal data, no free text beyond the complaint title and category).
- The prompt requires every sentence to be supported by a provided field and forbids new facts.
- The output is checked: it must not contain numbers, dates, institution names or unit names that are absent from the input; if the check fails, **the template summary is returned instead** and the response says `used_ai: false, reason: "validation_failed"`.
- Timeouts and errors also fall back to the template. The UI always shows which kind of summary it is.

### 6.10 Embeddings adapter
- Loaded once at startup (or lazily); vectors are computed on complaint create/update and cached by `text_hash`.
- If the model is unavailable or `embeddings_enabled = false`, the adapter reports `unavailable` and the fallback formula is used.
- SQLite: vectors stored as blobs and compared in Python for candidate sets (small by construction). PostgreSQL: `vector` column with an index (target).

---

## 7. Management Intelligence

### 7.1 Clusters (U7, F-20)
Within one institution and category, build a graph where complaints are connected if `S_issue ≥ cluster_sim_threshold`; connected components of size ≥ `cluster_min_size` within `cluster_window_days` become a **cluster**. Clusters are recomputed incrementally on intake and fully by a nightly job. A cluster is shown as "N similar complaints in D days".

### 7.2 Institution risk score (U7)
A prioritisation aid for management, **not** a judgement about an institution. Score = 100 × Σ wᵢ·cᵢ with each component cᵢ in [0, 1] and shown to the user:

| Component | Definition | Normalisation | Weight (start) |
|---|---|---|---|
| `volume` | Open complaints in the last 12 months | min(n / 10, 1) | 0.20 |
| `ageing` | Median age of open cases | min(days / 180, 1) | 0.20 |
| `multi_unit` | Distinct units holding open cases | min((units − 1) / 2, 1) | 0.15 |
| `repeat` | Share of complaints in the same category as an earlier one | ratio | 0.15 |
| `severity` | Mean `severity_weight` of categories of open cases | scaled to [0,1] | 0.15 |
| `open_conflicts` | Unresolved CONFLICT overlaps | min(n / 3, 1) | 0.10 |
| `trend` | Complaints in the last 90 days vs the previous 90 days | clamp((Δ ratio)/1, 0, 1) | 0.05 |

Weights are configuration (V-B7). Every score response carries the components and a note: "Score is a ranking aid based on complaint data only."
**Fairness checks (tests):** the score does not use institution size or name; a high-volume large institution is not automatically ranked above a small one with older, conflicting cases (a scripted example in the tests).

### 7.3 Deadlines, reminders, SLA and escalation alerts (F-17, F-29)
`due_on = received_on + category.sla_days` (working days, using a holiday table). `expected_disposal_on` defaults to `due_on` and may be changed by the owner with a remark. A scheduled job creates these alerts:

| Alert (PS item) | Rule | Recipient |
|---|---|---|
| Pending-case reminder (KF7.2) | A case in `RECEIVED`/`ASSIGNED` has had no officer action, or an `UNDER_PROCESS` case has had no history event, for `pending_reminder_days` (default 7); repeats each period | owner |
| SLA approaching (KF7.4) | 80% of the SLA window used | owner |
| SLA breached (KF7.4) | after `due_on` | owner and supervisor |
| Escalation alert (KF7.3) | overdue by more than `escalation_grace_days` (default 3); or a coordination thread expired; or a case was just escalated to the recipient | supervisor / next level |

**Escalation is advisory by default** (principle P2): the alert tells the supervisor, and a person escalates. The setting `auto_escalate` (default **off**) lets an administrator turn on automatic escalation to Level 2 after the grace period; the system then records the escalation with actor "system" in the history and the audit trail. Notifications per officer per day are capped by the alert budget (P8); CONFLICT-level and escalation alerts are never capped out.

### 7.4 Live updates (F-31)
The `/stream` endpoint pushes `counters_changed`, `case_changed`, `overlap_created` and `notification` events for the caller's scope. Every event carries a server timestamp; the client shows "last updated" and a stale warning after 30 s without a heartbeat, then falls back to polling. Events contain identifiers and counters only (no personal data); the client re-fetches details through the normal, role-checked endpoints.

### 7.5 Ask the Dashboard (U10, F-21) — safe by construction
- Input: a short text question.
- The LLM (when enabled) is asked to return **JSON only**, matching a fixed schema of allowed filters (unit, region, category, state, `older_than_days`, `institution_text`, date ranges, `has_overlap`, `overdue`).
- The server **validates** the JSON against the schema and the user's role; unknown keys are dropped, values are checked against reference tables, and institution text is resolved through the matching engine.
- The response shows `parsed_filters` and a plain-language restatement. **No SQL is ever generated or executed from model output.**
- Fallback (AI off or invalid output): a rule-based parser handles a small set of phrasings (counts like "older than 60 days", unit names, region names, statuses); otherwise it returns `needs_manual_filters`.

---

## 8. Audit Trail with Hash Chain (U3)

### 8.1 What is recorded
Every state-changing request, every Gate check and decision, every overlap decision, every PII reveal, every settings change, every login success/failure, every import commit, and every admin action. Each entry: `seq`, `occurred_at`, `actor_user_id`, `action`, `entity_type`, `entity_id`, `payload_json` (no personal data; IDs and changed fields only).

### 8.2 Chain
```
 entry_hash = SHA-256( canonical_json(seq, occurred_at, actor_user_id, action,
                                       entity_type, entity_id, payload_json) || prev_hash )
 prev_hash of seq 1 = a fixed documented genesis value
```
`canonical_json` has sorted keys and no insignificant whitespace; the exact algorithm is in the code and covered by test vectors.

### 8.3 Verification
`GET /audit/verify` walks the chain, recomputes each hash, and returns `{intact, entries_checked, first_broken_seq, head_hash}`. The UI shows the **head hash** so it can be written down or printed on the Joint Case Brief.

### 8.4 What it does and does not give (honest statement, risk R10)
- ✅ **Tamper-evident:** changing or deleting any past entry breaks the chain from that point; Verify shows where.
- ❌ **Not tamper-proof:** someone with full database write access could recompute the whole chain. Mitigation: periodically publish the head hash somewhere outside the database (roadmap), and restrict database access in deployment.
- Appends are serialised (V-B5); a concurrency test checks that parallel writers cannot fork the chain.

---

## 9. Security and Privacy

### 9.1 Authentication
Argon2 password hashes; login rate-limited per account and per IP; short-lived access tokens, rotating refresh tokens revoked on logout; account lock after repeated failures with an audit entry. SSO/2FA is roadmap (F-26).

### 9.2 Permission matrix (starting)

| Capability | unit_officer | unit_supervisor | regional_officer | management | competent_authority | admin | auditor |
|---|---|---|---|---|---|---|---|
| View dashboard (scoped) | ✔ | ✔ (unit) | ✔ (region) | ✔ (all) | ✔ (all) | ✔ | ✔ |
| View own-unit case details | ✔ | ✔ (whole unit) | ✔ (region) | summary | ✔ | ✔ | ✔ (read) |
| View other unit's case **summary** | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| View other unit's case **detail** | via coordination/link | via coordination/link | via coordination/link | ✔ | ✔ (read) | ✔ | ✔ (read) |
| Create / edit complaint | ✔ | ✔ | ✔ | ✘ | ✘ | ✔ | ✘ |
| Reassign cases within a unit | ✘ | ✔ | ✘ | ✘ | ✘ | ✔ | ✘ |
| Escalate a case | ✔ (own) | ✔ (unit) | ✔ (region) | ✘ | ✘ | ✘ | ✘ |
| Act on an escalated case | ✘ | ✔ (Level 2) | ✘ | ✘ | ✔ (Level 3) | ✘ | ✘ |
| Run Action Gate | ✔ | ✔ | ✔ | ✘ | ✔ | ✘ | ✘ |
| Decide an overlap | ✔ | ✔ | ✔ | ✘ | ✔ | ✔ | ✘ |
| Reveal PII (with reason) | ✔ (own unit) | ✔ (unit) | ✔ (region) | ✔ | ✔ | ✔ | ✘ |
| Import data | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ | ✘ |
| Reports | ✔ (scoped) | ✔ (unit) | ✔ (region) | ✔ | ✔ | ✔ | ✔ |
| Risk ranking | ✘ | ✘ | ✘ | ✔ | ✔ | ✔ | ✔ |
| Settings, users, scenarios, AI switches | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ | ✘ |
| Audit view and Verify | ✘ | ✘ | ✘ | ✘ | ✔ (read) | ✔ | ✔ |

This matrix is **encoded as data** and a parametrised test walks every endpoint × role and asserts the expected status code (a new endpoint without a matrix row fails the test).

### 9.3 Masking
Responses replace personal fields with masked forms (e.g. `R*** K****`, `98******21`, `r***@d***.com`) unless the caller's role allows plain text. `POST /complaints/{id}/reveal-pii` requires a reason (min length), returns plain values for that request only, and writes an audit entry.

### 9.4 Other controls
Input validation on every model; upload size/type limits and SHA-256 recorded; filenames sanitised; no secrets in the repository or images (`.env.example` only); security headers on the API; CORS closed because the frontend is served same-origin; logs never contain personal data; dependency audit in CI; the import parser treats files as untrusted (row limits, formula-injection neutralised for CSV/Excel exports by prefixing risky cells).

---

## 10. Import Wizard (U8, F-03)

1. **Upload** (CSV/XLSX) → `import_job` `UPLOADED`; the server reads a bounded number of rows and returns columns and a sample.
2. **Map** columns to canonical fields (reference no, institution text, AICTE ID, category, title, description, dates, state, owner, complainant fields). Mappings are saved per unit and reused. Category values can be mapped to our categories through a value-mapping table.
3. **Dry-run:** per row → validate, resolve institution (best match with score), compute whether it would raise an overlap, and list errors with row numbers. Nothing is written except the job report.
4. **Commit:** idempotent by (`unit_id`, `reference_no`); re-running skips existing records; a failed row never aborts the whole job; the final report is stored.
5. A file with an already-seen `sha256` is flagged before step 2.
6. The import commit runs the same overlap scan as manual intake, and notifications are batched to respect the alert budget.

---

## 11. Quality: Ground Truth and Evaluation

### 11.1 Synthetic data generator
`app/cli.py seed --seed 42` creates the dataset in MASTER_PLAN §8 deterministically (including cases approaching or beyond SLA and escalated cases, with last-action and next-action fields filled) and writes `data/ground_truth.json` containing, for every planted scenario, the expected institution link, expected overlap type/severity, and expected Gate result.

**Variant generators for institution names:** abbreviations, dropped/added words, typos (edit distance 1–2), word-order swaps, mixed-case, punctuation noise, Devanagari spellings, Hinglish spellings, and **decoys** (different institutions that share most words and/or the same city).

### 11.2 Evaluation harness
`python -m app.cli evaluate` runs the engine over the ground truth and prints precision, recall and F1 **per layer and overall**, plus a list of every miss and false merge.
- **Split:** scenarios are divided into a **development split (70%)** for tuning thresholds and a **held-out split (30%)** used only for reporting. Reported numbers always come from the held-out split.
- Every threshold change records the date, the dev-split result and the held-out result in Appendix B.

### 11.3 Targets (not claims — see V-B7)

| Measure | Target |
|---|---|
| Institution matching, variant pairs | recall ≥ 0.95, precision ≥ 0.95 |
| Decoys wrongly treated as strong matches | 0 |
| Issue matching (with embeddings) | recall ≥ 0.80, precision ≥ 0.85 |
| Gate result vs expected, planted scenarios | 100% |
| Audit tamper detection | 100% |

### 11.4 Test layers

| Layer | Tooling | Content |
|---|---|---|
| Unit | pytest | normalisation steps, each similarity function, rules table, risk components, state machine, hash chain test vectors |
| Property-based | hypothesis | normalisation idempotence; score symmetry and range [0,1]; adding noise within the generator's limits keeps the strong match |
| Engine evaluation | pytest + CLI | ground-truth run asserts targets on the **held-out** split |
| API | pytest + test client | every endpoint happy path and error codes; envelope shape; 501 stubs return `planned_phase` |
| Role matrix | parametrised pytest | endpoint × role expectation table (§9.2) |
| Security | pytest | masking, reveal-with-reason audit, rate limit, locked account, upload limits, formula-injection neutralisation |
| Audit | pytest | chain verifies; edited row, deleted row and reordered rows are each detected; concurrent append test |
| AI-off | pytest | whole suite of overlap and Gate tests with `embeddings_enabled=false` and `llm_enabled=false` |
| LLM guard | pytest with a fake adapter | invented fact in output → template fallback |
| Migration | pytest | upgrade from empty and downgrade; run on both SQLite and PostgreSQL (V-B4) |
| Performance | script | scan time at 1k/10k/50k complaints; Gate p95; recorded in Appendix B |
| Contract | CI step | exported OpenAPI equals the committed copy |

**Rules:** a bug fix starts with a failing test; no network access in tests (adapters are faked); the seed is fixed so tests are deterministic.

---

## 12. Configuration Reference

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/samanvay.db` | Database connection |
| `SECRET_KEY` | *(required, no default)* | Token signing |
| `PII_ENCRYPTION_KEY` | *(required, no default)* | Field encryption key |
| `ENVIRONMENT` | `dev` | `dev`/`test`/`demo`/`prod` |
| `EMBEDDINGS_ENABLED` | `true` | Initial value of the setting |
| `EMBEDDING_MODEL` | *(chosen at B4, V-B2)* | Model name/path |
| `LLM_ENABLED` | `false` | Initial value |
| `LLM_PROVIDER` / `LLM_API_KEY` | unset | Adapter configuration (V-B6) |
| `ACCESS_TOKEN_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_DAYS` | `7` | Refresh token lifetime |
| `MAX_UPLOAD_MB` | `10` | Upload limit |
| `LOG_LEVEL` | `INFO` | Logging |

`.env.example` is committed; real `.env` is never committed.

---

## 13. Planned Repository Layout (backend)

```
backend/
├── BACKEND_PLAN.md
├── pyproject.toml · uv.lock
├── Dockerfile
├── alembic.ini · migrations/
├── app/
│   ├── main.py                  app factory, middleware (request id, errors, security headers)
│   ├── cli.py                   seed · evaluate · openapi · verify-audit · recompute-risk
│   ├── core/                    config.py · security.py · roles.py · masking.py · audit.py · errors.py · clock.py
│   ├── db/                      base.py · models/*.py · repositories/*.py
│   ├── engine/                  normalize.py · institution.py · issue.py · rules.py · receipt.py · scoring.py
│   ├── adapters/                embeddings.py (real + fallback) · llm.py (real + template) · pdf.py
│   ├── services/                complaints.py · institutions.py · overlaps.py · gate.py · coordination.py
│   │                            imports.py · reports.py · risk.py · clusters.py · ask.py · notifications.py · escalations.py · dashboard.py · stream.py
│   └── api/v1/                  routers per area (§5)
├── data/                        seed outputs · ground_truth.json (generated, not hand-edited)
└── tests/                       unit/ · engine/ · api/ · security/ · audit/ · ai_off/ · perf/
```

---

## 14. Designed vs. Built (backend)

Status keys: 📋 Planned · 🔨 In progress · ✅ Built & tested · ⚠️ Built with a known limitation.

| # | Item | Phase | Status | Evidence |
|---|---|---|---|---|
| 1 | Project skeleton, lockfile, lint/type/test tooling, CI | B1 | ⚠️ | backend/pyproject.toml, backend/tests/. Known limits: no lockfile, no CI, no mypy/ruff run yet, Python 3.14 used (plan says 3.12), no Docker image |
| 2 | Schema + migrations (§3), portable across SQLite/PostgreSQL | B1 | ⚠️ | backend/app/db/models/. Built: units, regions, categories, users, refresh tokens, institutions, aliases, complaints, events, overlaps, gate checks, notifications (table only), audit log. Not built: link groups, coordination, attachments, actions, embeddings, clusters, risk, imports, settings use. SQLite only; no Alembic migrations (tables created from models) |
| 3 | Config, error envelope, request id, health/ready/meta | B1 | ✅ | app/main.py, app/api/v1/system.py; tests test_health_and_ready, test_unauthenticated_is_401_with_envelope |
| 4 | Seed generator + ground truth (§11.1) | B1 | ⚠️ | app/seed.py, `python -m app.cli seed`, data/ground_truth.json. Limits: 60 institutions not 40; no Devanagari variants; no 70/30 split; scenarios counts differ slightly from MASTER_PLAN §8 |
| 5 | Auth, roles, masking, role-matrix test | B1/B4 | ⚠️ | app/core/security.py, app/api/deps.py, app/core/crypto.py; tests test_role_enforced_on_backend, test_reveal_pii_needs_reason_and_is_audited, test_other_unit_detail_is_hidden_but_summary_visible. Not built: the matrix-driven endpoint x role test, rate limiting by IP, admin user management |
| 6 | Audit log with hash chain + Verify | B2 | ✅ | app/core/audit.py; test_audit_chain_intact_and_tamper_detected (edit detected). Delete/reorder detection is by the same check but not separately tested |
| 7 | Institution registry, aliases, suggest endpoint | B2 | ✅ | records.py, extras.py; test_unmatched_case_can_be_linked_and_alias_is_remembered, test_institution_admin_and_complaint_edit_and_attachment |
| 8 | Complaint lifecycle, events, transfer, deadlines fields | B2 | ⚠️ | services/complaints.py, extras.py; test_lifecycle_rules, test_institution_admin_and_complaint_edit_and_attachment (edit, attachments). Not built: receiving-unit acceptance step; attachments are stored on local disk only |
| 9 | Dashboard summary/ageing/workload, search/filters | B2 | ✅ | app/services/dashboard.py; test_dashboard_counters_equal_database, test_unit_officer_dashboard_is_scoped. Filters in GET /complaints (tested through the UI flow, not every filter by unit test) |
| 10 | Import Wizard (map, dry-run, commit) | B2 | ⚠️ | services/imports.py; tests test_import_wizard_reports_bad_rows_and_commit_is_idempotent, test_import_unquoted_comma_is_a_row_error_not_a_crash, test_import_rejects_bad_files. CSV only (no Excel); no saved column mappings; commit is admin-only |
| 11 | Engine L1/L2/L4 + Match Receipt + evaluation harness | B3 | ⚠️ | app/engine/, app/evaluate.py. L1, L2 and L4 built; no held-out split; thresholds not tuned. Measured on our own generated data: see Appendix B |
| 12 | Overlap scan on intake, overlap queue, decisions, Alias Memory | B3 | ✅ | app/engine/overlap.py, records.py; test_create_complaint_resolves_variant_and_flags_overlap, test_overlap_always_has_receipt_and_label |
| 13 | Action Gate (check + decision) | B3 | ✅ | records.py gate endpoints; test_gate_requires_justification_on_conflict_and_close_is_gated |
| 14 | Issue matching (L3) with embeddings + fallback | B4 | ⚠️ | Built without embeddings: engine/concepts.py is a hand-written concept lexicon (English, Hinglish, Devanagari); engine/overlap.py uses shared concepts to add an O4 type and a receipt reason; tests/test_concepts.py. It is not a language model and misses concepts not in the list. issue_similarity (word overlap) stays information-only. Optional AI reading: services/issue_judge.py (setting ai_issue_matching, default off; tests/test_issue_judge.py with a fake model; never run against the real service). Neural embeddings: not built, because fastembed installed but the model file download was blocked on the build machine |
| 15 | Coordination Handshake | B4 | ✅ | extras.py coordination routes; test_coordination_handshake_two_users, test_coordination_expiry_alerts_supervisor |
| 16 | SLA job, notifications, alert budget | B4 | ⚠️ | services/notifications.py; test_sla_job_creates_alerts_and_respects_advisory_escalation, test_alert_budget_caps_non_conflict_alerts, test_budget_never_blocks_a_request_from_a_colleague. In-app only. The job runs when an admin triggers it (POST /admin/jobs/sla); there is no background scheduler |
| 17 | Reports + CSV/PDF export | B5 | ⚠️ | JSON and CSV for all kinds, plus /reports/performance (monthly, quarterly); test_performance_report_and_overlaps_for_case, test_csv_report_declares_synthetic. No PDF reports |
| 18 | Risk score, clusters | B5 | ⚠️ | services/intelligence.py; test_risk_components_and_fairness, test_clusters_found. Clusters group by college and category only (wording is not compared). No stored score history |
| 19 | AI summary with validation + template fallback | B5 | ⚠️ | services/summary.py; test_summary_template_and_llm_guard. The language-model path was tested only with a fake; it has never run against the real service (no API key was available) |
| 20 | Ask the Dashboard (validated filters) | B5 | ⚠️ | services/ask.py; test_ask_returns_filters_only, test_older_than_days_filter. Rule-based path tested; the language-model path was not run against the real service |
| 21 | Joint Case Brief PDF | B5 | ✅ | services/pdfbrief.py; test_brief_pdf (checks the file is a PDF and the role guard; page content was not inspected automatically) |
| 22 | Scenario loader (synthetic only) | B5 | ✅ | extras.py scenarios; test_admin_users_and_scenarios (loads, and refuses when non-synthetic data exists) |
| 23 | Performance measurement, security review, PostgreSQL run | B6 | 📋 | — |
| 24 | System Case ID and case tracking fields: last/next action, date of last action, expected disposal date (F-30) | B1 | ✅ | app/services/complaints.py (case ID, last/next action, expected disposal); test_lifecycle_rules |
| 25 | Escalation workflow: status, history, escalate endpoint, escalations queue; alerts in B4 (F-29) | B2/B4 | ✅ | escalate + /escalations + advisory alerts; auto-escalation off by default and audited when on; test_lifecycle_rules, test_auto_escalation_off_by_default_and_audited_when_on |
| 26 | Live updates stream with polling fallback (F-31); institution-wise dashboard endpoint | B2 | ✅ | GET /stream (Server-Sent Events) and by-institution endpoint; test_stream_sends_counters_and_heartbeat |
| 27 | Extended reports: status-wise, institution history, overlaps, monthly/quarterly (F-32) | B5 | ⚠️ | status-wise, institution history, overlaps, monthly/quarterly built (JSON/CSV); no PDF |

---

## 15. Phase Plan (backend)

| Phase | Scope | Exit criteria |
|---|---|---|
| **B0 Planning** | This document | ✅ Committed |
| **B1 Foundations** | Items 1–5 and 24 (auth baseline), 501 stubs for every route in §5 with `planned_phase` | `make up` works; `/readyz` healthy; OpenAPI exported and committed; seed produces dataset + ground truth; CI green |
| **B2 Records & visibility** | Items 6–10, 26, and the status/history part of 25 | Audit chain verifies and detects edit/delete/reorder; counters equal raw database counts (tested); import dry-run reports bad rows by number |
| **B3 Overlap core** | Items 11–13 | Targets in §11.3 met on the held-out split **or** the shortfall recorded; Gate correct for every planted scenario; decoys never strong |
| **B4 Intelligence & roles** | Items 14–16, escalation alerts (rest of item 25), role matrix complete | L3 evaluated with the chosen model (V-B2) and fallback proven; role-matrix test covers every endpoint |
| **B5 Management & AI** | Items 17–22 and 27 | Report totals reconcile with raw data; every AI feature passes the AI-off and LLM-guard tests |
| **B6 Hardening** | Item 23 | Appendix B filled with real measurements; PostgreSQL suite passes; dependency audit clean |

---

## 16. Architecture Decision Log

| ID | Chose | Over | Why |
|---|---|---|---|
| ADR-B1 | FastAPI + Pydantic | Django, Node | Typed models give an OpenAPI contract for the frontend; strong ecosystem for the text-matching libraries |
| ADR-B2 | Pure-function engine | Logic inside services/ORM | Testable against ground truth, runnable offline, easy to explain |
| ADR-B3 | SQLite first, portable schema, PostgreSQL + pgvector as target | PostgreSQL only | Zero-setup prototype without painting ourselves into a corner |
| ADR-B4 | Rules as data in `settings` | Hard-coded thresholds | Tunable and auditable without a release |
| ADR-B5 | Officer-confirmed aliases | Automatic institution merging | Avoids false merges; makes "learning" visible and safe |
| ADR-B6 | Match Receipt with a templated text reason | Free-text AI explanation | Always consistent with the numbers |
| ADR-B7 | LLM output validated, fallback template | Trust LLM output | Prevents invented facts |
| ADR-B8 | LLM returns filter JSON validated server-side | Text-to-SQL | Safety and explainability |
| ADR-B9 | Hash-chained audit with Verify | Plain log table | Demonstrable integrity |
| ADR-B10 | Encrypt complainant fields at rest; mask on output | Plain text with role checks only | Defence in depth |
| ADR-B11 | Gate shows summaries, hides details across units | Full cross-unit visibility | Coordination without over-sharing |
| ADR-B12 | Held-out evaluation split | Tune and report on the same data | Prevents over-claiming accuracy |
| ADR-B13 | Escalation is advisory by default; automatic escalation is a switch | Always-automatic escalation | Keeps officials in control (P2) while allowing a stricter deployment |
| ADR-B14 | Server-Sent Events with a polling fallback | WebSockets | One-way updates are enough; simpler through proxies; fallback keeps the dashboard live when streaming fails |
| ADR-B15 | Roles are `unit_officer` + unit assignment, not one role per Bureau | A role per Bureau/Cell | The statement allows "other Bureaus/Cells"; adding a unit must not need a code change |

---

## 17. Backend Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RB1 | False merge of different institutions | Medium | High | Two-signal rule, never auto-merge, decoys in tests |
| RB2 | Hindi/Hinglish matching weak | Medium | Medium | Evaluate transliteration and multilingual model (V-B2, V-B3); alias seed list |
| RB3 | Embedding model heavy for the machine | Medium | Medium | Lazy load, cache vectors, fallback formula |
| RB4 | LLM invents facts | Medium | High | Validation + template fallback |
| RB5 | Hash chain forks under concurrency | Low | High | Serialised appends, concurrency test (V-B5) |
| RB6 | Role matrix gaps | Medium | High | Matrix-as-data test that fails for any unlisted endpoint |
| RB7 | Alert overload | Medium | Medium | Alert budget, grouping by institution |
| RB8 | SQLite/PostgreSQL divergence | Medium | Medium | Dual-database tests from B3 (V-B4) |
| RB9 | Over-claiming accuracy | Medium | High | Held-out split, numbers only from Appendix B |
| RB10 | Personal data leaking in logs or payloads | Low | High | Logging filters, payload rules in §8.1, tests |
| RB11 | Our definitions of "pending" and "under process" differ from AICTE's | Medium | Medium | V-B9: confirm with officers; definitions in one tested place so a change is one edit |
| RB12 | Live stream drops silently and the dashboard looks current when it is not | Medium | Medium | Heartbeat, "last updated" and stale warning in the client; polling fallback |

---

## Appendix A — Resolved Versions (to be filled at B1)

*(empty — nothing built yet)*

## Appendix B — Verification Record (to be filled as we build)

| Check | Command | Result | Date |
|---|---|---|---|
| *(empty — nothing built yet)* | | | |

## Appendix C — Document Maintenance Rules

- Dated update lines go in the header; wrong statements are corrected in place with a dated note.
- Update §14 here and the API routes in the same commit as the code.
- Every "✅" cites a file and a test.
- **Git rule:** every commit and push is authored by Ayush More only; no co-author trailers or tool attribution (see `../CLAUDE.md`).

---

## Appendix B — Measured so far (2026-10-28)

All figures are from `python -m app.cli evaluate` on the generated dataset (seed 42, rules-1.0). The data and the answers were produced by us, no held-out split exists, and thresholds (0.92 auto-link, 0.78 suggest) were set before the data was generated and not tuned afterwards. These show the rules behave as designed, not accuracy on real data.

| Check | Result |
|---|---|
| Misspelled / abbreviated names resolved automatically to the right college | 13 of 20 (the other 7 scored below 0.92 and are sent to an officer, by design) |
| Overlaps found for those 20 planted pairs | 13 of 20 (the 7 are not linked, so no overlap check runs until an officer links them) |
| Planted conflicting-action pairs flagged Conflict | 8 of 8 |
| Different-wording pairs flagged | 15 of 15; 15 of 15 also carry a shared concept in the receipt. The pairs and the lexicon were written by the same author, so this is not a held-out measurement |
| Look-alike decoys wrongly merged | 0 of 10; all 10 resolved to their own record |
| Automated tests | 25 passed (backend/tests) |


