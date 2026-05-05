# V3 Content Update — Lead Procedural Content & Narrative Designer

> Codename: **Graceful Spark**  
> Role: Lead Procedural Content & Narrative Designer  
> Date: 2026-04-29  
> V_CURRENT: V3 (Experience Rebuild) → V_NEXT: V4 (Web Architecture Foundation)

---

## Project Trajectory

### WHERE WE WERE

Dodgeball Manager shipped V3 with a functional Manager Mode loop, scouting, recruitment, playoffs, and an off-season ceremony. The copy-quality tooling enforced ID-free display names and correct capitalization, and recruit classes gained deterministic uniqueness. However, the underlying content pools were still operating at prototype scale:

- **Player names:** 10 first names × 10 last names = 100 possible full names. In a league of 8 clubs × 9 roster slots = 72 players, collisions were statistically near-certain by season two. The V3 name-uniqueness fix added a numeric fallback suffix (`Rin Voss #2`) rather than expanding the source pool.
- **Team names:** 12 base names × 7 suffixes = 84 combinations. Procedural leagues could produce "Aurora Pilots" twice.
- **News headlines:** One fixed template per category. Every upset read identically. Every retirement used the same phrasing. Repetition killed the illusion of a living league.
- **Nickname prefixes/suffixes:** 4 entries per archetype. With 6 archetypes × 4 prefixes × 4 suffixes = 96 possible nicknames, repeat monikers arrived within the first draft class.
- **Club lore:** Zero. Teams had names, colors, and coach policies but no backstory, no city identity, no rivalry framing beyond a raw numeric score.
- **Random events:** None. The offseason ceremony had ten fixed beats, and the in-season wire carried only match-driven headlines. No narrative surprise was possible.

The simulation was mechanically honest but narratively silent.

### WHERE WE ARE

This document delivers the first full content payload for Dodgeball Manager. It introduces:

1. **Expanded name banks** — 64 first names, 64 last names, covering diverse aesthetic registers while maintaining the league's slightly futuristic, genre-adjacent feel.
2. **Expanded nickname vocabulary** — 8 prefixes and 8 suffixes per archetype (was 4), tripling the combinatorial space.
3. **Expanded team name pools** — 24 base names and 22 suffixes for procedural league generation.
4. **Multi-variant headline templates** — 4–6 templates per headline category, enabling the wire to feel varied across a season.
5. **12 random event scenarios** — modular JSON structs with prompt text, choices, and mechanic-hint mappings for future implementation.
6. **8 canonical club lore entries** — cities, taglines, founding lore, and rivalry pairings for the default league.
7. **Tone guidelines** — concise rules governing voice, register, and what the copy is and is not allowed to claim.

### WHERE WE ARE GOING

V4 targets web feature parity with the V3 Tkinter app. The React frontend already has `server.py` serving the same persistence and franchise layers. The first V4 surfaces that need this content are:

- **League Wire panel** — will rotate multi-variant headline templates; needs the full template array.
- **Player cards** — archetype titles and nicknames rendered in the web club browser; needs the expanded nickname vocabulary.
- **Club browser** — taglines, colors, and home regions visible on hover; needs club lore JSON.
- **Prospect scouting cards** — full names for incoming recruit classes; needs the expanded name pools to prevent visible collisions for several seasons without the numeric-suffix fallback.

V5 and beyond will be able to wire the random event scenarios into the offseason ceremony and in-season hub once the event-dispatch infrastructure is designed. These scenarios are ready to reference from a sprint plan.

---

## Tone Guidelines

> These rules govern all player-facing copy in Dodgeball Manager. They apply to headlines, event prompts, award text, match reports, and UI labels.

**Voice register:** Fictional league office wire. Think a dry, slightly sardonic sports bureau that takes the game seriously even when the situation is absurd. Not corporate-safe but not juvenile. The humor comes from specificity, not exaggeration.

**Stats anchor every claim.** Never imply a player is elite without citing a data point. Never describe a match as "close" — give the score. Never call an upset "shocking" — give the OVR gap.

**Fragments are allowed in headlines.** `"Upset Alert:"` prefix style is established and consistent. One strong fragment beats a weak full sentence.

**Exclamation points:** Maximum one per headline block, and only if the event genuinely warrants it. A record broken = maybe. A routine recap = never.

**Clichés:** Allowed only when used deliberately and sparingly. `"Hangs up the jersey"` is acceptable once per retirement in a career. Repeating it every retirement makes it invisible.

**Player reference:** Last name only in headlines (`Voss eliminates three`). Full name on first reference in body text, last name thereafter.

**Club reference:** Full name on first use in a session or article. Acceptable to abbreviate to nickname after that only if one has been established in lore (`The Jets`, `The Storm`).

