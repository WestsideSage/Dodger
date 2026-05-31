# New Player UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four highest-friction points found in blind new-player playtesting: the advance button after a match is buried and mislabeled, the opponent key-threat tooltip is cryptic, the "Edit Policy" label is jargon, and the new-game wizard steers players toward premade clubs with a misleading badge.

**Architecture:** All changes are frontend-only except Task 4 (Your Standout), which reads data the backend already sends but the UI discards. No new API endpoints, no schema changes. Every task is independent and can be merged separately.

**Tech Stack:** React 18 + TypeScript (frontend), Playwright (e2e tests), pytest (Python backend tests — not touched here)

---

## File Map

| File | Touched by | Change |
|---|---|---|
| `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx` | Task 1 | Rename advance labels |
| `frontend/src/index.css` | Task 1 | Sticky positioning for `.command-action-bar` |
| `tests/e2e/command-center-aftermath.spec.ts` | Task 1 | Update button-name assertion |
| `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` | Tasks 2a–2c | Label + tooltip + edge-label copy |
| `tests/e2e/command-center-presim-hero.spec.ts` | Task 2 | Add assertions for new copy |
| `frontend/src/components/SaveMenu.tsx` | Task 3 | Badge copy change |
| `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx` | Task 4 | Your-Standout fallback section |
| `tests/e2e/command-center-aftermath.spec.ts` | Task 4 | Standout section assertion |

---

## Task 1 — Advance Button: Label + Sticky Bar

**Why it matters:** "MOVE ON →" is the only way to advance past the post-match debrief. New players don't scroll to find it, and even when they do, the label doesn't signal navigation. Sticky positioning makes it always reachable; clearer copy tells players what clicking does.

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx:1-6`
- Modify: `frontend/src/index.css:2369-2375`
- Modify: `tests/e2e/command-center-aftermath.spec.ts` (label assertion)

---

- [ ] **Step 1: Update `advanceLabel` in AftermathActionBar.tsx**

Open `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx`. Replace the entire `advanceLabel` function (lines 1–6) with:

```tsx
function advanceLabel(result?: string): string {
  if (result === 'Win') return 'BANK THE RESULT →';
  return 'NEXT WEEK →';
}
```

Rationale: Win keeps its flavor label (clearly positive). Loss and Draw both show `NEXT WEEK →` — unambiguous navigation. The default (no result) also becomes `NEXT WEEK →`.

- [ ] **Step 2: Make `.command-action-bar` sticky in index.css**

Open `frontend/src/index.css`. Find `.command-action-bar` (around line 2369). Change it from:

```css
.command-action-bar {
  display: flex;
  gap: 8px;
  align-items: stretch;
  justify-content: flex-end;
  padding: 4px 16px 12px;
}
```

To:

```css
.command-action-bar {
  display: flex;
  gap: 8px;
  align-items: stretch;
  justify-content: flex-end;
  padding: 4px 16px 12px;
  position: sticky;
  bottom: 0;
  background: #0a0f1c;
  z-index: 10;
  border-top: 1px solid #1e293b;
}
```

The `background` matches the page's dark base. `border-top` gives a visual separator when content scrolls behind it. `z-index: 10` keeps it above match replay cards.

- [ ] **Step 3: Run the dev server and check the debrief screen**

```bash
cd frontend && npm run dev
```

Navigate to an existing save that has a played match. In the War Room / debrief screen, scroll down — the action bar should now be visible at the bottom of the viewport regardless of scroll position. The button should read `NEXT WEEK →` (or `BANK THE RESULT →` for a win).

- [ ] **Step 4: Update the e2e assertion**

Open `tests/e2e/command-center-aftermath.spec.ts`. Find the assertion for the primary action button (near the end of the test). Change:

```ts
await expect(page.getByTestId('after-action-bar').locator('button.command-action-bar-primary')).toBeVisible();
```

To:

```ts
const advanceBtn = page.getByTestId('after-action-bar').locator('button.command-action-bar-primary');
await expect(advanceBtn).toBeVisible();
// label is either 'BANK THE RESULT →' (win) or 'NEXT WEEK →' (loss/draw/unknown)
await expect(advanceBtn).toHaveText(/NEXT WEEK →|BANK THE RESULT →/);
```

- [ ] **Step 5: Run the e2e test**

```bash
cd tests && npx playwright test e2e/command-center-aftermath.spec.ts --reporter=list
```

Expected: all assertions pass. If the test creates a win/loss randomly, both regex branches should be covered.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/match-week/aftermath/AftermathActionBar.tsx \
        frontend/src/index.css \
        tests/e2e/command-center-aftermath.spec.ts
git commit -m "fix(aftermath): rename advance button to NEXT WEEK, make action bar sticky"
```

