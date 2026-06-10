# V16 — Contested Offseason: Learnings (2026-06-10)

1. **Check whether the fog is invertible before shipping fog-of-war.** The
   public OVR band was generated symmetric around the hidden truth, so its
   midpoint WAS the true rating — every "estimate" surface built on it was
   decorative. When a design says "show the estimate, hide the truth",
   verify the estimate cannot be arithmetically inverted to the truth
   (here: jitter the band center, and pin non-centeredness in a test).

2. **Tune offer economies against measurement, never against intuition.**
   The dormant user-offer formula (100 + interest·0.2) read plausible and
   was unbeatable; the modeled AI range (~73–100) was wrong too (actual
   84.9–111.7 on stars). A 60-seed probe (`tools/contested_offer_probe.py`)
   produced the real distribution, the retuned constants, the witness seeds
   for the cause→effect tests, and the documented snipe rates — one tool,
   four artifacts. Keep probes importable so tests reuse their cores.

3. **Auto-pick paths leak through behavior, not just payloads.** After
   banding the picker payload, "Sign Best Available" still sorted by
   true_overall — an invisible leak that no payload assertion catches. Pin
   behavioral contracts with fixtures where public order and truth order
   disagree (the gem/overrated pair), at both the helper and service layer.

4. **Flow tests must not depend on balance constants.** Tests that court a
   prospect to interest 100 to "guarantee" a signing are seed luck (margins
   measured as thin as 3.7 offer points). When a test asserts counters and
   transitions, make the contested dimension structurally impossible
   (monkeypatch the rival-eligibility helper to an empty set) instead of
   probabilistically unlikely.

5. **Gates need a revert tripwire, not just a health ceiling.** The first
   title-share bound (≤0.70) passed against the very code the gate existed
   to prevent. Derive bounds from both measurements — the broken value
   (41.7%) and the healthy value (12.5%) — and add one assertion that is
   *categorically* impossible under a revert (≥1 snipe across the sweep).

6. **When a dormant system gets its first production caller, audit its
   inputs for drift against the live surfaces.** The dormant round computed
   credibility from single-season history while the shipping board used
   career-wide history — invisible while dormant, an instant two-surface
   contradiction once wired.

7. **Idempotent close-hooks beat per-path wiring.** Recruitment can close
   via skip, third signing, roster-full, beat-advance, or the begin-season
   self-heal. One state-key-guarded `ensure_ai_offseason_signings` called
   from every exit (plus the canonical `begin_next_season` as safety net)
   is far safer than reasoning about which path fires first.

8. **Subagent review fleets can die mid-flight — sequence the lenses by
   information value.** The adversarial review hit a session limit with only
   one of six lenses complete. The completed lens (tests) carried measured
   evidence and was worth the whole run; the drift/leak lenses were cheap
   to re-run inline. If budget is uncertain, run the lens you cannot easily
   do yourself first.