**Numbers:** Always specific. `"a 12.3 OVR gap"` not `"a big gap"`. `"career elimination number 147"` not `"another milestone"`.

**Forbidden patterns:**
- Do not imply mechanics that do not exist (morale bars, injury meters, transfer fees, contract years).
- Do not use `{raw_id}` tokens in any player-facing surface — `copy_quality.has_unresolved_token()` will flag these.
- Do not use comeback language (`"found another gear"`, `"dug deep"`) unless a specific event log moment supports it.
- Do not write hero/villain framings that are not backed by data.

**Easter egg rule (per AGENTS.md):** Graceful Spark reserves the right to hide exactly one piece of unexplained lore per content batch. This batch's easter egg is embedded in the Club Lore section. Find it if you can.

---

## Section 1: Expanded Name Banks

### 1.1 First Names (64 entries)

Drop-in replacement for `_FIRST_NAMES` in `src/dodgeball_sim/randomizer.py`.

```json
[
  "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules", "Remy", "Quinn",
  "Drew", "Sage", "Blake", "Reese", "Skye", "Morgan", "Bex", "Lex", "Cass", "Wren",
  "Lux", "Soren", "Brin", "Zoe", "Arlo", "Tate", "Fenn", "Lane", "Yuki", "Hana",
  "Sora", "Nori", "Kenji", "Zhen", "Lin", "Cruz", "Lena", "Nico", "Sol", "Vera",
  "Dex", "Nola", "Zara", "Kemi", "Noa", "Ayo", "Amara", "Zuri", "Mira", "Sasha",
  "Orin", "Saga", "Leif", "Lyra", "Cade", "Nex", "Tyne", "Vale", "Zeph", "Arc",
  "Dray", "Pix", "Priya", "Kiran"
]
```

**Design notes:** Maintains the league's gender-neutral, moderately futuristic feel. Covers multiple aesthetic registers (modern Western neutral, East/Southeast Asian-inspired, African-inspired, Nordic, sci-fi original) without caricature. Every name is monosyllabic or two syllables for fast readability on a card.

### 1.2 Last Names (64 entries)

Drop-in replacement for `_LAST_NAMES` in `src/dodgeball_sim/randomizer.py`.

```json
[
  "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart", "Rowe", "Slate",
  "Nova", "Crest", "Prism", "Zenith", "Aura", "Apex", "Corona", "Lyric", "Solace", "Meridian",
  "Steel", "Forge", "Colt", "Flint", "Holt", "Drake", "Crane", "Bolt", "Cross", "Braun",
  "Ash", "Moss", "Stone", "Fern", "Brook", "Vale", "Reed", "Shore", "Wilder", "Gale",
  "Fox", "Knox", "Ward", "Dale", "Kade", "Bloom", "March", "Stowe", "Kwan", "Archer",
  "Rayne", "Mercer", "Frost", "Pierce", "Marsh", "Valdez", "Okafor", "Sato", "Dusk", "Mace",
  "Vane", "Hale", "Spire", "Cray"
]
```

**Design notes:** Three registers — cosmic/clean (Nova, Prism, Zenith), industrial/punchy (Steel, Forge, Bolt), and nature/geographic (Ash, Reed, Wilder). Last names feel like surnames a person might actually have in a near-future context. `Okafor`, `Sato`, `Valdez`, `Kwan` provide cultural weight without being token additions.

### 1.3 Expanded Archetype Nickname Vocabulary

Replacement for `_ARCHETYPE_PREFIXES` and `_ARCHETYPE_SUFFIXES` in `src/dodgeball_sim/identity.py`. Doubles each set from 4 to 8 entries.

```json
{
  "prefixes": {
    "ace sniper":     ["Laser", "Scope", "Needle", "Bullseye", "Crosshair", "Pinpoint", "Zero", "Tracer"],
    "power cannon":   ["Hammer", "Thunder", "Anvil", "Torque", "Crusher", "Rampart", "Battering", "Ironclad"],
    "escape artist":  ["Ghost", "Slip", "Shadow", "Drift", "Vapor", "Phantom", "Mirage", "Fade"],
    "ball hawk":      ["Magnet", "Snare", "Clamp", "Latch", "Vice", "Snarl", "Anchor", "Lock"],
    "iron anchor":    ["Brick", "Atlas", "Boiler", "Granite", "Bastion", "Bulwark", "Rampart", "Slab"],
    "two-way spark":  ["Switch", "Fuse", "Pulse", "Circuit", "Relay", "Toggle", "Amp", "Coil"]
  },
  "suffixes": {
    "ace sniper":     ["Shot", "Line", "Eye", "Lock", "Mark", "Aim", "Strike", "Target"],
    "power cannon":   ["Arm", "Blast", "Drive", "Core", "Fist", "Slam", "Force", "Impact"],
    "escape artist":  ["Step", "Mist", "Glide", "Fade", "Wind", "Trace", "Pass", "Whisper"],
    "ball hawk":      ["Hands", "Trap", "Net", "Hook", "Grip", "Catch", "Snatch", "Reel"],
    "iron anchor":    ["Wall", "Tank", "Forge", "Guard", "Plate", "Shield", "Dome", "Citadel"],
    "two-way spark":  ["Wave", "Spark", "Flux", "Charge", "Current", "Surge", "Volt", "Arc"]
  }
}
```

