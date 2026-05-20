# Post-V11 Redesign Brief

Date: 2026-05-20
Status: Draft for user review.
Author: Brainstorm session output (Maurice + Claude).

This is a **scoping brief**, not an implementation spec. It captures a
vision-level pivot that V11 made possible and decomposes the redesign into
sub-projects, each of which will get its own design + plan when its turn
comes. The terminal artifact of this brief is the identification of the
**first sub-project** ("Tier 1 Match Loop") plus the approach options for it.

If this brief and the source disagree, the source wins — then fix this
brief.

---

## 1. Why this exists

V11 shipped the Official USA Dodgeball Rules engine (`official_engine.py` and
~14 sibling modules: ball state, catch queue, burden, sequence-of-play,
no-blocking, discipline, clocks, rulesets). The engine is real. But the
*content layer* on top of it — `CoachPolicy`, `PlayerRatings`,
`PlayerArchetype`, Command Center plans, aftermath voice, match replay UI,
scouting, awards — was designed against the generic engine that preceded
V11. Most of it speaks a sport-agnostic language that doesn't reflect how
real dodgeball is actually played.

The pivot: **drop the generic engine entirely; rebuild the player-facing
layer around the official engine as the only engine.** Then go further —
restructure the game itself around how a real club moves through real
dodgeball competition, from rec league up to USA Dodgeball-sanctioned
"Worlds."

This brief scopes that pivot.

## 2. Vision (locked)

### 2.1 Genre and reference class

Management sim with a watchable proof match. **Not** a spectator sim. **Not**
a menu-only manager. Closest reference class:

- **Teamfight Manager** — draft/prep decisions tested by a watchable automated
  contest. Climb-the-tiers structure.
- **Golden Lap** — light but meaningful race-day calls shown through a clean
  readable live event.
- **Football Coach: College Dynasty** — long-term roster/program-building
  creates attachment and strategic identity.

Dodger combines these lessons. It is **not** Football Manager (too
menu-heavy, too season-sim-pure), **not** Out of the Park Baseball (too
spreadsheet-forward), and **not** a watch-live arcade sim.

### 2.2 Time budget per week

| Phase | Share | What happens |
|---|---|---|
| Management / prep | 35–45% | Roster decisions, scouting, tactics, training, recruiting |
| Match / replay | 25–35% | Watch the simulation play out with speed controls and readable beats |
| Aftermath | 20–30% | Review why it happened, stats, narratives, next-step decisions |

The match is the **emotional proof surface**, not the main UI surface. If
the player can't recognize dodgeball logic in the replay, the management
layer feels fake. But if the replay dominates, the game becomes a
spectator sim and loses decision density.

### 2.3 Core loop

```
form a theory → make constrained pre-match choices →
watch the match test those choices → receive readable evidence →
adjust the theory → continue the season arc
```

Every screen exists to make the next match more meaningful. If a screen
doesn't, it's a candidate for cut.

### 2.4 Audience and success test

Target user, in order of priority:

1. **Rec-league / club dodgeball player.** Plays weekly, knows the rules in
   practice, doesn't care about edge cases like designated-retriever timing.
   **Primary market.**
2. **Gym-class / pickup veteran.** Knows the sport by feel.
3. **USA Dodgeball competitor.** Used as a realism reference, not the
   primary market. The fact that the top of the climb plays by their rules
   makes the rest of the climb credible.

**Success test:** "Recognizable to someone who actually plays dodgeball."
A rec-league player watching a tier-1 match should think "yes, that's how
this goes." A USAD competitor watching a tier-7 match should think the
same thing about their version of the sport.

### 2.5 Subsystem priority order

Subsystems redesigned in this order (drives milestone sequencing):

1. **Engine realism** (highest — everything depends on the sim producing
   believable dodgeball)
