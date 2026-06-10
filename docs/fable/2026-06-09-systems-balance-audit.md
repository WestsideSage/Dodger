# Systems Design / Balance Audit — 2026-06-09

Role: lead game systems designer / balance director / simulation analyst.
Scope: does the actual decision space produce interesting, understandable,
repeatable, manager-driven outcomes — and where should systems be tightened,
expanded, or corrected? All work in the main repo working tree, on top of the
(uncommitted) watchability, first-hour-onboarding, trust-audit, and UX passes.

Tooling note: Pare MCP was bypassed for this pass — the work needed raw probe
stdout, custom Monte-Carlo loops, and verbatim pytest/playwright output, so
plain shell commands were used (fallback disclosed per `AGENTS.md`).

Measurement integrity: every balance number below is a fresh measurement from
this pass (seeded, reproducible; tools and trial counts stated inline). Claims
I could not measure are labeled as such.

---

## 1. Systems verdict

**Healthiest systems:** the weekly plumbing is sound. Locked tactics reach the
sim and the recap (re-verified by reading `use_cases.simulate_week` →
`_apply_command_plan_to_match` → club reload → engine); lineup choice is the
single strongest decision (OVR curve: rec +16.5pp, official +36.0pp slope);
development is headroom-proportional and consumes dev_focus (club-filtered);
opponent scouting reveals real past-tape; prospect scouting genuinely narrows
the band the rest of the UI reads; AI managers run the same plan→tactics→
lineup pipeline as the player with no hidden boosts (verified in
`ai_program_manager.py` / `ai_tactics.py` / `ai_lineup.py`).

**Weakest systems (found this pass):**

1. **The official catch economy is inverted at the margin** (measured, NOT
   tuned this pass — see §3.4 and the plan in §7). At even strength, +12
   catch = **+31pp** win rate while +12 accuracy = **−8pp** and +12 dodge =
   **−10pp** (both significantly negative at N=1000). Throwing on-target into
   an always-attempting catcher is negative EV (a catch outs the thrower AND
   resurrects a defender, and p(catch|attempt) ≈ 0.53 at evens). This is also
   why the Defensive Specialist shape wins **73.8%** of matched-OVR titles
   (champion-parity probe, 40 seeds × 2 seasons) and why `go_for_catches` is
   the dominant posture in both engines.
2. **PLAY_SAFE was a forfeit button on official careers** — 0 wins in 400
   even-strength matches, 100% losses on a realistic roster fixture — and the
   "Preserve Health" intent preset selects it. **Fixed this pass** (§4.1);
   now 36.8% vs a 44.0% default mirror.
3. **Recruiting courtship has no signing consumer.** The only production
   signing path (`offseason_ceremony.sign_chosen_rookie` via the offseason
   picker) signs the player's choice directly; `conduct_recruitment_round`
   (where interest strengthens the user offer) has **no production caller**,
   and `/api/recruiting/sign` is a dead stub guarding on a career state that
   does not exist. Interest/Fit/Pipeline/Credibility were all labeled
   "mechanical" with signing-power claims. Copy truth-fixed this pass (§4.3);
   wiring a contested Signing Day is the top design gap (§7).
4. **The slot-role "liability" model is presentation fiction.** Only the
   retired legacy `MatchEngine` (engine.py — no production caller) ever
   applied liability penalties, yet the replay claimed "suffered a liability
   penalty" / "Liability exploited … was punished", and the aftermath could
   rank "Lineup liability involved" as the PRIMARY FACTOR of a loss. Fixed at
   the presentation layer this pass (§4.2); wire-or-drop is an owner call.
