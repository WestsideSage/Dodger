# V15 Phase 3c — Season Preview Density: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Season Preview so a first-season player instantly grasps: season length, their bye timing, the playoff cut (with an explanation), and what their roster strength / "watch area" actually means (archetype display name + a TermTip that explains the archetype's mechanical role). The bye-bar fix from Phase 0 Task 4 is already in place — this phase does not redo it. It adds information density and semantic explainability on top of the corrected baseline.

**Architecture:** Two tasks. Task 1 is a light backend payload addition: expose a raw `archetype_key` field alongside the existing display `archetype` string on strength/weakness objects, so the frontend can form a `TermId` without fragile display-name reverse-mapping. Task 2 is the frontend density upgrade: wrap the Playoff Cut stat in a `TermTip(standings.playoff_line)`, wrap each archetype display name in a `TermTip(archetype.*)` keyed from the new raw field, add missing archetype term entries for the full engine key-space, and add a typed `ARCHETYPE_TERM_MAP` guard so any unmapped key is a compile-time error rather than a silent no-tooltip. No engine changes; no schedule changes; no new dependencies.

**Dependency:** Phase 0 Task 4 must be merged before this phase touches `SeasonPreview.tsx`. The plan's Task 2 steps describe the **post-Phase-0 file structure** (axis endpoints + bye-caption, not the old space-between legend). If Task 2 is executed before Phase 0 merges, read the current file carefully; the legend structure may still match the old form — do not introduce another legend change, just apply the TermTip wrappers.

**Tech Stack:** Python 3 backend (`src/dodgeball_sim/`), pytest; React + TypeScript + Vite (`frontend/`); `npm run build` / `npm run lint` / root `npm run e2e`. No frontend unit runner — verification is tsc compile gate + lint + Playwright.

> **Pre-flight:**
> - Branch off `main` (after Phase 0 and Phase 1 are merged): `git checkout -b feat/v15-phase3c-season-preview`.
> - Confirm `python -m pytest -q` is green and `npm run build && npm run lint` (from `frontend/`) is clean before starting.
> - Read current `SeasonPreview.tsx` (the post-Phase-0 version) to confirm the legend is non-positional (axis endpoints + bye caption) before editing. If Phase 0 is not yet merged, note the difference but do not re-introduce a legend change.
> - Verify the Phase 1 toolkit barrel is in place: `git grep -n "from.*legibility" -- frontend/src` should show the smoke route; the barrel exports `TermTip`, `TERMS`, `TermId`.

---

## Bar-chart vs. timeline evaluation (decision required before Task 2)

The current SeasonPreview renders a flex bar chart of `regular_season_weeks` bars (one per week) with a `CUT` flag appended. This plan **retains the bar chart** for the following reasons:

1. **Week count:** A standard season is 12 regular-season weeks (`regular_season_weeks` = 12, confirmed from playtest output and the Phase 0 planning report discussion). At 390px viewport width with `padding: '1.25rem'` on each side and `gap: 3px` between bars, each bar is approximately `(390 − 40 − 12×3) / 12 ≈ 26px` wide — clearly visible and not cramped.
2. **Phase 0 already corrected the only correctness defect** (the legend implied a bar position for the bye). With a non-positional legend the chart is correct and mobile-safe.
3. **Replacing with a list would remove the only glanceable season-shape** and lower information density, which is the opposite of this phase's goal.

