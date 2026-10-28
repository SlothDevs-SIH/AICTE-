# SAMANVAY — Master Plan

**Team:** SlothDevs (SIH) · **Solution (working name):** SAMANVAY, Hindi for "coordination" · **Domain:** Governance / Regulatory technology
**Problem statement:** AICTE (Regulation Bureau) — *Integrated Institution Complaint Monitoring and Status Dashboard*. Official text: [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md)
**PS number:** 26264 (see V-M1)
**Document date:** 2026-10-27 (v1.1 — reconciled with the official problem statement)
**Companion documents:** [`backend/BACKEND_PLAN.md`](backend/BACKEND_PLAN.md) (data, API, engine) · [`frontend/FRONTEND_PLAN.md`](frontend/FRONTEND_PLAN.md) (web app)
**Project phase:** **M0 — Planning: ✅ this document set.** Nothing is built yet. Next: **M1 — Foundations.**

> ⚠️ **Honesty rule (applies to all three documents):** a "✅" is allowed only when it points to a file in this repository and a test that passed. Until code exists, everything is **📋 Planned**. Numbers about performance or accuracy are *targets* until they are measured and recorded in an Appendix.
> When this document and the two companion plans disagree, fix all three in the same commit.

---

## ⚠️ Verification & Discrepancy Log — Read First

| # | Item | Detail | Resolution / action | Status |
|---|---|---|---|---|
| V-M1 | Official problem-statement text, and the PS number | Text was supplied on 2026-10-27 and saved in `docs/PROBLEM_STATEMENT.md`. The PS number was not in the pasted text; it was given separately (26264). | Text: done. Number 26264 was supplied by the team on 2026-10-28 and added to `docs/PROBLEM_STATEMENT.md` and the three plan headers | ✅ Resolved |
| V-M2 | Earlier working requirement IDs `R-01…R-11` | They were reconstructed before the official text was available and **missed several official items** (see V-M7) | Replaced everywhere by official IDs (`OBJ-n`, `KFn.m`, `INN`, `OUT-n`, `TU-n`) — §1.3 | ✅ Resolved 2026-10-27 |
| V-M7 | Gaps found when comparing the earlier plan with the official text | (1) **Escalated** cases were not a status, counter, history item or alert; (2) case fields *last action*, *next action*, *date of last action*, *expected disposal date* were missing, and there was no unique **Case ID**; (3) reports for **status-wise**, **overlapping/duplicate cases**, **institution-wise history** and **monthly/quarterly performance** were missing; (4) **Competent Authority** was not a user type; (5) the dashboard was not defined as **real-time**; (6) **institution-wise case status** was not on the dashboard; (7) *pending case reminders* and *escalation alerts* were not separate alert types | Fixed in this version in all three plans: F-29 to F-32 added, F-17 and F-18 widened, states, tables, routes and screens updated | ✅ Resolved 2026-10-27 |
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

### 1.3 Requirements — official items and how we cover them

The official statement is saved in [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md). Its items carry the IDs used everywhere in these plans: `OBJ-n` (objectives), `KFn.m` (key features), `INN` (innovation), `OUT-n` (expected outcomes), `TU-n` (target users). Feature IDs (`F-nn`) are defined in §5. **Every cell below is 📋 Planned** until code and tests exist.