**Combinatorial space:** 8 prefixes × 8 suffixes × 3 nickname styles (prefix+last, prefix+suffix, prefix-suffix) = 192 distinct outcomes per archetype before the player ID salt is applied. Across 6 archetypes: 1,152 theoretical nicknames.

---

## Section 2: Expanded Team Name Pools

Drop-in additions for `_TEAM_NAMES` and `_SUFFIXES` in `src/dodgeball_sim/randomizer.py`.

### 2.1 Base Names (24 total, was 12)

```json
[
  "Aurora", "Lunar", "Nebula", "Vanguard", "Echo", "Solstice", "Ion", "Blaze",
  "Harbor", "Atlas", "Mirage", "Circuit",
  "Apex", "Prism", "Quasar", "Titan", "Comet", "Zephyr", "Vector", "Summit",
  "Bastion", "Radiant", "Nexus", "Fractal"
]
```

### 2.2 Suffixes (22 total, was 7)

```json
[
  "Pilots", "Jets", "Sentinels", "Shadows", "Storm", "Orbit", "Flux",
  "Surge", "Blades", "Raptors", "Havoc", "Crush", "Volts", "Breach",
  "Raze", "Wraith", "Charge", "Forge", "Hawks", "Lancers", "Comets", "Drift"
]
```

**Combined pool:** 24 × 22 = 528 possible team names, up from 84. Procedural eight-club leagues can now run hundreds of seasons without exact-name collision.

---

## Section 3: Multi-Variant Headline Templates

These replace the single-template strings hard-coded in `src/dodgeball_sim/news.py`. The implementation engineer should store these as a list per category and select one via `DeterministicRNG` keyed to `(season_id, week, match_id, category)` — same seed every time you render the same matchday, different template across different matchdays.

Variable conventions follow the existing `MatchdayResult` and `RecordBroken` field names. All `{variable}` tokens must resolve before the string reaches `copy_quality.has_unresolved_token()`.

### 3.1 `record_broken` (priority 100)

```json
[
  "Record Watch: {player_name} set a new {record_type} mark at {value}.",
  "{player_name} rewrites the books — new {record_type} record stands at {value}.",
  "History Made: {player_name} breaks the all-time {record_type} record with {value}.",
  "The {record_type} record falls. {player_name} now holds the mark at {value}.",
  "By the Numbers: {player_name}'s {value} {record_type} eclipses the previous best."
]
```

### 3.2 `big_upset` (priority 90)

```json
[
  "Upset Alert: {winner_name} stunned {loser_name} {winner_score}-{loser_score} despite a {ovr_gap} OVR gap.",
  "Nobody saw this coming. {winner_name} takes down {loser_name} {winner_score}-{loser_score}.",
  "{loser_name} had the ratings. {winner_name} had the result. Final: {winner_score}-{loser_score}.",
  "Chaos League: {winner_name} erases a {ovr_gap}-point OVR disadvantage and beats {loser_name}.",
  "{winner_name} stuns the wire. {loser_name} drops despite leading on paper by {ovr_gap} OVR."
]
```

### 3.3 `rivalry_flashpoint` (priority 80)

```json
[
  "Rivalry Boils Over: {winner_name} vs {loser_name} added another chapter when {flashpoint_text}.",
  "Old Wounds: {winner_name} and {loser_name} renewed their feud, and it got personal when {flashpoint_text}.",
  "This one had history. {winner_name} edged {loser_name} in a matchup where {flashpoint_text}.",
  "Another Chapter: {winner_name} pulls ahead in the rivalry ledger after {flashpoint_text}."
]
```

### 3.4 `player_milestone` (priority 70)

```json
[
  "Milestone Reached: {player_name} hit {value} career {stat_label}.",
  "{player_name} crosses the {value} career {stat_label} threshold. The numbers speak.",
  "By The Books: {player_name} officially joins the {value} {stat_label} club.",
  "Career Watch: {player_name} records career {stat_label} number {value} for {club_name}.",
  "Running History: {player_name}'s {value} {stat_label} moves them into elite company."
]
```

### 3.5 `retirement` (priority 65)

