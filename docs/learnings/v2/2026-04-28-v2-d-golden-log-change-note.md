# V2-D Golden Log Change Note

Date: 2026-04-28

V2-D expands `CoachPolicy` from five tendencies to eight:

- `target_ball_holder`
- `catch_bias`
- `rush_proximity`

The Phase 1 golden log was regenerated after verifying that neutral defaults preserve the old match behavior:

- winner unchanged,
- final tick unchanged,
- event actor order unchanged,
- throw outcomes unchanged,
- probability and roll sequences unchanged,
- box score unchanged.

The golden file changed because throw events and match-start context now include the expanded policy snapshot, target-selection component fields, catch-bias decision fields, and rush context audit payload. This is an intentional audit-shape change, not a balance or outcome change.