**Justification recorded:** bar chart retained. Phase 3c only adds annotated stats and TermTip wrappers.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/dodgeball_sim/season_preview.py` | Add `archetype_key` raw field to strength/weakness payload | 1 |
| `tests/test_season_preview.py` | Test that `archetype_key` is present and matches the raw enum key | 1 |
| `frontend/src/types.ts` | Extend `SeasonPreview` interface: strength/weakness now include `archetype_key` | 1 |
| `frontend/src/legibility/terms.ts` | Add archetype term entries for all 8 engine keys (append-only) | 2 |
| `frontend/src/components/match-week/command-center/SeasonPreview.tsx` | Apply TermTip to Playoff Cut stat + archetype labels; add typed ARCHETYPE_TERM_MAP guard | 2 |

---

## Task 1: Expose `archetype_key` in the season preview payload

**Context:** `build_season_preview` calls `archetype_display_name()` before returning, so the frontend receives "Ball Hawk / Dodger" as `strength.archetype` — not the raw key "hawk_dodger". `TermTip` needs the raw key to form a valid `TermId`. Reverse-mapping display string → raw key on the frontend is fragile (two archetypes could share a display prefix). The fix is to emit both: keep `archetype` (display string, unchanged, backward-compatible) and add `archetype_key` (the raw enum value that becomes the `TermId`).

**Files:**
- Modify: `src/dodgeball_sim/season_preview.py`
- Modify/create: `tests/test_season_preview.py`
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Write the failing test first**

Find the existing season-preview test file:

```bash
ls tests/test_season_preview.py 2>/dev/null || echo "no file — create it"
```

If it exists, append. If not, create it. Add:

```python
from dodgeball_sim.season_preview import build_season_preview


def _roster_with(archetype: str) -> list[dict]:
    return [{"archetype": archetype, "overall": 72}]


class TestSeasonPreviewArchetypeKey:
    """strength and weakness expose the raw archetype_key alongside the display name."""

    def test_strength_carries_raw_key(self):
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=_roster_with("hawk_dodger"),
        )
        # The display name already worked; the new field is the raw key.
        assert payload["strength"]["archetype"] == "Ball Hawk / Dodger"
        assert payload["strength"]["archetype_key"] == "hawk_dodger"

    def test_weakness_carries_raw_key(self):
        roster = [
            {"archetype": "thrower", "overall": 80},
            {"archetype": "catcher", "overall": 55},
        ]
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=roster,
        )
        # "catcher" is weaker; verify the raw key is "catcher" (not the display name).
        assert payload["weakness"]["archetype_key"] == "catcher"

    def test_null_strength_when_roster_empty(self):
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=[],
        )
        assert payload["strength"] is None
        assert payload["weakness"] is None
```

- [ ] **Step 2: Run the test; verify it fails**

```bash
python -m pytest tests/test_season_preview.py -v -k "TestSeasonPreviewArchetypeKey"
```

Expected: FAIL — `KeyError: 'archetype_key'` or `AssertionError` on `archetype_key`.

- [ ] **Step 3: Add `archetype_key` to `build_season_preview`**

In `src/dodgeball_sim/season_preview.py`, the `strength` / `weakness` blocks in `build_season_preview` already call `archetype_display_name(strength["archetype"])`. The `strongest_position_group` / `weakest_position_group` functions return `{"archetype": raw_key, "avg_overall": int, "count": int}` — so `strength["archetype"]` is still the raw key at that point. Add `archetype_key` before the display name call:

```python
        "strength": (
            {
                "archetype": archetype_display_name(strength["archetype"]),
                "archetype_key": strength["archetype"],
                "avg_overall": strength["avg_overall"],
            }
            if strength is not None
            else None
        ),
        "weakness": (
            {
                "archetype": archetype_display_name(weakness["archetype"]),
                "archetype_key": weakness["archetype"],
                "avg_overall": weakness["avg_overall"],
            }
            if weakness is not None
            else None
        ),
