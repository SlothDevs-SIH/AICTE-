# SAMANVAY Frontend — Plan & Build Record

**Team:** SlothDevs (SIH) · **Solution (working name):** SAMANVAY · **Problem statement:** AICTE (Regulation Bureau) — integrated institution complaint monitoring and status dashboard · **PS number:** not supplied yet (MASTER_PLAN V-M1) · **Official text:** [`../docs/PROBLEM_STATEMENT.md`](../docs/PROBLEM_STATEMENT.md)
**Parent documents:** [`../MASTER_PLAN.md`](../MASTER_PLAN.md) (product) · [`../backend/BACKEND_PLAN.md`](../backend/BACKEND_PLAN.md) (API, data, engine). This document is the source of truth for the web app. When they disagree, fix all three in the same commit.
**Document date:** 2026-10-27 (v1.1 — reconciled with the official problem statement)
**Frontend phase:** **F0 — Planning: ✅ this document.** Nothing is built. Next: **F1 — Skeleton.**

> ⚠️ **Honesty rule:** a "✅" must point to a file and a test that passed. Everything here is **📋 Planned** until code exists. Measured numbers go into Appendix B only after they are measured.
> **Structure note:** this plan follows the same structure as the team's reference frontend plan (a different project), applied to this product. None of that project's built-status claims apply here.

---

## ⚠️ Verification & Discrepancy Log — Read First

| # | Item | Detail | Resolution / action | Status |
|---|---|---|---|---|
| V-F1 | No library versions are pinned in this plan | Versions change; a number written now would be a guess | Resolve into `package-lock.json` at F1 and record in Appendix A | ⏳ F1 |
| V-F2 | Chart library choice (Recharts) and accessibility | Chart libraries are weak for screen readers by default | Every chart gets a visible data-table alternative and a text summary (§3.4, §4.2) | ⏳ F2 |
| V-F3 | Devanagari rendering | Hindi/Hinglish complaint text and institution names must render correctly on the demo machine | Use a font stack with Devanagari fallbacks; add a rendering check in e2e (F2); no web-font download so it works offline | ⏳ F2 |
| V-F4 | PDF preview of the Joint Case Brief | Browsers differ in inline PDF display and the strict security policy may block embedding | Open the PDF through a download/new-tab link; do not embed; decide at F5 | ⏳ F5 |
| V-F5 | Strict Content-Security-Policy | Inline scripts and third-party hosts break under a strict policy | Same-origin only, no inline scripts, no CDN assets; every exception is recorded here | ✅ Decided |
| V-F6 | "shadcn/ui" | It is a copy-in component convention, not a dependency | Hand-write components in that convention (`cn()` = `clsx` + `tailwind-merge`) as needed | ✅ Decided |
| V-F7 | Source maps in the production image | They expose source | Build with hidden source maps and strip `*.map` from the image before any real pilot | ⏳ F6 |
| V-F8 | Requirement IDs | Earlier working IDs `R-xx` were replaced by the official IDs (`OBJ`, `KF`, `INN`, `OUT`, `TU`). The comparison found UI gaps (MASTER_PLAN V-M7), fixed here: Escalated status and Escalations screen, last/next action and expected disposal date on cases, Case ID, institution-wise status on the dashboard, live indicator, extra reports, Competent Authority user | Done; coverage matrix in MASTER_PLAN §1.3 | ✅ Resolved 2026-10-27 |

---

## 1. Frontend Identity & Scope

