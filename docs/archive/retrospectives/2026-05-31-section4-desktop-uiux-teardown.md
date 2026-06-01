# Section 4 Desktop UI/UX Teardown

## Executive Verdict
- Overall readiness: **Conditionally ready for desktop iteration.** A large amount of the Section 4 brief work has already landed in source, and sampled desktop viewports did not show horizontal overflow. The remaining issues are state-specific truth/hierarchy problems, not broad layout collapse.
- Biggest product risk: **Offseason result screens can still tell the wrong story in fallback or edge states.** The class-report fallback showed `Total Rookies 0` while the body said 12 prospects were available, and it leaked float OVR values.
- Highest-leverage fix: **Make every Section 4 screen derive its hero facts from the same structured payload it visually claims to summarize.** Do not let fallback prose, hidden timeline state, or long recruitment lists carry primary comprehension.
- What not to touch: Engine math, event canon, official scoring, outcome derivation, CoachPolicy v2 keys, replay endpoint shape, or recruitment API contracts.

## Evidence Inspected
- Docs: `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, `docs/specs/MILESTONES.md`, `docs/specs/2026-05-29-section4-design-briefs/README.md`, and briefs 4.1 through 4.8.
- Source files: `frontend/src/components/ceremonies/Ceremonies.tsx`, `RookieClassPreview.tsx`, `StructuredOffseasonBeats.tsx`, `frontend/src/components/MatchWeek.tsx`, aftermath child components, `SeasonPreview.tsx`, `PolicyEditor.tsx`, `LeagueContext.tsx`, `PlayoffBracket.tsx`, `src/dodgeball_sim/offseason_beats.py`.
- Browser states: Week 2 Command Center, Policy Editor modal, regular-season Standings, Week 2 match aftermath, offseason recap/champion/records/development/rookie/signing/class-report states.
- Viewports: 1440x900, 1366x768, 1280x720. No sampled horizontal overflow.
- Tests/commands: `git status --short --branch`, fresh backend restart, REST save/beat inspection, Playwright viewport/DOM/screenshot checks.
- MCPs/skills used: `web-design-guidelines`, `dodger-ui-teardown`, Playwright via `node_repl`, latest Vercel Web Interface Guidelines fetched from GitHub.
- Fallbacks, if any: Pare MCP was not available in this session, so shell/REST/Playwright browser evidence was used instead. Browser screenshots were saved in `playtest_artifacts/section4-audit-*.png`.

## Desktop-First Compliance Check
- 1440x900: Command Center and Standings fit without horizontal overflow. Command Center remained information-dense but scan-heavy.
- 1366x768: Command Center and Standings fit without horizontal overflow.
- 1280x720: Command Center, Standings, aftermath, records, rookie preview, and class report fit without horizontal overflow in sampled states. Policy Editor modal content exceeded the viewport bottom by about 10px in the sampled state.
- Any stale mobile-first assumptions found: no active 390px requirement was observed in current authority docs. Some old mobile/accessibility test lineage still exists in docs/status history, but current AGENTS/Section 4 guidance is desktop-first.

## Top Findings
| ID | Severity | Screen | Component/File | Problem | Fix Direction |
| --- | --- | --- | --- | --- | --- |
| UX-001 | S1 | Class Report fallback | `Ceremonies.tsx` | Fallback report says `Total Rookies 0` while prose says 12 prospects available; OVR values leak as floats. | Build fallback metrics from real class/prospect counts where available, or rename metrics to "Signed Rookies"; format numeric OVR as ints. |
| UX-002 | S1 | Match Aftermath | `ReplayTimeline.tsx`, `MatchWeek.tsx` | A match with 5 moments hides all dramatic moment detail behind a collapsed `POSTGAME REPORT`. | Surface one strongest moment summary above the fold when `moment_events.length > 0`; keep full timeline as drill-down. |
| UX-003 | S2 | Policy Editor | `PolicyEditor.tsx`, `PreSimDashboard.tsx` | Modal is just too tall for 1280x720; sampled editor bottom was at 729.9px in a 720px viewport. | Add modal max-height/internal scroll or reduce vertical density while preserving radiogroups and lock banner. |
| UX-004 | S2 | Rookie Class Preview | `offseason_beats.py`, `RookieClassPreview.tsx` | Storyline copy can render "1 seasons"; class-size 12 can appear with no archetype breakdown, leaving composition unexplained. | Pluralize storyline templates and add an explicit "composition unavailable" note when `class_size > 0 && archetypes.length === 0`. |
| UX-005 | S2 | Signing Day picker | `RecruitmentChoice.tsx` adjacent flow | 40+ prospect buttons create a long undifferentiated list; action controls are not structurally sticky. | Add desktop filters/sort/grouping and a sticky decision rail; do not change recruitment logic. |
| UX-006 | S2 | Key Performers | `KeyPlayersPanel.tsx` | Accessible/plain text concatenates player and club names (`LUX STONEAurora Sentinels`). | Add visible/sequential separators or `aria-label` strings for performer rows. |
| UX-007 | S3 | Records Ratified | `StructuredOffseasonBeats.tsx` | Screen repeats "Records Ratified" in the page title and internal kicker; low harm but noisy. | Remove or reword the internal kicker to a content label such as "Record Scope". |

## Detailed Findings

### UX-001 - Class Report fallback contradicts itself
- Severity: S1
- Screen/state: Offseason Class Report after skipping recruitment on `section4-uiux-audit-temp.db`.
- Evidence: live 1280x720 text showed `0/3 YOUR SIGNINGS`, `0 OTHERS JOINED`, `0 TOTAL ROOKIES`, then body prose: "Top of this year's class - 12 prospects available. Cass Sato: OVR 69.0..."
- Component/file: `frontend/src/components/ceremonies/Ceremonies.tsx:467-480`, `frontend/src/components/ceremonies/Ceremonies.tsx:515-530`.
- Problem: The hero metrics imply no rookie class existed, while the fallback prose says the class had available prospects. The float OVR values also regress the current "integer OVR" presentation standard.
- Fix direction: In fallback mode, either derive class size from structured recruitment payload if available, or label these metrics as signed outcomes only. Sanitize fallback body facts before rendering, especially OVR formatting.
- Verification method: Load a skipped-recruitment offseason state, assert the hero metric and body agree, and check no `\d+\.0 OVR` appears.
- Work type: implementation + a small regression test.

### UX-002 - Dramatic match moments are still hidden below a collapsed drill-down
- Severity: S1
- Screen/state: Week 2 post-match aftermath, 1280x720.
- Evidence: live aftermath showed `POSTGAME REPORT · 5 moments ▼`, but no moment text was visible until expansion. Score and Primary Factor worked; the moment layer did not meet brief 4.4's above-fold criterion.
- Component/file: `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx:89-134`, `frontend/src/components/MatchWeek.tsx:556-575`.
- Problem: Moments are the clearest "what happened" texture for a match, but they are presented as a collapsed count. A player can finish the result without seeing any of the five recognized moments.
- Fix direction: Select one server-provided `moment_events[*].display_text` as a visible "Moment of the Match" strip near `PrimaryFactorCard` or above the collapsed timeline. Keep full `ReplayTimeline` collapsed for drill-down.
- Verification method: Simulate an official-foam match with moment events and assert one `display_text` is visible before expanding the timeline.
- Work type: implementation + e2e assertion.

### UX-003 - Policy Editor barely misses the 1280x720 height target
- Severity: S2
- Screen/state: Command Center Policy Editor modal, 1280x720.
- Evidence: Playwright measured `data-testid="policy-editor"` at `{ y: 53, height: 676.86, bottom: 729.86 }` in a 720px viewport.
- Component/file: `frontend/src/components/match-week/command-center/PolicyEditor.tsx:120-252`, `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:875-895`.
- Problem: The restyle correctly improves grouping and state, but the modal is slightly too tall at the minimum desktop height. This is where users edit a core weekly decision, so clipped bottom content feels broken even if scroll exists.
- Fix direction: Put `max-height: calc(100vh - 48px)` and `overflow-y: auto` on the overlay body, or tighten row gaps/padding by roughly 16-24px at the minimum desktop breakpoint.
- Verification method: Open Policy Editor at 1280x720 and assert overlay body bottom is within viewport or scrollable with no hidden controls.
- Work type: implementation.

### UX-004 - Rookie Class Preview has copy and composition edge-state leaks
- Severity: S2
- Screen/state: Rookie Class Preview, 1280x720.
- Evidence: live text showed "Lightest free-agent crop in 1 seasons". Same state showed `12 INCOMING ROOKIES` but no archetype breakdown because `archetypes.length === 0`.
- Component/file: `src/dodgeball_sim/offseason_beats.py:542-550`, `frontend/src/components/ceremonies/RookieClassPreview.tsx:101-116`.
- Problem: The screen is otherwise much improved, but the grammar leak makes the ceremony feel generated, and the absent composition section gives no explanation for why a 12-player class has no archetype shape.
- Fix direction: Pluralize `season/seasons` in backend storyline templates. If archetypes are absent with a non-zero class, render a compact honest empty-state instead of silently removing the composition section.
- Verification method: Seed a class with one prior season and empty archetype distribution; assert singular grammar and explicit composition empty-state.
- Work type: implementation + backend presentation test.

### UX-005 - Signing Day picker is a long flat list, not a desktop decision surface
- Severity: S2
- Screen/state: Signing Day recruitment picker before Class Report.
- Evidence: live picker exposed 40+ candidate buttons in one vertical run; action controls were not structurally sticky, and automation repeatedly stayed in the same state after reaching the list.
- Component/file: `frontend/src/components/ceremonies/RecruitmentChoice.tsx`.
- Problem: This is adjacent to the Class Report and directly affects whether the player understands the later report. Desktop width is not being used for comparison, filtering, or shortlist workflow.
- Fix direction: Add a desktop decision rail: selected prospect, signing progress, and Sign/Skip actions stay visible while the prospect list scrolls. Add simple grouping by rookie/free agent and sort chips already supported by available fields.
- Verification method: At 1280x720, select a prospect near the bottom and confirm the primary action remains visible without returning to the top.
- Work type: implementation.

### UX-006 - Key performer rows lack semantic separation
- Severity: S2
- Screen/state: Match aftermath Key Performers.
- Evidence: live text extraction produced `LUX STONEAurora Sentinels`, `AYO SMIRNOVAurora Sentinels`, and `IMANI CROSBYYour Club`.
- Component/file: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx:95-117`.
- Problem: The visual row may be readable, but text/AT extraction fuses names and club labels. This violates the design goal that the UI be machine-readable and AI-friendly.
- Fix direction: Add a visible separator (` · `) or give each performer article an `aria-label` such as "`Lux Stone, Aurora Sentinels, 2 eliminations, 2 catches, impact 21`".
- Verification method: Browser accessibility snapshot of aftermath should announce performer rows as separated facts.
- Work type: implementation.