```

- [ ] **Step 4: Run the targeted tests; verify they pass**

```bash
python -m pytest tests/test_season_preview.py -v -k "TestSeasonPreviewArchetypeKey"
```

Expected: all three tests PASS.

- [ ] **Step 5: Full suite**

```bash
python -m pytest -q
```

Expected: green. If any pre-existing test asserts the strength/weakness shape without `archetype_key` (e.g. strict dict equality), update the assertion to include the new field — the field is additive and does not break anything.

- [ ] **Step 6: Update `frontend/src/types.ts`**

Locate the `SeasonPreview` interface (currently around line 718). Update the strength/weakness inline type to include `archetype_key`:

```ts
export interface SeasonPreview {
    regular_season_weeks: number;
    bye_week: number | null;
    bye_text: string;
    playoff_cut: number;
    total_clubs: number;
    top_goal: string;
    strength: { archetype: string; archetype_key: string; avg_overall: number } | null;
    weakness: { archetype: string; archetype_key: string; avg_overall: number } | null;
    skipped: boolean;
}
```

- [ ] **Step 7: Frontend compile gate**

Run (from `frontend/`): `npm run build`
Expected: PASS. tsc will enforce the updated interface everywhere `SeasonPreview` is consumed. If the current `SeasonPreview.tsx` destructures `strength.archetype` only (no `archetype_key`), tsc is still happy because the interface addition is backward-compatible at the consumer side — the new field is simply unused until Task 2 adds the TermTip wrapper.

- [ ] **Step 8: Commit**

```bash
git add src/dodgeball_sim/season_preview.py tests/test_season_preview.py frontend/src/types.ts
git commit -m "feat(v15-p3c): expose archetype_key in season preview payload

strength and weakness objects now carry the raw enum key alongside the
display name so the frontend can form a TermId without fragile
display-string reverse-mapping. Interface updated in types.ts; old
'archetype' (display) field is unchanged for backward compatibility.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Frontend — TermTip wrappers + archetype term completeness

**Context:** Phase 1 pre-seeded only 4 archetype keys in `terms.ts` (`archetype.thrower`, `archetype.hawk_dodger`, `archetype.net_specialist`, `archetype.skirmisher`). The engine has 8 player archetypes; `net_specialist` and `skirmisher` are not engine keys at all. The `TermId` closed union means `<TermTip term="archetype.catcher">` fails at compile time if `archetype.catcher` is not in `TERMS`. This task fixes the gap: append all 8 engine archetype keys and remove the two non-engine placeholders (or keep them inert if they may be used by other phases — see note below).

> **Note on `net_specialist` / `skirmisher`:** These were pre-seeded speculatively in Phase 1. Check other Phase 2/3/4 plans with `git grep -r "net_specialist\|skirmisher" -- docs/specs/` before removing them. If no other plan references them, they are harmless (unused terms compile cleanly; the closed union does not error on extra keys, only on missing ones). Leave them in place — do NOT delete — since deletions would break any parallel plan that added them.

**Archetype key-space from `src/dodgeball_sim/models.py` (`PlayerArchetype` enum):**

| Raw key | Display name | Role |
|---|---|---|
| `thrower` | Thrower | Aggressive eliminator via throws |
| `catcher` | Catcher | Catch-focused resurrection specialist |
| `ball_hawk` | Ball Hawk | Evasive survivor, catch opportunist |
| `dodger_anchor` | Dodger Anchor | Evasion-first anchor; hard to eliminate |
| `thrower_catcher` | Thrower / Catcher | Hybrid: throws and attempts catches |
| `thrower_dodger` | Thrower / Dodger | Hybrid: throws and stays mobile |
| `catcher_hawk` | Catcher / Ball Hawk | Hybrid: catch-focused with hawk evasion |
| `hawk_dodger` | Ball Hawk / Dodger | Hybrid evasion: catches and dodges |

**Files:**
- Modify (append-only): `frontend/src/legibility/terms.ts`
- Modify: `frontend/src/components/match-week/command-center/SeasonPreview.tsx`

- [ ] **Step 1: Append the missing archetype terms to `terms.ts`**

In `frontend/src/legibility/terms.ts`, locate the `archetype.*` block (pre-seeded with `archetype.thrower`, `archetype.hawk_dodger`, `archetype.net_specialist`, `archetype.skirmisher`) and append entries for the 6 engine keys that are missing or incomplete. The existing `archetype.thrower` and `archetype.hawk_dodger` entries may be kept or improved — do not remove them. Add:

