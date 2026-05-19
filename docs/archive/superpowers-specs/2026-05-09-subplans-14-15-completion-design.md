# Subplans 14 & 15 Completion — Design Spec
**Date:** 2026-05-09
**Scope:** Fill the stub-quality gaps left by the prior implementation session in subplans 14 (History sub-tab) and 15 (Offseason Ceremony Takeovers). Also covers housekeeping debt: `patch.js` deletion and uncommitted plan-doc edits.

---

## Context

Subplans 14 and 15 shipped with build/test gates green but with stub-quality frontends:
- All five ceremonies render 1–2 lines of `beat.body` text via an identical `CeremonyShell` call
- `MyProgramView` hero strip is a placeholder `<h3>`; alumni show only name (no stats)
- `LeagueView` HoF and dynasty rankings are empty arrays; program directory has no click-through
- Backend history endpoints are hardcoded stubs; ceremony endpoint sends `body: str` with no structured payload

This spec defines what "actually done" looks like for both subplans.

---

## Housekeeping (ship first, no design required)

1. **Delete `patch.js`** from repo root — one-off script used during prior session, never part of the product.
2. **Commit the 11 modified plan docs** in `docs/superpowers/plans/2026-05-08-ux-polish/wave-2-hierarchy/` and `wave-3-soul/` — these were edited inline by the prior session instead of going through the wave-authoring protocol. Commit them as-is so the working tree is clean before implementation begins.

---

## Approach: Backend Payload Enrichment

The ceremony endpoint (`/api/offseason/beat`) currently returns `body: str` (newline-joined text). This is insufficient for per-entity card rendering.

**Solution:** Add a `payload` dict to the beat response alongside the existing `body` string. Each beat type defines its own `payload` shape. The frontend reads `payload`; `body` is kept for any legacy consumers.

The history endpoints (`/api/history/my-program`, `/api/history/league`) are hardcoded stubs. They will be wired to existing persistence functions already in `persistence.py`.

No new persistence tables or Python models are required.

---

## Part 1 — Subplan 15: Offseason Ceremony Takeovers

### 1.1 Backend: Structured Payload per Beat

Add `payload: dict` to the `/api/offseason/beat` response. Shapes by beat key:

**`awards`**
```json
{
  "payload": {
    "awards": [
      { "player_name": "Marcus Reyes", "club_name": "Thunder Bay Bolts",
        "award_type": "mvp", "career_elims": 94, "ovr": 88, "ovr_delta": 5 }
    ]
  }
}
```
Source: `load_awards(conn, season_id)` joined with player/club data from rosters and clubs.

**`retirements`**
```json
{
  "payload": {
    "retirees": [
      { "name": "Marcus Reyes", "seasons_with_club": 4,
        "ovr_start": 62, "ovr_peak": 88, "ovr_final": 85,
        "career_elims": 311, "championships": 1, "potential_tier": "Elite" }
    ]
  }
}
```
Source: `load_retired_players(conn)` + `load_player_career_stats(conn, player_id)`. `ovr_start` is the player's overall in their first recorded season; `potential_tier` from `calculate_potential_tier()`.

**`champion`** and **`recap`** — separate beats, separate payloads, both use the generic fallback renderer (no new TSX component in this spec; payload enrichment happens so a future subplan can add ceremony components if desired)

`champion` payload:
```json
{ "payload": { "champion": { "club_name": "Thunder Bay Bolts", "wins": 10, "losses": 2, "draws": 0, "title_count": 1 } } }
```
Source: season outcome + `load_club_trophies` count for that club.

`recap` payload:
```json
{ "payload": { "standings": [ { "rank": 1, "club_name": "Thunder Bay Bolts", "wins": 10, "losses": 2, "draws": 0, "points": 30, "is_player_club": true } ] } }
```
Source: `load_standings(conn, season_id)` + club name lookup.

**`schedule_reveal`**
```json
{
  "payload": {
    "season_label": "2027",
    "fixtures": [
      { "week": 1, "home": "Thunder Bay Bolts", "away": "Lakeside Lions", "is_player_match": true }
    ],
    "prediction": "Thunder Bay enters as defending champions — but three rivals quietly upgraded this off-season."
  }
}
```
Source: `next_season.scheduled_matches` (already available in `_build_beat_response`). `prediction` from `voice_pregame.py`'s framing line for the player's opening fixture.

