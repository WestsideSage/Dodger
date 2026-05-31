# Section 4 Design Briefs — Claude Design Handoff (2026-05-29)

These eight briefs are the Phase 8 deliverable of the May 2026 Playtest-Fixes Multi-Phase Plan
(`docs/specs/2026-05-29-playtest-fixes-multi-phase-plan.md`, decision D8).

**Phases 1–7 have shipped.** All logic is settled: set-based scoring is live, PRIMARY FACTOR is honest,
moments flow through the official engine, readiness gates require real actions, records have a scope filter
and honest empty-states, Policy Editor de-duplication is done, and growth deltas are visible.
**Claude Design starts elevated — no further teardown or logic work is needed before iterating on layout.**

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
