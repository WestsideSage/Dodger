# Dodgeball Manager — Milestones Index

Thin index of all designed/shipped/planned milestones. Any agent (Claude, Codex, ChatGPT, Gemini) working on this project should read this file first to orient on milestone status, then load only the relevant milestone spec(s).

Each milestone has its own folder under `docs/specs/`, containing the canonical design spec and (when written) the implementation plan + retrospective.

---

## Conventions

- **One spec per shippable milestone.** No monolith. No fragmentation.
- **Each spec opens with a "Relation to Prior Specs" section** linking back to predecessors and explicitly noting which sections of older specs it supersedes.
- **The integrity contract in `docs/specs/AGENTS.md` is inherited by every milestone.** Don't re-state it; reference it.
- **V1 closeout notes** live in `docs/retrospectives/2026-04-26-manager-mode-handoff.md` and `docs/learnings/2026-04-26-manager-mode-implementation-learnings.md`. These are the canonical V1 state-of-the-world.

---

## Milestone Status

**Current next milestone:** Polish and hardening after the V8-V10 implementation blitz.

V8-V10 shipped as a thin implementation blitz on 2026-05-06 — recruiting promises/program credibility, league memory, and staff market loops are exposed through the Dynasty Office. Handoff: `docs/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`. Learnings: `docs/learnings/v8-v10/2026-05-06-dynasty-office-blitz-learnings.md`.

**Long-range scope control:** `docs/specs/long-range-playable-roadmap.md`.