5. **The attribute sheet oversells itself.** Per-driver dead attributes:
   stamina and tactical_iq have no in-match consumer in either shipping
   engine (stamina only leaks in through OVR-weighted *targeting* — raising
   it makes you more targeted under `their_stars` with zero defensive
   payoff); power is dead in the rec driver; the three identity traits
   (catch_courage / throw_selection_iq / conditioning_curve) are dead in the
   official engine while their TermTips claimed in-match effects
   ruleset-blind. Now pinned by tests and qualified in copy (§4.4); the
   stamina-keyed "health check" readiness gate still gates on a dead rating
   (owner call, §6).

**Biggest risk:** the catch-economy inversion quietly makes team-building
solvable (stack catch, then power; dump accuracy/dodge/stamina at equal OVR)
while the UI teaches the opposite (OVR weights all five equally; "Sharpshooter
… your primary source of eliminations"). It needs its own retune pass with a
golden-log strategy — half-shipping it here would have violated the
outcome-change bar.

---

## 2. Evidence inspected

- Docs (in order): `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`,
  `docs/specs/MILESTONES.md`, `CLAUDE.md`,
  `docs/specs/long-range-playable-roadmap.md`.
- Engine/domain source: `engine.py` (legacy), `rec_engine.py`, `rec_adapter.py`,
  `official_engine.py`, `official_resolution.py`, `official_tactics.py`,
  `official_adapter.py`, `config.py`, `models.py`, `rng.py`, `franchise.py`,
  `season.py`, `playoffs.py`, `development.py`, `recruitment.py`,
  `recruiting_actions.py`, `recruiting_office.py`, `scouting.py` (skim),
  `ai_program_manager.py` + `ai_intent/ai_orders/ai_lineup/ai_tactics`,
  `use_cases.py` (simulate_week + aftermath), `command_center.py`,
  `week_briefing.py`, `match_explanation.py`, `replay_proof.py`, `lineup.py`,
  `career_state.py`, `server.py` (recruiting endpoints),
  `offseason_ceremony.py` (signing paths), `offseason_service.py`.
- Probes run: `tools/tier_engine_health_probe.py` (400/rung, both drivers),
  `tools/archetype_champion_parity_probe.py` (40 seeds × 2 seasons), the new
  `tools/decision_impact_probe.py` (400/condition, both drivers, tactics +
  attributes), plus ad-hoc 1000-trial confirmations and before/after
  play_safe fixtures.
- Tests: full `python -m pytest -q` (1,304 collected, exit 0), targeted suites
  during work, 24/24 targeted Playwright, live prod-server browser checks.

## 2.1 Systems map (decision inventory — condensed)

| Decision | Enters code at | Affects | Verdict |
|---|---|---|---|
| Which six start | plan lineup → `LineupResolver` → engine starters | outcome | **Strongest lever** (OVR slope +16.5/+36pp) |
| Slot order (1–6) | starters tuple order | outcome (marginal) | rec tick-0 sprinters / official initial balls only; role labels advisory (fixed copy) |
| Intent (5 presets) | `_policy_for_intent` → CoachPolicy | outcome via tactics | real; Preserve Health was a trap on officials (fixed) |
| Approach | thrower weighting both engines | outcome (weak) | ±2pp at evens — distinct flavor, near-flat impact |
| Target focus | target scoring both engines | outcome (mild) | ~3–6pp spreads; no dominant option |
| Catch posture | rec branch shares / official attempt threshold | outcome (**dominant axis**) | go_for strictly best both engines (§3.3) |
| Rush commit | rec tick-0 only; official announced-only (disclosed) | outcome (rec, tiny) | flat within CI on both (§3.3) |
| Rush target | event metadata only (both) | none | dead knob; disclosed on officials, NOT disclosed on rec (§6) |
| Department orders | none (except dev_focus) | none | flavor, already disclosed (prior pass) |
| Dev focus | `apply_season_development` multipliers | outcome (offseason) | real |
| Scout opponent | readiness gate + tape reveal | info | honest |
| Scout prospect | band narrowing (persisted) | info | honest |
| Contact/Visit | persisted interest | **nothing** (no consumer) | copy fixed; wire-or-drop (§7) |
| Offseason signing pick | `sign_chosen_rookie` | outcome (roster) | real, uncontested (always succeeds) |
| Staff hires | `staff_development_modifier` → development | outcome (offseason) | real (dev lane); other lanes advisory |
| Promises | evaluation only, no UI | none | known open item (STATUS #5) |
| Playoffs | top-4 by points/diff, resolved ties | outcome | sound |
| Awards/records | aggregated real stats | presentation | mechanically earned (not deep-audited this pass) |

---

## 3. Measurements

### 3.1 Baselines (unchanged, reconfirmed)

`tier_engine_health_probe --driver both --trials 400`:

- rec: even 50.7% → +72 OVR 67.2% (slope +16.5pp, floor PASS, draws 2.2%)
- official: even 36.0% → +72 72.0% (slope +36.0pp, floor PASS, draws 23.1%
  across rungs — the known WT-31 honest-draw issue, gated behind WT-20)

Champion parity (40 seeds × 2 seasons, official_foam): Defensive Specialist
73.8% of titles / Balanced Rebuild 22.5% / Power Throwers 3.8% — gate passes
(≥3 distinct, max ≤ 0.85) but the defense skew is large and consistent with
§3.4.

### 3.2 Tactic impact — new probe (`tools/decision_impact_probe.py`)

400 trials/option, even teams, both teams on a realistic catch/dodge spread
(48–77, mean 63). Post-fix numbers (full table in the probe output):

| Axis | Official spread | Rec spread | Read |
|---|---|---|---|
| catch_posture | go_for 50.0 / opp 44.2 / play_safe 34.8 | 58.8 / 51.0 / 36.0 | **Dominant axis both engines; go_for strictly best** |
| target_focus | 42.0–48.2 | 45.8–49.0 | mild, no dominant option |
| approach | 42.8–44.2 | 45.5–51.0 | near-flat |
| rush_commit | 43.2–45.5 | 49.8–52.0 | flat within CI |
| rush_target | 45.2–46.0 | 47.8–54.0 | flat within CI (structurally dead — see below) |

Structural deadness was separately pinned by same-seed invariance (not just
CI overlap): `tests/test_attribute_consumers.py` proves the byte-identical
cases; rush knobs on officials were already disclosed announced-only.

### 3.3 PLAY_SAFE before/after (the shipped balance fix)

| Fixture | Before | After |
|---|---|---|
| Uniform 63, even, 400 trials | **0.0% W / 5.5 D / 94.5 L** | 0.0% W / 9.2 D / 90.8 L (uniform = degenerate threshold case, see note) |
| Catch/dodge spread (realistic), 400 trials | **0.0% W / 0.0 D / 100.0 L** | **36.8% W / 12.8 D / 50.5 L** (default mirror: 44.0% W) |
| Non-play_safe matches | — | **byte-identical** (WT-7 frozen winner list re-verified equal) |

Note: a uniform-rating roster sits entirely on one side of any deterministic
threshold, so it stays degenerate by construction; real career rosters draw
each attribute ~gauss(62,10) and now land ~37%. Two new gates pin the floor
(`test_play_safe_posture_is_not_a_forfeit`,
`test_play_safe_team_still_attempts_catches`).

### 3.4 Attribute value, official engine (1000 trials/attr, even strength)

| +12 in… | Win% [95% CI] | vs baseline 38.7 [35.7–41.8] |
|---|---|---|
| catch | **69.4 [66.5–72.2]** | massively positive |
| power | **55.4 [52.3–58.5]** | strongly positive |
| accuracy | **30.9 [28.1–33.8]** | **significantly NEGATIVE** |
| dodge | **28.2 [25.5–31.1]** | **significantly NEGATIVE** |
| stamina / identity traits (400-trial runs) | 32.5–43.2 | within noise of baseline (dead) |

Mechanism (traced in `official_resolution.compute_throw_probabilities`): at
even ratings every defender attempts the catch (opportunistic threshold 0.50 <
0.63) and p(catch|attempt) ≈ 0.527, so an on-target throw is EV-negative
(−2-swing catch more likely than +1 hit). More accuracy = more on-target
throws = more catches against you; more dodge = fewer incoming on-target
throws = fewer catch opportunities FOR you. Power is positive twice (reduces
defender catch prob via the −0.6·power term; weights thrower selection).
Rec driver: catch +6pp, courage +2.7, others flat; accuracy ~flat for the
same economy reason (its catch also outs the thrower and resurrects).

---

## 4. Implemented changes, by system

### 4.1 Official engine — PLAY_SAFE forfeit cliff (outcome-affecting, measured)

- `official_tactics._catch_thresholds`: PLAY_SAFE threshold 0.75 → **0.65**
  (above-average catchers still attempt; the old value sat above virtually
  the entire rating band, zeroing attempts). GO_FOR/OPPORTUNISTIC pairs
  numerically unchanged.
- `official_resolution._PLAY_SAFE_EVASION_BONUS = 0.25`: a play-safe defender
  that *declines* the catch gets the posture's promised other half —
  committed evasion — instead of the brutal bare dodge roll. Same RNG draw
  count; only play_safe-defender branches change, so all other matches replay
  byte-identical (verified against the WT-7 frozen winner list).
- Design reason: "Preserve Health" (a first-class intent) selected a posture
  that measured 0-for-400; the AI "Aging Veterans" archetype and the
  Preserve-Health AI override fell into the same pit, systematically feeding
  losses into the league. The posture's announced semantic is "fewer risky
  catch attempts, prefer evasion" — not "opt out of the rules' core
  counterplay".
- Gates added in `tests/test_official_engine_balance.py` (floor 25% at even
  strength on the realistic fixture + a never-zero-catches pin).

### 4.2 Aftermath/replay — slot-role liability fiction (presentation truth)

- `replay_proof.py`: "suffered a liability penalty" → "was fielded out of
  role … advisory fit note; the engine applies no role penalty"; "Liability
  exploited: … was punished" → "Out-of-role starter eliminated: …" (saved
  fact, no causal claim); lane summary now states the advisory framing;
  `_liability_tag` docstring made precise (machine key over saved facts, not
  a causality claim).
- `match_explanation.py`: the `liability_involvement` PRIMARY FACTOR is
  **removed** (with `use_cases.py` plumbing) — a mechanism that doesn't exist
  cannot be a factor in a result, and it could crowd the honest fallback on
  decisive losses while pointing players at a dead lever.
- `lineup.check_lineup_liabilities`: warning string reframed as an advisory
  fit note; docstring states the consumer truth.
- `command_center._lineup_warnings`: the all-in-rush "extreme fatigue risk"
  warning (no engine applies any rush fatigue cost; the rec driver logs a
  `fatigue_delta` it never applies) replaced with the true tradeoff (more
  opening throws = more early catch exposure).
- `terms.ts` `lineup.slot_order`: kind → flavor; honest copy (which six start
  is the lever; order sets opening-play assignments only).

### 4.3 Recruiting — courtship truth (presentation truth + dormant-path fix)

- `terms.ts`: `recruit.interest`, `recruit.fit`, `recruit.pipeline`,
  `program.credibility` → kind flavor with honest copy ("courtship tracker…
  the offseason picker signs your choice directly; contested signings are not
  yet modeled"). `recruit.ovr_range` stays mechanical (scout narrowing is
  real revealed information).
- `recruiting_actions.py`: module docstring now documents the consumer truth
  (no production caller for `conduct_recruitment_round`; `/api/recruiting/sign`
  is a dead stub guarding on a nonexistent career state); `_next_step` no
  longer promises "makes your Signing Day offer hard to beat".
- `recruitment.conduct_recruitment_round`: hardcoded `credibility_score=50`
  replaced with the real program credibility (board-displayed interest and
  signing-used interest can no longer disagree for untouched prospects when
  the round system is eventually wired).

### 4.4 Instrumentation (new, committed)

- `tools/decision_impact_probe.py`: tactic-axis W/D/L (realistic spread
  fixture, both drivers) + per-attribute +12 win-rate impact. This is the
  probe that found §3.3/§3.4.
- `tests/test_attribute_consumers.py` (8 tests): same-seed byte-identity pins
  for the per-driver dead-attribute matrix (rec: power/stamina/tactical_iq
  under spread targeting; official: the three identity traits), plus two
  live-attribute divergence sanity checks. Wiring an attribute later will
  fail these loudly and force the copy/docs update in the same pass.
- `terms.ts` identity-trait entries (`attr.throw_selection_iq`,
  `attr.catch_courage`): claims qualified per ruleset ("Rec-league matches
  only … official-rules matches do not model it in-play").

### 4.5 Docs

- `docs/STATUS.md`: new Shipped-And-Verified entry; this report.

---

## 5. Tests / checks run

| Check | Result |
|---|---|
| Full `python -m pytest -q` (1,304 collected) | **PASS** (exit 0, 100%) |
| `tests/test_official_engine_balance.py` (incl. 2 new gates) | PASS |
| `tests/test_official_catch_posture_wt6.py` (defender-posture pin) | PASS |
| `tests/test_attribute_consumers.py` (8 new) | PASS |
| WT-7 frozen winners byte-identity (default policies, post-fix) | PASS (equal) |
| `tests/test_match_explanation.py` / `test_replay_proof.py` / `test_liability_tags.py` (updated) | PASS |
| Recruiting suites (`test_dispersed_helpers`, `test_recruiting_*`, `test_recruitment`) | PASS |
| `npm run build` / `npm run lint` | PASS / PASS |
| Playwright `v15-lineup-editor` + `v15-recruit-board` + `v15-legibility-surfaces` (chromium) | **24/24 PASS** |
| Live prod-server browser (Interest/Fit/Slot-Order tooltips show FLAVOR + new copy) | verified, zero console errors |
| Probes re-run post-fix (decision impact, both drivers) | recorded in §3 |

Not run: AI-symmetric development balance probe (pre-existing open item);
multi-season league health sweep beyond the 40-seed parity probe; awards/
records deep audit (no behavior touched there).

---

## 6. Answers to the analysis questions

- **Top 5 highest-leverage issues:** §1 list (catch-economy inversion;
  play_safe forfeit [fixed]; recruiting courtship consumer-less; slot-role
  fiction [presentation fixed]; dead-attribute sheet).
- **Decisions that matter most:** which six start; catch posture; intent (as
  the posture/approach carrier); the offseason signing pick; dev focus; staff
  dev-lane hires.
- **Decisions that appear to matter but don't (enough):** Contact/Visit
  interest (none — now disclosed); rush_target (dead in both drivers — on rec
  it is NOT yet disclosed, see below); rush_commit on officials (disclosed)
  and near-flat on rec; approach (±2pp — distinct in flavor, weak in effect);
  department orders (flavor, disclosed); slot order beyond the six (marginal);
  stamina ("health check" gates on a rating no engine reads).
- **Systems at risk of becoming solved/degenerate:** catch posture
  (go_for_catches strictly dominant in both engines — once a player notices,
  there is no reason to pick anything else); team-building at equal OVR
  (stack catch/power, dump accuracy/dodge/stamina); AI posture traps
  (mitigated by 4.1 but Aging Veterans still chooses the weakest posture).
- **Too opaque to trust:** displayed OVR vs real value (catch ≈ 10× accuracy
  at the margin, weighted equally on the card); per-ruleset attribute
  relevance (now partially disclosed); even-strength official draws
  (23–31%, honest but unexplained in-product).
- **Most likely to feel unfair while technically correct:** 0-0 official
  draws at even strength; losing as a slight favorite with "variance" copy;
  investing in accuracy/dodge development and getting *worse* results.
- **Balance numbers that should become ongoing gates:** official OVR slope
  (exists); play_safe floor (added); champion-shape ceiling (exists, 0.85);
  candidates for the retune pass: posture spread cap (max−min posture win
  delta), attribute-sign gate (accuracy/dodge must not be net-negative),
  even-rung draw ceiling (after WT-20).
- **Do not touch yet (insufficient evidence or blocked):** WT-20 live rules
  (owner decision on reduced-blocking params); the core catch-economy retune
  (needs golden-log strategy + owner sign-off, plan below); rec posture share
  model (O1 gates pin it; same economy fix should cover both); promise lane
  (owner keep/drop, STATUS #5); awards/records (no evidence of problems, not
  deep-audited).

---

## 7. Recommended next systems pass (ranked by impact)

1. **Official catch-economy retune (owner-gated, outcome-changing).** Goal:
   make accuracy/dodge non-negative at even strength while keeping the
   faithful catch rule and the OVR slope. Candidate levers, in order of
   bluntness: raise `_CATCH_BIAS` (0.9 → ~1.2–1.3 puts p(catch|attempt) at
   evens below 0.5, flipping throw EV positive); add a catch-drop band that
   neither outs nor resurrects (rules-faithful: a dropped catch attempt is
   just a hit); shade p(catch|attempt) by throw quality (accuracy reduces
   catchability, giving accuracy a defensive-economy answer). Process: probe
   matrix (attribute values + posture spread + OVR slope + draw rate) before/
   after, update the WT-7 frozen winners + any frozen-seed replay pins in the
   same change, re-run champion parity (expect Defensive share to drop toward
   ~50%), document in STATUS. This also likely shrinks the go_for dominance,
   since attempts stop being free value.
2. **Contested Signing Day (design gap, medium scope).** Wire the dormant
   V2-B round system (or a lighter version) into the offseason picker so
   interest/credibility/pipeline buy real signing odds against AI competition
   — with the snipe/regret texture the recruiting fantasy needs. The
   credibility plumbing fix from this pass makes the dormant path correct to
   wire. Then flip the four recruiting terms back to mechanical.
3. **Slot-role model: wire or drop (owner decision).** Either give role fit a
   real, disclosed engine effect (e.g. slot-based opening assignments with
   archetype modifiers) or remove the role labels/liability lane entirely.
   Current state (advisory copy) is honest but inert UI weight.
4. **Attribute sheet rationalization.** Give stamina a consumer (e.g. rec
   fatigue currently keyed only on conditioning_curve; official has no
   fatigue at all) or stop displaying it as a peer of catch/accuracy; same
   call for tactical_iq. Re-key the "health check" readiness gate and staff
   stamina advice to whatever is actually consumed. The invariance pins from
   this pass will catch any silent wiring.
5. **Rec rush/posture disclosure parity.** `rush_target` is outcome-dead in
   the REC driver too (ball-target labels are event metadata only) but the
   Policy Editor only discloses announced-only on officials. Either wire rec
   rush targeting or extend the disclosure to rec careers.
6. **Even-rung draw texture (WT-20-adjacent).** 23–31% draws at even strength
   on officials is honest but reads flat; the throw-clock / No-Blocking
   enforcement decision (open owner item) is the real fix — fold the draw
   ceiling gate into that milestone.

---

## 8. Open issues carried (not new, reconfirmed)

- WT-20 Official Live Rules: still owner-gated (unchanged).
- Promises lane: backend-complete, no UI, feeds nothing (STATUS #5).
- Department orders other than dev_focus: flavor-only (STATUS #6).
- AI-symmetric development balance probe: still not re-run (first-hour pass
  open item).
- `test_server_save_boundary` order-dependent flake: not observed in this
  pass's full run (exit 0), still worth the known-flake caveat.