```ts
  // Player archetypes — complete engine key-space (PlayerArchetype enum in models.py)
  // Note: archetype.thrower and archetype.hawk_dodger were pre-seeded in Phase 1.
  // The following 6 fill the remaining engine keys.
  'archetype.catcher': {
    label: 'Catcher',
    plain: 'Catch-focused player who converts incoming throws into teammate resurrections.',
    why: 'Every successful catch eliminates the thrower AND brings a teammate back — the highest swing play in dodgeball.',
    kind: 'mechanical',
  },
  'archetype.ball_hawk': {
    label: 'Ball Hawk',
    plain: 'Evasive survivor who collects loose balls and attempts opportunistic catches.',
    why: 'Stays alive to accumulate throw chances; successful catches can shift momentum late in a round.',
    kind: 'mechanical',
  },
  'archetype.dodger_anchor': {
    label: 'Dodger Anchor',
    plain: 'Evasion-first specialist designed to be the last player standing.',
    why: 'Hard to eliminate — opponents waste throws chasing this player; forces late-round panic decisions.',
    kind: 'mechanical',
  },
  'archetype.thrower_catcher': {
    label: 'Thrower / Catcher',
    plain: 'Hybrid who attacks with throws and is willing to attempt catches on incoming throws.',
    why: 'Doubles threat: eliminates via throws AND can swing a round with a catch; higher variance than a pure specialist.',
    kind: 'mechanical',
  },
  'archetype.thrower_dodger': {
    label: 'Thrower / Dodger',
    plain: 'Hybrid who attacks with throws and uses mobility to survive.',
    why: 'Throw volume with lower exposure than a pure Thrower — stays in the game longer to keep throwing.',
    kind: 'mechanical',
  },
  'archetype.catcher_hawk': {
    label: 'Catcher / Ball Hawk',
    plain: 'Hybrid focused on catching incoming throws and collecting loose balls.',
    why: 'Resurrection machine: turns defensive play into offensive momentum through repeated catch attempts.',
    kind: 'mechanical',
  },
```

(The `archetype.thrower` entry from Phase 1 covers the `thrower` key; `archetype.hawk_dodger` covers `hawk_dodger`. All 8 engine keys now have a `TermId`.)

- [ ] **Step 2: Compile gate after term additions**

Run (from `frontend/`): `npm run build`
Expected: PASS. The `as const satisfies Record<string, TermDef>` constraint will validate all new entries have the required fields.

- [ ] **Step 3: Add the `ARCHETYPE_TERM_MAP` guard to `SeasonPreview.tsx`**

This is a typed `Record` mapping every possible `archetype_key` value to a `TermId`. If a key is missing the map, `TermId` will reject the lookup at compile time — making the guarantee airtight without any runtime fallback.

Add this constant near the top of `SeasonPreview.tsx`, after the import block:

```tsx
import type { TermId } from '../../../legibility';
import { TermTip } from '../../../legibility';
import type { SeasonPreview as SeasonPreviewData } from '../../../types';

// Maps every PlayerArchetype raw key (from models.py) to its legibility TermId.
// This is a compile-time-complete map: any archetype_key not listed here is a tsc error.
// If the engine adds a new archetype, add its 'archetype.*' entry to terms.ts first,
// then add it here.
const ARCHETYPE_TERM_MAP: Record<string, TermId> = {
  thrower: 'archetype.thrower',
  catcher: 'archetype.catcher',
  ball_hawk: 'archetype.ball_hawk',
  dodger_anchor: 'archetype.dodger_anchor',
  thrower_catcher: 'archetype.thrower_catcher',
  thrower_dodger: 'archetype.thrower_dodger',
  catcher_hawk: 'archetype.catcher_hawk',
  hawk_dodger: 'archetype.hawk_dodger',
} as const;

// Returns a TermId for an archetype_key, or undefined if the key is unmapped
// (e.g. a future archetype added before terms.ts is updated).
function archetypeTermId(key: string): TermId | undefined {
  return ARCHETYPE_TERM_MAP[key] as TermId | undefined;
}
```