```json
[
  "Farewell Tour: {player_name} announced a retirement decision.",
  "End of an Era: {player_name} steps away after {seasons} seasons with {club_name}.",
  "{player_name} hangs up the jersey. {club_name} and the wire acknowledge the career.",
  "League Note: {player_name} retires. {seasons} seasons. The record stands.",
  "The Wire Says Goodbye: {player_name}, {club_name}'s own, closes out at {seasons} seasons."
]
```

### 3.6 `rookie_debut` (priority 60)

```json
[
  "Rookie Watch: {player_name} made a first impression for {club_name}.",
  "New Blood: {player_name} steps onto the court for {club_name} in week {week}.",
  "First Touch: {player_name} logs court time in their {club_name} debut.",
  "{player_name} arrives. {club_name}'s newest recruit entered in week {week}.",
  "The Class Arrives: {player_name} records their first action in a {club_name} uniform."
]
```

### 3.7 `match_recap` (priority 25)

```json
[
  "Final Whistle: {winner_name} beat {loser_name} {winner_score}-{loser_score}.",
  "{winner_name} {winner_score}, {loser_name} {loser_score}. Week {week} in the books.",
  "Result: {winner_name} over {loser_name}, {winner_score} to {loser_score}.",
  "{winner_name} holds on against {loser_name}. Score: {winner_score}-{loser_score}.",
  "Wrap-Up: {loser_name} falls to {winner_name}, {winner_score}-{loser_score}."
]
```

### 3.8 Future categories (no current code binding — document for V5 sprint planning)

| Category | Priority | Trigger |
|---|---|---|
| `playoff_clinch` | 85 | Club secures a playoff slot (standings check at week end) |
| `season_opening` | 55 | First matchday of a new season |
| `championship_crowned` | 95 | Champion named at offseason ceremony |
| `scouting_buzz` | 40 | High-ceiling prospect surfaces in scouting center |
| `coaching_shift` | 50 | CoachPolicy changes significantly between seasons |

Templates for these categories should be written when the trigger logic is implemented.

---

## Section 4: Random Event Scenarios

These scenarios are content-only. They do not require engine changes. Each has a `mechanic_hint` field that describes which existing sim variable is affected — an implementation engineer uses this to wire stat adjustments when the event system is built.

**Format per scenario:**

```
id            — snake_case unique key
trigger       — "mid_season" | "offseason" | "any"
category      — "team_chemistry" | "player_spotlight" | "media" | "logistics" | "rival_drama"
title         — short wire-style headline
prompt        — body text shown to the manager (2–4 sentences, second-person)
choices       — array of { text, mechanic_hint }
```

The `mechanic_hint` string is not player-facing. It describes the sim variable in terms of existing fields: `club.coach_policy.*`, `player.ratings.*` (as a bounded delta, e.g. `+5 accuracy, capped 98`), or a narrative-only flag with no stat impact.

