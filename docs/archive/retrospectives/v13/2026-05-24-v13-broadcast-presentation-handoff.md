# V13 Broadcast And Presentation Layer Handoff

Date: 2026-05-24
Milestone: V13
Status: Shipped and verified on `main`.

## Summary

V13 adds a presentation layer on top of existing match, replay, and league-memory truth without changing outcomes. The ship centers on deterministic broadcast framing before matches, proof-backed highlight packages after matches, playoff overlays in replay, lightweight record-backed commentary inserts, and richer offseason record / Hall of Fame cards.

## Shipped Surface

Backend:

- `src/dodgeball_sim/broadcast.py`
- `src/dodgeball_sim/highlights.py`
- `src/dodgeball_sim/matchup_details.py`
- `src/dodgeball_sim/replay_service.py`
- `src/dodgeball_sim/server.py`
- `src/dodgeball_sim/offseason_presentation.py`
- `src/dodgeball_sim/voice_register.py`

Frontend:

- `frontend/src/components/BroadcastFrameBlock.tsx`
- `frontend/src/features/replay/MatchHighlights.tsx`
- `frontend/src/components/MatchReplay.tsx`
- `frontend/src/components/match-week/MatchupCard.tsx`
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- `frontend/src/components/ceremonies/StructuredOffseasonBeats.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types.ts`

New tests:

- `tests/test_broadcast.py`
- `tests/test_highlights.py`
- `tests/test_highlights_api.py`
- `tests/e2e/v13_broadcast_layer.spec.ts`

Expanded coverage:

- `tests/test_matchup_payload.py`
- `tests/e2e/command-center-aftermath.spec.ts`

## What Landed

- Matchup preview now carries a structured `broadcast_frame` with stakes, rivalry, optional archetype framing, and a visible proof toggle.
- Replay payload now carries `broadcast_frame`, `playoff_frame`, and `commentary_inserts`.
- `GET /api/matches/{match_id}/highlights` returns a deterministic highlight package keyed back to real replay events.
- Replay UI defaults to a `HIGHLIGHTS` tab, keeps the raw play-by-play reachable, and exposes proof sources on highlights and commentary inserts.
- Playoff matches render a distinct header strip in replay.
- Offseason `records_ratified` and `hof_induction` beats now surface proof-backed cards instead of terse structured dumps.

## Verification

Repo gates:

- `python -m pytest -q`
- `npm run build`
- `npm run lint`
- `git diff --check`

Browser proof:

- `npx playwright test tests/e2e/command-center-aftermath.spec.ts tests/e2e/v13_broadcast_layer.spec.ts --project=chromium`

The V13 Playwright walk now covers:

- pre-match broadcast framing
- replay open from the aftermath screen
- highlight-package proof links
- playoff-frame visibility on the season-ending playoff match
- offseason record cards with visible proof affordances

## Integrity Notes

- V13 is presentation-only. No new engine math or outcome-affecting randomness was added.
- Highlight beats and commentary inserts are derived from existing event log, moment events, standings, rivalry history, and record tables.
- Raw replay proof remains one click away from every new surface.

## Known Limits

- `archetype_tag` degrades gracefully when V12 trajectory data is absent.
- Commentary inserts only render when a record claim is still true at replay-build time.
- Hall of Fame presentation upgrades are live, but first-season browser proof usually reaches `records_ratified` before there is meaningful Hall of Fame data.
