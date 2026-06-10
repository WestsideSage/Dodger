# Product Director / Milestone Planning Pass — 2026-06-09

Planning-only pass (no code changes). Decided the next milestone from current
repo truth, wrote the sprint plan, and reconciled stale docs. Tooling note:
orientation and git-state checks used Pare MCP (`pare-git status/log`) plus
normal Read/Grep; the full Python suite was run via the project venv
(PowerShell background run) because no Pare pytest call was needed beyond it.

## Decision

**Next milestone: V16 — Contested Offseason.** Full plan, scoring table,
scope fences, atomic tasks, acceptance criteria, and the first
implementation handoff prompt live in the single authority:

- `docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md`

One-line thesis: the offseason class becomes a market — AI clubs sign real
prospects (fixes the measured static league + 60% title snowball), Signing
Day shows scouted bands instead of leaking `true_overall()` (makes scouting
real), and the user's pick resolves through the dormant-but-tested V2-B
contested round so interest/credibility become mechanical again.

Basis: all five 2026-06-09 cross-disciplinary reports in this folder
independently converge on AI offseason recruiting + contested/scouted
Signing Day as the top product work. The mechanism (`recruitment.
conduct_recruitment_round`, recruitment.py:580) and the fog-of-war band
(`recruiting_office.py:156` `public_ovr_band`) already exist; verified in
source this pass, not assumed from docs.

Explicitly NOT chosen (and why, in the plan §2): catch-economy retune
(owner-gated, golden-log churn — queued as the likely V17 candidate), replay
intent frames (research-stage), WT-20 (hard-blocked on unresolved
reduced-blocking parameters), promises / department orders (owner keep-drop
decisions, not buildable).

## Readiness facts established

- `main` = `origin/main` = `6bfc775`; the six 2026-06-09 audit passes sit
  verified but **uncommitted** in the working tree (~58 modified + 11
  untracked files). Landing them is Task 0 of the plan — nothing else first.
- Full `python -m pytest -q` re-run on that exact tree by this pass:
  **green, exit 0** (no failures; the known `test_server_save_boundary`
  order flake did not fire). Exact test count not recaptured (output tail
  trimmed); latest handoff recorded ~1,325.

## Docs reconciled this pass (stale-doc dispositions)

- `docs/STATUS.md`: header commit pointer was stale (`0673d40` → actual
  `6bfc775`); now also states the uncommitted six-pass working tree and the
  active V16 plan; added Open Work #7 (V16 pointer + scope fences).
- `docs/specs/MILESTONES.md`: added the V16 row, `Planned (2026-06-09)`.
- `docs/README.md`: the directory guide did not mention `docs/fable/` even
  though seven handoffs live here and STATUS links them; added the entry
  (records, never active authority).
- `docs/specs/2026-06-09-watchable-match-replay-research.md`: its informal
  "V16A/B/C" working titles now collide with V16; added a renumber-on-
  activation note.
- Verified non-stale, left alone: root `AGENTS.md` (no current-phase facts,
  per its own anti-staleness rule), `CLAUDE.md`,
  `docs/specs/long-range-playable-roadmap.md` (already carries its
  pre-V11-pivot renumbering caveat).

## Open items deliberately left to the owner

- D1/D2/D3 design defaults in the plan §5 (band vs reveal; snipe model; AI
  signing volume) — recommendations are written in; confirm or override at
  Task 3.
- `origin/playtest-fixes-2026-05-27` keep/delete (STATUS Open Work #3).
- Stray root screenshots `replay-official-strip-before/after.png` — exclude
  at the Task 0 commit.
