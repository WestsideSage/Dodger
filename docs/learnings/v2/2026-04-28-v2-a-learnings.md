# V2-A Scouting Model Learnings

- Keep scouting RNG namespace-separated from match simulation RNG. This preserves golden-log stability while allowing deterministic scouting variance.
- Persisting the full scouting domain (state, assignments, strategies, contributions, events, labels, and traits) was necessary to avoid UI/engine drift across week advances and save/load cycles.
- Prospect signing must be a single canonical path: mark prospect signed, persist trajectory, and drop prospect-only scouting state in the same transaction boundary.
- Carry-forward decay is safest as an explicit season-transition hook rather than implicit week math; this keeps re-entry idempotent and avoids duplicate decays.
- Fuzzy profile UX and uncertainty bar need to read from the same scouting tiers used by engine progression so presentation cannot overstate certainty.