```json
[
  {
    "id": "locker_room_static",
    "trigger": "mid_season",
    "category": "team_chemistry",
    "title": "Tension in the Locker Room",
    "prompt": "Word reaches you that two of your starters exchanged words after last week's match. Practice has been quiet — too quiet. The assistant coaches aren't sure whether to intervene. What do you do?",
    "choices": [
      {
        "text": "Hold a closed-door team meeting. Address it directly.",
        "mechanic_hint": "club.chemistry +0.05, capped 1.0"
      },
      {
        "text": "Let it ride. The court will sort it out.",
        "mechanic_hint": "no stat effect; sets narrative flag 'tension_unresolved' for possible follow-up event"
      },
      {
        "text": "Rotate the players into different lineup slots to separate them.",
        "mechanic_hint": "resets lineup_override for both players; narrative-only"
      }
    ]
  },
  {
    "id": "rival_scout_sighting",
    "trigger": "mid_season",
    "category": "rival_drama",
    "title": "Familiar Face in the Stands",
    "prompt": "Your staff spots a known scout from {rival_club_name} watching your last practice session from the upper tier. Your top prospect notices them too. Nothing has been said yet — but the look on your player's face said something.",
    "choices": [
      {
        "text": "Say nothing. Let your player focus on the season.",
        "mechanic_hint": "narrative-only; sets flag 'rival_interest_known'"
      },
      {
        "text": "Pull your player aside and make clear they're valued here.",
        "mechanic_hint": "narrative-only; clears 'rival_interest_known' flag if set"
      },
      {
        "text": "Have staff ask the scout to leave private practice.",
        "mechanic_hint": "narrative-only; sets flag 'rival_tension_active' for possible rivalry score bump in future"
      }
    ]
  },
  {
    "id": "media_blitz_week",
    "trigger": "mid_season",
    "category": "media",
    "title": "The Cameras Are Here",
    "prompt": "A regional sports outlet wants to run a feature on your club this week. Full access — practices, pre-match prep, the works. Your players are split on the attention. What's your call?",
    "choices": [
      {
        "text": "Grant full access. The exposure is good for the club.",
        "mechanic_hint": "narrative-only; sets 'media_feature_active' flag; may generate additional rookie_debut-category headline this week"
      },
      {
        "text": "Limited access only — court time is off limits.",
        "mechanic_hint": "narrative-only"
      },
      {
        "text": "Decline. The season comes first.",
        "mechanic_hint": "narrative-only"
      }
    ]
  },
  {
    "id": "hard_court_conditions",
    "trigger": "mid_season",
    "category": "logistics",
    "title": "Court Surface Advisory",
    "prompt": "Maintenance reports that the away venue this week has a surface irregularity in the left quadrant. It won't affect the official match ruling, but your staff believes it could create unpredictable bounces in that zone. Do you adjust the lineup?",
    "choices": [
      {
        "text": "Shuffle the lineup to put your most agile starters in the risk zone.",
        "mechanic_hint": "lineup_override for one starter slot; player with highest dodge rating takes left-quadrant position"
      },
      {
        "text": "Run your standard lineup. Trust the system.",
        "mechanic_hint": "no stat effect"
      },
      {
        "text": "File a formal protest with the league office.",
        "mechanic_hint": "narrative-only; flavor text only; no mechanical consequence"
      }
    ]
  },
  {
    "id": "exit_interview_tension",
    "trigger": "offseason",
    "category": "player_spotlight",
    "title": "The Exit Interview",
    "prompt": "{retiring_player_name} sat down with you before their official farewell announcement. They had one request: they want their final season remembered accurately, not through the lens of the team's record. You have final say over the club's official farewell statement.",
    "choices": [
      {
        "text": "Honor the request. Focus the statement on their individual career stats.",
        "mechanic_hint": "narrative-only; generates retirement headline using player milestone framing"
      },
      {
        "text": "Thank them as part of the team's story — that's what the club represents.",
        "mechanic_hint": "narrative-only; generates standard retirement headline"
      },
      {
        "text": "Let them write their own statement. You'll sign off.",
        "mechanic_hint": "narrative-only; generates retirement headline with flavor suffix 'in their own words'"
      }
    ]
  },
  {
    "id": "viral_moment",
    "trigger": "any",
    "category": "media",
    "title": "The Clip Goes Wide",
    "prompt": "A highlight from your last match — {player_name}'s {highlight_event} — has been circulating beyond the usual sports feeds. The league office has already sent a note about 'increased visibility.' Your player is handling the attention well. What's your response?",
    "choices": [
      {
        "text": "Acknowledge it publicly. Let {player_name} enjoy the moment.",
        "mechanic_hint": "narrative-only; sets 'player_highlighted' flag; may bump rookie_debut priority if player is in first season"
      },
      {
        "text": "Keep it low-key. Tell them to stay focused.",
        "mechanic_hint": "narrative-only"
      }
    ]
  },
  {
    "id": "documentary_crew",
    "trigger": "offseason",
    "category": "media",
    "title": "They Want To Make a Documentary",
    "prompt": "A production company has reached out. They want to follow your club for the upcoming season — full fly-on-the-wall access from recruitment day through the playoffs. It is a significant commitment for the organization. The league has no objection.",
    "choices": [
      {
        "text": "Agree. This kind of exposure builds the program.",
        "mechanic_hint": "narrative-only; sets 'documentary_active' season flag; generates media-category events more frequently during season"
      },
      {
        "text": "Pass. You don't need the distraction.",
        "mechanic_hint": "narrative-only"
      },
      {
        "text": "Negotiate — practice access only, no locker room.",
        "mechanic_hint": "narrative-only; sets 'documentary_limited' flag"
      }
    ]
  },
  {
    "id": "cross_training_camp",
    "trigger": "offseason",
    "category": "logistics",
    "title": "The Off-Season Offer",
    "prompt": "A training facility outside the league is offering your starters a two-week intensive cross-training camp focused on reaction time and court movement. It costs nothing but time — and your players would miss the early stages of your own offseason preparation.",
    "choices": [
      {
        "text": "Send your top three starters. The development opportunity is real.",
        "mechanic_hint": "player.ratings.dodge +3 for top 3 starters by dodge rating, capped 98; player.ratings.stamina -2, floor 25"
      },
      {
        "text": "Keep everyone home. The offseason program is yours to control.",
        "mechanic_hint": "no stat effect"
      },
      {
        "text": "Send whoever volunteers.",
        "mechanic_hint": "player.ratings.dodge +3 for first two players by roster order who 'volunteer' (DeterministicRNG selection), capped 98"
      }
    ]
  },
  {
    "id": "injury_scare",
    "trigger": "any",
    "category": "player_spotlight",
    "title": "Practice Incident",
    "prompt": "{player_name} took a hard collision in practice this week and came up slow. Medical staff clears them to play, but they flagged it in the report. Nothing official, but you noticed. They say they're fine.",
    "choices": [
      {
        "text": "Trust the clearance. They play.",
        "mechanic_hint": "no stat effect; narrative-only"
      },
      {
        "text": "Hold them out of the next match as a precaution.",
        "mechanic_hint": "lineup_override: player benched for one match; no long-term stat effect"
      }
    ]
  },
  {
    "id": "community_day",
    "trigger": "any",
    "category": "team_chemistry",
    "title": "Community Day Request",
    "prompt": "The league asks each club to nominate two players for a public community appearance this week — youth clinic, local broadcast, the standard circuit. It is not mandatory, but the league office appreciates participation.",
    "choices": [
      {
        "text": "Send two starters. Good for the players, good for the club.",
        "mechanic_hint": "club.chemistry +0.03, capped 1.0; narrative-only otherwise"
      },
      {
        "text": "Send bench players. Keep the starters focused.",
        "mechanic_hint": "narrative-only"
      },
      {
        "text": "Decline this cycle. Schedule won't allow it.",
        "mechanic_hint": "narrative-only"
      }
    ]
  },
  {
    "id": "sponsor_equipment_issue",
    "trigger": "any",
    "category": "logistics",
    "title": "Equipment Complaint",
    "prompt": "Three of your starters have flagged that a recent equipment shipment — court shoes, specifically — doesn't match what was agreed. The supplier says it's within spec. Your players disagree. Match day is in four days.",
    "choices": [
      {
        "text": "Escalate with the supplier. Get the right gear or find another source.",
        "mechanic_hint": "narrative-only; resolves with flavor text; no stat effect"
      },
      {
        "text": "Tell the players to make it work. Focus on the match.",
        "mechanic_hint": "narrative-only"
      },
      {
        "text": "Authorize emergency gear purchase from league-approved stock.",
        "mechanic_hint": "narrative-only; flavor text only"
      }
    ]
  },
  {
    "id": "rival_poaches_staff",
    "trigger": "offseason",
    "category": "rival_drama",
    "title": "Staff Movement",
    "prompt": "{rival_club_name} has reportedly approached one of your assistant coaches about an open position. The coach has not said yes, and they have not said no. They came to you first, which you respect. But the offer is real.",
    "choices": [
      {
        "text": "Express how much you value them. Make it clear there is a path here.",
        "mechanic_hint": "narrative-only; clears potential departure flag"
      },
      {
        "text": "Wish them well and start thinking about a replacement.",
        "mechanic_hint": "narrative-only; sets 'staff_vacancy_pending' flag for future event"
      },
      {
        "text": "Ask them what it would take to stay.",
        "mechanic_hint": "narrative-only"
      }
    ]
  }
]
```