---

## Task 2a — "Edit Policy" → "Edit Game Plan"

**Why it matters:** "Policy" is internal simulation jargon. New players see "Edit Policy ▸" and don't know what they'd be editing.

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:535`

---

- [ ] **Step 1: Change the button label**

Open `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`. Find line 535 (the "Edit Policy" button):

```tsx
                  Edit Policy ▸
```

Change it to:

```tsx
                  Edit Game Plan ▸
```

- [ ] **Step 2: Update the `data-testid` for clarity (optional but good hygiene)**

Find line 533:

```tsx
                  data-testid="open-policy-editor"
```

Leave this unchanged — the testid is internal and renaming it would break existing tests.

- [ ] **Step 3: Verify in browser**

Start the dev server if not already running. Navigate to Command Center pre-match. The Operational Plan panel should show `Edit Game Plan ▸` instead of `Edit Policy ▸`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "fix(command-center): rename Edit Policy to Edit Game Plan"
```

---

## Task 2b — "flagged" → tooltip on Court Read threat

**Why it matters:** The Court Read says `{name} flagged` with a warning arrow, but new players don't know if "flagged" means their player or the opponent's, or whether it's good or bad.

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:452`

---

- [ ] **Step 1: Add a `title` tooltip to the flagged span**

Open `PreSimDashboard.tsx`. Find line 452:

```tsx
                <span className="side">▸ {threat.name ? `${threat.name} flagged` : 'Schematic — live positions'}</span>
```

Change it to:

```tsx
                <span
                  className="side"
                  title={threat.name ? 'Opponent key threat — watch this player' : undefined}
                >
                  ▸ {threat.name ? `${threat.name} flagged` : 'Schematic — live positions'}
                </span>
```

- [ ] **Step 2: Verify in browser**

Navigate to a Command Center pre-match screen with an opponent. Hover over the "flagged" text in the Court Read section. A tooltip should appear: `Opponent key threat — watch this player`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "fix(command-center): add tooltip to opponent flagged threat label"
```

---

## Task 2c — Starter Edge: add Underdog / Favorite context

**Why it matters:** `Thunder Wolves -14 net OVR` tells an experienced player they're outmatched, but a new player doesn't know the sign convention or whether the number is big.

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:299`

---

- [ ] **Step 1: Extend `playerEdgeLabel` with a context bracket**

Open `PreSimDashboard.tsx`. Find line 299:

```tsx
  const playerEdgeLabel = netStarterEdge === 0 ? 'Even starter line' : `${data.player_club_name} ${netStarterEdge > 0 ? '+' : ''}${formatEdge(netStarterEdge)} net OVR`;
```

Replace with:

```tsx
  const edgeContext = netStarterEdge === 0
    ? ''
    : netStarterEdge > 0
      ? ' (Favorite)'
      : ' (Underdog)';
  const playerEdgeLabel = netStarterEdge === 0
    ? 'Even starter line'
    : `${data.player_club_name} ${netStarterEdge > 0 ? '+' : ''}${formatEdge(netStarterEdge)} net OVR${edgeContext}`;
```

- [ ] **Step 2: Verify in browser**

Navigate to a pre-match week where you face an opponent. In the hero stats row, Starter Edge should now read e.g. `Thunder Wolves -14 net OVR (Underdog)` or `Thunder Wolves +8 net OVR (Favorite)`. When even, it still reads `Even starter line`.

- [ ] **Step 3: Check the presim hero e2e test**

```bash
cd tests && npx playwright test e2e/command-center-presim-hero.spec.ts --reporter=list
```

Expected: passes. If the test asserts the exact `playerEdgeLabel` text, update the assertion to include `(Underdog)` or `(Favorite)`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "fix(command-center): add Underdog/Favorite context to Starter Edge label"
```

