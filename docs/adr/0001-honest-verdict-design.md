# ADR 0001 — Honest post-match Verdict

**Status:** accepted (2026-05-19)

## Context

The 2026-05-15 Product Coherence Audit identified the broken decision→consequence
loop as the game's biggest weakness. Its proposed Fix 1 — a "Did Your Plan Work?"
verdict shown after each match — was deferred from the Codex coherence pass
because it requires a backend sentence generator. While designing it we found
that the audit's own model of how Approaches mechanically work ("Aggressive =
pressure / rush / fatigue") is wrong: `command_center._policy_for_intent`
actually moves *different* tactics per approach (Aggressive raises `target_stars`
and `catch_bias`; Defensive is the only approach that lowers `rush_frequency`;
Control raises `sync_throws` and `target_ball_holder`). Building the verdict on
the audit's flavour copy would ship a UI element that lies about levers the
player never pulled.

## Decision

The post-match **Verdict** is a single sentence asserting whether the chosen
**Approach**'s *intended mechanical behaviour* actually showed up in the match,
expressed in observational language (correlation, never causation) and carrying
its own numerical evidence.

The five binding decisions are:

1. **Signature-not-result honesty.** The verdict tracks the approach's
   measurable signature in the box score, not the win/loss. "You won despite
   your plan" and "your plan worked but you lost" are first-class states.
2. **Comparative metrics vs the opponent in the same match.** Per-match
   comparison removes the need for league-norm calibration:
   Aggressive→`catches_made`, Defensive→eliminations against you, Control→
   `throws_on_target / throws_attempted` ratio, Balanced→none (always neutral).
3. **Data injection in every sentence.** Verdicts include the signature numbers
   ("Your Aggressive plan delivered — 7 catches to 3."). The number *is* the
   audit trail. No seeded RNG flavour variants in v1.
4. **No-op as a first-class verdict state.** `_policy_for_intent` clamps with
   `max()`/`min()` against the club's base `CoachPolicy`, so an approach can be
   a complete no-op for a given squad. When the resulting tactics dict equals
   the base, the verdict says so, regardless of result.
5. **Lane cleanup is a mandatory companion.** The existing "Why it happened"
   lane and "Roster health" lane include hollow plan-paraphrase notes
   (`_pressure_plan_note`, `_target_plan_note`, `fatigue_note`) that contradict
   an honest verdict. They are removed in the same change. The honest
   `_target_note` bullet stays. The pre-existing `f"Intent: {plan['intent']}"`
   leak (`command_center.py:268` rendering "Win Now" to a player who clicked
   "Aggressive") is fixed in the same site.

## Considered and rejected

- **Pure templated verdict without data injection** — passes the audit's letter
  but not its spirit. A claim without a number is the same dishonesty trap as
  the "Trend: UP" chip the audit explicitly killed (Fix 8).
- **Seeded RNG flavour variants** (matching `voice_aftermath.render_headline`).
  Adds size without addressing the audit's complaint. Can be added later if
  sentences feel stale after extended play.
- **Static thresholds for signature presence** (e.g. "catches ≥ 7"). Requires
  league-norm calibration we don't have. Comparative-vs-opponent is
  self-normalising.
- **Deleting `Develop Youth`** alongside `Evaluate Lineup`. `Develop Youth` is
  load-bearing for the AI Program Manager and recruiting logic; deleting it
  would silently change AI club behaviour and break four tests for no
  player-visible benefit. It stays as a backend-only intent, unexposed to the
  player.

## Consequences

- The verdict will sometimes deliver bad news on a win ("you won despite your
  plan"). This is intended — it gives the player a reason to change next week.
- Because Approaches mechanically move outcomes weakly (see open item O1 in
  `docs/STATUS.md`), the honest verdict will frequently report
  `signature_absent` or `no_op`. That is a finding to surface, not hide; it
  motivates the engine-balance work.
- The verdict is presentation-only and does not influence match outcomes, so
  no golden-log regeneration is required.
- Future engine changes that alter how `_policy_for_intent` maps approaches to
  tactics must also revisit the signature metrics in `voice_verdict`.
