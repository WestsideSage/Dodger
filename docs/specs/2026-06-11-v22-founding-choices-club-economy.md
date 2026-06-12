# V22 — Founding Choices & Club Economy (2026-06-11)

Owner directive: the create-a-club flow is the oldest untouched path in the
game. Buff it so a founder knows exactly what they are bringing in — and use
it to introduce the game's first economy layer.

Owner decisions (2026-06-11, recorded verbatim intent):

1. **Founding staff hiring = shared pool + budget.** "Up the stakes and add a
   budget component to the game now… not extremely detailed in the way that
   you have to manage literally every single CENT, but make it so that there
   is a financial management aspect to the game" (Teamfight Manager 1/2 cited
   as the fun reference).
2. **Wire all six departments** — staff-head ratings must DO something
   (today only training is mechanical).
3. **Fresh founding pool per save** (the pool was hardcoded to seed 12345 —
   every new club drafted the same 25 prospects).
4. **Natural ceilings + arcs for founders** (drop the 70 floor; same V19
   rule as every other signing, trajectory arcs included and shown openly).

Plus the original asks: founding-picker legibility (ratings, ceiling,
archetype tooltips — "you can't even see what exactly their archetype even
does"), and **much wider name pools** ("tired of seeing so many Ferns, Remys,
Mikas… many of these older systems have not been touched since the game was
first brainstormed").

## Phases

### Phase 1 — Generation refresh (names + founding pools + ceilings)
- New `names.py`: wide curated pools (~200+ first / ~300+ last names,
  culturally broad), shared by prospect gen, rookie gen, staff gen.
- Unique-name picker reworked to FIXED RNG consumption that scales (the
  current implementation shuffles the full first×last combo list per name —
  O(56k) per draw at the new pool sizes).
- Founding pool seeded per creation: the wizard holds a creation seed that
  drives `GET /api/saves/starting-prospects?seed=` and rides the build POST,
  so picker and builder always agree.
- Founding ceilings: `min(100, max(ratings)+8)` (no 70 floor) + the same
  hidden-trajectory arcs every prospect rolls; arcs persist via
  `save_player_trajectory` at creation exactly like signings.
- **Universe change**: name draws and pool seeds shift every generated
  rating downstream. Pinned witnesses (signing-band hidden gem, founding
  names in tests) are re-derived; golden logs untouched (engine inputs from
  fixtures, not generated pools).

### Phase 2 — Club treasury + season finances (economy core)
- Treasury: integer thousands ("$420k"), user club only — AI club finances
  stay abstracted (disclosed in the rules copy). State key `club_treasury_k`.
- Config block `DEFAULT_ECONOMY` (all tunable):
  - `starting_budget_k = 600` for new clubs (takeover careers seed a
    mid-table treasury, e.g. 150).
  - Season income at offseason init: league payout by final table position
    (rank 1→340 … rank 7→220, linear) + playoff bonuses (semifinal +40,
    final +80, champion +140).
  - Season expense: staff payroll = sum of head salaries (below).
- Finances surface: a line block in the offseason recap beat (income /
  payroll / net / balance) + a treasury chip in the Dynasty Office header
  and staff tab. No new ceremony beat.
- Floor rule: treasury may go negative after a bad season, but hiring is
  frozen while negative ("payroll frozen") — pressure without a bankruptcy
  spiral.
- `tools/economy_probe.py`: 10-season autopilot — a mid-table club must stay
  solvent on default staff; a tail-table club must feel the squeeze without
  spiraling below one season of payroll debt.

### Phase 3 — Founding staff hiring (budget pool) + paid staff market
- `GET /api/saves/starting-staff?seed=`: one shared pool of ~15 candidates
  spanning the 6 departments (≥2 per department, at least one cheap
  journeyman per department so filling all six is ALWAYS affordable).
  Candidate card: name (new pools), department, ratings, salary ($k/season),
  voice line, plain-language effect with the disclosed number (Phase 4's
  hooks).
- New wizard step between Coach and Roster ("Hire Your Staff", step 3 of 4):
  must fill all 6 departments within `starting_budget_k`; remaining budget
  becomes the opening treasury; live budget bar.
- Build POST gains `staff_choices: {department: candidate_id}`; created
  clubs write the chosen heads (replacing the hardcoded defaults). Takeover
  careers keep the default six.
- In-season staff market: hiring a candidate now costs (their salary joins
  payroll; the replaced head's leaves). Blocked while treasury negative.

### Phase 4 — Wire all six staff-head ratings to real effects
All effects scale linearly from rating 50 (baseline) to 99; every number is
disclosed on the hiring card and in Program Settings.
- **training** (already real): offseason dev modifier (existing formula).
- **tactics**: scales the tactics staff-focus TIQ bonus (flat +18 today →
  12 + (rating−50)/50 × 12, i.e. 12–24).
- **conditioning**: scales the conditioning-focus fatigue-drag reduction
  (flat 50% today → 35–65% reduction).
- **culture**: scales the culture-focus interest multiplier (flat 1.25× →
  1.15–1.40×).
- **scouting**: scales the Scout action's band narrowing (the fixed
  narrowing fraction becomes rating-driven); the focus week's +1 slot stays.
- **medical**: owns the age-decline mitigation slot in
  `apply_season_development`'s decline path (recovery/availability fiction);
  training keeps the growth path.
- Tests: monotonicity pin per hook (better head ⇒ measurably better effect
  through the real pipeline), plus probe sanity.

### Phase 5 — Founding draft picker legibility
- Endpoint adds age, the six display ratings, ceiling + potential tier, and
  the arc grade — openly. This is the player's own founding class; the
  recruiting fog-of-war does not apply (it never did — the endpoint already
  returns true OVR).
- Picker cards: ratings row, ceiling/tier, `CeilingGrade` badge, archetype
  `TermTip` (the journal's "no tooltip" complaint), age; the role-track
  composition guide stays.

### Phase 6 — Verify + ship
Full pytest, frontend build/lint, browser walk of the whole wizard through
the first Dynasty Office screen (treasury chip visible), STATUS update,
phase-themed commits.

## Non-goals (explicit)
- Player salaries/contracts, facilities purchases, sponsorships — future
  economy hooks, not this milestone.
- AI club economies.
- Mobile layouts (per AGENTS.md).