| ID    | Name                                            | Status                       | Spec                                                                  | Notes |
|-------|-------------------------------------------------|------------------------------|-----------------------------------------------------------------------|-------|
| V1-M0 | Engine & State Contracts                        | Shipped (2026-04-26)         | `docs/specs/v1/2026-04-26-manager-mode/milestone-0-plan.md`              | Club extension, Lineup persistence, Win-probability analyzer, Match-MVP function, Career state machine, schema v7. Documented in V1 design §2.5. |
| V1    | Manager Mode (full v1 scope)                    | Shipped (2026-04-26)         | `docs/specs/v1/2026-04-26-manager-mode/design.md`                        | Full season loop, off-season ceremony (7 beats: Champion · Recap · Awards · Development · Retirements · v1 Draft · Schedule Reveal), Friendly mode, save/resume. 153 tests passing. |
| V2-A  | Stateful Scouting Model                         | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-26-v2-a-scouting/design.md`                       | Mid-season scouting loop, named scouts, tiered narrowing, CEILING label, trajectory reveal at Draft Day, fuzzy Profile mode (V2-G collapsed in) shipped with schema v10 persistence and deterministic weekly scouting ticks. |
| V2-B  | Recruitment Domain Model                        | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-28-v2-b-recruitment/design.md`                   | AI club preferences, sign rounds, sniping, public-vs-private info. Cinematic Recruitment Day with parallel signings. |
| V2-C  | Build a Club Path                               | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-28-v2-c-build-a-club/design.md`                  | Custom expansion franchise, hidden-gem rebuild fantasy. Deterministic expansion roster, odd-club bye schedule, scouting, and recruitment setup shipped. |
| V2-D  | Expanded `CoachPolicy` Tendencies               | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-28-v2-d-expanded-coach-policy/design.md`         | Adds Target Ball-Holder, Catch Bias, Rush Proximity to the existing 5 fields. Engine behavior, AI legibility tests, and golden-log change note shipped. |
| V2-E  | Off-season Beats Completion                     | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-28-v2-e-offseason-beats/design.md`               | Adds Records Ratified (idempotent), HoF Induction (uses career.evaluate_hall_of_fame), and Rookie Class Preview (V2-A/V2-B-derived storylines) to complete the 10-beat ceremony. |
| V2-F  | Playoffs                                        | Shipped (2026-04-28)         | `docs/specs/v2/2026-04-28-v2-f-playoffs/design.md`                      | Top-4 playoff bracket, persisted season outcome, playoff champion ceremony, and legacy regular-season fallback shipped. |
| V2-G  | UncertaintyBar + Fuzzy Profile Mode             | **Collapsed into V2-A**      | See `docs/specs/v2/2026-04-26-v2-a-scouting/design.md` §6.2, §6.3        | The Scouting Center cannot ship honestly without UncertaintyBar, so V2-G ships as part of V2-A. |
| V3    | Experience Rebuild                              | Shipped (2026-04-29)         | `docs/specs/v3/2026-04-29-v3-experience-rebuild/design.md`              | Roster integrity, pacing controls, replay rebuild, copy quality, and name uniqueness implemented with 318+ tests. GUI verified and merged. |
| V4    | Web Architecture Foundation                     | Shipped (2026-04-29)         | `docs/specs/v4/2026-04-29-v4-sprint-plan.md`                            | Web backend, React app, shared orchestration, DB concurrency fixes, AI balancing, and first-pass parity screens. V5 builds on the web app as the product foundation. |
| V5    | Weekly Command Center                           | Shipped (2026-05-04)         | `docs/specs/v5/2026-05-02-v5-weekly-command-center/design.md`           | Playable week-by-week command loop: intent, department orders, staff recommendations, lineup/tactics accountability, post-week dashboard, command history, offseason ceremony (10-beat web flow), recruitment, and dev hot-reload. All gates passed. Retro: `docs/retrospectives/v5/2026-05-02-v5-weekly-command-center-handoff.md`. |
| V6    | Player Identity and Development Loop            | Shipped (2026-05-05)         | `docs/specs/v6/2026-05-04-v6-player-identity/design.md`                 | Archetype-first player model, Tactical IQ, Lineup Liabilities matrix, AI lineup avoidance, engine liability penalties, and development focus. Handoff: `docs/retrospectives/v6/2026-05-05-v6-player-identity-handoff.md`. Learnings: `docs/learnings/v6/2026-05-05-v6-player-identity-learnings.md`. |
| V7    | Watchable Match Proof Loop                      | Shipped (2026-05-05)         | `docs/specs/2026-05-05-v7-sprint-plan.md`                                | Replay proof loop: key-play navigation, event-derived tactical/fatigue/liability evidence, report evidence lanes, and command-plan-to-replay continuity. QA: `docs/retrospectives/v7/2026-05-05-v7-playthrough-qa.md`. |
| V8    | Recruiting, Promises, and Program Credibility   | Shipped thin (2026-05-06)    | `docs/specs/long-range-playable-roadmap.md`                              | Implemented in the Dynasty Office: credibility from command history/prestige, limited saved recruiting promises, prospect interest evidence, and explicit future promise-check boundaries. |
| V9    | Living League Memory Loop                       | Shipped thin (2026-05-06)    | `docs/specs/long-range-playable-roadmap.md`                              | Implemented in the Dynasty Office: records, awards, rivalry, and recent-match memory surfaces that report real saved data or clear limited-state copy. |
| V10   | Staff Market and Program Arms Race Loop         | Shipped thin (2026-05-06)    | `docs/specs/long-range-playable-roadmap.md`                              | Implemented in the Dynasty Office: deterministic staff candidates, visible staff hires, staff-action history, and current recommendation-facing effects. |

---

## How to Use This Index

**For the agent picking up a new milestone:**

1. Read this file.
2. Read `docs/specs/AGENTS.md` for the integrity contract.
3. Read the canonical spec for the milestone you're working on.
4. Read the predecessor specs only as needed (the milestone spec's "Relation to Prior Specs" section will tell you which sections to consult).
5. If the milestone has a written implementation plan in its folder, read that too.

**For an agent adding a new milestone:**

1. Create `docs/specs/YYYY-MM-DD-<milestone-id>-<short-name>/`.
2. Write `design.md` inside it.
3. Open the spec with a "Relation to Prior Specs" section.
4. Add a row to the table above with status `Designed (YYYY-MM-DD)`.

**For an agent shipping a milestone:**

1. Update the status to `Shipped (YYYY-MM-DD)` in the table above.
2. Add a retrospective at `docs/retrospectives/YYYY-MM-DD-<milestone>-handoff.md`.
3. Add learnings at `docs/learnings/YYYY-MM-DD-<milestone>-learnings.md`.
4. Reference both from the next-milestone spec's "Relation to Prior Specs" section.
