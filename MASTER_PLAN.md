# SAMANVAY — Master Plan

**Team:** SlothDevs (SIH) · **Solution (working name):** SAMANVAY, Hindi for "coordination" · **Domain:** Governance / Regulatory technology
**Problem statement:** AICTE (Regulation Bureau) — an integrated institution complaint monitoring and status dashboard
**PS number:** *not recorded yet* (see V-M1)
**Document date:** 2026-10-27 (v1.0)
**Companion documents:** [`backend/BACKEND_PLAN.md`](backend/BACKEND_PLAN.md) (data, API, engine) · [`frontend/FRONTEND_PLAN.md`](frontend/FRONTEND_PLAN.md) (web app)
**Project phase:** **M0 — Planning: ✅ this document set.** Nothing is built yet. Next: **M1 — Foundations.**

> ⚠️ **Honesty rule (applies to all three documents):** a "✅" is allowed only when it points to a file in this repository and a test that passed. Until code exists, everything is **📋 Planned**. Numbers about performance or accuracy are *targets* until they are measured and recorded in an Appendix.
> When this document and the two companion plans disagree, fix all three in the same commit.

---

## ⚠️ Verification & Discrepancy Log — Read First

| # | Item | Detail | Resolution / action | Status |
|---|---|---|---|---|
| V-M1 | The exact problem-statement text and PS number are not in this repo | The official portal was unavailable when this plan was written. Requirements below were reconstructed from the team's own reading of the statement (listed in §1.3) | The first person with access pastes the official text into `docs/PROBLEM_STATEMENT.md`; then re-map every requirement ID `R-xx` in §5 to the official wording and fix the PS number in all three headers | ⏳ Open |
| V-M2 | Requirement IDs `R-01…` are **working IDs**, not official ones | They come from V-M1's reconstruction | Re-map when V-M1 is closed | ⏳ Open |
| V-M3 | The product name SAMANVAY is a working name | It must be checked for clashes before any public use | Decide before the final presentation | ⏳ Open |
| V-M4 | No real AICTE data is available | Complaint data is sensitive and not public | Use **synthetic data only** and say so on every screen that shows it (§8) | ✅ Decided |
| V-M5 | Embedding model and LLM are optional dependencies | They may be unavailable offline or on the demo machine | Every AI feature has a **non-AI fallback** (§4.3, backend plan §6) | ✅ Decided |
| V-M6 | Real AICTE units use existing systems we have not seen | The shape of their data is assumed | Integration is designed as an **import layer** (CSV/Excel/API) with a column-mapping step, not a replacement system (U8) | ✅ Decided |

---

## 1. The Problem

### 1.1 In simple words

AICTE oversees technical colleges in India. Students, parents, teachers and others send complaints about colleges. Inside AICTE, **different units handle these complaints** — mainly the **Regulation Bureau (RB)** and the **Public Grievance Redressal Cell (PGRC)**, and possibly others such as regional offices.

Each unit keeps its own records in its own way. So when College X has one complaint with PGRC and another with RB, **nobody sees both**. This causes:

1. **Duplicate work** — two units investigate the same issue separately.
2. **Conflicting actions** — one unit may be penalising a college while another is closing a complaint in its favour.
3. **Delays** — each unit waits, unaware the other has already collected evidence.
4. **No single answer** to "Who is handling this college right now, and what has already happened?"

### 1.2 What AICTE needs

One dashboard where authorised officials can:
- see **all complaints from all units** in one place;
- see **who holds each complaint**, its status and its full history;
- get a **warning when more than one unit is dealing with the same institution**, even if the complaint wording, case numbers or college spellings differ.

### 1.3 Requirements as understood (working list — see V-M1)

| ID | Requirement (reconstructed) |
|---|---|
| R-01 | Central repository of complaints from all units (RB, PGRC, others) |
| R-02 | Dashboard of counts: total, pending, under process, disposed, transferred, overdue |
| R-03 | Search and filters: institution, AICTE ID, unit, region, category, status, date range |
| R-04 | Per-institution view of all complaints across units |
| R-05 | Workflow history per case: who did what, when, with remarks and documents |
| R-06 | Detect overlapping cases for the same institution, including with different wording or references |
| R-07 | Raise an alert titled **"Potential Overlapping Cases – Coordination Required"** |
| R-08 | Reminders / alerts for cases close to their deadline or overdue |
| R-09 | Reports by unit, region and institution (ageing, disposal rate, workload) |
| R-10 | Role-based access for authorised officials |
| R-11 | Innovation expected: intelligent (AI-assisted) analytics beyond plain filters |

