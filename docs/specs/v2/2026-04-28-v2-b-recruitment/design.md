# V2-B — Recruitment Domain Model — Design Spec

**Date:** 2026-04-28
**Status:** Design approved, ready for implementation planning
**Scope:** Replace the V1 one-rookie Draft beat with a deterministic contested recruitment domain: AI club boards, sign rounds, public/private prospect evaluation, visible sniping, and a Recruitment Day UI that consumes V2-A scouting information without weakening it.

---

## 0. Relation to Prior Specs

This document is the canonical V2-B spec. It follows:

- `docs/specs/2026-04-26-v2-a-scouting/design.md` — V2-A provides prospect pool truth, private scouting state, CEILING labels, fuzzy prospect profile, and Draft Day scout accuracy reckoning.
- `docs/specs/2026-04-26-manager-mode/design.md` — V1 shipped a deliberately simple one-rookie Draft beat with no AI competition.
- `docs/specs/AGENTS.md` — all sim integrity, determinism, auditability, and no-hidden-buffs rules apply.

V2-B explicitly does not cover:

- Build a Club expansion path — V2-C.
- Expanded `CoachPolicy` tendencies — V2-D.
- Records / Hall of Fame / Rookie Preview off-season beats — V2-E.
- Playoffs — V2-F.
- Scout hiring, firing, aging, or new scouting tiers.
- Mid-season free-agent signings.

---

## 1. Goals

1. **Contested signings.** Prospects are no longer guaranteed to be available when the user clicks them. AI clubs pursue their own boards under deterministic rules.
2. **Fair sniping.** A snipe is a visible outcome of another club's needs, preferences, public evaluation, and round priority. It is not random punishment.
3. **Scouting payoff without certainty.** V2-A private information helps the user rank and prioritize prospects, but it does not guarantee access.
4. **Legible AI clubs.** Each club has stable recruitment preferences and roster needs that produce distinct boards.
5. **Idempotent Recruitment Day.** Save/resume or screen revisit never double-signs prospects or rewrites completed rounds.

---

## 2. Architecture

### 2.1 Module layout

**New module: `recruitment_domain.py`**
Owns recruitment profiles, board generation, round resolution, offer/signing resolution, and recap payloads. It is pure and has no database imports.

**Existing module: `recruitment.py`**
Remains focused on prospect/rookie generation and transaction helpers. It should not absorb AI board logic.

**Extended: `persistence.py`**
Adds additive recruitment tables and load/save helpers.

**Extended: `manager_gui.py`**
Replaces the V1 Draft beat with Recruitment Day. Adds market-risk and shortlist affordances to prospect surfaces.

### 2.2 Data model

Add recruitment persistence tables:

```
club_recruitment_profile(
    club_id TEXT PRIMARY KEY,
    archetype_priorities_json TEXT,
    risk_tolerance REAL,
    prestige REAL,
    playing_time_pitch REAL,
    evaluation_quality REAL      -- lower public-score noise only; never private scouting truth
)

recruitment_board(
    season_id TEXT,
    club_id TEXT,
    player_id TEXT,
    rank INTEGER,
    public_score REAL,
    need_score REAL,
    preference_score REAL,
    total_score REAL,
    PRIMARY KEY (season_id, club_id, player_id)
)

recruitment_round(
    season_id TEXT,
    round_number INTEGER,
    status TEXT,              -- prepared | resolved
    payload_json TEXT,
    PRIMARY KEY (season_id, round_number)
)

recruitment_offer(
    season_id TEXT,
    round_number INTEGER,
    club_id TEXT,
    player_id TEXT,
    offer_strength REAL,
    source TEXT,              -- user | ai
    PRIMARY KEY (season_id, round_number, club_id, player_id)
)

recruitment_signing(
    season_id TEXT,
    player_id TEXT PRIMARY KEY,
    club_id TEXT,
    round_number INTEGER,
    source_offer_json TEXT,
    recap_json TEXT
)

prospect_market_signal(
    season_id TEXT,
    player_id TEXT,
    signal_json TEXT,
    PRIMARY KEY (season_id, player_id)
)
```

V2-B consumes V2-A `prospect_pool`, `scouting_state`, `scouting_ceiling_label`, `player_trajectory`, and scout contribution data. Signing a prospect must use one canonical path: convert prospect truth into a `Player`, persist trajectory, mark the prospect signed, save the roster, and clear or migrate fuzzy prospect state.

---

## 3. Recruitment Model

### 3.1 Club profiles

Each club receives a deterministic recruitment profile at career creation or migration. Profiles should include:

- archetype preferences,
- roster need weighting,
- risk tolerance,
- prestige / contender appeal,
- playing-time pitch,
- public evaluation quality.

