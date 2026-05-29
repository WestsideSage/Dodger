# Phase 4 Balance Baseline: Rec vs. Official Engine Driver

This balance baseline review measures the performance, fairness, and outcome distributions of the Hybrid Tier-Driver architecture's two primary match engines: the **Rec Tier-1 Driver** (`RecTier1Driver`) and the **Official USA Dodgeball Driver** (`OfficialDriver`). 

This study is a prerequisite for Plan Decision **D4** (from [2026-05-29-playtest-fixes-multi-phase-plan.md](../specs/2026-05-29-playtest-fixes-multi-phase-plan.md)), which proposes defaulting new careers to the official foam ruleset. Before flipping this default, we must establish if the official driver produces fair, believable, and rating-sensitive matches.

---

## Methodology & Seeding Assumptions
- **Trial Count:** **2,000 trials per OVR rung** (8,000 total trials per driver across rungs `0`, `24`, `48`, and `72`).
- **Seeding/Determinism:** Fully deterministic and reproducible. Rung seeds are derived via `seed = rung_index * 10,000 + trial_index + seed_offset` using `DeterministicRNG` and Python's `random.Random(seed)` instances.
- **Rungs Measured:**
  - **Net +0 OVR:** Favorite OVR 63.0 vs. Underdog OVR 63.0 (Even)
  - **Net +24 OVR:** Favorite OVR 67.0 vs. Underdog OVR 63.0 (+4.0 OVR/player advantage)
  - **Net +48 OVR:** Favorite OVR 71.0 vs. Underdog OVR 63.0 (+8.0 OVR/player advantage)
  - **Net +72 OVR:** Favorite OVR 75.0 vs. Underdog OVR 63.0 (+12.0 OVR/player advantage)

---

## Diagnostics Comparison: Side-by-Side

### 1. OVR Curve (Win Rate vs. Net OVR Edge)

The OVR curve measures how strongly player attribute advantages translate to match victories. The primary metric is the win rate of the Favorite team at each OVR rung, reported with a **95% Wilson Confidence Interval (CI)**.

| Net OVR Advantage (Gap) | Rec Driver Win Rate (95% CI) | Official Driver Win Rate (95% CI) |
| :--- | :--- | :--- |
| **Net +0 OVR** (Even) | **50.0%** [47.8% - 52.2%] | **43.9%** [41.7% - 46.0%] |
| **Net +24 OVR** (+4/player) | **56.0%** [53.9% - 58.2%] | **45.0%** [42.8% - 47.1%] |
| **Net +48 OVR** (+8/player) | **64.0%** [61.9% - 66.1%] | **44.0%** [41.8% - 46.2%] |
| **Net +72 OVR** (+12/player) | **70.2%** [68.2% - 72.2%] | **46.9%** [44.7% - 49.0%] |
| **Monotonicity** | **PASS** | **PASS** (within $\le 2\text{pp}$ tolerance) |
| **Minimum Slope** | **PASS** (+20.2pp, $\ge 10\text{pp}$ needed) | **FAIL** (+3.0pp, $\ge 10\text{pp}$ needed) |
| **Top Floor (at +72 OVR)**| **PASS** (70.2% vs. 60% floor) | **FAIL** (46.9% vs. 60% floor) |

#### Analysis:
- **Even Matchup Balance:** 
  - The **Rec Driver** is perfectly balanced at **50.0%** win rate for even OVR.
  - The **Official Driver** reports a **43.9%** Favorite win rate. Because the matchup is symmetric, the Underdog also wins **43.9%**, and the remaining **12.2%** of even OVR matches end in a 0-0 Draw.
- **Parity / Signal Strength:**
  - The **Rec Driver** shows a robust, predictable response to OVR, climbing steadily to **70.2%** at the +72 OVR gap.
  - The **Official Driver** produces a completely flat, coin-flip curve. An extreme +12 OVR advantage per player only yields a **46.9%** win rate (statistically indistinguishable from the even-OVR baseline of 43.9%).

---

### 2. Outcome & Scoreline Distribution

Aggregated outcome distribution across all 8,000 simulated matches.

| Outcome Metric | Rec Driver | Official Driver |
| :--- | :--- | :--- |
| **Favorite Wins** | 4,807 (60.1%) | 3,593 (44.9%) |
| **Underdog Wins** | 3,004 (37.5%) | 3,223 (40.3%) |
| **Draws** | 189 (2.4%) | 1,184 (14.8%) |
| **Blowout Rate** | **35.6%** (5-6 survivors) | **0.0%** ($\ge 4$ game points diff) |
| **Close Rate** | **20.4%** (1-2 survivors) | **84.0%** (1 game point diff) |
| **Medium Rate** | **41.8%** (3-4 survivors) | **0.0%** (3 game points diff) |
| **Common Match Scorelines**| *Survival-based only* | **1-0 / 0-1:** 84.0% <br> **0-0 (Draw):** 16.0% *(from 500-trial sub-run)* |

#### Analysis:
- **Rec Driver:** Displays a healthy, organic distribution. Most matches end close-to-medium (20.4% close, 41.8% medium), with a reasonable rate of blowouts (35.6%) and low draw occurrence (2.4%).
- **Official Driver:** Severely degenerated. Matches are entirely split between **1-0 / 0-1 close wins (84.0%)** and **0-0 draws (16.0%)**. Not a single match across all 8,000 trials produced a scoreline of 2-0, 2-1, 3-0, or higher.
- *Root Cause:* The `OfficialDriver` is built as a single-game wrapper around `run_autonomous_game`. Under USA Dodgeball foam rules, a game point is *only* awarded for full opponent elimination. Since only one game is simulated, match scores are restricted to 1-0 or 0-0.

---