### 1.4 Honest assessment of where the difficulty lies

Dashboards, filters, status counts and reports are standard work; most teams will build them. The hard, judged part is **R-06/R-07/R-11: finding that two cases are "about the same institution and issue" when the data does not say so directly.** That is an entity-resolution problem plus a text-similarity problem, and it must be **explainable** because the users are government officials who must trust and defend what the system tells them.

---

## 2. Users and Roles

| Persona | Works in | What they need | Main screens |
|---|---|---|---|
| **RB Officer** | Regulation Bureau | Before issuing a notice or penalty: "Is anyone else already dealing with this college?" | Pre-Action Check, College 360°, My Cases, Overlaps |
| **PGRC Officer** | Public Grievance Redressal Cell | Log and track complaints; see if RB already has a related case | My Cases, Complaint Detail, Overlaps |
| **Regional Officer** | Regional office | See complaints in own region; coordinate with units | Dashboard (region scope), College 360° |
| **Senior Management** | Leadership | Where are the problems? Which colleges repeat? Which unit is overloaded? | Management View, Reports, Hotspots |
| **Data Steward / Admin** | Support team | Import data, fix institution records, manage users and thresholds | Import, Institution Registry, Admin |
| **Auditor (read-only)** | Vigilance / audit | Prove who did what and that records were not altered | Audit Trail, Verify Chain |

Role rules are enforced by the **backend**; the UI only hides what a role cannot use (backend plan §9).

---

## 3. Principles (non-negotiable)

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **No flag without a reason** | Every overlap alert shows the evidence that produced it (a "Match Receipt", U2). No black-box scores. |
| P2 | **Assist, never decide** | The system suggests; an officer confirms, dismisses or links. It never closes, transfers or penalises on its own. |
| P3 | **Fail safe, not silent** | If the AI part is unavailable, the rules and fuzzy engine still work and the UI says "AI summary unavailable". Never fake an AI output. |
| P4 | **Everything is traceable** | Every action writes an audit entry; entries are hash-chained so tampering is detectable (U3). |
| P5 | **Least privilege and masked by default** | Complainant personal data is masked unless the role needs it; revealing it requires a reason that is logged (U6). |
| P6 | **Honest numbers** | Match confidence is shown as a "match score", not as a probability, unless it is calibrated on labelled data. |
| P7 | **Humans can correct the machine** | Wrong merges can be unlinked; wrong institution matches can be fixed and the alias remembered (U4). |
| P8 | **Alert budget** | Too many alerts get ignored. Alerts are ranked and capped per officer per day; critical conflicts are never collapsed. |
| P9 | **Demo data is declared** | All data is synthetic and every view shows a **SYNTHETIC DATA** badge. |

---

## 4. The Solution

### 4.1 One line

> **A single dashboard for all AICTE complaints that warns an officer before they act on a college another unit is already handling, explains why, and shows management which colleges need attention.**

### 4.2 The four building blocks

1. **One place for all data** — complaints from RB, PGRC and other units flow into one database through an import layer; every college gets one canonical profile.
2. **The Overlap Engine** (the brain) — layered matching that decides "same institution?" and "same issue?" and produces an explained result (§4.3).
3. **The Action Gate** (the headline feature) — a pre-action conflict check that runs *before* an officer acts on a college (§4.4).
4. **The Monitoring Layer** — dashboard, College 360°, deadlines, reports, and an institution risk score for management.

### 4.3 The Overlap Engine, in plain words

Two complaints are compared in layers; each layer adds evidence and is shown to the officer.