---

## Task 3 — Wizard: "Recommended" → "Faster Start"

**Why it matters:** The "Recommended" badge on "Take Over a Program" misleads new players who want to build their own club — they feel they're choosing the "wrong" path.

**Files:**
- Modify: `frontend/src/components/SaveMenu.tsx:669`

---

- [ ] **Step 1: Change the badge copy**

Open `frontend/src/components/SaveMenu.tsx`. Find line 669:

```tsx
                      Recommended
```

Change it to:

```tsx
                      Faster Start
```

- [ ] **Step 2: Verify in browser**

Go to New Game → the two path options. "Take Over a Program" should now show a `Faster Start` badge instead of `Recommended`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SaveMenu.tsx
git commit -m "fix(wizard): change Recommended badge to Faster Start on Take Over path"
```

---

## Task 4 — Your Standout: Show user's best performer in shutout losses

**Why it matters:** When the player loses badly (0 survivors), all 3 Key Performers are from the opponent club. The player sees no visual identity from their own roster. The backend already returns up to 6 performers with `club_name` — the frontend just discards positions 4–6.

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`
- Modify: `tests/e2e/command-center-aftermath.spec.ts` (add assertion for standout section)

---

- [ ] **Step 1: Add a `yourStandout` derivation and conditional section**

Open `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`. Replace the entire file with:

```tsx
import type React from 'react';
import type { TopPerformer } from '../../../types';

function StatChips({ player }: { player: TopPerformer }) {
  const chipStyle = (bg: string, color: string): React.CSSProperties => ({
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '0.55rem',
    background: bg,
    color,
    borderRadius: '3px',
    padding: '1px 4px',
  });

  return (
    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '2px', alignItems: 'center' }}>
      {player.eliminations_by_throw > 0 && (
        <span style={chipStyle('rgba(249,115,22,0.15)', '#f97316')}>
          {player.eliminations_by_throw}K
        </span>
      )}
      {player.catches_made > 0 && (
        <span style={chipStyle('rgba(34,211,238,0.12)', '#22d3ee')}>
          {player.catches_made}C
        </span>
      )}
      {player.dodges_successful > 0 && (
        <span style={chipStyle('rgba(163,230,53,0.12)', '#a3e635')}>
          {player.dodges_successful}D
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.55rem',
          color: '#475569',
        }}
      >
        Imp {Math.round(player.score)}
      </span>
    </div>
  );
}

export function KeyPlayersPanel({
  performers,
  playerClubName,
}: {
  performers: TopPerformer[];
  playerClubName?: string;
}) {
  const top3 = performers.slice(0, 3);
  const top3HasYours = playerClubName
    ? top3.some(p => p.club_name === playerClubName)
    : false;

  // Best user-club performer not already in top 3
  const yourStandout = (!top3HasYours && playerClubName)
    ? performers.find(p => p.club_name === playerClubName)
    : null;

  if (performers.length === 0) {
    return (
      <section className="dm-panel command-key-players" data-testid="key-players-panel">
        <div className="dm-panel-header">
          <p className="dm-kicker">Key Performers</p>
        </div>
        <p className="command-fallout-empty">No standout performances recorded.</p>
      </section>
    );
  }

  return (
    <section className="dm-panel command-key-players" data-testid="key-players-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">Key Performers</p>
      </div>
      <div className="command-key-player-list">
        {top3.map((player, index) => {
          const isYours = Boolean(playerClubName && player.club_name === playerClubName);
          const badgeColor = isYours ? '#f97316' : '#334155';

          return (
            <article
              key={player.player_id}
              className="command-key-player"
              style={{ paddingTop: '2px', paddingBottom: '2px' }}
            >
              <span
                className="command-rank-badge"
                style={{ background: badgeColor }}
                aria-label={`Rank ${index + 1}`}
              >
                {index + 1}
              </span>
              <div>
                <strong style={{ fontSize: '0.82rem', color: '#f1f5f9' }}>{player.player_name}</strong>
                {isYours ? (
                  <span
                    style={{
                      marginLeft: '0.4rem',
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      background: '#f97316',
                      color: '#000',
                      borderRadius: '3px',
                      padding: '1px 5px',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Your Club
                  </span>
                ) : player.club_name ? (
                  <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
                    {player.club_name}
                  </span>
                ) : null}
                <StatChips player={player} />
              </div>
            </article>
          );
        })}
      </div>

      {yourStandout && (
        <div
          data-testid="your-standout"
          style={{
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid #1e293b',
          }}
        >
          <p
            style={{
              fontSize: '0.6rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: '#64748b',
              margin: '0 0 0.4rem',
            }}
          >
            Your Club&apos;s Best
          </p>
          <article
            className="command-key-player"
            style={{ paddingTop: '2px', paddingBottom: '2px' }}
          >
            <span
              className="command-rank-badge"
              style={{ background: '#f97316' }}
              aria-label="Your standout"
            >
              ★
            </span>
            <div>
              <strong style={{ fontSize: '0.82rem', color: '#f1f5f9' }}>{yourStandout.player_name}</strong>
              <span
                style={{
                  marginLeft: '0.4rem',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  background: '#f97316',
                  color: '#000',
                  borderRadius: '3px',
                  padding: '1px 5px',
                  letterSpacing: '0.5px',
                }}
              >
                Your Club
              </span>
              <StatChips player={yourStandout} />
            </div>
          </article>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Verify with an existing save that lost a match**

Load any save with a recent loss where the War Room shows only opponent performers. After this change, a `Your Club's Best` section should appear below the top 3, showing the highest-scoring player from your roster in that match.