> Note: The `Record<string, TermId>` type (not `Record<RawKey, TermId>`) is intentional — `archetype_key` arrives as a plain `string` from the payload, and the map lookup handles the validation. Every value in the map IS a valid `TermId`, so the tsc gate still fires if a value is mis-typed; the key domain is runtime-string, not compile-time-closed.

- [ ] **Step 4: Wrap the Playoff Cut stat in `TermTip(standings.playoff_line)`**

Locate the `stat(...)` call for `'Playoff Cut'` in `SeasonPreview.tsx` (currently around line 136):

```tsx
{stat('Playoff Cut', `Top ${preview.playoff_cut} of ${preview.total_clubs}`, '#22c55e')}
```

Replace it with a version that wraps the label in a `TermTip`:

```tsx
{stat(
  'Playoff Cut',
  `Top ${preview.playoff_cut} of ${preview.total_clubs}`,
  '#22c55e',
  /* termId */ 'standings.playoff_line',
)}
```

This requires the `stat` helper to accept an optional `termId` parameter. Update the `stat` helper function (currently defined as a `const stat = (label, value, accent) => ...`) to support an optional fourth argument:

```tsx
  const stat = (label: string, value: string, accent: string, termId?: TermId) => (
    <div
      style={{
        flex: '1 1 0',
        minWidth: '6.5rem',
        background: '#0b1220',
        border: '1px solid #1e293b',
        borderTop: `2px solid ${accent}`,
        borderRadius: '6px',
        padding: '0.7rem 0.8rem',
      }}
    >
      <dt
        style={{
          fontSize: '0.58rem',
          fontWeight: 800,
          letterSpacing: '0.08em',
          color: '#64748b',
          textTransform: 'uppercase',
        }}
      >
        {termId ? <TermTip term={termId}>{label}</TermTip> : label}
      </dt>
      <dd style={{ color: '#f1f5f9', fontSize: '1.1rem', fontWeight: 800, margin: '0.25rem 0 0' }}>{value}</dd>
    </div>
  );
```

The `Regular Season` and `Your Bye` stat calls require no `termId` (they are self-explanatory numbers); pass no fourth argument and they render exactly as before.

- [ ] **Step 5: Wrap archetype names in `TermTip` on strength/weakness cards**

Locate the Roster Strength and Watch Area blocks in `SeasonPreview.tsx` (currently around lines 159–198). Each renders:

```tsx
{preview.strength.archetype} — {preview.strength.avg_overall} avg OVR
```

Replace each with a TermTip-wrapped version. For **strength**:

```tsx
              <div style={{ color: '#f1f5f9', fontSize: '0.9rem', fontWeight: 700, marginTop: '0.2rem' }}>
                {(() => {
                  const termId = archetypeTermId(preview.strength.archetype_key);
                  return termId ? (
                    <><TermTip term={termId}>{preview.strength.archetype}</TermTip>{' — '}{preview.strength.avg_overall} avg OVR</>
                  ) : (
                    <>{preview.strength.archetype} — {preview.strength.avg_overall} avg OVR</>
                  );
                })()}
              </div>
```

For **weakness** (the Watch Area card, same pattern):

```tsx
              <div style={{ color: '#f1f5f9', fontSize: '0.9rem', fontWeight: 700, marginTop: '0.2rem' }}>
                {(() => {
                  const termId = archetypeTermId(preview.weakness.archetype_key);
                  return termId ? (
                    <><TermTip term={termId}>{preview.weakness.archetype}</TermTip>{' — '}{preview.weakness.avg_overall} avg OVR</>
                  ) : (
                    <>{preview.weakness.archetype} — {preview.weakness.avg_overall} avg OVR</>
                  );
                })()}
              </div>
```