---

## Section 5: Club Lore — Canonical Default League

Eight clubs forming the default starting league. These entries define the `venue_name`, `tagline`, `home_region`, and extended lore text that the web club browser and future in-game flavor can draw from.

All `founded` values are expressed as season numbers relative to the league's inaugural season (S1). The league itself is unnamed at the design level — the Technical Project Manager sprint plan should assign a name or leave it procedurally generated per save file.

```json
[
  {
    "club_id": "aurora_jets",
    "name": "Aurora Jets",
    "home_region": "Solara City",
    "venue_name": "Solara Apex Arena",
    "founded": "S1",
    "primary_color": "#00BFFF",
    "secondary_color": "#FFFFFF",
    "tagline": "Speed is a statement.",
    "lore": "One of the league's two founding clubs, the Jets were built around the idea that a team moving faster than the opponent's read speed doesn't need to be stronger — just never still. Solara City's coastal geography and forward-leaning culture shaped an organization that has consistently prioritized tempo and accuracy over raw power. They have won more opening-week matches than any club in league history, and they have also blown more late-season leads. The Jets are not a safe bet. They are an interesting one.",
    "primary_rival_id": "vanguard_storm",
    "secondary_rival_id": "echo_orbit"
  },
  {
    "club_id": "lunar_pilots",
    "name": "Lunar Pilots",
    "home_region": "Halcyon Station",
    "venue_name": "Station Null Court",
    "founded": "S1",
    "primary_color": "#C0C0C0",
    "secondary_color": "#1A1A2E",
    "tagline": "Precision over panic.",
    "lore": "Founded the same season as the Jets, the Pilots have always operated as their philosophical opposite. Where Solara City moves fast, Halcyon Station moves deliberately. The Pilots emphasize ball control, catch-first positioning, and the psychological discipline of waiting for an opponent to make the first mistake. Their home venue, Station Null Court, is famously quiet — visiting clubs sometimes describe it as unsettling. The Pilots consider this a design feature.",
    "primary_rival_id": "nebula_sentinels",
    "secondary_rival_id": "aurora_jets"
  },
  {
    "club_id": "nebula_sentinels",
    "name": "Nebula Sentinels",
    "home_region": "New Cascadia",
    "venue_name": "Cascadia Ridgeline Court",
    "founded": "S2",
    "primary_color": "#7B2D8B",
    "secondary_color": "#E8E8E8",
    "tagline": "The wall holds.",
    "lore": "The Sentinels arrived in Season 2 as the league's first expansion club, and they have spent every season since proving that a second-wave club can outlast founding franchises. New Cascadia's industrial history shaped a roster-building philosophy centered on stamina and physical endurance — the Sentinels consistently field the most durable lineups in the league. They have never produced a season MVP. They have also never finished below fourth place. Some clubs peak. The Sentinels persist.",
    "primary_rival_id": "lunar_pilots",
    "secondary_rival_id": "vanguard_storm"
  },
  {
    "club_id": "vanguard_storm",
    "name": "Vanguard Storm",
    "home_region": "Eastport",
    "venue_name": "Eastport Vanguard Coliseum",
    "founded": "S1",
    "primary_color": "#FF4500",
    "secondary_color": "#1C1C1C",
    "tagline": "First in. Last standing.",
    "lore": "Eastport's financial corridor funded the Storm as a founding-season prestige project, and the club has leaned into that identity ever since — high-profile signings, aggressive recruiting, and a CoachPolicy biased toward synchronized throws and high-pressure ball carrier targeting. Their record against the Jets is the most-cited rivalry statistic in league history, though both clubs dispute which side the ledger favors. The Storm win more championships. The Jets win more hearts. The debate continues.",
    "primary_rival_id": "aurora_jets",
    "secondary_rival_id": "nebula_sentinels"
  },
  {
    "club_id": "echo_orbit",
    "name": "Echo Orbit",
    "home_region": "Meridian Plains",
    "venue_name": "Meridian Open Court",
    "founded": "S3",
    "primary_color": "#20B2AA",
    "secondary_color": "#F5F5DC",
    "tagline": "Resonance wins.",
    "lore": "The Orbit arrived quietly in Season 3 and have never made much noise off the court — deliberately. Their organizational philosophy holds that public attention is a distraction that compounds over time, while consistent performance compounds quietly. The Meridian Plains provide no natural geographic advantage, no storied local sports culture, and no large recruiting base. The Orbit have responded by developing the most sophisticated internal scouting network in the league. They find players nobody else is watching, and by the time anyone notices, those players are already committed.",
    "primary_rival_id": "blaze_flux",
    "secondary_rival_id": "aurora_jets"
  },
  {
    "club_id": "blaze_flux",
    "name": "Blaze Flux",
    "home_region": "Irondale",
    "venue_name": "Irondale Forge Court",
    "founded": "S3",
    "primary_color": "#FF6600",
    "secondary_color": "#2F2F2F",
    "tagline": "Burn hotter.",
    "lore": "Irondale's industrial corridor produced a club that has no interest in subtlety. The Flux build power-forward lineups, prioritize elimination rate over survival time, and run the most aggressive rush frequencies of any club with a positive season record. Critics call it a coinflip organization. Supporters call it the only club that makes the back half of a close match worth watching. The Flux have never won a championship. They hold the league record for most elimination-by-throw events in a single season. They are fine with this trade.",
    "primary_rival_id": "echo_orbit",
    "secondary_rival_id": "atlas_surge"
  },
  {
    "club_id": "atlas_surge",
    "name": "Atlas Surge",
    "home_region": "High Summit",
    "venue_name": "Summit Elevation Court",
    "founded": "S4",
    "primary_color": "#4169E1",
    "secondary_color": "#FFD700",
    "tagline": "Carry the weight.",
    "lore": "High Summit's geographic isolation produced a club defined by self-reliance. The Surge were the fourth expansion franchise and entered the league with no established recruiting pipeline and no rival club to define themselves against. They built one anyway. Their roster philosophy favors balanced players — two-way sparks and iron anchors — over specialists, and their CoachPolicy defaults to high catch bias and conservative rush frequency. The Surge are not the most exciting team in the league. They are the team you want holding a late lead.",
    "primary_rival_id": "circuit_hawks",
    "secondary_rival_id": "blaze_flux"
  },
  {
    "club_id": "circuit_hawks",
    "name": "Circuit Hawks",
    "home_region": "Dataport",
    "venue_name": "Dataport Processing Court",
    "founded": "S4",
    "primary_color": "#00FF7F",
    "secondary_color": "#0D0D0D",
    "tagline": "Precision at velocity.",
    "lore": "Dataport's technology corridor produced the league's most analytically-driven franchise. The Hawks were the first club to systematically track scouting state across multiple recruit classes before signing a single player, and they have never deviated from that approach. Their public-facing identity is minimal — a stylized hawk glyph on a dark ground, no mascot performances, no walk-up music. Their internal documentation, which leaked once in Season 6, revealed that they refer to their own players by archetype classification rather than name in tactical review sessions. The players reportedly do not mind. One of them once said, in an exit interview, that being seen clearly felt better than being seen warmly. That quote has never been confirmed. It has also never been denied.",
    "primary_rival_id": "atlas_surge",
    "secondary_rival_id": "echo_orbit"
  }
]
```

