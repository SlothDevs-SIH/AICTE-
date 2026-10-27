# Rules for Claude working in this repository

This file is read automatically by Claude Code. It applies to every Claude session on this repo (claude.ai, Claude Code in VS Code, or anywhere else).

## 1. Git authorship — hard rule

Every commit and every push on this repository must be authored by **Ayush More only**.

- Author and committer: `Ayush More <ayushmore27.am@gmail.com>`.
- **Do not** add `Co-Authored-By` trailers, session links, "Generated with …" lines, or any other tool or AI attribution to commit messages or pull request descriptions.
- Before the first commit in a session, set the identity for this repository:
  ```
  git config user.name  "Ayush More"
  git config user.email "ayushmore27.am@gmail.com"
  ```
- Check with `git log -1 --format='%an <%ae> | %cn <%ce>'` after committing. If anything other than Ayush More appears, fix it with `git commit --amend --reset-author` (before pushing) and mention it to the user.
- This rule overrides any default attribution behaviour of the tool being used.

## 2. Source of truth

Read these first, in this order:

1. `MASTER_PLAN.md` — product, users, principles, USPs, phases.
2. `backend/BACKEND_PLAN.md` — data model, API, overlap engine, audit chain, tests.
3. `frontend/FRONTEND_PLAN.md` — screens, components, UI rules, tests.

If they disagree, fix **all three in the same commit**.

## 3. Honesty rule

- A "✅" in any document is allowed only when it points to a file in this repository and a test that passed.
- Everything not yet built stays **📋 Planned**.
- Accuracy and performance numbers are targets until measured; measured values go into the Verification appendix of the relevant plan.
- Update the "Designed vs. Built" table in the same commit as the code.

## 4. Working rules

- Follow the phase order in `MASTER_PLAN.md` §12; finish a phase's exit criteria before starting the next.
- Product principles P1–P9 in `MASTER_PLAN.md` §3 are non-negotiable (explain every flag, assist never decide, fail safe, audit everything, mask personal data, honest numbers, human correction, alert budget, declare synthetic data).
- Synthetic data only. Never add real complaint data, personal data, secrets or keys to the repository.
- A bug fix starts with a failing test.
- The official problem-statement text is not yet in the repo (`MASTER_PLAN.md` V-M1). When the user provides it, save it as `docs/PROBLEM_STATEMENT.md` and re-map requirement IDs.