2. **Player attribute model** (individuals must behave recognizably)
3. **Match replay UI** (the engine's truth must be visible)
4. **Aftermath / stat explanation** (player learns from results)
5. **Coach tactics** (meaningful agency)
6. **Roster / scouting / recruitment** (long-term attachment, climb spine)
7. **Command Center** (frame, not star — hub that prepares and explains
   the loop)
8. **Stats / awards** (recognition and history)
9. **AI Program Managers** (valuable later, cuttable until core sings)

Subsystems 1 + 2 + 3 are tightly coupled and will be co-developed; see §6.

## 3. Career structure: the climb is the game

### 3.1 Tier ladder

Seven tiers from rec league to Worlds. Tier names below are working
placeholders — final naming will be settled during implementation:

| # | Working name | Stakes | Tournaments? |
|---|---|---|---|
| 1 | Rec League | Local pride. Signup-based. Regular season only. | No |
| 2 | Rec League Open | Top rec teams. First taste of stakes. | **Unlock** |
| 3 | Semi-Pro Div 2 | First semi-formal level. | Yes |
| 4 | Semi-Pro Div 1 | Established semi-pro. | Yes |
| 5 | Pro Div 2 | First professional tier. | Yes |
| 6 | Pro Div 1 | Top pro league. | Yes |
| 7 | **Worlds** | USAD-sanctioned international championship. **Endgame.** | Yes |

### 3.2 Promotion / relegation

- **Promotion:** finish top 2 at the end of the season → promoted to next
  tier next season.
- **Relegation:** bottom-finish (exact threshold TBD per tier) → relegated
  to previous tier. Tier 1 has no relegation (it's the floor).
- **Tournament play** unlocks at tier 2 and persists at every tier above.
  Tournament results may modify or co-gate promotion alongside
  regular-season placement (mechanic TBD per-tier).

### 3.3 Endgame

**Win Worlds → credits roll.** That's the game. The climb is the meal,
not the appetizer.

Out of scope for this brief: New Game+, sustained-dominance dynasty
content, post-Worlds replay loops. These are parking-lot for a future
expansion.

### 3.4 Tier-distinction axes

A 7-tier climb is shallow if every tier plays the same with stronger AI.
**Five axes vary by tier**, intentionally chosen to keep scope bounded:

1. **Rule complexity.** Tier 1 = no refs, headshot-thrower-out, chaos
   retrieval, no discipline. Tier 7 = full USAD 2026.1 with discipline
   persistence, designated retrievers, sequence formalization. V11's
   existing engine slots in at tiers 5–7. Tiers 1–4 use progressively
   simplified rule sets.
2. **Recruiting reality.** Tier 1 = local signups, friends, gym
   acquaintances. Tier 7 = national/international scouting, USAD-pedigree
   athletes, formal recruiting trips.
3. **Roster size / position formalization.** Tier 1 = loose roster, no
   formal positions, everyone does everything. Tier 7 = formal positions
   (thrower, catcher, retriever, dodger-anchor), depth-chart discipline.
4. **Vocabulary / narration.** Tier 1 = rec-league slang ("bro got pegged",
   "he's gassed"). Tier 7 = broadcast register ("sequence resolved with
   three pending outs", "discipline state escalated"). Aftermath voice,
   match commentary, and dashboard copy scale with tier.
5. **Tournament structure + relegation.** Tier 1 = regular season only,
   no relegation. Tier 2+ = tournaments unlock; relegation in play.
   Stakes of a losing season scale up dramatically by tier 5–7.

**Off-court training** is orthogonal: informal/personal at low tiers ("you
go to the gym on your own time"), formal/staff-driven at high tiers
(strength coach, conditioning program, film study). Folded into recruiting
/ roster axes for implementation.

**Out of scope (deferred):** facilities economy, salary/contract sim,
sponsorship economy, player morale demands, scripted media controversies.
These remain in the parking lot from the long-range roadmap.

## 4. The six recognition moments

A rec-league dodgeball player recognizes *moments and feel* before *rules*.
These are the moments the user named from lived experience as the test of
"feels like real dodgeball":

1. **The 1v3 / 1v4 late-game escape attempt.** A solo survivor against a
   stacked side, sometimes pulling off the impossible.
2. **The dramatic catch that brings a teammate back.** The biggest
   momentum-swinger in the sport.
3. **The gassed star whose late-match performance collapses.** Stamina
   matters; conditioning has visible consequences.
4. **The flood throw.** Multiple throwers attacking simultaneously,
   common with knowledgeable players late in a match.
5. **The 1v1 between the best surviving players.** Hype, sometimes
   happens, decides matches.
6. **The comeback through clutch catches.** Down many players, a
   catcher chains catches to flip the game.

These six moments are the **operational definition** of recognition for
the primary audience. They define what the engine must produce and what
the replay must surface.

### Engine vs replay split

| Moment | Already supported by engine? | Gap |
|---|---|---|
| 1v3 / 1v4 escape | Yes — count tracking + dodge resolution | Tuning + late-game state recognition |
| Dramatic catch → return | Yes — `catch_queue.py` does this | **Replay** must highlight the beat |
| Gassed star collapse | **No — in-match fatigue not modeled** | **Engine gap** |
| Flood throws | **No — ledger handles one sequence at a time** | **Engine gap** |
| 1v1 finale | Yes — emerges from count math | Replay framing |
| Comeback via catches | Yes — catches already return players | Tuning + replay framing |

Two real engine gaps: **in-match fatigue** and **simultaneous-throw / flood
sequences**. The other four moments are already mechanically possible;
they need replay surfacing.

**This is why subsystems #1 (engine), #2 (attributes), and #3 (replay) are
co-developed in the first sub-project.** Half of "feels like real dodgeball"
lives in the replay layer, not the engine layer.

## 5. What stays from V11

V11 was not wasted. It built the engine that the top of the climb uses.

**Preserved as tier 5–7 content:**

- `official_engine.py` autonomous game loop
- `discipline.py` — warnings, blue cards, escalation
- `catch_queue.py` — FIFO return mechanic
- `burden.py` — possession-attack obligation
- `sequence.py` — sequence-of-play ledger
- `no_blocking.py` — game-time-driven mode transitions
- `official_translator.py` — translates official events to generic
  match-event shape (still needed for stats/save compatibility)
- `rulesets.py` — Foam / No-Sting / Cloth profiles (these become
  *additional* ball-material variants the player can use within higher
  tiers, not the tier-axis itself)

**Repurposed:**

- The discipline modules are tier-gated. Tier 1 has no refs, so no
  discipline state. Tier 2 introduces basic ref presence. Discipline
  escalation appears at tier 4+.
- Designated retriever role is tier-gated. Tier 1 = chaos retrieval (any
  active player can grab any ball). Designated retrievers appear at tier
  3+.

**Demoted / deleted:**

- The generic `MatchEngine` and its resolution path are deleted.
- The generic-engine variance probe (`tools/o1_variance_probe.py`) is
  deleted or repurposed for the new engine.
- `PlayerArchetype` enum (vestigial; only `TACTICAL` is ever assigned) is
  redesigned per §6.2.
- Generic `CoachPolicy` 8-field model is redesigned per §6.5.
- Tkinter-era code (`gui.py`, `manager_gui.py`, etc.) deleted as part of
  this redesign — already flagged in STATUS.md as cleanup candidates.

**Save migration:** V1–V10 saves and V11 official-ruleset saves do not
carry forward. This is a clean break. The game is pre-release; we accept
the migration cost.

## 6. Subsystem-level scope notes

These are deliberately thin — full design happens per sub-project.

### 6.1 Engine realism (subsystem #1)

**Tier 1 engine** is *simpler* than V11. No refs, no discipline, no
designated retriever, headshot-thrower-out (inverted from USAD), chaos
retrieval. Build this first as a clean module that can later be extended
tier-by-tier.

**Net-new engine features needed for the six moments:**

- In-match fatigue accumulation and decay tied to player stamina and
  match duration.
- Simultaneous / rapid-fire throw sequences (flood-throw support — the
  ledger must accept overlapping sequences, or "flood" must become a
  distinct sequence kind).
- Late-game asymmetric state recognition (1v3, 1v4, 1v1 produce flagged
  events for replay framing).

### 6.2 Player attribute model (subsystem #2)

Current `PlayerRatings` (accuracy, power, dodge, catch, stamina,
tactical_iq) is roughly right but blind to:

- **Catch courage / decision quality** — who tries the catch, who plays
  safe.
- **Throw selection IQ** — when to fire, when to hold, when to flood.
- **Retrieval IQ** — situational awareness for ball recovery (tier 3+).
- **Discipline under pressure** — tier 4+ attribute.
- **Conditioning curve** — how fatigue accumulates, not just total
  stamina.

Archetypes get rebuilt around real dodgeball positions: **thrower,
catcher, retriever, dodger-anchor**, with hybrid types. The vestigial
`PlayerArchetype.TACTICAL` enum is replaced.

### 6.3 Match replay UI (subsystem #3)

Already plumbed: `official_state` is in the replay payload, banner shows
ruleset. Not yet doing the work of surfacing the six moments.

Replay must:

- Highlight the moment beats (catch → return, gassed collapse, flood,
  1v1, late escape, comeback).
- Provide speed controls and readable event narration.
- Adapt vocabulary to tier (see §3.4 axis 4).

### 6.4 Aftermath / stat explanation (subsystem #4)

Current `voice_verdict` is a generic-engine artifact. Aftermath rebuilds
around: which moments happened this match, what tactics produced them,
which players showed up, what the result means for the season arc.
Tier-aware vocabulary.

### 6.5 Coach tactics (subsystem #5)

`CoachPolicy` 8-field model is deleted. Replaced with tier-appropriate
levers:

- Tier 1: pre-match approach (aggressive / patient / mixed), target focus
  (their stars / spread the pressure), catch posture (go for catches /
  play safe). ~3–4 knobs.
- Tier 4+: adds discipline posture, retrieval priority, sequence pacing.
- Tier 7: full tactical surface mirroring USAD coaching depth.

Tactical levers grow with tier — both the engine and the player learn
new vocabulary together.

### 6.6 Roster / scouting / recruitment (subsystem #6)

Climb spine. Recruiting at tier 1 is "this guy from your gym is
interested"; at tier 7 it's "scout a national prospect." Roster size and
position formalization scale per axis 3.

### 6.7 Command Center (subsystem #7)

Frame, not star. Hub that prepares and explains the loop. Current intent
list ("Win Now / Develop Youth / Preserve Health") survives in concept
but copy is rewritten to be tier-aware. Department orders likely
collapse into 2–3 categories per tier.

### 6.8 Stats / awards (subsystem #8)

USAD-native stats at tier 7 (sequence efficiency, catches under burden,
discipline-adjusted plus-minus). Rec-style stats at tier 1 (eliminations,
catches, survival rate). The stats vocabulary climbs with the player.

### 6.9 AI Program Managers (subsystem #9, **cuttable**)

`ai_program_manager.py` is half-scaffolded. If the climb works without
it, ship without it. If rival programs feel flat at tier 5+, add it
then. Do not block earlier milestones on this.

## 7. First sub-project: Tier 1 Match Loop

The **first sub-project** is the smallest coherent unit that delivers a
playable rec-league match with the six recognition moments visible.

**Scope:**

- Tier 1 engine (rec-league rules, simpler than V11)
- In-match fatigue
- Flood-throw / simultaneous sequence support
- Player attribute v2 (catch courage, throw selection IQ, conditioning
  curve, position-aware archetypes — minimum needed for tier 1)
- Replay UI that surfaces all six moments
- Aftermath voice rewritten for rec-league vocabulary
- Tier 1 tactical surface (3–4 pre-match knobs)
- *Single* tier of play; no promotion/relegation yet (next sub-project)

**Out of scope for this sub-project:**

- Tier 2+ rule layers
- Promotion/relegation system
- Tournament structure
- Recruiting redesign (interim: keep current recruiting working at tier 1
  feel — local signups)
- Stats/awards redesign (interim: stay with current minimal stats)
- AI Program Manager work

**Done definition:**

A new career starts at tier 1. The player makes a small set of pre-match
choices, watches the match, and the replay visibly produces multiple of
the six recognition moments. The aftermath describes what happened in
rec-league terms. The player understands why the result happened. Tests
pass. Playwright e2e covers the loop. A rec-league dodgeball player
watching a session would recognize the sport.

### 7.1 Approach options

Three approaches to Tier 1 Match Loop, with tradeoffs:

**(A) Strangler-fig: extend V11's official engine downward.**
Treat tier 1 as "V11 with most features disabled." Build a tier
configuration layer; turn off discipline, retriever, burden mechanics,
etc., at tier 1. Add fatigue and flood as new official-engine features
that all tiers share but only matter at higher tiers when paired with
discipline/positions. **Pro:** maximum reuse, single engine. **Con:** the
tier-1 engine is conceptually a stripped-down USAD sim rather than a
genuine rec engine; the simplifications feel like "missing features"
rather than "different sport." Existing tests stay relevant.

**(B) Greenfield tier engine + later convergence.**
Write a new `rec_engine.py` from scratch, designed around the six
moments. Use V11 as reference but don't try to share code initially.
Once tier 2/3 redesign happens, factor common pieces back out. **Pro:**
tier 1 engine is conceptually clean — designed for the experience, not
inherited from USAD-with-features-off. **Con:** code duplication early;
convergence later may be painful. New tests.

**(C) Hybrid: shared primitive modules, two engine drivers.**
Keep V11's primitive modules (`ball_state`, `catch_queue`, `sequence`,
`player_state`) as shared library. Write two thin engine "drivers" — one
rec, one USAD — that compose the primitives differently. Fatigue and
flood become primitive-level features available to both. **Pro:** clean
separation of "rules" from "primitives"; mid-tier engines (2–6) are just
new drivers, not new code. **Con:** requires factoring V11 primitives to
be driver-agnostic, which may surface coupling.

**Recommendation: (C) Hybrid.** It's the only option that scales to a
7-tier climb without either accumulating dead code or rewriting the
engine seven times. The factoring cost is real but pays back at every
tier above 1. (A) collapses on the second-tier redesign when "USAD with
features off" stops being a good abstraction. (B) accepts duplication
that gets worse over time.

If the user prefers (A) for speed-to-first-playable, that's defensible —
but the brief should call out that (C) is the architecturally right
answer for the 7-tier vision.

## 8. Open questions deferred to per-sub-project design

- Exact tier names (placeholders used here).
- Relegation thresholds per tier.
- Tournament format per tier (round-robin, double-elimination, etc.).
- Number of in-game seasons per tier (how long does the climb take?).
- Whether tier 1 has "city / region" identity or is generic.
- Save-format / database migration mechanics from V11 schemas.
- Exact rule mapping per tier (which rules turn on at which tier — a
  rule-by-tier matrix needs to be authored).
- Position model details (how many positions, how strictly enforced).
- How off-court training surfaces in the UI per tier.

These are not blockers for the first sub-project. They'll be settled in
the per-tier design passes.

## 9. Drift control

Every sub-project added under this brief must answer the same checklist
the long-range roadmap requires:

1. What playable loop does this improve?
2. What decision does the player make?
3. What visible consequence proves the decision mattered?
4. What data must be persisted for later systems?
5. Can a browser automation agent play or inspect it?
6. What is explicitly out of scope?
7. Does it preserve the integrity contract?

If any answer is weak, the sub-project is wrong-sized.

## 10. Next steps

1. **User reviews this brief.**
2. On approval: invoke the writing-plans skill to draft the
   implementation plan for **Tier 1 Match Loop**, picking the engine
   approach (A/B/C) the user selects.
3. STATUS.md and MILESTONES.md get updated to reflect the rescoping:
   the original O1 (engine balance) is closed as obsolete (was
   generic-engine-only); the new milestone slot is "Tier 1 Match Loop";
   the long-range roadmap entries past V11 are deprecated and replaced
   by the climb structure described here.
4. The four-axis-deferred items (facilities economy, morale, etc.) stay
   in the parking lot.

---

## Appendix A: Sources of truth

- This brief: vision-level scoping for the post-V11 redesign.
- `docs/STATUS.md`: current build state (will be updated to reflect this
  pivot on approval).
- `docs/specs/MILESTONES.md`: milestone history (will gain entries for
  the Tier 1 Match Loop and successor sub-projects).
- `AGENTS.md`: repo rules, workflow, architecture snapshot.
- Source code and tests: final authority when docs and code disagree.

## Appendix B: Open conversational record

The vision pillars in §2 and the tier structure in §3 emerged from a
grilling session on 2026-05-20. Key user-stated commitments captured
verbatim:

- "I want this to be able to be played and understood by someone who
  actually plays Dodgeball. If the game works in a way that a real
  Dodgeball player would not recognize then it is an inaccurate game."
- "The player will be watching the games the majority of the time" —
  later refined to "the match is the emotional proof surface… ~40%
  prep / ~30% match / ~30% aftermath."
- "The climb is the game."
- "After you win Worlds the game is done. Eventually there can be like
  a New Game+ where the game is much harder but that is a dessert and
  we haven't even got the main course."

These quotes are the load-bearing commitments. Subsequent design must
serve them.