> **Graceful Spark's easter egg:** The Circuit Hawks' Season 6 leak is internally consistent with the archetype classification system in `identity.py`. If you search the commit history from S6, you will find nothing — because S6 hasn't happened yet. The leak is from the future. Whether this means the Hawks have already won, or that the documentation was planted, is left as an exercise for the lore team.

---

## Summary

### Files to Update (Implementation Tasks — for V4 Sprint Plan)

| File | Change | Priority |
|---|---|---|
| `src/dodgeball_sim/randomizer.py` | Replace `_FIRST_NAMES`, `_LAST_NAMES` with 64-entry arrays | High — prevents name collisions across multi-season careers |
| `src/dodgeball_sim/randomizer.py` | Replace `_TEAM_NAMES`, `_SUFFIXES` with expanded arrays | Medium — combinatorial breadth for procedural leagues |
| `src/dodgeball_sim/identity.py` | Replace `_ARCHETYPE_PREFIXES`, `_ARCHETYPE_SUFFIXES` with 8-entry arrays | Medium — nickname variety in player cards |
| `src/dodgeball_sim/news.py` | Refactor headline strings to select from template arrays via DeterministicRNG | High — wire variety is immediately player-visible |
| New: `src/dodgeball_sim/content/club_lore.json` | Add canonical club lore JSON; load in server.py for web club browser | Medium — needed for V4 web club browser |
| New: `src/dodgeball_sim/content/event_scenarios.json` | Add 12 event scenarios; no wiring required at this stage — document only | Low — wiring deferred to V5 event system |

