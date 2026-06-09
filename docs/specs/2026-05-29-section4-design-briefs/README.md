# Section 4 Design Briefs — Claude Design Handoff (2026-05-29)

These eight briefs are the Phase 8 deliverable of the May 2026 Playtest-Fixes Multi-Phase Plan
(`docs/archive/plans/2026-05-29-playtest-fixes-multi-phase-plan.md`, decision D8).

**STATUS: IMPLEMENTED + VERIFIED (2026-06-09).** All eight briefs are shipped on
`main` and browser-verified. These are now historical design references, not
pending work - do **not** re-implement them. The UI landed on 2026-05-30 in four
`feat(design)` commits: `1de41e2` (4.1), `719f036` (4.2/4.5/4.8), `17e0f6e`
(4.3/4.4), `542e6fe` (4.6/4.7). A 2026-06-09 re-validation + live prod-server
browser sweep (1280x720, the no-overflow floor; deep states reached via
fast-forward and a build-from-scratch bye career) confirmed every brief's success
criteria with zero horizontal overflow - HONEST EXCEPTION: 4.1's read-only legacy
fallback path was browser-rendered, but its card-grid tab mode
(`My/Rival/Surprise` -> "Your Picks/Rival Picks/Surprises") is code-verified only
(`FILTER_LABELS`); it populates from in-season Recruitment Day signings, which the
fast-forwarded verify careers skipped. Drift since these briefs froze (Phases
2-7 + `0673d40`) was confirmed *resolved* in the shipped UI, not pending - e.g.
4.1 `signed_count` authority, 4.2 `archetype_key`, 4.4 game-point hero +
`manager_lesson`, 4.6 game-point bracket scorelines, 4.8 scope-toggle counts. One
fix landed (a §4.1 fallback-prose `64.0 OVR` float leak). See
`docs/STATUS.md` -> "Section 4 desktop-first visual implementation" for the full
verification record and the remaining owner-decision enhancements.

**Phases 1-7 have shipped.** All logic is settled: set-based scoring is live,
PRIMARY FACTOR is honest, moments flow through the official engine, readiness
gates require real actions, records have a scope filter and honest empty-states,
Policy Editor de-duplication is done, and growth deltas are visible. That
settled logic is what the now-shipped Section 4 UI renders.

## Brief index

| File | Screen | Component / Backing data |
|------|--------|--------------------------|
| [4.1-class-report.md](4.1-class-report.md) | Class Report | `SigningDay` (Ceremonies.tsx) / `RecruitmentBeatPayload` |
| [4.2-season-preview.md](4.2-season-preview.md) | Season Preview | `SeasonPreview.tsx` / `build_season_preview` (season_preview.py) |
| [4.3-bye-week-aftermath.md](4.3-bye-week-aftermath.md) | Bye Week Aftermath | `MatchWeek.tsx` post-sim path when `bye_recovery` present |
| [4.4-match-aftermath.md](4.4-match-aftermath.md) | Match Aftermath Hierarchy | `MatchWeek.tsx` post-sim path / `Aftermath` type |
| [4.5-rookie-class-preview.md](4.5-rookie-class-preview.md) | Rookie Class Preview | `RookieClassPreview.tsx` / `RookieClassPreviewBeatPayload` |
| [4.6-war-room.md](4.6-war-room.md) | War Room (Playoff Flair) | `LeagueContext.tsx` + `PlayoffBracket.tsx` / `StandingsResponse` + `PlayoffBracketResponse` |
| [4.7-policy-editor.md](4.7-policy-editor.md) | Policy Editor Restyle | `PolicyEditor.tsx` / `CoachPolicy` |
| [4.8-records-ratified.md](4.8-records-ratified.md) | Records Ratified | `StructuredOffseasonBeats.tsx` (`RecordsRatified`) / `RecordsRatifiedBeatPayload` |

## Constraints shared by all screens

- Frontend/UI work is desktop-first/desktop-only for now. Supported design targets: 1440x900 primary, 1366x768 desktop stress, 1280x720 minimum desktop. Mobile optimization is a non-goal.
- AI-friendly / semantic markup (`role`, `aria-*`, landmark elements).
- No new dependencies.
- No routing or auth changes.
- "Explain, don't decide" — the event log is canon; UI surfaces it, never replaces it.