| Layer | Question | Example | Fallback if unavailable |
|---|---|---|---|
| L1 Exact ID | Same AICTE permanent ID? | Both cite the same ID | n/a (always on) |
| L2 Institution matching | Do the names/addresses refer to the same college? | "VIT Pune", "Vishwakarma Inst. of Technology", "VIIT", "विश्वकर्मा इंस्टिट्यूट ऑफ टेक्नोलॉजी" | Normalisation + fuzzy matching (always on) |
| L3 Issue matching | Are they about the same kind of problem? | "fees not refunded" vs "money not returned after withdrawing admission" | Category + keyword overlap |
| L4 Rules | Do the case states create a conflict? | RB open + PGRC open on same college within N days | n/a (always on) |
| L5 Explanation | Why was this flagged? | A short, readable reason | Template text built from L1–L4 evidence |
| L6 Officer decision | Is the flag right? | Confirm / Dismiss / Link | Stored and reused (U4) |

### 4.4 The Action Gate (headline feature)

When an officer is about to take a significant action on a college (issue a notice, impose a penalty, close a case, transfer a case), the system runs a **conflict check** first and shows one of three results:

- **🟢 Clear** — no other unit has a related open case. Proceed.
- **🟡 Related activity** — another unit has a case with a lower match score or a different issue. Show it, let the officer proceed with a note.
- **🔴 Conflict** — another unit has an open case on the same institution and issue, or a conflicting action is pending. The officer must either **request coordination**, **link the cases**, or **proceed with a written justification** (which is audited). The action is never silently blocked and never silently allowed.

This turns the system from a *report* into a *prevention* tool, which is the headline USP.

### 4.5 Differentiators (USPs) — "small, real, buildable"

These are added on top of the agreed idea. Each is small, but together they make the solution distinctive, credible and easy to present.

| ID | USP | What it is | Why it matters to judges / users |
|---|---|---|---|
| **U1** | **Action Gate with Coordination Handshake** | The conflict check (§4.4) plus a one-click "Request coordination" that opens a shared thread between the two units' officers and puts both cases on hold-for-discussion with a visible clock | Turns a warning into resolution; directly attacks "conflicting actions" |
| **U2** | **Match Receipt** | Every overlap shows a compact receipt: per-layer evidence, weights, and the final score (e.g. "ID ✔ · Name 0.94 · Same district ✔ · Issue 0.81 · Both open ✔") | Explainability that a government user can quote in a file note |
| **U3** | **Tamper-evident audit trail with a "Verify" button** | Each audit entry stores the hash of the previous one; the Auditor view re-computes the chain and reports "Chain intact" or the first broken entry | Concrete accountability and integrity story; cheap to build, impressive to demo |
| **U4** | **Alias Memory** | When an officer confirms that two spellings are the same college, the alias is saved to the institution registry and is used immediately for all future matching | Visible "learning from officers" with no ML training risk; supports the roadmap claim |
| **U5** | **Hinglish / Hindi-aware matching** | Names and text are normalised across scripts and common spelling variants (transliteration, abbreviations like "Inst.", "Engg.") before matching | Realistic for Indian complaint data; shows local fit |
| **U6** | **Privacy by default** | Complainant name/phone/email are masked per role; "Reveal" needs a stated reason that is logged | Sensitive-data credibility; aligns with public-sector expectations |
| **U7** | **Systemic Issue Clusters + Institution Risk Score** | Many similar complaints about one college are grouped into one cluster; each college gets an explainable risk score with its components shown | Gives management an early-warning view; the "bonus layer" of the agreed idea |
| **U8** | **Import Wizard (integration-first)** | Upload a unit's CSV/Excel, map its columns to ours once, save the mapping per unit, and preview what will be created or flagged before committing | Answers "how does this work with our existing systems?" without replacing them |
| **U9** | **Joint Case Brief (one-page PDF)** | One click produces a printable brief of an overlap: both cases, timeline, match receipt, and who to contact | A tangible artefact for coordination meetings and for the presentation |
| **U10** | **Ask the Dashboard (safe natural-language filters)** | A search box such as "pending RB cases older than 60 days in the West region" is turned into **validated filter parameters** (never raw SQL) and shows the parsed filters before running | Visible AI that is safe and explainable; fallback is a normal filter form |
| **U11** | **Scenario Runner for the demo** | An admin-only panel that loads a named scenario (e.g. "Spelling-variant conflict") and replays planted events step by step | Makes the live demo repeatable and robust |

> **Scope control:** U1–U6, U8 are part of the core build. U7, U9, U10, U11 are part of the full build but are the first to move to "roadmap" if quality suffers. See §12.

### 4.6 Why this will be remembered