### Tests to Add or Update

- `tests/test_randomizer.py` — assert `_FIRST_NAMES` has ≥ 60 entries; assert `_LAST_NAMES` has ≥ 60 entries; assert no duplicate entries in either list.
- `tests/test_identity.py` — assert each archetype has ≥ 8 prefixes and ≥ 8 suffixes; assert nickname generation still produces deterministic output after pool expansion.
- `tests/test_news.py` (new or expand) — assert multi-variant templates render without unresolved tokens; assert DeterministicRNG template selection is stable for same seed inputs.

### Non-Goals for This Content Batch

- No new mechanics implied by any copy above.
- No new Python modules created by this document alone — content is delivered as JSON and ready-to-replace arrays.
- No changes to `copy_quality.py`, `career_state.py`, `engine.py`, or `persistence.py`.
- No UI components. The React engineer wires these after the sprint plan assigns the task.

---

## Files Touched

- `docs/retrospectives/2026-04-29-v3-content-update.md` (this file)

## Integrity Check

- Monotonicity: N/A (content-only)
- Symmetry: All template variants use the same variable tokens; no asymmetric framing.
- Seeded determinism: Template selection uses existing DeterministicRNG; documented in headline template section.
- Explained variance: All `mechanic_hint` fields map to existing bounded variables.
- Difficulty without buffs: No event scenario grants unconditional stat buffs; all deltas are bounded and explainable.

## Risks / Follow-ups

- The `flashpoint_text` field in `MatchdayResult` is currently populated only when rivalry score ≥ 55. The rivalry-flashpoint template variants that reference it are only reached on that path — no change needed, but the V4 engineer should confirm the rivalry score threshold remains appropriate.
- The `seasons` variable referenced in retirement headline templates requires a career stats lookup. The current `news.py` retirement path only has `retirement_player_name` on the `MatchdayResult`. The V4 sprint should either add `retirement_seasons` to `MatchdayResult` or fall back to template variants that don't require it when the field is absent.
- Club lore colors are expressed as hex strings. The web club browser should validate these against the `primary_color`/`secondary_color` fields on the `Club` dataclass. If procedurally generated clubs use different formats, a normalization step may be needed in `server.py`.
