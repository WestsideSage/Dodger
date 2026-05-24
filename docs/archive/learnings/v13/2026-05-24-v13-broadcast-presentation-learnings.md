# V13 Broadcast And Presentation Layer Learnings

Date: 2026-05-24
Milestone: V13

## Summary

The right implementation shape for V13 was to treat presentation as a deterministic facade over existing truth instead of a new simulation layer. That kept the feature visibly richer while preserving the project's honesty contract.

## What Worked

- A dedicated `broadcast.py` facade kept rivalry, stakes, playoff, and hook selection out of the core replay and command-center modules.
- A separate `highlights.py` selector made deterministic recap rules easy to test in isolation.
- Proof attributes on every surface (`data-broadcast-proof-source`) turned honesty from a documentation claim into a browser-checkable contract.
- Reusing `voice_register` templates kept copy changes centralized and prevented one-off string drift across matchup preview, replay, and ceremony surfaces.
- Browser coverage mattered. The replay-open path looked healthy from API tests alone, but the browser walk forced verification of the actual transition from aftermath -> replay -> offseason.

## Implementation Lessons

- Presentation should consume stable ids, not inferred text. Event ids, record ids, and match ids made highlight cards and commentary inserts auditable.
- Graceful degradation is cheaper than schema expansion when the upstream data is optional. `archetype_tag` can disappear without breaking framing.
- Ceremony upgrades are safer when the backend adds proof metadata directly to the structured payload instead of asking the frontend to reconstruct provenance.
- Small browser helpers are worth it. Fast-forwarding to Week 6 through the API gave reliable playoff proof without turning the Playwright suite into a full-season slog.

## Verification Lessons

- Unit coverage was the right first stop for deterministic selectors:
  - `tests/test_broadcast.py`
  - `tests/test_highlights.py`
  - `tests/test_highlights_api.py`
- Full-suite verification still mattered because V13 touched payload contracts consumed by existing command-center and replay surfaces.
- `git diff --check` was useful again here because unrelated trailing whitespace would have hidden whether the repo was actually ready to close out.
- Playwright needed both a fresh-save flow and a late-season flow. One replay was not enough to prove the playoff frame and offseason cards.

## Next-Time Guidance

1. Keep new presentation features behind data-first facades so review can reason about honesty separately from rendering.
2. Add proof-source attributes at the same time as the UI, not as a cleanup pass afterward.
3. Treat replay-open transitions as browser-critical any time replay payloads or top-level app routing change.
4. Use API-assisted browser setup for season-state coverage instead of duplicating long manual flows in every spec.