1. It answers the stated pain directly — **"conflict before it happens"** — rather than only reporting it afterwards.
2. Every smart output is **explained and auditable**, which is what a regulator needs.
3. It is **honest about AI**: rules and fuzzy matching always work; AI features degrade gracefully.
4. It is **integration-first**: it sits above existing unit systems.

---

## 5. Feature Catalogue

Priority: **C** = core, **F** = full build, **R** = roadmap (described, not built). Phase = §12.

| ID | Feature | Req | Prio | Phase |
|---|---|---|---|---|
| F-01 | Institution registry with canonical records, AICTE IDs and aliases | R-04, R-06 | C | M1 |
| F-02 | Complaint intake (manual form) with unit, category, institution, details, dates | R-01 | C | M1 |
| F-03 | Import Wizard (CSV/Excel with column mapping, preview, dry-run) | R-01 | C | M2 |
| F-04 | Complaint lifecycle: states, owner, transfer, remarks, attachments (metadata) | R-05 | C | M1 |
| F-05 | Dashboard counters with drill-down | R-02 | C | M2 |
| F-06 | Search and filters (all listed fields) with URL-shareable state | R-03 | C | M2 |
| F-07 | College 360° (timeline across units, owner per case, open overlaps, risk, past actions) | R-04 | C | M2 |
| F-08 | Overlap Engine L1–L4 (ID, fuzzy institution, rules) | R-06 | C | M3 |
| F-09 | Overlap alert "Potential Overlapping Cases – Coordination Required" with Match Receipt | R-07 | C | M3 |
| F-10 | Action Gate (pre-action check: clear / related / conflict) | R-07 | C | M3 |
| F-11 | Officer decision: Confirm / Dismiss / Link / Unlink, with reason | R-07 | C | M3 |
| F-12 | Alias Memory (confirmed aliases feed back into matching) | R-06 | C | M3 |
| F-13 | Audit trail, hash-chained, with Verify | R-05 | C | M3 |
| F-14 | Role-based access and masked personal data | R-10 | C | M4 |
| F-15 | Issue matching with embeddings (L3) with keyword fallback | R-06, R-11 | F | M4 |
| F-16 | Coordination Handshake (shared thread, hold-for-discussion, clock) | R-07 | F | M4 |
| F-17 | Deadlines, SLA clocks, reminders, escalation flags | R-08 | F | M4 |
| F-18 | Reports: by unit, region, institution; ageing; disposal rate; export CSV/PDF | R-09 | F | M5 |
| F-19 | AI-written overlap summary (LLM) with template fallback | R-11 | F | M5 |
| F-20 | Systemic Issue Clusters and Institution Risk Score | R-11 | F | M5 |
| F-21 | Ask the Dashboard (validated filter generation) | R-11 | F | M5 |
| F-22 | Joint Case Brief PDF | R-07 | F | M5 |
| F-23 | Scenario Runner (demo) | — | F | M5 |
| F-24 | Learning from feedback to tune thresholds (offline analysis of stored decisions) | R-11 | R | later |
| F-25 | Geographic hotspot map | R-11 | R | later |
| F-26 | SSO / 2FA with an institutional identity provider | R-10 | R | later |
| F-27 | Live connectors to unit systems (database/API) | R-01 | R | later |
| F-28 | Complainant-facing status tracker | — | R | later |

---

## 6. Key User Flows

### 6.1 Intake and automatic overlap check
1. A PGRC officer opens *New Complaint*, types "Vishwakarma Inst. of Tech, Pune", chooses a category and writes the details.
2. The system suggests institution matches from the registry (with scores) and the officer picks one, or creates a new institution record.
3. On save, the Overlap Engine compares the new complaint with all **open or recently closed** complaints on the same institution (and on high-scoring look-alike institutions).
4. If it finds a candidate, an **overlap record** is created with status *Suggested* and the officers of both units see the alert on their dashboard.

### 6.2 The Action Gate (headline flow)
1. An RB officer opens "Issue show-cause notice" for "VIT Pune".
2. Before the form is submitted, the **Gate** calls the conflict check.
3. The officer sees a 🔴 **Conflict** panel with the other unit's case, its owner, state, the Match Receipt and three choices: **Request coordination**, **Link cases**, **Proceed with justification**.
4. Whatever the officer chooses is written to the audit trail with the Gate result that was shown at that moment.