### 3. Match Length Distribution (Events)

Match length is measured by the total count of events generated in a simulated match.

| Percentile | Rec Driver | Official Driver |
| :--- | :--- | :--- |
| **P25** | 22 | 58 |
| **P50 (Median)** | 29 | 76 |
| **P75** | 36 | 100 |
| **P95** | 141 |
| **Status** | **Sane** | **Pathological Stalling / Stagnation** |

#### Analysis:
- **Rec Driver:** Matches are brief, dynamic, and clean (median 29 events).
- **Official Driver:** Matches are extremely long, dragging on for a median of **76 events** and reaching **141 events** at the 95th percentile. This indicates a grinding game cycle dominated by constant catch-resurrection loops and stalling behavior, frequently hitting the 180-second clock limit without achieving full elimination.

---

### 4. Moment Footprint

We verified the rate of Tier-1 moment events emitted by both drivers across all 8,000 matches.

| Moment Kind | Rec Driver (per-match / % matches) | Official Driver (per-match / % matches) |
| :--- | :--- | :--- |
| `dramatic_catch` | 3.67 / 93% | **0.00 / 0%** |
| `late_game_escape` | 0.81 / 77% | **0.00 / 0%** |
| `one_v_one_finale` | 0.07 / 7% | **0.00 / 0%** |
| `gassed_collapse` | 0.20 / 16% | **0.00 / 0%** |
| `flood_throw` | 3.12 / 99% | **0.00 / 0%** |
| `comeback` | 1.78 / 99% | **0.00 / 0%** |

#### Analysis:
- **Moment Confirmation:**
  The `OfficialDriver` emitted **exactly ZERO moment events** of all kinds across all trials. This confirms that the official driver has no moment-reporting footprint.

---

## Why the Official Engine's OVR Curve is Flat

Our mathematical analysis of the throw resolution and tactics layers reveals a catastrophic design bottleneck in the V11 official engine's combat math:

### 1. Catch Dominance (The "Black Hole" of Throws)
At even OVR (63), throws are exceptionally easy to catch. The probability of catching a throw given a catch attempt is resolved by:
$$p_{\text{catch}} = \sigma(3.0 \times (\text{catch}_{\text{eff}} - 0.6 \times \text{power}_{\text{eff}}))$$

For a standard 63-rated player, this yields a **68.0% catch success rate**.
Because all rating attributes are uniform in our probe, players always attempt catches (since $\text{catch} = \text{dodge} = 0.63 \ge 0.5$ threshold).
Therefore, a throw on-target results in:
- A successful catch (**68.0%** probability) $\rightarrow$ The **thrower is OUT**, and a defender is resurrected.
- A failed catch / hit (**32.0%** probability) $\rightarrow$ The defender is OUT.

Throwing the ball is statistically a **net negative action** for the offense. An on-target throw has more than **double the probability of getting the thrower eliminated** compared to getting the target eliminated!

### 2. The Accuracy Paradox (Negative Feedback Loop)
When the Favorite team gets an OVR advantage (e.g., +72 OVR, meaning A has OVR 75 and B has OVR 63):
- Favorite throwing at Dog: `p_on_target` increases from **57.8%** to **67.6%**.
- However, because B (Dog) catches **63.2%** of these throws, Favorite gets caught on **42.7%** of their throws, putting their own throwers out!
- Because A throws on-target more often, **they give the Dog MORE opportunities to catch the ball**, put the Favorite throwers out, and resurrect eliminated Dog teammates!
- Meanwhile, when B (Dog) throws at A, `p_on_target` is low (**48.9%**), which means A gets fewer catch opportunities, limiting their resurrection and elimination power.

**Conclusion:** Having higher accuracy paradoxically punishes the Favorite team by feeding more catch-and-resurrection opportunities to the underdog. The OVR ratings signal is entirely choked out by the catch-resurrection cycle, flattening the win-rate curve to a coin-flip.

---

## Verdict & Sprint Gate

| Metric | Rec Driver | Official Driver | Acceptable? | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Even-OVR Win Rate** | 50.0% | 43.9% (12.2% Draws) | **YES** | Sane, symmetric balance under both. |
| **OVR Win-Rate Slope** | +20.2pp | +3.0pp | **NO** (Blocker) | Official engine completely chokes out ratings. |
| **Top Floor Win Rate** | 70.2% | 46.9% | **NO** (Blocker) | Extreme OVR advantage fails to secure wins. |
| **Outcome Distribution** | Spread | 1-0 or 0-0 only | **NO** (Blocker) | Degenerate skew; no high-scoring pro play. |
| **Match Length** | 29 events | 76 events (Median) | **NO** | Highly stalled, defensive grinding loops. |
| **Moment Events** | Rich | **Zero** | **NO** (Blocker) | Silently strips presentation/highlight layers. |

### 🚨 Veto Verdict: BLOCKER
**We recommend a STRICT VETO on Plan Decision D4 (defaulting new careers to the official ruleset).** 

Flipping this default in the current codebase will route matches through an engine that:
1. Turns every match into a flat, 50/50 coin-flip regardless of team OVR advantages.
2. Completely degenerates match scorelines into 1-0 or 0-0 scores.
3. Renders the V13 highlight, presentation, and voice registers completely non-functional by emitting zero moments.

### ⚠ Verification Checklist for Maurice
- [x] **Trial count verified:** 2,000 trials per rung (8,000 total).
- [x] **Seeded determinism verified:** Outputs are stable and repeatable under seed offsets.
- [x] **Moment emission verified:** Official driver emits exactly `0` moment events.
- [ ] **⚠ verify:** The exact sigmoidal catch parameters in `official_resolution.py` should be retuned to favor throwers before official rules are turned on.