| Official item | Covered by | Where the user meets it |
|---|---|---|
| **OBJ-1** All cases in one place | F-02, F-03, F-05, F-06 | Dashboard, Complaints list, Import Wizard |
| **OBJ-2** Which Bureau/Cell holds each case | F-04 | Unit and owner on every list row and detail |
| **OBJ-3** Full status and movement of a case | F-04, F-29, F-30 | Complaint Detail timeline |
| **OBJ-4** Detect RB/PGRC and multi-unit overlap | F-08, F-09, F-15 | Overlaps queue and review |
| **OBJ-5** Avoid duplicate action, ensure coordination | F-10, F-11, F-16 | Action Gate, Coordination Thread |
| **OBJ-6** Monitor pending, disposed, under-process, transferred, **escalated** | F-05, F-29 | Dashboard counters |
| **OBJ-7** Institution-, region-, Bureau/Cell- and status-wise reports | F-18, F-32 | Reports |
| **OBJ-8** Alerts for pending cases and approaching timelines | F-17 | Notifications, Dashboard "due soon" |
| **KF1.1** Unique Institution / AICTE Permanent ID | F-01 | Institution Registry, College 360° |
| **KF1.2** Name, address, region, other details | F-01 | Institution Registry, College 360° |
| **KF1.3** Consolidated complaint history per institution | F-07 | College 360° |
| **KF2.1** Unique Complaint/Case ID | F-02 (system-generated Case ID, in addition to each unit's own reference number) | Every screen showing a case |
| **KF2.2** Date of receipt | F-02 | Complaint Detail, lists |
| **KF2.3** Nature/category | F-02 | Complaint Detail, lists, filters |
| **KF2.4** Current status | F-04, F-29 | Badge on every case |
| **KF2.5** Presently assigned Bureau/Cell | F-04 | Lists, detail, transfer |
| **KF2.6** Assigned officer/official | F-04 | Lists, detail |
| **KF2.7** Last action taken | F-30 | Complaint Detail, list column |
| **KF2.8** Next action required | F-30 | Complaint Detail, list column |
| **KF2.9** Date of last action and expected disposal date | F-30 | Complaint Detail, list columns |
| **KF3.1** Automatic overlap identification | F-08, F-15 | Overlap Engine |
| **KF3.2** Overlap alert to authorised officials | F-09 | Dashboard panel, notifications, Overlaps queue |
| **KF3.3** Link / map related cases | F-11 | Overlap review "Link cases", link groups |
| **KF4.1–KF4.6** Total, pending, under process, disposed, transferred, beyond timelines | F-05, F-31 | Dashboard tiles (live) |
| **KF4.7** Institution-wise case status | F-05 | Dashboard table, College 360° |
| **KF4.8** Bureau/Cell-wise workload | F-05 | Dashboard chart, Management View |
| **KF5.1–KF5.5** Chronological history, responsible officer/Bureau, time stamps, remarks and documents, transfer/escalation history | F-04, F-13, F-29 | Complaint Detail (Timeline, Documents, Audit tabs) |
| **KF6.1–KF6.8** Search by institution name, AICTE ID, case ID, Bureau/Cell, region, category, status, date range | F-06 | Complaints list filters, Ask bar |
| **KF7.1** Duplicate/overlapping case alerts | F-09 | Notifications, Overlaps |
| **KF7.2** Pending case reminders | F-17 | Notifications |
| **KF7.3** Escalation alerts | F-17, F-29 | Notifications |
| **KF7.4** Timeline/SLA alerts | F-17 | Notifications, due clocks |
| **KF8.1** Bureau-wise reports | F-18 | Reports |
| **KF8.2** Region-wise reports | F-18 | Reports |
| **KF8.3** Institution-wise complaint history | F-32 | Reports, College 360° export |
| **KF8.4** Pending case ageing analysis | F-18 | Dashboard, Reports |
| **KF8.5** Disposal rate | F-18 | Reports |
| **KF8.6** Overlapping/duplicate cases | F-32 | Reports |
| **KF8.7** Monthly/quarterly performance reports | F-32 | Reports |
| **INN** Matching beyond identical wording; alert "Potential Overlapping Cases – Coordination Required" | F-08, F-09, F-12, F-15, F-19, F-20, F-21 | Overlap Engine, Match Receipt |
| **OUT-1** Reduce duplication | F-10 | Action Gate |
| **OUT-2** Prevent conflicting or parallel actions | F-10, F-16 | Action Gate, Coordination |
| **OUT-3** Better coordination between Bureaus/Cells | F-16 | Coordination Thread |
| **OUT-4** Timely disposal | F-17, F-29 | SLA clocks, escalation |
| **OUT-5** Accountability and transparency | F-13, F-14 | Audit trail with Verify, roles |
| **OUT-6** Management monitors status in real time | F-20, F-31 | Management View, live dashboard |
| **OUT-7** Data-driven decisions | F-18, F-20, F-32 | Reports, risk ranking |
| **TU-1…TU-6** Target users | F-14 | Roles in §2 (RB, PGRC, other Bureaus/Cells, Regional Offices, senior management, Competent Authority) |

Our own additions beyond the statement (the USPs U1–U11) are listed in §4.5; they support these items and do not replace any of them.

### 1.4 Honest assessment of where the difficulty lies

Dashboards, filters, status counts and reports are standard work; most teams will build them. The hard, judged part is **KF3.1–KF3.3 and INN: finding that two cases are "about the same institution and issue" when the data does not say so directly.** That is an entity-resolution problem plus a text-similarity problem, and it must be **explainable** because the users are government officials who must trust and defend what the system tells them.

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
| **Unit Supervisor** | Any Bureau/Cell | Oversee the unit's queue, reassign cases, receive escalations from officers and overdue alerts | Unit queue, Escalations, Overlaps |
| **Other Bureau/Cell Officer** | Any other AICTE Bureau/Cell | Same needs as RB and PGRC officers for their own cases | My Cases, Pre-Action Check, Overlaps |
| **Competent Authority / AICTE administration** | Top management | Final decision on top-level escalations; an overall view of how every Bureau/Cell and institution is doing | Management View, Escalations, Reports |

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
| F-01 | Institution registry with canonical records, AICTE IDs and aliases | KF1.1–KF1.3, KF3.1 | C | M1 |
| F-02 | Complaint intake (manual form) with unit, category, institution, details, dates and a **system-generated unique Case ID** | KF2.1–KF2.6, OBJ-1 | C | M1 |
| F-03 | Import Wizard (CSV/Excel with column mapping, preview, dry-run) | OBJ-1 | C | M2 |
| F-04 | Complaint lifecycle: states (including **Escalated**), owner, transfer, remarks, attachments (metadata) | KF2.4–KF2.6, KF5 | C | M1 |
| F-05 | Dashboard counters (including **escalated** and **beyond timeline**) with drill-down, **institution-wise status** and Bureau/Cell workload | KF4.1–KF4.8, OBJ-6 | C | M2 |
| F-06 | Search and filters (all listed fields) with URL-shareable state | KF6.1–KF6.8 | C | M2 |
| F-07 | College 360° (timeline across units, owner per case, open overlaps, risk, past actions) | KF1.3, KF4.7 | C | M2 |
| F-08 | Overlap Engine L1–L4 (ID, fuzzy institution, rules) | KF3.1, INN | C | M3 |
| F-09 | Overlap alert "Potential Overlapping Cases – Coordination Required" with Match Receipt | KF3.2, KF7.1, INN | C | M3 |
| F-10 | Action Gate (pre-action check: clear / related / conflict) | OBJ-5, OUT-1, OUT-2 | C | M3 |
| F-11 | Officer decision: Confirm / Dismiss / Link / Unlink, with reason | KF3.3 | C | M3 |
| F-12 | Alias Memory (confirmed aliases feed back into matching) | KF3.1, INN | C | M3 |
| F-13 | Audit trail, hash-chained, with Verify | KF5, OUT-5 | C | M3 |
| F-14 | Role-based access and masked personal data | TU-1–TU-6, OUT-5 | C | M4 |
| F-15 | Issue matching with embeddings (L3) with keyword fallback | INN, KF3.1 | F | M4 |
| F-16 | Coordination Handshake (shared thread, hold-for-discussion, clock) | OBJ-5, OUT-3 | F | M4 |
| F-17 | Deadlines, SLA clocks, **pending-case reminders**, SLA alerts and **escalation alerts** | OBJ-8, KF7.2–KF7.4, OUT-4 | C | M4 |
| F-18 | Reports: **Bureau/Cell-wise**, **region-wise**, ageing, disposal rate; export CSV/PDF | KF8.1, KF8.2, KF8.4, KF8.5 | C | M5 |
| F-19 | AI-written overlap summary (LLM) with template fallback | INN | F | M5 |
| F-20 | Systemic Issue Clusters and Institution Risk Score | INN, OUT-6 | F | M5 |
| F-21 | Ask the Dashboard (validated filter generation) | INN | F | M5 |
| F-22 | Joint Case Brief PDF | KF3.2, OBJ-5 | F | M5 |
| F-23 | Scenario Runner (demo) | — | F | M5 |
| F-24 | Learning from feedback to tune thresholds (offline analysis of stored decisions) | INN | R | later |
| F-25 | Geographic hotspot map | INN | R | later |
| F-26 | SSO / 2FA with an institutional identity provider | TU-5, TU-6 | R | later |
| F-27 | Live connectors to unit systems (database/API) | OBJ-1 | R | later |
| F-28 | Complainant-facing status tracker | — | R | later |
| F-29 | **Escalation workflow:** Escalated status, escalation level and target, escalation history, de-escalation, escalation alerts | KF2.4, KF4 (OBJ-6), KF5.5, KF7.3, OUT-4 | C | M2 (status, history) · M4 (alerts) |
| F-30 | **Case tracking fields:** last action taken, next action required, date of last action, expected disposal date (last action is derived from history; next action is set by the owner) | KF2.7–KF2.9 | C | M1 |
| F-31 | **Live dashboard:** server-pushed updates with automatic polling fallback, "last updated" indicator, stale-data warning | KF4 (real-time), OUT-6 | C | M2 |
| F-32 | **Extended reports:** status-wise, institution-wise complaint history, overlapping/duplicate cases, monthly and quarterly performance | KF8.3, KF8.6, KF8.7, OBJ-7, OUT-7 | C | M5 |

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

### 6.7 Escalation (OBJ-6, KF5.5, KF7.3)
1. **Triggers for an escalation alert:** a case is overdue by more than the grace period (default 3 days); a coordination thread expires without an outcome; or the owner decides to escalate on their own.
2. The system **alerts** the owner and the supervisor. By default it does **not** escalate by itself (principle P2); an administrator may switch on automatic escalation, in which case the system records the escalation as a system action in the history and audit trail.
3. The owner or supervisor presses **Escalate**, chooses the level (Level 2 = supervisor, Level 3 = Competent Authority) and gives a reason. The case status becomes **Escalated**, the history records who escalated to whom and why, and the recipient is notified.
4. The recipient acts: gives instructions and returns the case to *Under process*, reassigns it, or disposes of it (the Action Gate runs before disposal). Each step is recorded.
5. The dashboard counts Escalated cases separately, and the Competent Authority sees an **Escalations** queue.

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
  - 12 complaints approaching their SLA, 8 beyond it, and 6 escalated (levels 2 and 3), with last-action and next-action fields filled;
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
14. **Escalations** — cases escalated to me or my unit, with the reason and history.

---

## 11. Non-Functional Requirements

| Area | Target |
|---|---|
| **Explainability** | 100% of overlap alerts carry a Match Receipt; 100% of AI summaries show their source evidence |
| **Matching quality** (on the planted ground truth, measured, not claimed) | Institution matching: recall ≥ 0.95, precision ≥ 0.95 on variant pairs; decoys wrongly merged: 0. Issue matching: recall ≥ 0.80, precision ≥ 0.85. Targets are recorded in the plan and replaced by measured numbers in the verification appendix |
| **Performance (prototype scale)** | Gate check ≤ 1 s; dashboard load ≤ 2 s; overlap scan on intake ≤ 3 s at 10,000 complaints |
| **Live updates** | A new case or status change appears on other officers' dashboards within 5 s through server push, or within 15 s through the polling fallback; the screen always shows "last updated" and a stale-data warning after 30 s without updates |
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
| **M1** | Foundations | Repo structure, backend skeleton, database schema and migrations, institution registry, complaint intake and lifecycle with system Case ID and the case tracking fields (F-30), synthetic data generator v1, frontend shell, API client generated from the backend contract | `make up` starts everything; data generator produces the dataset; complaint can be created and viewed; CI green |
| **M2** | Visibility | Dashboard (live updates F-31, institution-wise status), Escalated status and escalation history (F-29), search/filters, College 360°, Import Wizard | Counters match database counts (tested); filters are URL-shareable; an import with a bad row reports the row, not a crash |
| **M3** | Overlap core | Overlap Engine L1/L2/L4, Match Receipt, overlap alert, Action Gate, officer decisions, Alias Memory, hash-chained audit | Engine meets the quality targets on the planted ground truth; Gate returns correct result for every planted scenario; chain verifies, and a deliberately altered row is detected |
| **M4** | Intelligence and roles | Issue matching with embeddings (L3) and fallback, Coordination Handshake, deadlines/SLA, pending-case reminders and escalation alerts, roles and masking | Issue-matching targets met or the fallback is documented as the default; role matrix tests pass; reveal-with-reason is logged |
| **M5** | Management and polish | Reports and exports (including the extended reports F-32), risk score and clusters, AI summaries with fallback, Ask the Dashboard, Joint Case Brief, Scenario Runner | Report numbers reconcile with raw data; risk components shown; every AI feature degrades gracefully (tested with AI disabled) |
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
| Coverage of the official statement | Matrix in §1.3 | Every official item mapped to a planned feature; an item is marked built only with a file and a passing test |

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
| R7 | A judge reads the statement differently from us, or the PS number is wrong | Low | Medium | Official text is saved in `docs/PROBLEM_STATEMENT.md`; §1.3 maps every item; PS number 26264 recorded (taken from the team's portal, not independently checked) |
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

**"Does it cover every item in the problem statement?"**
Every objective, key feature, expected outcome and user type is mapped in §1.3 to a planned feature and screen. An item is marked built only when code and a passing test exist.

**"What happens when a case is stuck?"**
It gets SLA alerts, then an escalation alert; the owner or supervisor escalates it to a higher level with a reason, it is counted as Escalated on the dashboard, and the whole movement stays in the case history.

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