**`recruitment`** (Signing Day)

**State-machine clarification:** The `recruitment` beat is shown in two states driven by `can_recruit`:
- `can_recruit = true` → "Sign Best Rookie" CTA renders (handled by existing Offseason.tsx, not a ceremony component)
- `can_recruit = false` (after signing is complete) → `SigningDay` ceremony component renders

`SigningDay` is therefore a **results reveal**, not a live signing flow. The `payload.signings` reflects all signings completed at the moment of the request (the player's pick plus any AI signings that occurred during the draft pool resolution).

```json
{
  "payload": {
    "player_signing": { "name": "Kwame Asante", "ovr": 71, "role": "Thrower", "age": 17 },
    "other_signings": [
      { "name": "Taylor Osei", "club_name": "Lakeside Lions", "ovr": 68 }
    ]
  }
}
```
Source: `signed_player_id` from state → player record from rosters; other signings from roster diffs post-draft. If no AI draft data is available (v1 flow), `other_signings` is an empty list — `SigningDay` renders just the player's pick.

**`staff_carousel`**

> **Known constraint:** `staff_carousel` is not currently a key in `OFFSEASON_CEREMONY_BEATS`, so the backend never produces this beat key and `CoachingCarousel` never fires. The frontend routing (`beat.key === 'staff_carousel'`) is dead code.
>
> **Resolution for this spec:** `CoachingCarousel` stays as-is (body-text fallback). Wiring a real `staff_carousel` beat into the offseason pipeline is out of scope here — it would require changes to `OFFSEASON_CEREMONY_BEATS` and `finalize_season`. The acceptance criteria below excludes Coaching Carousel from the "payload-driven" requirement. It remains a no-op ceremony until a future subplan adds the beat key.

### 1.2 Frontend: Per-Ceremony Card Components

All five components live in `frontend/src/components/ceremonies/`. They all use the existing `CeremonyShell` (spacebar skip, reduced-motion, `stages` counter). Each gets a unique `renderStage` implementation using `payload` data.

#### `AwardsNight.tsx`
- `stages = payload.awards.length`
- Each stage reveals the next award card: large emoji icon for award type, player name (large), club + career stat line (subdued), glow border in orange
- Already-revealed cards stay visible above with a ✓ and reduced opacity on their border
- If `payload.awards` is empty, falls back to the existing body-text render

Award type → emoji map:
| award_type | emoji | color |
|---|---|---|
| `mvp` | 🏆 | `#f97316` |
| `top_rookie` | ⚡ | `#eab308` |
| `best_defender` | 🛡️ | `#3b82f6` |
| `most_improved` | 📈 | `#10b981` |
| `championship` | 🥇 | `#f97316` |

#### `Graduation.tsx`
- `stages = payload.retirees.length`
- Each stage reveals one senior card: role/seasons badge, name, OVR arc (`ovr_start → ovr_peak → ovr_final` with arrows), career stats row (elims, championships), potential-tier outlook line in tier color
- Green accent color (`#10b981`)

#### `CoachingCarousel.tsx`
- **Dead code note:** `staff_carousel` is not a real beat key (see §1.1). This component never fires under the current offseason pipeline. No changes to this component in this spec. It will render gracefully if somehow invoked with an empty or absent `payload` (the existing body-text fallback handles this).

#### `SigningDay.tsx`
- Results-reveal ceremony; shown only after `can_recruit = false` (signing complete)
- `stages = 1 + payload.other_signings.length` — stage 1 is the player's own pick (always present), subsequent stages reveal each AI club's signing
- Stage 1: large highlighted card for the player's signing (`payload.player_signing`), cyan border (`#22d3ee`), "Your pick" eyebrow
- Subsequent stages: muted cards for each `other_signings` entry
- If `payload.other_signings` is empty (v1 flow), the ceremony is a single-stage reveal of the player's pick only

#### `NewSeasonEve.tsx`
- `stages = 2`
- Stage 1: fixture list reveals (player's match highlighted in orange, others subdued)
- Stage 2: prediction headline fades in below the fixture list
- CTA is "Start the Season" (calls `beginSeason()`, not `advance()`)
- `payload.season_label` used in the header eyebrow

### 1.3 History Integration

Per the spec, each ceremony writes to History automatically. This is already handled by the existing offseason beat pipeline (trophies, HoF, alumni written via persistence layer during `finalize_season` and `initialize_manager_offseason`). No new writes are needed — the history backend just needs to read what's already there.

---

## Part 2 — Subplan 14: History Sub-Tab

### 2.1 Backend: Wire Real Persistence Data

#### `/api/history/my-program?club_id=`

Replace the hardcoded stub with real queries:

```python
{
  "club_id": club_id,
  "hero": {
    "season_1": { "wins": ..., "losses": ..., "draws": ..., "avg_ovr": ..., "season_label": ... },
    "current":  { "wins": ..., "losses": ..., "draws": ..., "avg_ovr": ..., "season_label": ..., "championships": ... }
  },
  "timeline": [
    { "season": "2024", "week": 4, "event_type": "first_win", "label": "First Win", "weight": "standard" },
    { "season": "2025", "week": null, "event_type": "award", "label": "MVP: Reyes", "weight": "award" },
    { "season": "2026", "week": null, "event_type": "championship", "label": "Champions", "weight": "championship" },
    { "season": "2026", "week": null, "event_type": "hof", "label": "HoF: Reyes", "weight": "hof" }
  ],
  "alumni": [
    { "id": "p1", "name": "Marcus Reyes", "seasons_start": "2023", "seasons_end": "2026",
      "peak_ovr": 88, "career_elims": 311, "championships": 1, "potential_tier": "Elite" }
  ],
  "banners": [
    { "type": "championship", "season": "2026", "label": "Champions" },
    { "type": "award", "season": "2025", "label": "MVP Award" }
  ]
}
```

Data sources:
- `hero.season_1`: first season's standings row for this club (from `standings` table, earliest `season_id` for this club). `avg_ovr` is best-effort: query `player_season_stats` for that season; if no historical OVR data exists (new save or old schema), omit the field — the hero renders without it rather than showing 0
- `hero.current`: latest season's standings row + current roster average OVR
- `timeline`: assembled from `league_records` (records broken by a player whose `holder_id` appears in this club's alumni or current roster → `event_type: "record"`), `club_trophies` (championships → `"championship"`), `hall_of_fame` (inductions of players from this club → `"hof"`), `awards` table (season awards for this club's players → `"award"`). First win derived from `match_records` (earliest `winner_club_id = club_id` → `"standard"`). `weight` field mirrors `event_type` name except `milestone` (used for playoff events if tracked)
- `alumni`: `load_retired_players(conn)` filtered to players whose last club was this club_id, joined with `player_career_stats`
- `banners`: `load_club_trophies(conn)` filtered to this club, plus distinct award wins

#### `/api/history/league`

```python
{
  "directory": [ { "club_id": "...", "name": "..." } ],
  "dynasty_rankings": [
    { "club_name": "Thunder Bay Bolts", "championships": 1, "longest_win_streak": 7 }
  ],
  "records": [ ... ],  # already wired via load_league_records
  "hof": [
    { "player_id": "p1", "player_name": "Marcus Reyes", "induction_season": "2026",
      "career_elims": 311, "championships": 1, "seasons_played": 4 }
  ],
  "rivalries": [
    { "club_a": "Thunder Bay Bolts", "club_b": "Lakeside Lions",
      "a_wins": 7, "b_wins": 4, "draws": 1, "meetings": 12 }
  ]
}
```

Data sources:
- `dynasty_rankings`: `load_club_trophies(conn)` grouped by `club_id` for championship count; win streak from `match_records`
- `hof`: `load_hall_of_fame(conn)` joined with `career_summary_json`
- `rivalries`: `load_rivalry_records(conn)`

### 2.2 Frontend: `MyProgramView.tsx`

**Non-self club behaviour:** `MyProgramView` accepts any `clubId` prop (including non-player clubs opened via the League directory modal). All data — hero, timeline, alumni, banners — reflects that club's history. `hero.current` uses that club's latest standings row and roster, not the player's. The "next banner" placeholder in `BannerShelf` is **omitted for non-self clubs** — it only makes sense as a motivational prompt on the player's own program page.

#### Hero Strip
Two side-by-side cards using `data.hero`:
- Left card ("How it started"): season label kicker, club name, W-L-D record, Avg OVR — plain dark card
- Right card ("Today"): same fields + championships count, green glow border, OVR delta vs. season 1 shown in green

#### Milestone Tree (`MilestoneTree.tsx` — new component)

SVG-based tree. Renders vertically, growing downward. Spec:

**Layout:**
- Trunk: vertical SVG `<line>` at a fixed x (~90px from left), full height, `stroke-width: 3`, color `#475569`
- One row per season in chronological order. Row height: `68px`
- Seasons with no milestones: dashed trunk node (ring, `stroke-dasharray="3 2"`), short dashed stub line to the right, "— no milestones" text label
- Seasons with milestones: solid trunk node, solid branch line(s) connecting to milestone dots in a chain from left to right
- Championship seasons: orange glowing trunk node (`filter: drop-shadow`), orange-tinted background band across the row

**Dot sizes by event_type weight:**
| weight | diameter | example events |
|---|---|---|
| `championship` | 32px (r=16) | League title |
| `hof` | 24px (r=12) | Hall of Fame induction |
| `award` | 20px (r=10) | Season award (MVP, Top Rookie, etc.) |
| `milestone` | 16px (r=8) | Playoff run |
| `standard` | 12px (r=6) | First win, rivalry win |

**Dot sizes by event_type weight (updated — adds `record`):**
| weight | diameter | example events |
|---|---|---|
| `championship` | 32px (r=16) | League title |
| `hof` | 24px (r=12) | Hall of Fame induction |
| `award` | 20px (r=10) | Season award (MVP, Top Rookie, etc.) |
| `record` | 18px (r=9) | League record broken by a player from this club |
| `milestone` | 16px (r=8) | Playoff run |
| `standard` | 12px (r=6) | First win, rivalry win |

**Colors by event_type:**
| event_type | dot fill | branch color |
|---|---|---|
| `championship` | radial `#f97316 → #9a3412` | `#f97316` |
| `hof` | `#065f46` / border `#34d399` | `#10b981` |
| `award` | `#d97706` / border `#fbbf24` | `#eab308` |
| `record` | `#0369a1` / border `#38bdf8` | `#0ea5e9` |
| `milestone` | `#7c3aed` / border `#a78bfa` | `#8b5cf6` |
| `standard` | `#3b82f6` / border `#60a5fa` | `#3b82f6` |

**Branch lines:** SVG `<line>` segments, `stroke-width: 1.5–2`, connecting trunk-node-edge → first-dot-edge → next-dot-edge → … in a chain. Empty seasons have a dashed stub only.

**Labels:**
- Season label: HTML div, right-aligned, left of trunk, vertically centered on trunk node
- Milestone label: HTML div, `transform: translateX(-50%)`, positioned below dot (dot_center_y + dot_radius + 4px)

**Season grouping:** Timeline events are grouped by season. The gap between season rows is fixed at 68px regardless of milestone count — seasons spread vertically by time, not by density. Multiple milestones in the same season spread horizontally along the branch with a **fixed 56px center-to-center pitch** between dots. Dot radius varies by weight but center spacing is always 56px, so branch line segments are computed as `(prev_cx + prev_r, cy) → (next_cx - next_r, cy)` with 56px between centers.

**Implementation note:** The tree is rendered as a single `<svg>` element with computed dimensions (height = num_seasons × 68 + padding), with HTML label divs absolutely positioned on top in a `position:relative` wrapper.

#### Alumni Lineage (`AlumniLineage.tsx`)
One card per entry in `data.alumni`:
- Name + seasons badge (`Seasons 1–4`) top row
- OVR arc: `ovr_start → peak → ovr_final` (peak highlighted in the tier color)
- Stats row: career elims, championships, peak OVR
- Potential tier label in tier color (`Elite` → `#10b981`, `High` → `#3b82f6`, `Solid` → `#94a3b8`, `Limited` → `#64748b`)
- "No departed players yet" empty state

#### Banner Shelf (`BannerShelf.tsx`)
Horizontal row of trophy items from `data.banners`:
- Championship: 🏆 emoji (large, 2.5rem) + "Champions {season}" label in orange
- Award: 🏅 emoji + award label in gold
- Faint dashed "next banner" placeholder at the end
- "No banners yet" empty state when array is empty

### 2.3 Frontend: `LeagueView.tsx`

#### Program Directory
Each chip is clickable and opens a modal (`ProgramModal`) rendering `<MyProgramView clubId={club.club_id} />`. The player's own club gets an orange border highlight.

#### Dynasty Rankings
Simple ranked list from `data.dynasty_rankings`: rank number, club name, championship count, longest win streak.

#### All-Time Records
Already wired via `load_league_records`. Display: record type (human-readable label), holder name (from `holder_id` + club name lookup), value, season set.

#### Hall of Fame
List from `data.hof`: ⭐ icon, player name, induction season, career elims, championships, seasons played.

#### Rivalries Directory
List from `data.rivalries` sorted by total meetings desc: Club A vs Club B, total meetings, head-to-head record (a_wins–b_wins–draws). Top rivalry shown as a featured card; full list below.

---

## Component File Map

| New / changed file | Purpose |
|---|---|
| `frontend/src/components/ceremonies/Ceremonies.tsx` | Rewrite all 5 exports with payload-driven card rendering |
| `frontend/src/components/dynasty/history/MyProgramView.tsx` | Hero strip + tree + alumni + banners |
| `frontend/src/components/dynasty/history/MilestoneTree.tsx` | New: SVG tree component |
| `frontend/src/components/dynasty/history/AlumniLineage.tsx` | New: alumni cards |
| `frontend/src/components/dynasty/history/BannerShelf.tsx` | New: banner shelf |
| `frontend/src/components/dynasty/history/LeagueView.tsx` | Dynasty rankings, HoF, rivalries, modal click-through |
| `frontend/src/components/dynasty/history/ProgramModal.tsx` | New: modal wrapper for LeagueView → MyProgramView click-through |
| `src/dodgeball_sim/server.py` | Enrich `/api/offseason/beat` payload + wire history endpoints |

---

## Verification

Build/test gates (`npm run build` + `python -m pytest -q`) are required as always. Visual work is verified manually in browser preview after each ceremony component lands. Payload shapes for all enriched beats are covered by server-level tests asserting the `payload` key exists with the correct top-level structure.

---

## Acceptance Criteria (per 00-MAIN.md)

### Subplan 15
- [ ] Awards Night: per-award cards reveal one at a time, real player names and stats
- [ ] Graduation: per-senior career arc cards (OVR arc, peak stats, potential tier outlook)
- [ ] Coaching Carousel: component renders gracefully when invoked with empty or absent payload (current dead-code state — beat key not produced by backend; full implementation deferred to a future subplan)
- [ ] Signing Day: prospect cards reveal one-by-one, progress bar fills, player's signing highlighted
- [ ] New Season Eve: fixtures list + voice-template prediction headline, "Start the Season" CTA
- [ ] All ceremonies: spacebar skip works, reduced-motion cuts instantly
- [ ] Payload-driven: all cards read from `payload` dict in beat response, not from body string parsing

### Subplan 14
- [ ] My Program / League toggle works
- [ ] Hero strip shows real Season 1 vs. current season data
- [ ] Milestone tree renders with SVG trunk/branches, variable dot sizes, season grouping, empty-season stubs
- [ ] Alumni lineage shows departed players with peak stats and potential tier
- [ ] Banner shelf shows real trophies from `club_trophies` table
- [ ] League: program directory chips open a club's My-Program view in a modal
- [ ] League: dynasty rankings populated from `club_trophies`
- [ ] League: HoF populated from `hall_of_fame` table
- [ ] League: rivalries populated from `rivalry_records` table
- [ ] All data auto-generated from sim history — no manual logging inputs anywhere

### Housekeeping
- [ ] `patch.js` deleted from repo root
- [ ] 11 modified plan docs committed
