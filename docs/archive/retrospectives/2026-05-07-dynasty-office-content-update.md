# V8-V10 Dynasty Office Content & Narrative Update

Date: 2026-05-07
Role: Lead Procedural Content & Narrative Designer
Target: Post-V8-V10 Polish and Hardening Phase
Focus: Dynasty Office (Recruiting, League Memory, Staff Market)

## Project Trajectory

- **WHERE WE WERE:** The Dynasty Office shipped in a "thin but honest" state. The loops for recruiting promises, league memory, and staff hiring are functional. However, the narrative flavor—staff names, department voices, empty states, and promise descriptions—is highly repetitive and mechanically literal.
- **WHERE WE ARE:** The current implementation correctly separates domain logic from UI presentation. However, text generation in `dynasty_office.py` relies on very small lists (e.g., 8 first names, 8 last names, 1 static sentence per department voice).
- **WHERE WE ARE GOING:** For the upcoming Polish phase, we need to inject reusable, data-shaped sports-management flavor. We will expand the staff generator pools, add variety to department voices, enrich the empty states for League Memory, and prepare new promise templates without breaking the "simulation honesty" rule (no hidden buffs or unlogged outcomes).

## Source Context

- **Inspected files:** `src/dodgeball_sim/dynasty_office.py`, `docs/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`, `docs/specs/MILESTONES.md`.
- **Current Data Shapes:** Staff candidates use deterministic RNG seeded by `root_seed`, `season_id`, and `department`. Content is mostly static dictionaries or small tuples.

## Ready-to-Use Payloads

These payloads are designed as Python literals that can cleanly replace the existing tuples and dictionaries in `src/dodgeball_sim/dynasty_office.py`.

### 1. Expanded Staff Name Banks

Replaces the 8-item lists in `_staff_first_name` and `_staff_last_name` to reduce repetition across long saves.

```python
STAFF_FIRST_NAMES = (
    "Ari", "Blair", "Carmen", "Dev", "Eli", "Juno", "Morgan", "Sasha",
    "Taylor", "Jordan", "Casey", "Riley", "Avery", "Quinn", "Peyton", "Skyler",
    "Dallas", "Reese", "Rowan", "Ellis", "Kendall", "Micah", "Emerson", "Finley"
)

STAFF_LAST_NAMES = (
    "Vale", "Cross", "Hart", "Rook", "Sol", "Pike", "Ives", "Chen",
    "Gaines", "Mercer", "Vance", "Sutton", "Hayes", "Frost", "Graves", "Cole",
    "Bridges", "Stark", "Rivers", "Banks", "Shaw", "Kerr", "Brooks", "Glover"
)
```

### 2. Department Voices

Currently, each department has a single string. To make staff feel like distinct personalities, we can shape this as a list of options per department, which the deterministic RNG can select from.

```python
STAFF_VOICES = {
    "tactics": [
        "Make every matchup leave evidence.",
        "Execution beats raw talent when the plan is clear.",
        "We dictate the tempo, they react to the pressure.",
        "A rigid lineup is a vulnerable lineup."
    ],
    "training": [
        "Growth needs visible reps.",
        "Potential means nothing without court time.",
        "Drills build the floor; match minutes build the ceiling.",
        "We measure progress in successful catches, not promises."
    ],
    "conditioning": [
        "Late-match legs are earned early.",
        "Fatigue makes cowards of us all.",
        "We win the war of attrition in the practice gym.",
        "Stamina is the shield that protects our strategy."
    ],
    "medical": [
        "Availability is the quiet edge.",
        "I tell you who can play; you tell them how.",
        "Managing overuse is managing the season's fate.",
        "Don't risk a career for a single regular-season win."
    ],
    "scouting": [
        "Fit beats noise.",
        "We draft for the liabilities we can hide and the traits we can use.",
        "The tape never lies, even when the public hype does.",
        "I find the ceiling; you build the floor."
    ],
    "culture": [
        "Promises become program memory.",
        "Trust is built on fulfilled expectations.",
        "A fractured locker room will drop the ball when it matters most.",
        "Recruits watch how we treat our veterans."
    ]
}
# Integration Note: Update `_staff_voice(department, rng)` to use `rng.choice(STAFF_VOICES.get(department, [...]))`.
```

### 3. Enriched Empty States (League Memory)

Replaces the literal empty state strings in `_league_memory_state` with text that maintains honesty but adds management flavor.

```python
# In `_league_memory_state`
EMPTY_STATE_RECORDS = "The league record books are currently empty. History begins when the first records are ratified."
EMPTY_STATE_AWARDS = "The trophy cabinet awaits. Season awards will be decided and displayed after the offseason closeout."
EMPTY_STATE_RIVALRIES = "True rivalries require history. Bad blood will build here after repeated, high-stakes match results."
```

### 4. Promise Typology Expansion (Proposed)

Currently, we only have three promise options. I propose three more that fit within the existing evaluation mechanics (Command History, Roster data, Match Stats) without requiring engine changes.

**Current:**
- `early_playing_time`
- `development_priority`
- `contender_path`

**Proposed Additions (For future implementation):**
- `roster_security`: "Promise they will not be cut or traded before their sophomore year." (Checked against roster persistence).
- `tactical_focal_point`: "Promise to center the team's tactics around their archetype." (Checked against CoachPolicy's `target_ball_holder` in command history).
- `championship_standard`: "Promise a deep playoff run or championship appearance." (Stricter version of `contender_path`).

## Tone Guidelines for Future Engineers

- **Simulation Honesty:** Never imply that a staff hire gives a +10% win chance unless the engine literally reads that data and logs it. Use terms like "framing", "clarity", and "recommendations" for UI-only effects.
- **Gritty Management Reality:** Frame the Dodgeball Manager world as an intense, administrative, and strategic endeavor. Use words like *evidence*, *reps*, *attrition*, and *accountability*.
- **Explicit Boundaries:** If a system is thin, own it. "No hidden promise effect is applied until a promise is saved" is a great example from V8-V10 that we should keep.

## Integration Notes

- **Action Required:** A developer on the `feature` or `polish` branch should update `src/dodgeball_sim/dynasty_office.py` to use the expanded `STAFF_FIRST_NAMES`, `STAFF_LAST_NAMES`, and RNG-driven `STAFF_VOICES`.
- **Database Safety:** Since names are deterministic based on `root_seed`, changing the pool of names *will* change the generated names of unhired staff on existing saves. This is acceptable for un-persisted candidates, but `department_heads` is already persisted in the SQLite DB, so existing hired staff will retain their old names. No DB migration is necessary.