### 6.3 Coordination Handshake
1. The officer chooses *Request coordination*; the other unit's officer gets a notification.
2. Both cases show "Coordination in progress" with a clock (default 3 working days, configurable).
3. They exchange notes in a short thread and record an outcome: *Proceed together*, *Defer to unit X*, or *Not related*.
4. If the clock runs out, a reminder goes to both and then to their supervisors.

### 6.4 Reviewing a suggested overlap
1. An officer opens an overlap, reads the Match Receipt, compares both cases side by side, and chooses **Confirm**, **Dismiss** or **Link**.
2. *Confirm* with different spellings also offers *Save as alias* (U4).
3. *Dismiss* needs a reason; the pair is not re-suggested unless new evidence appears.

### 6.5 Management review
1. Management opens the Management View: workload by unit, ageing, repeat institutions and the **risk ranking**.
2. They click a college → College 360° → open overlaps → Joint Case Brief PDF for a review meeting.

### 6.6 Audit
1. An auditor opens a case, reads its audit trail, and presses **Verify chain**.
2. The system re-computes hashes and reports *Intact* or *Broken at entry #N*.

---

## 7. What counts as an "overlap"? (taxonomy)

| Type | Definition | Default severity |
|---|---|---|
| **O1 Same institution, same issue, different units, both open** | The core case | 🔴 Conflict |
| **O2 Same institution, different issue, different units, both open** | Related activity, different subject | 🟡 Related |
| **O3 Same institution, same issue, one case closed recently** | Possible re-opening or inconsistent outcomes | 🟡 Related |
| **O4 Conflicting actions pending** | E.g. penalty proposed by one unit, closure proposed by another | 🔴 Conflict |
| **O5 Duplicate complaint within a unit** | Same complainant or same text submitted twice | 🟡 Related (merge suggestion) |
| **O6 Cluster** | Three or more similar complaints against one institution | 🟡 Systemic (feeds U7) |

The exact severity rules are configuration, not code (backend plan §6.6), so they can be changed without a release.

---

## 8. Data Plan (synthetic only)

**Why synthetic:** real complaint data is sensitive and unavailable (V-M4).

**What we generate (target for the demo dataset):**
- About **40 institutions** across at least 4 regions, each with 2–5 **name variants** (abbreviations, spelling slips, word-order changes, Hindi/Devanagari variants).
- About **250 complaints** across **3 units** (RB, PGRC, one regional office) in **8 categories** (for example fee refund, fake or unqualified faculty, unapproved intake, infrastructure shortfall, misleading advertisement, withholding of documents, affiliation or approval lapse, harassment).
- **Planted scenarios** with known answers so that matching quality can be **measured** (backend plan §11):
  - 20 true overlaps with spelling variants only;
  - 15 true overlaps with different wording of the same issue;
  - 10 look-alike **decoys** (similar names, different colleges) that must *not* be merged;
  - 8 conflicting-action pairs;
  - 3 systemic clusters;
  - complaints in mixed English/Hindi/Hinglish.
- Every record carries `is_synthetic = true`; all screens show **SYNTHETIC DATA**.

**Rules:** the generator is deterministic (fixed seed) so the demo, the tests and the screenshots always match; the planted answers are stored in a separate **ground-truth** file used only by tests.

---

## 9. Architecture Overview

```
 Browser (Officer · Management · Auditor · Admin)
        │  React single-page app
        │  /api/v1/*  (REST, JSON)
        ▼
 FastAPI backend ─────────────────────────────────────────────┐
   ├─ Auth & roles, masking, audit writer                      │
   ├─ Complaint service  (lifecycle, transfer, deadlines)      │
   ├─ Institution service (registry, aliases)                  │
   ├─ Overlap Engine  (L1 ID · L2 fuzzy · L3 issue · L4 rules) │
   ├─ Action Gate service                                      │
   ├─ Import service (mapping, dry-run, commit)                │
   ├─ Reports / risk / clusters / Ask-the-Dashboard            │
   └─ AI adapters (embeddings, LLM) — optional, with fallbacks │
        │                                                      │
        ▼                                                      │
 Database: SQLite (prototype) → PostgreSQL + pgvector (target) │
 Local model files: sentence-embedding model (optional)        │
 Optional external LLM API for summaries (optional) ◄──────────┘
```