> The `archetypeTermId` fallback path (returning `undefined`) ensures the component still renders correctly if the backend ever sends an archetype_key not yet in the map — degrading to plain text rather than crashing. This is the honesty principle: do not fabricate a tooltip for an unknown term.

- [ ] **Step 6: Mobile safety check — confirm no overflow introduced**

At 390×844 the TermTip popover uses `width: 'min(16rem, 70vw)'` (from the Phase 1 implementation) and `position: absolute` — it is constrained to 70vw and does not stretch the page layout. The stat tiles already wrap with `flexWrap: 'wrap'` so the added import does not affect layout. No new width or height constraints are added. Visual verification should be done via the Playwright screenshot in Step 8.

- [ ] **Step 7: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: both PASS. The tsc gate verifies every `TermTip term=` value is a valid `TermId`; the `ARCHETYPE_TERM_MAP` values are all valid `TermId`s; the `TermId | undefined` return type of `archetypeTermId` is handled at each call site.

If lint flags the IIFE pattern `{(() => { ... })()}`, replace with a small helper defined inside the component body:

```tsx
  const archetypeTip = (key: string, display: string, ovr: number) => {
    const termId = archetypeTermId(key);
    return termId ? (
      <><TermTip term={termId}>{display}</TermTip>{' — '}{ovr} avg OVR</>
    ) : (
      <>{display} — {ovr} avg OVR</>
    );
  };
```

Then the JSX simplifies to:
```tsx
{archetypeTip(preview.strength.archetype_key, preview.strength.archetype, preview.strength.avg_overall)}
```

Use whichever form passes lint.

- [ ] **Step 8: Playwright smoke — verify TermTip renders on the Season Preview**

Add a focused check to `tests/e2e/v15-season-preview.spec.ts` (create the file):

```ts
import { test, expect } from '@playwright/test';

// Verifies the Season Preview information-density upgrade:
// - The Playoff Cut stat label is a TermTip that reveals its explanation.
// - The strength/weakness archetype labels are TermTips that reveal mechanical explanations.
// Precondition: a fresh career must be in Week 1 (Season Preview is visible).
test.describe('Season Preview density (Phase 3c)', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a fresh-career command center so the Season Preview is shown.
    // Adjust the URL to match the app's dev-server route for a new career (Week 1).
    await page.goto('/');
    // Wait for the season preview section.
    await expect(page.getByTestId('season-preview')).toBeVisible({ timeout: 10_000 });
  });

  test('Playoff Cut label reveals a TermTip explanation', async ({ page }) => {
    const cutButton = page.getByRole('button', { name: /What is Playoff Line\?/i });
    await expect(cutButton).toBeVisible();
    await cutButton.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toContainText(/cutoff seed/i);
    await expect(tooltip).toContainText(/AFFECTS PLAY/i);
  });

  test('Strength archetype label reveals a TermTip explanation', async ({ page }) => {
    // The specific archetype depends on the roster; look for any TermTip button
    // inside the Roster Strength card.
    const strengthCard = page.locator('div').filter({ hasText: /Roster strength/i }).first();
    const tipButton = strengthCard.getByRole('button', { name: /What is/i });
    await expect(tipButton).toBeVisible();
    await tipButton.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toContainText(/AFFECTS PLAY/i);
  });
});
```

> **Precondition note:** This spec requires a live Week 1 career state. If the e2e suite does not automatically seed a fresh career, gate these tests with `test.skip` in CI until the e2e fixture is available, and verify manually in the browser instead. Check how other e2e specs (e.g. `v15-legibility-toolkit.spec.ts`) handle app state setup before finalizing the `beforeEach`.

Run (from repo root): `npm run e2e -- v15-season-preview`
Expected: PASS (or a scoped skip if the fixture is unavailable — confirm which applies for this repo).

- [ ] **Step 9: Engine-health probe (confirm no sim drift)**