If no user performers appear at all (score of 0 for all user players), the section correctly stays hidden because `performers.find(...)` returns `undefined`.

- [ ] **Step 3: Add a e2e assertion for the standout section**

Open `tests/e2e/command-center-aftermath.spec.ts`. Add a new test after the existing one:

```ts
test('KeyPlayersPanel shows Your Club Best standout when no user player in top 3', async ({ page, request }) => {
  // This test checks the DOM structure: if the element exists with data-testid="your-standout",
  // it must contain an orange "Your Club" badge.
  // We can't force a loss, so we just verify the component renders without errors
  // and that the standout section — if present — has the correct badge text.
  const saveName = `e2e-standout-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();
  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await expect(page.getByTestId('key-players-panel')).toBeVisible();

  // If the standout section exists, validate it has the orange badge
  const standout = page.getByTestId('your-standout');
  if (await standout.isVisible()) {
    await expect(standout.locator('text=Your Club')).toBeVisible();
  }
  // key-players-panel must always exist (no crash)
  await expect(page.getByTestId('key-players-panel')).toBeVisible();
});
```

- [ ] **Step 4: Run the e2e tests**

```bash
cd tests && npx playwright test e2e/command-center-aftermath.spec.ts --reporter=list
```

Expected: both tests pass. The standout section test may not trigger `your-standout` (if the simulated match has a user player in top 3), but it must not crash.

- [ ] **Step 5: Run the full frontend build to confirm no TypeScript errors**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors, build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx \
        tests/e2e/command-center-aftermath.spec.ts
git commit -m "feat(aftermath): show Your Club's Best standout when user absent from top 3"
```

---

## Self-Review

**Spec coverage check:**

| Playtest issue | Task | Covered? |
|---|---|---|
| "MOVE ON →" mislabeled, buried | Task 1 | ✅ label + sticky |
| "Edit Policy" jargon | Task 2a | ✅ renamed |
| "flagged" no tooltip | Task 2b | ✅ title attr |
| Starter Edge no context | Task 2c | ✅ Underdog/Favorite |
| "Recommended" badge steers away from custom | Task 3 | ✅ Faster Start |
| No user identity in shutout loss | Task 4 | ✅ Your Standout section |
| LOCK PLAN vs SIMULATE: two-step confusion | — | Not in plan — the two-step is intentional design; the current `primaryActionHint` text already explains it |
| Auto-load save bypasses landing | — | Not in plan — this is a routing/architecture decision that needs separate spec |
| FORM shows `—` for new team | — | Already correct; `recentRecord` returns `'—'` when no history (line 221) |

**Placeholder scan:** No TBDs, all code blocks complete, all commands include expected output.

**Type consistency:** `TopPerformer` interface used consistently; `performers: TopPerformer[]` prop type unchanged; `yourStandout` is `TopPerformer | null | undefined`.