**Prototype vs target:**

| Part | Prototype (what we build) | Target (described, not built) |
|---|---|---|
| Database | SQLite | PostgreSQL + pgvector for embedding search |
| Auth | Local users with roles | SSO / 2FA with an institutional identity provider |
| Background work | In-process scheduler | A job queue with workers |
| AI | Local embedding model; optional LLM API with template fallback | Hosted, access-controlled model endpoint |
| Deployment | Docker Compose on a laptop | Government cloud / on-prem |

---

## 10. Screens (summary; details in the frontend plan)

1. **Dashboard** — counters, unit workload, ageing, alerts.
2. **Complaints** — list with filters and Ask the Dashboard.
3. **Complaint Detail** — summary, timeline, documents, overlap panel, audit tab.
4. **College 360°** — one institution across all units.
5. **Overlaps** — queue of suggested/confirmed overlaps; side-by-side review.
6. **Action Gate** — modal/page shown before significant actions.
7. **Coordination Thread** — shared notes and clock.
8. **Management View** — risk ranking, clusters, repeat institutions.
9. **Reports** — builder and exports.
10. **Import Wizard** — upload, map, preview, commit.
11. **Institution Registry** — canonical records and aliases.
12. **Audit & Verify** — trail and chain verification.
13. **Admin** — users, roles, thresholds, scenarios.

---

## 11. Non-Functional Requirements

| Area | Target |
|---|---|
| **Explainability** | 100% of overlap alerts carry a Match Receipt; 100% of AI summaries show their source evidence |
| **Matching quality** (on the planted ground truth, measured, not claimed) | Institution matching: recall ≥ 0.95, precision ≥ 0.95 on variant pairs; decoys wrongly merged: 0. Issue matching: recall ≥ 0.80, precision ≥ 0.85. Targets are recorded in the plan and replaced by measured numbers in the verification appendix |
| **Performance (prototype scale)** | Gate check ≤ 1 s; dashboard load ≤ 2 s; overlap scan on intake ≤ 3 s at 10,000 complaints |
| **Security** | Role checks on every endpoint; passwords hashed; no secrets in the repo; input validation; rate limiting on auth; masked PII by default |
| **Privacy** | Reveal-with-reason for personal data; synthetic data only in the prototype |
| **Integrity** | Hash-chained audit entries; verification endpoint |
| **Availability of AI features** | System stays fully usable when embeddings or LLM are unavailable |
| **Accessibility** | WCAG 2.2 AA target; keyboard navigation; colour never the only signal |
| **Language** | English UI; Hindi-aware text matching; Hindi UI labels are roadmap |
| **Browser/device** | Current desktop browsers; usable on a tablet |

---

## 12. Phase Plan

There is **no time limit** on the build, so phases are ordered by **dependency and risk**, each ending with a measurable exit condition. A phase is finished only when its exit criteria are met and recorded.

| Phase | Name | Scope | Exit criteria |
|---|---|---|---|
| **M0** | Planning | These three documents, repo skeleton, authorship rule | ✅ Documents committed |
| **M1** | Foundations | Repo structure, backend skeleton, database schema and migrations, institution registry, complaint intake and lifecycle, synthetic data generator v1, frontend shell, API client generated from the backend contract | `make up` starts everything; data generator produces the dataset; complaint can be created and viewed; CI green |
| **M2** | Visibility | Dashboard, search/filters, College 360°, Import Wizard | Counters match database counts (tested); filters are URL-shareable; an import with a bad row reports the row, not a crash |
| **M3** | Overlap core | Overlap Engine L1/L2/L4, Match Receipt, overlap alert, Action Gate, officer decisions, Alias Memory, hash-chained audit | Engine meets the quality targets on the planted ground truth; Gate returns correct result for every planted scenario; chain verifies, and a deliberately altered row is detected |
| **M4** | Intelligence and roles | Issue matching with embeddings (L3) and fallback, Coordination Handshake, deadlines/SLA, roles and masking | Issue-matching targets met or the fallback is documented as the default; role matrix tests pass; reveal-with-reason is logged |
| **M5** | Management and polish | Reports and exports, risk score and clusters, AI summaries with fallback, Ask the Dashboard, Joint Case Brief, Scenario Runner | Report numbers reconcile with raw data; risk components shown; every AI feature degrades gracefully (tested with AI disabled) |
| **M6** | Hardening and presentation | Accessibility pass, security review, performance measurement, usability walkthrough, demo script, backup recording, presentation deck | Verification appendix filled with real measurements; demo runs three times end to end without intervention |

