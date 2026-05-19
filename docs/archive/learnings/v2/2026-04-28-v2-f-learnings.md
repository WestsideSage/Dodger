# V2-F Playoffs Learnings

- Playoff eligibility needs an explicit season-format row. Inferring from schema version would retroactively change in-flight saves, which the spec forbids.
- Regular-season standings must ignore playoff match records. Playoff matches share the normal schedule and match record tables, so every standings recompute needs to filter by playoff match id.
- If the user is eliminated, playoff progression still has to continue. The manager hook now simulates AI-only playoff games so the season can reach a persisted outcome.
- `season_outcomes` is the right champion source for new seasons, but standings fallback remains necessary for legacy saves and tests that construct regular-season-only data.