`evaluation_quality` is strictly an AI noise-control field over public prospect data. A high-evaluation club sees less noise when interpreting public OVR bands and public archetype guesses. It never grants access to the user's V2-A private scouting state, hidden prospect truth, hidden trajectory, hidden traits, or CEILING labels unless those facts are public through another explicit system.

These are visible enough for the user to understand the market. The UI does not expose exact AI board scores, but it can show broad signals such as "high interest from power-focused clubs."

### 3.2 Board generation

For each club, generate a board from:

- public prospect OVR band midpoint,
- public archetype guess,
- roster needs,
- club archetype priorities,
- risk tolerance and evaluation quality,
- deterministic evaluation noise.

The user board is not auto-generated as a hidden truth. The user sees public market info plus private V2-A scouting information and chooses manually.

### 3.3 Round resolution

Recruitment Day runs in discrete rounds.

Each round has two persisted phases:

1. **Prepare round.** Build and persist the AI offer payload for the round before the user acts. This payload includes each AI club's intended target, offer strength, ordered conflict priority, and visible reason fields. Reloading during the user's decision reuses this exact payload.
2. **User choice.** User selects one target or passes.
3. **Resolve conflicts.** Combine the user's offer with the prepared AI offers. For each prospect with multiple offers, highest `offer_strength` wins. Ties resolve by stable priority tuple: higher club need score, higher playing-time pitch, higher prestige, lower deterministic round-order value, then `club_id` ascending. The user club participates in the same tuple and receives no hidden tie advantage.
4. **Persist result.** Signed prospects leave the available pool immediately, and the resolved round payload is written before the next round can render.

If an AI club signs a prospect the user shortlisted or attempted to sign, the UI renders it as a snipe with the visible reason: club need, public fit, and round priority.

---

## 4. Determinism

All random draws use `derive_seed(root_seed, namespace, *ids)`.

Namespaces introduced by V2-B:

- `recruitment_profile`
- `recruitment_ai_board`
- `recruitment_round_order`
- `recruitment_offer_strength`
- `recruitment_market_signal`
- `recruitment_public_evaluation_noise`

Every list involved in resolution must be sorted before sampling or tie-breaking: clubs, prospects, offers, shortlists, and board candidates.

Same save state, same root seed, and same user choices must produce byte-identical boards, offers, signings, market signals, and recap payloads.

---

## 5. UI Surfaces

### 5.1 Recruitment Day

The off-season Draft beat becomes Recruitment Day:

- round timeline,
- available prospect list,
- user shortlist,
- public market risk,
- private scouting columns from V2-A,
- live AI signing ticker,
- snipe callouts,
- final recap.

### 5.2 Scouting Center additions

Prospect board adds recruitment-facing fields:

- shortlist marker,
- public interest,
- likely competition,
- market-risk signal,
- signability / playing-time fit where available.

### 5.3 Prospect Profile additions

Fuzzy prospect profile gains a market context panel. It shows public interest and user shortlist status without revealing hidden AI board internals.

---

## 6. Edge Cases

- **User passes every round:** AI clubs continue signing under their profiles.
- **Target already signed:** UI disables the action and shows who signed the player.
- **Roster full:** Club cannot submit offers unless implementation includes an explicit release path. V2-B does not require releases.
- **No useful board candidates:** AI club passes.
- **Save mid-round:** prepared AI offer payloads are already persisted before the user chooses. Reloading the screen cannot reroll AI targets, offer strengths, or conflict priority. Only the user's still-unsubmitted choice remains pending.

---

## 7. Testing

Required coverage:

- Pure board-ranking tests.
- Club preference and roster-need sensitivity tests.
- Offer resolution and tie-break determinism tests.
- Snipe test with visible reproducible cause.
- Save/resume during recruitment rounds.
- Persistence migration and idempotent write tests.
- Canonical prospect-to-player conversion test that proves V1's one-rookie signing path is retired or routed through the same conversion helper.
- UI helper tests for rows, market signals, ticker entries, and recap payloads.
- Phase 1 golden regression unchanged.
- V2-A scouting determinism unchanged.

---

## 8. Acceptance Criteria

V2-B ships when:

1. Recruitment Day replaces the V1 one-rookie Draft in Manager Mode.
2. AI clubs generate distinct deterministic boards.
3. User can shortlist prospects and attempt signings across rounds.
4. AI clubs sign prospects under persisted round rules.
5. Snipes are visible and explainable.
6. Prospect signing uses one canonical conversion path.
7. Save/resume cannot double-sign prospects or reroll completed rounds.
8. Recruitment records persist and support recap display.
9. Phase 1 golden regression remains unchanged.
10. All V2-A scouting tests remain green.

---

*End of V2-B Recruitment Domain Model design spec.*