**Cut-line guidance:** if quality of a later feature is poor, **move it to roadmap** and say so, rather than showing something half-working (P3, P6). Order of removal: F-23, F-22, F-21, F-20, F-19.

---

## 13. Success Measures

| Measure | How measured | Target |
|---|---|---|
| Overlap detection quality | Planted ground-truth test (backend plan §11) | See §11 |
| Gate correctness | Scripted scenarios, expected result per scenario | 100% |
| Explanation coverage | Test that fails if an alert lacks a receipt | 100% |
| Audit integrity | Tamper test | Detected 100% |
| Usability | 5-person walkthrough with 6 tasks (e.g. "find all open cases for College X", "resolve a conflict") | ≥ 80% task success, SUS ≥ 70 |
| Robustness | Run with AI disabled and with the network off | No error screens |

---

## 14. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Institution matching merges different colleges (false merge) | Medium | **High** | Decoys in the ground truth; conservative thresholds; two-signal rule (name **and** a second signal such as district/pin); officer confirmation before any link |
| R2 | Embedding model too slow or unavailable | Medium | Medium | Keyword/category fallback; model loaded once; precomputed vectors; L3 is optional |
| R3 | LLM summary invents facts | Medium | High | LLM sees only structured evidence; output must cite fields; otherwise show the template summary (backend plan §6.9) |
| R4 | Too many alerts | Medium | Medium | Alert budget (P8), ranking, grouping by institution |
| R5 | Over-claiming "AI" or "learning" | Medium | High | Only claim what is built; "learning" is roadmap; alias memory is described as what it is |
| R6 | Scope grows beyond what can be finished | High | Medium | Phases with cut-lines (§12) |
| R7 | PS text differs from our reconstruction | Medium | Medium | V-M1 closed early; re-map requirement IDs |
| R8 | Sensitive-data concerns | Low | High | Synthetic data only; masking; no real data in the repo |
| R9 | Contract drift between frontend and backend | Medium | Medium | Generated API types plus CI diff check (frontend plan §2.3) |
| R10 | Hash-chain claims misunderstood (it is tamper-*evident*, not tamper-*proof*) | Medium | Medium | Say "tamper-evident"; document what it does not cover (backend plan §8) |

---

## 15. Decision Log

| ID | Chose | Over | Why |
|---|---|---|---|
| D-01 | Pre-action Action Gate as headline | Reporting-only dashboard | Directly prevents the stated pain |
| D-02 | Explainable layers (rules + fuzzy + embeddings) | A single opaque model | Officials must justify decisions |
| D-03 | Non-AI fallback for every AI feature | AI-only features | Reliability, offline demo, honesty |
| D-04 | SQLite for the prototype, PostgreSQL + pgvector as the target | Postgres from day one | Zero-setup prototype; schema written to be portable |
| D-05 | Alias Memory instead of model retraining | "Self-learning" claim | Real, safe, visible; retraining is roadmap |
| D-06 | Hash-chained audit trail | Plain log table | Cheap integrity story with a demonstrable Verify |
| D-07 | Import Wizard | Replace unit systems | Integration-first; realistic adoption |
| D-08 | LLM produces **validated filter JSON**, never SQL | Text-to-SQL | Safety and explainability |
| D-09 | Synthetic data with a ground-truth file | Hand-picked demo rows | Lets us **measure** matching quality |
| D-10 | Web app (responsive) | Native app | One codebase, no installation in an office setting |

---

## 16. Q&A Preparation (for judges)

**"Is this just a dashboard?"**
No. The dashboard is the visible part. The value is the Overlap Engine and the Action Gate, which warn an officer *before* a conflicting action, with the evidence shown.

**"How do you find overlaps when the wording and case numbers differ?"**
In layers: exact ID, normalised and fuzzy institution matching including Hindi/Hinglish variants, issue similarity, and rules on the case states. Each layer's evidence appears in the Match Receipt.

**"Why should an officer trust the AI?"**
They do not have to: every flag shows its reason, the officer decides, and a wrong flag can be dismissed or unlinked. AI features are optional and labelled.