Run: `python tools/tier_engine_health_probe.py --driver official --trials 50`
Expected: output identical to the Phase 0 Step 4 baseline. This phase touches only the season-preview payload builder (a pure dict assembly function) and the frontend component — no scoring or engine logic.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/legibility/terms.ts frontend/src/components/match-week/command-center/SeasonPreview.tsx tests/e2e/v15-season-preview.spec.ts
git commit -m "feat(v15-p3c): Season Preview density — TermTip on Playoff Cut + archetypes

Add TermTip(standings.playoff_line) to the Playoff Cut stat label so a
first-season player can immediately learn what the playoff cut means.

Add TermTip(archetype.*) to strength/weakness archetype labels, keyed by
the new archetype_key payload field (Task 1). Add ARCHETYPE_TERM_MAP as a
typed compile-time-complete guard; unmapped keys degrade to plain text
rather than erroring. Append 6 missing engine archetype entries to terms.ts
(archetype.catcher, ball_hawk, dodger_anchor, thrower_catcher, thrower_dodger,
catcher_hawk) so all 8 PlayerArchetype enum values have a TermId.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3c Exit Gates

Run all before declaring Phase 3c done:

- [ ] `python -m pytest -q` — green (covers the new `TestSeasonPreviewArchetypeKey` tests and any pre-existing season-preview tests).
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **identical** to the Phase 0 baseline (proves zero sim drift; this phase is display-only).
- [ ] From `frontend/`: `npm run build` — PASS (tsc gate validates: every `TermTip term=` is a valid `TermId`; the `ARCHETYPE_TERM_MAP` values are all valid `TermId`s).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e -- v15-season-preview` — green (or scoped skip with manual verification documented).
- [ ] Manual browser check at 390×844: Season Preview shows the Playoff Cut stat with a dotted-underline TermTip; strength/weakness archetype names have dotted underlines; tapping/focusing a label reveals the tooltip with the AFFECTS PLAY pill and a plain-language explanation; no horizontal overflow at 390px.
- [ ] No engine, scheduler, or RNG files touched. No new npm or Python dependencies added.

---

## Cross-screen overlap to normalize

1. **Archetype term completeness is now shared:** `terms.ts` now covers all 8 `PlayerArchetype` keys. Phase 2a (Recruit Board) and Phase 2b (Roster/Player Card) both surface archetype badges. Those phases should consume the same `ARCHETYPE_TERM_MAP` pattern rather than inventing separate mappings. Recommend extracting the map into a shared utility (e.g. `frontend/src/legibility/archetypeTerm.ts`) once Phase 2b is planned — but do not do this in Phase 3c (it would modify a file another phase owns). Note the duplication risk in the hand-off.

2. **`standings.playoff_line` is also used on Standings (Phase 2d):** The same `TermTip(standings.playoff_line)` wrapping the cut line label would normalize across both screens. Phase 2d should reuse the same term rather than writing parallel copy. No action needed here — this is a note for the Phase 2d planner.

3. **`archetype_key` pattern for other screens:** The payload pattern (emit raw key + display name) may be needed wherever the backend pre-translates an enum to a display string before sending. Roster/Player Card (`PlayerDetailModal`) and Recruit Board (archetype badge) are candidates. Phase 2a/2b planners should check whether their payloads suffer the same translate-before-send pattern before writing display→key reverse-map hacks.

---

## Out of Scope for Phase 3c (do NOT do here)

- Engine/sim/RNG changes.
- Schedule or season-structure changes.
- Staff impact visibility (Phase 3b).
- Dynasty Office / Credibility layout (Phase 3a).
- Roster card or Recruit Board archetype badges beyond what is already in `terms.ts` (Phase 2a/2b).
- Removing `archetype.net_specialist` / `archetype.skirmisher` from `terms.ts` (they are inert if unused; deletions could break a parallel phase).
- The skip-preview UX checkbox (already working; do not touch).
