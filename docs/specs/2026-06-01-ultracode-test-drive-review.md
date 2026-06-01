# Ultracode Test-Drive — Independent Review

Date: 2026-06-01
Reviewer pass: adversarial verification of the "ULTRACODE Test-Drive — Final Report"
Method: authoritative gates + linchpin web re-fetch + WT-6 red-green run by the
reviewer directly; 7-agent adversarial fan-out for per-item code grounding (treated
as leads, every contradiction re-checked against the file by hand).

## Verdict (a gradient, not a thumbs-up)

**The hard discipline held; the bookkeeping did not.** The single most consequential
act — refusing to ship WT-20 (No Blocking enforcement) because its keystone parameter
is unsourced — is **correct and independently re-confirmed**. Gates are genuinely green,
nothing was committed, and the Python/engine fixes (WT-1, WT-2, WT-6) are faithful and
test-backed. WT-6's exact red-proof reproduces to the integer.

But the report makes **several verification overclaims of exactly the kind the protocol
exists to prevent**, and one **player-facing lie (pre-existing, untouched this session)
sits undisclosed in a surface the sweep covered**. The report's "Honest gaps" section is
genuinely above-average (it discloses
WT-20-not-done, no browser walk, frontend-not-executed) — but it does *not* disclose the
fabricated test cases, the surviving 4th lie, the un-shipped proximity interim, or a test
miscount.

Net: **Python items verified by execution; frontend items are code-correct but
asserted-not-executed; and four specific claims are overstated.**

## Confirmed true (reviewer observed the output directly)

| Claim | Evidence |
|---|---|
| `pytest -q` → 1131 tests, exit 0 | all-dots output, count reconciles against every % marker, exit 0 ⟺ no failures |
| `npm run build` clean | `tsc -b && vite build`, exit 0, 84 modules |
| `npm run lint` clean | `eslint .`, exit 0 |
| Nothing committed | HEAD still `4f2e983`; all WT work unstaged (re-confirmed after red-green) |
| WT-20 keystone genuinely OPEN | independent WebFetch of usadodgeball.com/rules: No-Blocking mechanics + residual-tie both "not addressed" |
| WT-1 target-less labels | faithful; 6 tests; headshot/clock read as fouls, miss reads clean; `open space` framing banned (test:25-28) |
| WT-2 headline game points | faithful; 7 tests; `test_…0_0…` (test:46) asserts 0-0 draw not 0-3; 1-0 guard (test:86) bans "shutout/total control" |
| WT-4 gate-detail fix (backend) | **substantively correct**: week_briefing.py:118-181 — all 6 gates state-aware; every positive string gated behind the same `ready` boolean; no leak |
| WT-6 catch-posture fix | one-line change (official_engine.py:691 `policies[offense_team]`→`policies[target_state.team_id]`); **red-green run: revert → `GO=0 SAFE=152` fail, restore → pass** — exact magnitudes reproduce |
| Balance AFTER numbers | `tier_engine_health_probe --driver both --trials 400` reproduces official 36.0/49.5/63.2/72.0, slope +36.0pp, floor 72%, draws 23.1% — byte-exact |
| W0 doc claims (a)(b) | `three_per_side` hardcoded (no_blocking.py:29, official_engine.py:595) and **latent** (translate_events drops non-SEQUENCE; collect_official_metadata test-only; replay_contracts has no `ball_reset`; frontend grep empty) — all accurate |

## Overclaims & gaps the report did not disclose (severity-ranked)

1. **[Faithfulness — HIGH] A 4th residual lie survives in a WT-4 surface, undisclosed.**
   `PreSimDashboard.tsx:252` (and :246) renders **"Current approach aligns with the
   opponent profile."** on the aligned path (under "Profile aligned.", :487/:489). But
   `compute_staff_recommendation` (week_briefing.py:35-70) reads **only `recent_results`
   + `at_risk_count`** — its own docstring says *"NEVER the player's currently-selected
   plan"* and it never reads opponent data. The honest backend reason is *"Your plan fits
   the situation."* The frontend substitutes an opponent-comparison the data never made.
   This is the exact ADR-0002 misattribution class the report says the fan-out exists to
   catch — present in the same file the trust feature touches, on the default (no-conflict)
   path. **Provenance: pre-existing.** `git diff HEAD` shows PreSimDashboard.tsx changed
   +12/-1 this session (the gate-detail visibility block at :722-735), and **none** of those
   lines touch the planRead/scoutRead readout — so the misattribution was *missed by the
   sweep and left undisclosed*, not introduced by it. It still undercuts the report's WT-4
   "increase trust" framing: a trust surface that ships a live misattribution defeats its own
   purpose, whether the lie is new or inherited.
   **RESOLVED 2026-06-01 (this pass):** all three render sites
   (PreSimDashboard.tsx scoutRead:242, planRead:248, scouting-note callout:679) now surface
   the honest `recommendation.reason` instead of the hardcoded opponent-profile string;
   conflict-path copy unchanged. Backend invariant pinned by a new regression guard,
   `tests/test_week_briefing.py::test_aligned_recommendation_reason_makes_no_opponent_claim`
   (red-green verified: injecting the lie at week_briefing.py:312 turns it red). Full suite
   1132 passed (exit 0); `npm --prefix frontend run build` + `lint` clean. Note: the prompt
   named only :246/:252 — a third instance at :679 was found by grep and also fixed.
   Known-minor (intentionally not addressed, to avoid scope creep): when `scoutGapRead` is
   empty (unscouted / early-season, `ovrGap === null`) the :679 "Scouting note." callout now
   reads the form/health `reason` under a scouting header — honest but topically mixed; a
   scouting-specific honest fallback ("No scouting edge to report yet.") would read cleaner
   if this copy is revisited.