**"What if the AI is down?"**
Everything still works; AI summaries fall back to a template and issue matching falls back to category and keyword overlap. We test with AI disabled.

**"Does the system learn?"**
Today it remembers officer-confirmed aliases and stores every decision. Using those decisions to tune thresholds is on the roadmap; we do not claim it is built.

**"What about our existing systems?"**
The Import Wizard maps each unit's export to our format once and saves the mapping. Live connectors are on the roadmap.

**"How do you protect complainants?"**
Personal data is masked by default, revealing it needs a logged reason, and the prototype uses synthetic data only.

**"Can the audit trail be edited?"**
Entries are hash-chained, so any edit breaks the chain and the Verify button shows where. It is tamper-evident; protecting the database itself is a deployment responsibility.

**"Whose data is in the demo?"**
None. All data is synthetic and every screen says so.

---

## 17. Presentation Outline (for the person preparing slides)

1. Title and one-line idea.
2. The problem in simple words, with one concrete story (College X, two units, conflicting actions).
3. Why current practice fails (four consequences).
4. Our solution in one picture (four building blocks).
5. **Headline: the Action Gate** (screenshot of the 🔴 panel).
6. **How we find overlaps** (layers diagram + Match Receipt).
7. Unique features (U1–U11, grouped).
8. Architecture (diagram from §9).
9. Data and honesty (synthetic data, how quality is measured, the results table once measured).
10. Security, privacy and audit.
11. Demo flow (script in §18).
12. Impact: what changes for officers and management.
13. What is built vs roadmap (copy the honest table from the status section).
14. Team and thanks.

Slides must use only numbers from the **Verification Appendix** once it is filled.

---

## 18. Demo Script (scenario-driven)

1. **Dashboard:** all units' complaints in one place; point to counters.
2. **Spelling-variant conflict:** a PGRC officer logs a complaint for "Vishwakarma Inst. of Tech, Pune". The alert appears for the RB officer who already holds a case on "VIT Pune".
3. **Action Gate:** the RB officer tries to issue a notice; the 🔴 Conflict panel appears with the Match Receipt.
4. **Coordination Handshake:** request coordination; show the shared thread and clock.
5. **Alias Memory:** confirm the overlap and save the alias; log another complaint with the same spelling and show it matches instantly.
6. **Hindi/Hinglish variant:** a complaint in Devanagari is matched to the same college.
7. **Audit and Verify:** open the trail, press Verify (intact); then show the pre-prepared tampered copy where Verify reports the broken entry.
8. **Management View:** risk ranking and a cluster; open the Joint Case Brief PDF.
9. **AI off:** switch AI features off in Admin and show everything still works with fallbacks.

A **recorded backup** of this run is kept in case the live demo fails.

---

## 19. Roadmap After the Prototype (not built)

Learning from officer feedback to tune thresholds; geographic hotspot map; SSO/2FA; live connectors to unit systems; complainant-facing tracker; Hindi UI; multilingual embeddings; PostgreSQL + pgvector deployment; job queue; accessibility audit by an external reviewer; deployment on government cloud.

---

## Appendix A — Glossary

| Term | Meaning |
|---|---|
| AICTE | All India Council for Technical Education |
| RB | Regulation Bureau |
| PGRC | Public Grievance Redressal Cell |
| Overlap | Two or more cases touching the same institution (and usually the same issue) |
| Action Gate | The pre-action conflict check |
| Match Receipt | Per-layer evidence and score behind an overlap |
| Alias Memory | Officer-confirmed alternative names stored for an institution |
| Hash chain | Each audit entry includes the hash of the previous entry |
| Ground truth | The file of planted, known-correct answers used by tests |

## Appendix B — Verification Appendix (to be filled as we build)

| Check | Command / source | Result | Date |
|---|---|---|---|
| *(empty — nothing built yet)* | | | |

## Appendix C — Document Maintenance Rules

- Dated update lines go in the header.
- Correct wrong statements in place with a dated note.
- Update the "Designed vs Built" tables in the companion plans in the same commit as the code.
- Every "✅" cites a file and a test.
- **Git rule:** every commit and push on this repository is authored by Ayush More only. No co-author trailers, no tool attribution lines (see `CLAUDE.md`).