### UX-007 - Records Ratified repeats its title
- Severity: S3
- Screen/state: Records Ratified beat.
- Evidence: live text showed `RECORDS RATIFIED` as the page title and again as the internal panel kicker before the scope toggle.
- Component/file: `frontend/src/components/ceremonies/StructuredOffseasonBeats.tsx:151-157`.
- Problem: Low-risk copy duplication; the scope toggle and records are the actual content.
- Fix direction: Replace the internal kicker with `Record Scope`, or remove it and let the segmented control lead.
- Verification method: Records beat text should include one primary `Records Ratified` heading.
- Work type: implementation polish.

## Passes / Do Not Rework
- Season Preview: current source already implements a timeline strip, semantic `<dl>`, visible bye note, demoted skip preference, and integer OVR display. Keep iterating only if live evidence finds a specific issue.
- Match score hero: live official-foam aftermath correctly showed game points as the hero score and did not invert survivor counts.
- Bye aftermath: current source has a dedicated rest report section and skips replay timeline on bye. Verify with a bye save before changing, but source matches the brief.
- Playoff bracket: current source puts the bracket above the standings shell when active, uses ordered seeds, visible `narrative_note`, and player outcome ribbons. Keep this direction.
- Policy Editor semantics: five radiogroups, 15 radios, and five selected radios were present; preserve this structure.

## Recommended Implementation Plan
1. Fix UX-001 and UX-004 together as offseason presentation truth/copy cleanup. Add tests for class-report fallback and rookie storyline pluralization.
2. Fix UX-002 and UX-006 together as aftermath explainability/accessibility cleanup. Add an e2e check for visible moment text and a text/ARIA assertion for performer rows.
3. Fix UX-003 with CSS only. Re-test at 1280x720.
4. Treat UX-005 as the largest product-design slice. Do it after the above targeted fixes so the picker can be redesigned without mixing in report-truth bugs.
5. Sweep UX-007 opportunistically during Records Ratified polish.

## Verification Notes
- No sampled horizontal overflow at 1440x900, 1366x768, or 1280x720.
- Console warnings/errors captured during the live pass: none.
- Screenshots captured:
  - `playtest_artifacts/section4-audit-policy-editor-1280x720.png`
  - `playtest_artifacts/section4-audit-standings-1280x720.png`
  - `playtest_artifacts/section4-audit-aftermath-1280x720.png`
  - `playtest_artifacts/section4-audit-rookie-preview-1280x720.png`
  - `playtest_artifacts/section4-audit-records-1280x720.png`
  - `playtest_artifacts/section4-audit-class-report-1280x720.png`