2. **[Verification overclaim — HIGH] WT-5 "9+8 behavioral cases" do not exist.**
   The string appears nowhere in the repo; there is no frontend test runner
   (`frontend/package.json` scripts = dev/build/lint/preview only; zero `*.test/*.spec`
   under `frontend/src`). The de-keying itself is real and correct (scoreboard
   matchResult.ts:38 + MatchReplay.tsx:248,300 all route through `rulesetNames.ts`), but
   the "9+8 cases" are enumerated reasoning at best — neither written as tests nor executed.

3. **[Verification overclaim — MEDIUM] WT-4 fail-state copy has zero automated coverage.**
   `tests/test_week_briefing.py` + `tests/test_readiness_gates.py` (32 passing) assert only
   `ready`/`is_ready_to_lock`/`next_issue` — **no test asserts any gate `detail` string**.
   The fix is real but code-read-verified only; the report's per-item proof implies more.

4. **[Doc accuracy — LOW] W0/ADR "stop displaying proximity_modifier ships now" is not in code (but no live false-proof).**
   `proximity_modifier` is produced only by engine.py/rec_engine.py (never the official
   engine); the display site `_tactic_context` (replay_proof.py:524-545) and `rec_engine.py`
   are **unchanged this session**. No code implements the claimed interim, and the W0 doc
   self-contradicts at line 98 ("which *is* shown"). **Severity closed:** `rush_context` is
   populated only by engine.py (195,232) / rec_engine.py (574,597) via rec_adapter.py —
   **never the official path** — so the copy surfaces only in rec/legacy replays, where the
   opening rush is a real computed mechanic and the note is faithful. The un-shipped interim
   is therefore a doc-accuracy error, **not** a live false-proof in official matches.

5. **[Bookkeeping — LOW] WT-3 test count off by one.** `tests/test_broadcast_official_scoreline.py`
   has exactly **6** `def test_` (lines 20,32,44,55,79,90); report claims 7 (`_hook`/`_conn`
   are helpers). Substantive (a)/(b) — game points + legacy-DB fallback — are correct.

6. **[Doc accuracy — LOW] Opening-rush wording.** W0 doc says "no separate opening-sprint
   section"; a re-fetch labels the same possession-rule content an "Opening Rush (Cloth)"
   section. Substance identical (a possession rule, not a sprint/activation mechanic), so the
   gate decision is unaffected — conservative-direction imprecision only.

7. **[Cleanliness — LOW] Duplicate imports.** `replay_service.py:31-54` repeats the same
   8-line import block three times (a botched edit in a WT-1 file). Harmless (Python dedups;
   suite green) but should be cleaned.

8. **[Minor] WT-1 over-specification.** The report's quoted ban string "threw into open space"
   is a code comment (voice_playbyplay.py:73), not a banned literal; the test bans the broader
   substring `open space`. Intent holds; the quote is a paraphrase.

## Recommendation

- The verified slice (WT-1/2/3/4/5/6 code + the WT-20 refusal) is sound to keep; **do not**
  read the report's frontend "behavioral cases" as executed verification.
- Fix the line-252 misattribution before the WT-4 trust feature is considered shippable — a
  trust feature that ships a fresh misattribution defeats its own purpose.
- Correct the W0/ADR "ships now" wording for the proximity interim (either ship the code or
  mark it pending), the WT-3 count, and the opening-rush phrasing.
- Clean the duplicate import block in replay_service.py.

## Scope of this review

Covered: the four global gates, the WT-20 primary-source refusal (re-fetched), and WT-1/2/3/4/5/6
plus the W0 doc's in-repo code claims. **Not** independently audited: WT-7 (DRAMATIC_CATCH
context-gating — presentation-only, gated, and not in the report's per-item results table) and
the `official_match_probe` foam/cloth split (only `tier_engine_health_probe` was re-run). No live
browser walk was performed — frontend behavior was checked by reading source + build/lint, the same
limitation the report itself discloses.

## Cleanup pass — resolved 2026-06-01

After the review, a cleanup pass closed the actionable findings (full suite **1133 passed, exit 0**;
frontend build + lint clean):

- **#1 (misattribution lie) — FIXED.** All three render sites surface `recommendation.reason`;
  new regression guard `test_aligned_recommendation_reason_makes_no_opponent_claim` (red-green verified).
- **#3 (WT-4 zero detail coverage) — CLOSED.** New guard
  `test_unmet_gate_detail_states_the_blocker_not_a_satisfied_assertion` pins that a red gate's detail
  is the blocker string, not a satisfied-state assertion (red-green verified by injecting the lie).
- **#4 (proximity "ships now") — CORRECTED** in this W0 doc's sibling
  (`2026-06-01-workflow0-primary-source-rule-verification.md`): the claim now states the inert copy
  surfaces only in the rec/legacy path (no official-mode false-proof), not that a code interim shipped.
- **#7 (duplicate imports) — FIXED.** `replay_service.py` import block collapsed 3×→1×.

Remaining open **by design** (no code to change — report-wording / owner's-doc items): #2 (WT-5 "9+8
behavioral cases" — needs a frontend test runner to ever be real), #5 (WT-3 count 6≠7), #6 opening-rush
doc phrasing, the WT-1 quoted-string over-specification, and the ADR-0002 amendment (owner's doc). The
line-679 "Scouting note." topical-mismatch known-minor (above) is also left intentionally.