| Field | Planned value (to be resolved at F1) |
|---|---|
| Runtime / package manager | Current LTS Node, npm with committed `package-lock.json` |
| UI | React |
| Language | TypeScript (`strict`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`) |
| Build / dev server | Vite |
| Routing | React Router (data router) |
| Server state | TanStack Query |
| Styling | Tailwind CSS with CSS-variable design tokens, `clsx` + `tailwind-merge` |
| Icons | lucide-react |
| Charts | Recharts (accessible alternatives required, V-F2) |
| Tables | TanStack Table (virtualised above 200 rows) |
| Forms | React Hook Form + Zod (validation shared in spirit with backend models) |
| API types | `openapi-typescript`, generated from the backend's exported OpenAPI |
| Unit/component tests | Vitest, Testing Library, jest-dom, user-event |
| E2E + a11y | Playwright, `@axe-core/playwright` |
| Lint / format | oxlint (or ESLint with `jsx-a11y` if an a11y rule is missing), Prettier |
| Serving | nginx (alpine), multi-stage Docker image |

**The frontend owns:** every screen in MASTER_PLAN §10, accessibility, client-side performance, and the UI rules that enforce the product's honesty principles (receipts, masking, "suggested" wording, AI labels).
**It does not own:** matching, scoring, severity, permissions or risk calculations. The backend returns results; the frontend displays them. The UI hides what a role cannot use, but the backend enforces it.

---

## 2. Architecture

### 2.1 Runtime view

```
 Browser (officer desk · management room · auditor)
   │  https://<host>/            SPA (React)       ─┐
   │  /api/v1/*   REST (JSON, PDF downloads)        │ same origin → no CORS,
   │  /healthz /readyz                              │ no hard-coded API host
   ▼                                               ─┘
 nginx (frontend container)
   ├─ /assets/*   hashed files, long-lived cache
   ├─ /*          SPA fallback to index.html (no-cache), strict CSP + security headers
   └─ /api …      proxy ──► backend (FastAPI)
 Dev: Vite dev server proxies the same paths to the backend (VITE_API_PROXY_TARGET).
```

### 2.2 Planned code structure and data flow

```
src/main.tsx                 entry: <Providers> (QueryClient, Theme, Auth) + <RouterProvider>
src/app/
  router.tsx                 routes generated from the screen registry; role guards; "*" → NotFound
  screens.ts                 SCREEN REGISTRY: id, path, title, purpose, roles, phase, status, endpoints
                             — single source for navigation, routes and tests
  AppShell.tsx               sidebar (filtered by role), header (user, SYNTHETIC badge, AI status,
                             notifications bell, theme), skip-link, landmarks
  providers.tsx · queryClient.ts · theme.tsx · themeContext.ts · auth.tsx · authContext.ts
src/lib/api/
  openapi.json               COMMITTED copy of the backend contract
  schema.d.ts                GENERATED types — never edited by hand
  client.ts                  apiFetch<T>(), ApiError (code, status, details, requestId, plannedPhase)
  hooks.ts                   one hook per endpoint group; centralised queryKeys
src/lib/format/              dates.ts (IST) · numbers.ts (en-IN) · text.ts (masking helpers, truncation)
src/lib/storage.ts           guarded localStorage (per-viewer preferences only)
src/components/ui/           Button, Card, Badge, Dialog, Tabs, Select, Tooltip, Toast, Skeleton (shadcn-style)
src/components/domain/       MatchReceipt, SeverityBadge, GateDialog, OverlapCompare, CaseSummaryCard,
                             MaskedValue, RevealDialog, TimelineList, InstitutionPicker, AuditVerifyPanel,
                             SyntheticBadge, AiLabel, DataTable, ChartWithTable, AskBar
src/pages/                   one folder per screen (§4)
src/styles/index.css         Tailwind + tokens (light/dark)
public/theme-init.js         pre-paint theme (external file for the strict CSP)
```

**Data-flow rule:** components never call `fetch` directly. They use hooks (TanStack Query) → `apiFetch` → backend. Responses are typed from the generated schema, so a backend contract change breaks the type-check, not the demo.

### 2.3 How the contract stays in sync
1. A backend developer changes a route or model.
2. The backend CLI exports `openapi.json` into the frontend; the frontend regenerates `schema.d.ts` (one `make api-contract` target does both).
3. CI enforces it twice: the backend job diffs a fresh export against the committed file; the frontend job regenerates types and fails on any diff.
4. A test fails if any entry in the screen registry references an endpoint that is not in the contract.
5. Until a backend route exists it returns `501` with `planned_phase`; the screen shows "planned for phase Bx" (§3.5).

---

## 3. Conventions

### 3.1 Code
- TypeScript strict; no `any` (use `unknown` and narrow).
- One component per file for fast refresh; hooks, contexts and constants live in `.ts` files.
- **Server state only in TanStack Query.** UI state is local, or a small context (theme, auth). No Redux.
- Query keys centralised in `lib/api/hooks.ts`.
- Styling: Tailwind utilities with tokens (`bg-surface`, `text-muted`, `bg-conflict-bg`…). **No raw hex colours in components.**
- Tests sit next to code (`*.test.ts(x)`); browser tests in `e2e/`.
- Prettier: no semicolons, single quotes, width 100, trailing commas.
- `dangerouslySetInnerHTML` is banned (lint rule); all complaint text renders as text.

### 3.2 UI rules that implement the master-plan principles (non-negotiable)

| Principle | Frontend rule |
|---|---|
| P1 No flag without a reason | Anywhere an overlap or Gate result is shown, `<MatchReceipt>` is rendered with the per-layer evidence. A component that shows an overlap without a receipt fails review; a test asserts the overlap card throws or shows a defect banner when `receipt` is missing. |
| P2 Assist, never decide | Wording is "suggested", "possible", "may overlap", never "duplicate found" or "violation". Buttons that act are labelled with the officer's decision ("Confirm overlap", "Dismiss", "Link cases"). No auto-closing, no auto-linking. |
| P3 Fail safe, not silent | `<AiLabel>` marks every summary as **AI-written** or **Template summary**, with the reason when it fell back. The header shows adapter status (embeddings on/off, LLM on/off). The UI never presents a template as AI or hides that meaning matching was unavailable (it reads `receipt.issue.formula`). |
| P4 Everything is traceable | Each case and overlap has an "Audit" tab. The Verify panel shows `Chain intact` / `Broken at entry #N` and the head hash. |
| P5 Masked by default | Personal fields render through `<MaskedValue>`. "Reveal" opens `<RevealDialog>` requiring a reason (minimum length enforced client- and server-side); values are shown only for that view and re-mask on navigation. |
| P6 Honest numbers | Scores are labelled "match score" (never "probability", "chance" or "confidence"). Risk scores always show their components and the note "ranking aid based on complaint data only". |
| P7 Humans can correct the machine | Every confirmed overlap has **Unlink**; every institution match has **Save as alias** when spellings differ. |
| P8 Alert budget | No sound, no auto-popups for non-critical items. CONFLICT items are pinned, visually distinct and never collapsed. Notification bell shows counts with text, not just colour. |
| P9 Demo data is declared | A persistent **SYNTHETIC DATA** badge sits in the header on every screen while the data is synthetic; exported PDFs and CSVs carry the same line. |

### 3.3 Formatting
- Dates and times come from the backend in UTC ISO-8601 and display in **IST (`Asia/Kolkata`)** with a timezone suffix, e.g. `27 Oct 2026, 23:42 IST`. Date-only fields display as `27 Oct 2026`.
- Numbers use `Intl.NumberFormat('en-IN')` (Indian digit grouping). Scores display with two decimals; percentages with no decimals.
- Working-day clocks display as "2 working days left" with the exact due date on hover/focus.
- Institution names display exactly as stored, with the matched alias shown beside them when different ("typed as *VIT Pune*").

### 3.4 Accessibility (WCAG 2.2 AA target)
- Everything reachable and operable by keyboard; visible `:focus-visible` ring; skip link; logical focus order; dialogs trap and restore focus.
- Colour is never the only signal: severity is **icon + text + colour** (§8).
- Landmarks: `<nav aria-label="Main">`, `<main>`, one `h1` per page, headings in order.
- Tables: real `<table>` semantics, sortable headers announce sort state, sticky header does not hide focus.
- Charts: each has a text summary above and a "View as table" toggle; hover-only details are also reachable by keyboard.
- Live regions: Gate results and toasts use `aria-live` appropriately (assertive only for CONFLICT).
- Touch targets ≥ 44 px on tablet layouts.
- **Automated axe checks run on every screen from F1** and fail the build on serious/critical violations; a manual keyboard pass is recorded per screen.

### 3.5 Error, loading and empty states (every data view)

| State | Rendering |
|---|---|
| Loading | Skeleton rows/cards; `aria-busy`; no spinner-only screens |
| 501 `not_implemented` | "Planned for backend phase Bx" badge from `ApiError.plannedPhase`, never a generic error |
| 401 | Redirect to login with a "session expired" notice; unsaved form text is kept in memory |
| 403 | "Your role cannot do this" with the required role named (message from the server) |
| 409 `invalid_transition` | Explain the allowed next states |
| Network error | "Backend unreachable — retrying" with manual retry |
| Other API error | Message plus copyable `request_id` |
| Empty | Say why and what to do ("No open cases for this institution in the last 24 months — widen the date range") |

### 3.6 Live data rule
Dashboards and queues are live (MASTER_PLAN F-31). The page header shows a **Live indicator** driven by the stream's heartbeat. **Never show stale values as live:** after 30 s without an update or heartbeat the indicator changes to "Stale — last update N s ago" with icon and text, numbers are dimmed, and the client polls at the interval from the server settings until the stream returns. Stream events carry identifiers and counters only; the client re-fetches details through the normal endpoints.

---

## 4. Screen Designs

Each screen: **Purpose · Roles · Layout · Data · Key components · States and rules · Tests · Done when.** Phases refer to §7; backend phases to the backend plan §15.

### 4.1 Login
- **Purpose:** authenticate. **Roles:** public.
- **Layout:** centred form (email, password), product name, SYNTHETIC DATA notice, "demo users" hint panel shown only when `ENVIRONMENT != prod` (lists role names, **not passwords** — passwords live in the seed docs).
- **Data:** `POST /auth/login`, `GET /me`.
- **Rules:** error messages do not reveal whether the email exists; lockout message shows when the server reports it; no autofill of stored credentials by the app.
- **Tests:** wrong password, locked account, success redirect to the role's home, token kept in memory only.
- **Done when:** each of the seven roles (unit officer, unit supervisor, regional officer, management, Competent Authority, admin, auditor) can sign in and lands on its home screen.

### 4.2 Dashboard — OBJ-6, KF4, KF7
- **Purpose:** the first screen for officers and management. **Roles:** all.
- **Layout:**
  - Row of **counter tiles**: Total received, Pending, Under process, Disposed, Transferred, **Escalated**, **Beyond timeline** — each a link to the Complaints list with the matching filter in the URL.
  - **Conflicts needing attention** panel (CONFLICT overlaps assigned to my unit), pinned at the top and never collapsed.
  - **Ageing** bar chart (age buckets of open cases) and **workload by unit** chart, each with "View as table".
  - **Due soon** list (SLA clock).
  - **Institution-wise case status** table (KF4.7): institution, open cases by status, units involved, open overlaps; each row links to College 360°.
  - **Live indicator** next to the page title: "Live · updated 8 s ago". If no update or heartbeat arrives for 30 s it changes to "Stale — last update 42 s ago" with an icon and text, and the numbers are dimmed (§3.6).
  - **Ask the Dashboard** bar (§4.17) above the tiles.
- **Data:** `GET /dashboard/summary`, `/dashboard/by-institution`, `/dashboard/ageing`, `/dashboard/workload`, `GET /stream` (live events, polling fallback), `GET /overlaps?severity=CONFLICT&status=SUGGESTED`, `GET /complaints?due_soon=true`.
- **Rules:** counts reflect the user's scope (stated in a caption: "Showing: RB, all regions"); empty state explains the scope.
- **Tests:** tile numbers equal mocked API values; each tile link sets the right URL filters; charts have the table alternative.
- **Done when:** tile numbers equal the database counts in an e2e check against seeded data.

### 4.3 Complaints list — OBJ-1, KF2, KF6
- **Layout:** left filter column (institution picker, AICTE ID, **Case ID / reference no**, Bureau/Cell, region, category, status, overdue toggle, **escalated toggle**, received-date range, owner, "has overlap"), top search/Ask bar, results table (Case ID, reference no, institution, category, Bureau/Cell, status, owner, **last action, next action**, received, **expected disposal**, overlap badge), pagination or virtualisation, "Export CSV" button (calls the report endpoint).
- **Data:** `GET /complaints` with the filter parameters.
- **Rules:** **filter state lives in the URL** (`/complaints?unit=RB&state=UNDER_PROCESS&overdue=true`) so views are shareable; personal fields never appear in the list; a row with a CONFLICT overlap shows a red badge with icon and text.
- **Tests:** URL ↔ filter sync both ways; sort; keyboard row navigation; export link.
- **Done when:** every filter in KF6.1–KF6.8 works and is reflected in the URL.

### 4.4 New Complaint
- **Purpose:** create a complaint and see overlaps immediately.
- **Layout:** form (unit preselected from the user, category, title, description, institution picker, AICTE ID if known, received date, complainant fields, attachments), with an **overlap preview** panel on the right that updates after the institution and description are filled (calls the scan in "preview" mode if the backend provides it; otherwise shows results after save).
- **Key component — `InstitutionPicker`:** as the officer types, calls `GET /institutions/suggest?text=` and lists ranked matches with score, location and "typed as / matches alias" notes. Selecting a **Possible** (not Strong) match shows a "confirm this is the same institution" step. **Create new institution** is admin-only; others see "Ask admin to add".
- **Data:** `GET /institutions/suggest`, `POST /complaints`, `POST /complaints/{id}/attachments`.
- **Rules:** validation errors inline and in a summary; the form never silently picks an institution.
- **Tests:** suggest list for "VIT Pune", "Vishwakarma Inst. of Tech", a Devanagari spelling; possible-match confirmation; submit shows the resulting overlap alert.
- **Done when:** the spelling-variant demo scenario works end to end.

### 4.5 Complaint Detail — KF2, KF5
- **Layout:** header (Case ID, reference, institution, Bureau/Cell, owner, status, due clock, escalation level badge, badges including "On hold for coordination"), actions menu (transition, transfer, **escalate**, set next action, add remark, add attachment), tabs: **Summary**, **Timeline**, **Documents**, **Overlaps**, **Audit**.
- **Summary:** description, category, dates, masked complainant block (`MaskedValue` + Reveal), and a **Tracking block** (KF2.7–KF2.9): last action taken with who and when, next action required with its due date, date of last action, expected disposal date. The owner can edit next action and expected disposal date in place (the change is recorded in the history).
- **Timeline:** `TimelineList` of workflow events with actor, time, remark and state change, including transfers and escalations (who escalated to whom, level, reason).
- **Overlaps:** cards for each overlap (receipt, other case summary, decision buttons).
- **Documents:** attachment list with SHA-256 shown.
- **Data:** `GET /complaints/{id}`, `/events`, `/overlaps`, attachments endpoint, `/audit?entity=…` (auditor/admin).
- **Rules:** a significant action (notice, penalty, close, transfer) always opens the **Action Gate** first (§4.8); disabled transitions explain why; scope rules produce a "summary only" view for another unit's case.
- **Tests:** transition menu shows only legal next states; Gate opens before close; masked fields; "summary only" view hides description.
- **Done when:** every number and status on the page can be traced to a timeline or audit entry.

### 4.6 College 360° — KF1
- **Purpose:** one institution across all units.
- **Layout:** header (canonical name, AICTE ID, state/district, aliases with source badges, risk score tile for management/auditor roles), then:
  - **Cross-unit timeline:** one vertical timeline, each complaint a lane-coloured entry with unit badge, category, state, owner; overlaps drawn as connectors between entries labelled with severity icon+text.
  - **Who holds what** table (unit, case, owner, state, due).
  - **Open overlaps** panel and **clusters** panel ("5 similar complaints in 62 days").
  - **Past actions** (notices, penalties, closures).
- **Data:** `GET /institutions/{id}/360`, `/institutions/{id}/risk`, `/clusters?institution_id=`.
- **Rules:** the connector between overlapping entries is also available as a list for keyboard/screen-reader users; the timeline never uses colour alone to separate units.
- **Tests:** timeline order, connector list equivalence, risk tile hidden for officer roles.
- **Done when:** a college with two units' cases and one overlap displays all of it from one page.

### 4.7 Overlaps queue and Overlap review — KF3, KF7.1, INN
- **Queue:** table of overlaps (severity, institution, units, categories, match score, age, status) with filters; CONFLICT first. Title text on the page and any export: **"Potential Overlapping Cases – Coordination Required"** for suggested overlaps.
- **Review (`/overlaps/:id`):** two-column **side-by-side** case summaries (`CaseSummaryCard`) with differences highlighted (institution as typed, category, dates, owner, state); **Match Receipt** below spanning both columns; decision bar: **Confirm**, **Dismiss** (reason required), **Link cases**, **Save as alias** (shown when spellings differ), **Request coordination**, **Open Joint Case Brief (PDF)**; AI/Template summary block with `AiLabel`.
- **Data:** `GET /overlaps`, `GET /overlaps/{id}`, `POST /overlaps/{id}/decision`, `POST /overlaps/{id}/summary`, `GET /overlaps/{id}/brief.pdf`, `POST /coordination`.
- **Rules:** another unit's description text and personal data are **not** shown unless shared (the card says "Details visible after coordination is accepted"); decisions use optimistic UI that rolls back on error; a confirmed overlap shows **Unlink**.
- **Tests:** receipt required; dismiss without reason blocked; alias button only when spellings differ; unlink works; AI label shows fallback reason.
- **Done when:** the demo's step "confirm the overlap and save the alias" works and the alias is used by the next intake.

### 4.8 Action Gate — headline feature (U1)
- **Purpose:** stop conflicting actions before they happen.
- **Trigger:** a dialog opened by any significant action (notice, penalty, close, transfer, withdraw action). Not a separate navigation item.
- **Layout (by result):**
  - **🟢 Clear:** green banner "No related open case in other units", a one-line list of what was checked (institution, window, units), **Proceed** button.
  - **🟡 Related activity:** amber banner, list of related cases (case summary, owner, state, match score), **Proceed with a note** (note optional), **Request coordination**, **Link cases**.
  - **🔴 Conflict:** red banner, the conflicting case(s) with `MatchReceipt`, three explicit choices: **Request coordination** (default focus), **Link cases**, **Proceed with justification** (textarea, minimum length, audited). There is **no** close-dialog shortcut that proceeds.
- **Data:** `POST /gate/check`, `POST /gate/{check_id}/decision`.
- **Rules:**
  - The dialog shows exactly what was returned by the check, and that same snapshot is what the audit records.
  - Result is announced with `aria-live` (assertive for CONFLICT); focus starts on the banner heading, then the first choice.
  - If the check fails (network or server), the dialog says "Could not check for conflicts" and offers **Retry** and **Proceed without check (reason required)** — the second choice is audited as such. It never silently allows.
  - Wording is advisory ("another unit has an open case on this institution"), never "you cannot".
- **Tests:** one test per result colour; justification length enforced; failed check path; keyboard-only completion; screen-reader announcement text; the snapshot sent equals the snapshot displayed.
- **Done when:** every planted Gate scenario renders the expected result and choice set.

### 4.9 Coordination Thread — U1
- **Layout:** header (institution, the held cases, due clock "2 working days left"), message list, composer, **Resolve** form (outcome: Proceed together / Defer to unit A / Defer to unit B / Not related, plus a note).
- **Data:** `GET /coordination`, `GET /coordination/{id}`, `POST /coordination/{id}/messages`, `POST /coordination/{id}/resolve`.
- **Rules:** messages never contain personal data fields from other units unless shared; a clock past due shows "Overdue" with text and icon; resolved threads are read-only.
- **Tests:** post, resolve, expiry display, read-only after resolve.
- **Done when:** two users in different units can complete a handshake in one e2e run.

### 4.10 Management View — U7
- **Roles:** management, admin, auditor.
- **Layout:** **Risk ranking** table (institution, score, top two components, open cases, open conflicts, trend arrow with text), **Clusters** list, **Repeat institutions** list, **Unit workload** chart (+ table), "Why this score?" panel opening the component bars for the selected institution.
- **Data:** `GET /risk/ranking`, `/clusters`, `/dashboard/workload`, `/institutions/{id}/risk`.
- **Rules:** the "ranking aid based on complaint data only" note is always visible; component bars are labelled with values; a score is never shown without its components.
- **Tests:** components sum to the displayed score (within rounding); ordering; note present.
- **Done when:** selecting any ranked institution shows every component with its definition.

### 4.11 Reports — OBJ-7, KF8
- **Layout:** report kind picker (Bureau/Cell-wise, region-wise, status-wise, institution-wise, institution complaint history, pending-case ageing, disposal rate, overlapping/duplicate cases, monthly/quarterly performance with a period selector), filters, preview table/chart (with table alternative), **Export CSV** and **Export PDF** buttons.
- **Data:** `GET /reports/{kind}?format=json|csv|pdf` (plus `period=monthly|quarterly` and `institution_id` where the kind needs them).
- **Rules:** exports carry the SYNTHETIC DATA line and the filters used; the preview and the export come from the same endpoint so they cannot disagree.
- **Tests:** preview totals equal the export's totals; filters appear in export header.
- **Done when:** a report's grand total reconciles with the dashboard counter for the same filters.

### 4.12 Import Wizard — U8
- **Roles:** admin.
- **Layout:** stepper — **1 Upload** (drag-and-drop, duplicate-file notice) → **2 Map columns** (left: detected columns with sample values; right: canonical fields; saved mappings selectable; category value mapping) → **3 Dry-run** (counts of rows to create/skip/error, error table with row numbers, institution match suggestions, "would raise N overlaps") → **4 Commit** (progress, final report).
- **Data:** `POST /imports`, `/map`, `/dry-run`, `/commit`, `GET /imports/{id}`.
- **Rules:** commit is disabled until a dry-run exists for the current mapping; a failed row never hides the successful ones; the report is downloadable.
- **Tests:** file with bad rows shows the exact row numbers; duplicate file notice; re-commit is idempotent.
- **Done when:** a mixed good/bad CSV imports and the report matches the file.

### 4.13 Institution Registry
- **Roles:** admin (edit), others read.
- **Layout:** searchable list; detail with canonical fields, aliases (source badge: seed / import / officer-confirmed, who and when), add/remove alias, possible duplicates list (from the suggest engine) for admins to resolve outside the UI flow.
- **Data:** `GET/POST/PATCH /institutions`, alias endpoints.
- **Tests:** alias add/remove permissions; source badges.
- **Done when:** an alias confirmed in the overlap review appears here with its provenance.

### 4.14 Audit & Verify — U3
- **Roles:** auditor, admin.
- **Layout:** filter bar (actor, entity, action, date range), entries table (seq, time, actor, action, entity), entry detail, and a **Verify chain** panel: button → result card "Chain intact — N entries checked — head `abc123…`" or "Broken at entry #N". A copy button for the head hash.
- **Data:** `GET /audit`, `GET /audit/verify`.
- **Rules:** nothing on this screen is editable; the explanation text states honestly that the chain is *tamper-evident, not tamper-proof*.
- **Tests:** intact and broken result rendering; head hash copy; read-only.
- **Done when:** the demo's tamper scenario shows "Broken at entry #N".

### 4.15 Admin
- **Roles:** admin.
- **Tabs:** **Settings** (thresholds with descriptions, units, defaults, last changed by; edits require a reason and are audited), **Users** (create, role, unit, active), **AI switches** (embeddings, LLM — with the current status and what falls back), **Scenarios** (list, load, with a clear "synthetic data only" label).
- **Data:** `/admin/*` endpoints.
- **Rules:** changing a threshold shows its effect text ("will apply to the next scan"); dangerous actions need a confirm dialog naming the effect.
- **Tests:** reason required; AI switch updates the header status; scenario load confirmation.
- **Done when:** toggling AI off in Admin makes the header and receipts show fallback behaviour.

### 4.16 System Status (supporting)
Readiness per backend dependency with latency, backend version/build/environment/phase, adapter status (embeddings, LLM), frontend build, and the backend's component registry (from `/meta`). It is built first (F1) to prove the proxy and the contract.

### 4.17 Ask the Dashboard — U10
- **Component:** `AskBar` at the top of Dashboard and Complaints.
- **Behaviour:** user types a question → `POST /ask` → the UI shows **"I understood this as:"** with the parsed filters as removable chips and a plain-language restatement, then runs the normal list query. If `used_ai` is false the bar says "Parsed without AI". If the backend returns `needs_manual_filters`, the bar opens the filter column.
- **Rules:** the user can always edit the chips; the UI never shows results for an interpretation it did not display first.
- **Tests:** chips match response; removing a chip re-queries; fallback messages.

### 4.18 Notifications
Bell in the header with an unread count (text, not colour only); a panel listing notifications with links; mark as read. Notification kinds: overlap alerts (KF7.1), pending-case reminders (KF7.2), escalation alerts (KF7.3), SLA approaching/breached (KF7.4); each is labelled with text and an icon. Toasts appear only for new CONFLICT items and for escalations addressed to the user. No sounds; browser notifications are not used in the prototype.

### 4.19 Escalations — OBJ-6, KF5.5, KF7.3
- **Roles:** supervisor, Competent Authority, management, admin (read), officers see escalations on their own cases in Complaint Detail.
- **Layout:** queue table of escalated cases (Case ID, institution, Bureau/Cell, level badge "Level 2/3" with text, escalated by, reason, escalated on, age since escalation, due clock), filters (level, unit, institution), and an **Escalate** dialog reachable from Complaint Detail.
- **Escalate dialog (`EscalateDialog`):** choose level (2 = supervisor, 3 = Competent Authority), optional named recipient, reason (required, minimum length); shows who will be notified; the action is recorded in history and the audit trail. The wording is advisory: "Escalate for decision". Nothing in the UI escalates automatically; if the administrator has switched on automatic escalation, system escalations appear with actor "system" and a note.
- **Acting on an escalated case:** the recipient can add instructions and **Return to officer** (back to Under process), escalate to Level 3, or **Dispose** (the Action Gate runs first).
- **Data:** `GET /escalations`, `POST /complaints/{id}/escalate`, `POST /complaints/{id}/transition`.
- **Tests:** level and reason validation; queue shows only the caller's scope; return-to-officer updates the badge and timeline; disposal opens the Gate; system-actor display.
- **Done when:** an officer escalates a case, the supervisor returns it with instructions, and the full movement shows in the timeline.

---

## 5. Shared Components (inventory)

| Component | Phase | Notes |
|---|---|---|
| `Button`, `Card`, `Badge`, `Dialog`, `Tabs`, `Select`, `Tooltip`, `Toast`, `Skeleton` | F1 | shadcn-style, token-based |
| `SyntheticBadge`, `AiLabel` | F1 | Appear from the first screen |
| `DataTable` (sort, sticky header, virtualised > 200 rows) | F2 | Complaints, overlaps, audit |
| `MaskedValue`, `RevealDialog` | F2 | P5 |
| `InstitutionPicker` | F2 | Used by intake and filters |
| `TimelineList` | F2 | Complaint and 360° |
| `SeverityBadge` | F3 | Icon + text + colour |
| `MatchReceipt` | F3 | P1; fails visibly without data |
| `CaseSummaryCard`, `OverlapCompare` | F3 | Side-by-side review |
| `GateDialog` | F3 | Headline feature |
| `ChartWithTable` | F2 | Every chart wrapped, with text summary and table toggle |
| `AuditVerifyPanel` | F3 | U3 |
| `EscalateDialog` | F2 | §4.19 |
| `LiveIndicator` | F2 | §3.6 |
| `TrackingBlock` (last action, next action, dates) | F2 | KF2.7–KF2.9 |
| `AskBar` | F5 | U10 |
| `ImportStepper` | F2 | U8 |

---

## 6. Designed vs. Built (frontend)

Status keys: 📋 Planned · 🔨 In progress · ✅ Built & tested · ⚠️ Built with a known limitation. Keep in sync with `src/app/screens.ts` (`status`/`phase`).

| # | Item | Phase | Status | Evidence |
|---|---|---|---|---|
| 1 | Vite + React + TS strict project, lockfile, lint/format/test tooling | F1 | 📋 | — |
| 2 | Design tokens, light/dark/auto theme, pre-paint script | F1 | 📋 | — |
| 3 | App shell, role-filtered navigation from the screen registry | F1 | 📋 | — |
| 4 | Typed API client + generated schema + contract checks | F1 | 📋 | — |
| 5 | Login and auth context (in-memory tokens) | F1 | 📋 | — |
| 6 | System Status | F1 | 📋 | — |
| 7 | Planned-screen pages that probe real endpoints | F1 | 📋 | — |
| 8 | nginx image with strict CSP, proxy, Compose service | F1 | 📋 | — |
| 9 | CI: lint, types, unit, build, e2e, axe | F1 | 📋 | — |
| 10 | Dashboard | F2 | 📋 | §4.2 |
| 11 | Complaints list + filters in URL | F2 | 📋 | §4.3 |
| 12 | New Complaint + InstitutionPicker | F2 | 📋 | §4.4 |
| 13 | Complaint Detail with timeline, masked fields | F2 | 📋 | §4.5 |
| 14 | College 360° | F2 | 📋 | §4.6 |
| 15 | Import Wizard | F2 | 📋 | §4.12 |
| 16 | Institution Registry | F2 | 📋 | §4.13 |
| 17 | Overlaps queue/review, MatchReceipt | F3 | 📋 | §4.7 |
| 18 | Action Gate | F3 | 📋 | §4.8 |
| 19 | Audit & Verify | F3 | 📋 | §4.14 |
| 20 | Coordination Thread, notifications | F4 | 📋 | §4.9, §4.18 |
| 21 | Role-aware UI complete, masking everywhere, Admin | F4 | 📋 | §4.15 |
| 22 | Management View, Reports | F5 | 📋 | §4.10, §4.11 |
| 23 | AskBar, AI summary UI, Joint Case Brief link, Scenario loader UI | F5 | 📋 | §4.7, §4.17 |
| 24 | Usability walkthrough, performance measurement, hidden source maps, security headers review | F6 | 📋 | — |
| 25 | Escalate dialog and Escalations screen, escalation badge and history in the timeline (F-29) | F2 | 📋 | §4.19 |
| 26 | Live indicator and live dashboard updates, institution-wise status table, Tracking block (F-30, F-31) | F2 | 📋 | §3.6, §4.2, §4.5 |
| 27 | Extended reports UI: status-wise, institution history, overlapping cases, monthly/quarterly (F-32) | F5 | 📋 | §4.11 |

---

## 7. Phase Plan (frontend)

Frontend phases follow the backend phases they depend on, starting once real endpoints exist; until then screens are built against fixtures and the `501` contract stubs. There is no time limit; a phase ends only when its exit criteria are met and recorded.

| Phase | Needs backend | Scope | Exit criteria |
|---|---|---|---|
| **F0 Planning** | — | This document | ✅ Committed |
| **F1 Skeleton** | B1 | Items 1–9 | App runs in the Compose stack; Login for all seven roles; System Status shows live readiness; every other screen is a planned page showing its backend phase; axe has zero serious/critical violations; CI green |
| **F2 Records & visibility** | B2 | Items 10–16, 25–26 | Dashboard numbers equal seeded database counts (e2e); filters round-trip through the URL; import with bad rows reports exact rows; picker handles the variant and Devanagari names; keyboard pass recorded |
| **F3 Overlap core** | B3 | Items 17–19 | Every planted scenario renders the right receipt and Gate result; Verify shows intact and broken states; overlap without receipt cannot render (test) |
| **F4 Coordination & roles** | B4 | Items 20–21 | Two-user handshake e2e passes; role-visibility tests pass for all seven roles; masking verified on every screen showing personal fields |
| **F5 Management & AI** | B5 | Items 22–23, 27 | Report totals reconcile with the dashboard; every AI element shows its label and fallback state with AI disabled (e2e) |
| **F6 Hardening** | B6 | Item 24 | Usability walkthrough recorded (≥ 80% task success, SUS ≥ 70); budgets in §10 measured and recorded; source maps hidden |

### 7.1 F1 task breakdown (next up — ordered)
1. Create the project with strict TypeScript, lint, format, test tooling; commit the lockfile; record versions (Appendix A).
2. Design tokens and theme (light/dark/auto) with the pre-paint script as an external file.
3. Screen registry (`screens.ts`) containing all screens in §4 with roles, phases and endpoints; router and navigation generated from it.
4. App shell with role-filtered navigation, header (SYNTHETIC badge, adapter status, bell, theme), skip link, landmarks.
5. API client and hooks; `ApiError` with `plannedPhase`; contract generation and CI diff.
6. Auth context and Login (in-memory tokens), role guards.
7. System Status page with live readiness.
8. `PlannedScreen` page that states purpose, roles and requirements and probes the screen's real endpoints.
9. nginx image with strict CSP and the proxy; Compose service; Playwright e2e with axe on every screen; CI.

---

## 8. Design System

**Tokens (`src/styles/index.css`):** `bg`, `surface`, `surface-2`, `border`, `text`, `text-muted`, `accent`, `accent-contrast`, status pairs `ok`, `warn`, `danger`, `info`, each with a `-bg`; all defined for light and dark and exposed to Tailwind.

**Semantic tokens (added F3):**

| Meaning | Colour family | Icon | Text label |
|---|---|---|---|
| Clear | green | check-circle | "Clear" |
| Related | amber | alert-triangle | "Related" |
| Conflict | red | shield-alert | "Conflict" |
| Systemic | violet | layers | "Systemic" |
| Escalated | orange | arrow-up-circle | "Escalated (Level 2)" / "(Level 3)" |
| Synthetic data | neutral outline | flask | "SYNTHETIC DATA" |
| AI-written | blue outline | sparkles | "AI-written" |
| Template | grey outline | file-text | "Template summary" |

Colours are checked for AA contrast in both themes and for colour-blind safety; **the icon and text are mandatory** next to every severity colour.

**Typography:** system UI font stack with Devanagari-capable fallbacks (no web-font download, works offline); tabular numbers for all figures; 16 px base; line-height tuned for Devanagari text in complaint views.

**Layout:** left sidebar (collapsible), top header, content max-width for reading screens, full-width for tables; responsive down to tablet width and usable on a phone for read-only views (no horizontal page scroll at 375 px).

**Tone of voice:** plain, official, advisory. Examples: "Another unit has an open case on this institution", "Suggested overlap — please review", "Details visible after coordination is accepted."

---

## 9. Testing Strategy & CI

| Layer | Tooling | Runs | Content |
|---|---|---|---|
| Unit / component | Vitest + Testing Library + jsdom; `mockBackend()` fetch table; `renderApp(path, role)` | every push | formatters (IST, en-IN), masking helpers, filter↔URL sync, receipt rendering, Gate states, role-based navigation |
| Contract | `check:api` (types regenerated equal committed), backend export diff, registry endpoint check | every push | no drift either way |
| Browser e2e | Playwright (desktop and tablet projects) against the Compose stack through nginx | integration job | the nine demo-script scenarios in MASTER_PLAN §18, login per role, import with bad rows, handshake between two users |
| Accessibility | `@axe-core/playwright` on every screen and every Gate state | every push from F1 | zero serious/critical violations |
| Visual regression | Playwright screenshots of fixed seeded views | from F3 | Gate (three results), Match Receipt, College 360°, Verify intact/broken |
| Rendering check | Playwright | from F2 | Devanagari text renders (non-empty glyph widths, no tofu detection via comparison screenshot) |

**E2E guarantees enforced from F1:** no console errors on any screen; every screen has exactly one `h1`; no horizontal page scroll at 375 px; keyboard-only completion of login, intake, Gate and overlap decision; every severity shown with icon and text.

**Rules:** a bug fix starts with a failing test; no `sleep` in tests (use auto-waiting); fixtures are the backend's seed data so frontend and backend tests describe the same world.

---

## 10. Performance Budgets (targets — measured in F6)

| Metric | Budget |
|---|---|
| Initial JS for the shell (gzip) | ≤ 200 kB; each screen chunk ≤ 150 kB (route-level lazy loading from F1) |
| CSS (gzip) | ≤ 25 kB |
| Largest Contentful Paint (office laptop, LAN) | ≤ 1.5 s |
| Gate result rendered after the API responds | ≤ 100 ms |
| Table interaction (sort/filter) with 5,000 rows | ≤ 100 ms (virtualised) |
| Dashboard load with seeded data | ≤ 2 s |

Measured values are recorded in Appendix B; the table above is a target only.

---

## 11. Security

- **Strict Content-Security-Policy:** same-origin scripts only, no inline scripts, no third-party hosts, `frame-ancestors 'none'`; plus `X-Frame-Options: DENY`, `nosniff`, a referrer policy, `server_tokens off`.
- **Same-origin API** through the proxy, so no CORS surface.
- **Tokens held in memory only** (never in `localStorage`); silent refresh via the refresh endpoint; logout revokes; on 401 the app clears state.
- **No secrets in the bundle.** The only build-time variable is the git SHA.
- **Content safety:** complaint text, institution names and remarks always render as text; `dangerouslySetInnerHTML` is banned by lint.
- **PII handling in the UI:** masked by default; plain values only after a reason-gated reveal; revealed values are not cached by the query client beyond the view (cache time zero for that query) and are cleared on navigation.
- **Exports:** CSV cells beginning with `=`, `+`, `-`, `@` are neutralised by the backend; the UI never constructs exports itself.
- **Role-aware UI:** hiding is UX only; the backend enforces roles.
- `npm audit` (production dependencies) runs in CI.
- Source maps are hidden in production builds (V-F7).

---

## 12. Frontend Architecture Decision Log

| ID | Chose | Over | Why |
|---|---|---|---|
| ADR-F1 | React + Vite SPA served by nginx | Next.js (SSR) | Static hosting in a government network; no Node server to operate |
| ADR-F2 | Same-origin proxy | CORS + absolute API URLs | No CORS surface; one URL; same behaviour in dev and prod |
| ADR-F3 | TanStack Query for server state | Redux for everything | Nearly all state is server state; caching, retry, invalidation built in |
| ADR-F4 | Types generated from the backend OpenAPI with CI drift checks | Hand-written types | Frontend and backend cannot silently disagree |
| ADR-F5 | Tailwind + tokens + shadcn-style components | A full component library | Full control of accessibility, density and themes; small CSS |
| ADR-F6 | Recharts with mandatory table alternatives | A heavier charting stack | Dashboards need simple bar/line/area charts; accessibility handled by our wrapper |
| ADR-F7 | Screen registry drives routes, navigation and tests | Hand-maintained routes | One place to change; tests guarantee every plan screen exists and uses real endpoints |
| ADR-F8 | Planned screens probe real endpoints (501 + phase) | Static "coming soon" | Honest, live build status; exercises proxy and contract from day one |
| ADR-F9 | Gate as a dialog on actions, not a menu item | A separate "check" page | The check must happen *at the moment of action* to prevent conflicts |
| ADR-F10 | Filter state in the URL | Local component state | Shareable, bookmarkable, testable views |
| ADR-F11 | In-memory tokens | `localStorage` tokens | Reduces theft through script injection |
| ADR-F12 | Axe from F1, not later | Accessibility at the end | Cheaper to keep correct than to fix |
| ADR-F13 | Responsive web app | Native app | One codebase; no installation in an office setting |
| ADR-F14 | Explicit Live and Stale indicator driven by the stream heartbeat | Silent polling with no indicator | Officials must know whether the numbers are current (OUT-6) |

---

## 13. Frontend Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RF1 | Gate dialog is skipped or can be dismissed into "proceed" | Medium | High | No proceed on close; explicit choices only; tests for keyboard and Esc behaviour |
| RF2 | Receipt or overlap shown without evidence | Medium | High | Component throws/defect banner when `receipt` is missing; test |
| RF3 | UI overclaims ("probability", "duplicate found", "AI") | Medium | High | §3.2 wording rules; review checklist; AI label mandatory; lint rule for banned words in UI strings (`probability`, `chance`) |
| RF4 | Personal data visible by accident | Low | High | `MaskedValue` as the only way to render those fields; test that scans rendered pages for unmasked patterns in seeded data |
| RF5 | Accessibility gaps in charts and timelines | Medium | Medium | Tables and lists as equivalents; axe in CI; manual keyboard pass |
| RF6 | Devanagari renders as boxes on the demo machine | Medium | Medium | Font stack with fallbacks; rendering check; test on the demo machine early |
| RF7 | Contract drift frontend ↔ backend | Low (CI-guarded) | Medium | Three checks (§2.3) |
| RF8 | Bundle bloat | Medium | Medium | Lazy routes from F1; budgets in §10 |
| RF9 | Over-reliance on colour for severity | Medium | Medium | Icon + text mandatory; screenshot test in greyscale |
| RF10 | Session expiry loses a half-written remark | Medium | Low | Keep form text in memory across the re-login |
| RF11 | Dashboard looks live while the data is stale | Medium | Medium | Heartbeat-driven indicator, dimmed numbers after 30 s, polling fallback, e2e test that cuts the stream |
| RF12 | Escalation misunderstood as automatic | Low | Medium | Wording "Escalate for decision"; system escalations labelled with actor "system"; Q&A entry |

---

## 14. Frontend Q&A Preparation

**"Is the UI a mock-up?"**
No. It runs in the same Docker stack as the backend. Any screen whose backend is not ready says so, live, instead of showing invented data.

**"What does an officer actually see when there is a conflict?"**
A red panel in the middle of the action they are about to take: which other unit holds a related case, who owns it, what state it is in, and the evidence behind the match, with three clear choices. Every choice is recorded.

**"Can the officer ignore the warning?"**
Yes, with a written justification — the system advises and records; it does not take decisions away from officials.

**"How do you handle personal data?"**
It is masked by default. Revealing it needs a stated reason, which is logged. The demo uses synthetic data only.

**"What if the AI is not available?"**
Screens show "Template summary" and "meaning matching unavailable" in the receipt. Nothing breaks and nothing pretends.

**"Is it accessible?"**
Keyboard-first, colour is never the only signal, charts have table equivalents, and automated accessibility checks run on every screen in CI.

**"How do the frontend and backend stay in sync?"**
Types are generated from the backend's OpenAPI schema, and CI fails on drift in either direction.

---

## 15. Immediate Next Actions (frontend)

1. Add the PS number to `docs/PROBLEM_STATEMENT.md` and to the three plan headers (MASTER_PLAN V-M1). The official text is already saved there and the requirement IDs are mapped.
2. **F1 kickoff:** §7.1 tasks 1–4 (project, tokens, registry, shell) — can start now against fixtures.
3. Decide the demo machine and test Devanagari rendering on it (V-F3).
4. Write the seven demo-user role names into the seed docs (passwords live there, not in the UI).
5. Agree the shared fixtures with the backend (the seeded dataset and ground truth) so tests describe the same world.

---

## Appendix A — Resolved Versions (to be filled at F1)

*(empty — nothing built yet)*

## Appendix B — Verification Record (to be filled as we build)

| Check | Command | Result | Date |
|---|---|---|---|
| *(empty — nothing built yet)* | | | |

## Appendix C — Planned File Tree

```
frontend/
├── FRONTEND_PLAN.md
├── Dockerfile · nginx/default.conf.template
├── index.html · public/ (favicon.svg, theme-init.js)
├── package.json · package-lock.json · tsconfig*.json · vite.config.ts · playwright.config.ts
├── e2e/                      scenario specs mirroring MASTER_PLAN §18
└── src/
    ├── main.tsx
    ├── app/                  router, screens registry, AppShell, providers, theme, auth
    ├── components/ui/        Button, Card, Badge, Dialog, Tabs, Select, Tooltip, Toast, Skeleton
    ├── components/domain/    MatchReceipt, GateDialog, OverlapCompare, MaskedValue, …
    ├── lib/                  api/ (openapi.json, schema.d.ts, client, hooks), format/, storage.ts, cn.ts
    ├── pages/                Login, Dashboard, Complaints, NewComplaint, ComplaintDetail, College360,
    │                         Overlaps, OverlapReview, Coordination, Management, Reports, Import,
    │                         Registry, Audit, Admin, SystemStatus, PlannedScreen, NotFound
    ├── styles/index.css
    └── test/                 setup, utils (mockBackend, renderApp), fixtures from the backend seed
```

## Appendix D — Document Maintenance Rules

- Dated update lines go in the header; wrong statements are corrected in place with a dated note.
- Update §6 here and `src/app/screens.ts` in the same commit as the code.
- Every "✅" cites a file and a test.
- **Git rule:** every commit and push is authored by Ayush More only; no co-author trailers or tool attribution (see `../CLAUDE.md`).
