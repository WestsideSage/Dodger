# Subplan 02: Build Match Week Shell (State-Driven)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first. Depends on Subplan 01 (must merge first).

**Goal:** Rename `CommandCenter.tsx` to `MatchWeek.tsx` and convert it to a state-driven host that renders one of three modes — `pre-sim`, `post-sim`, or `offseason` — based on save state.

**Architecture:** This subplan creates the shell only. Each mode is a stub renderer with placeholder content + the correct primary CTA. Wave 2 fills in the rich content (hero matchup card, Aftermath blocks, etc.). The existing CommandCenter functionality (intent dropdown, dev focus dropdown, sim button, last replay link) is preserved inside the `pre-sim` mode stub during Wave 1 so the game remains playable. Subplans 03 and 04 will then surgically remove `dev focus` and `department orders` from this stub.

**Tech Stack:** React/TypeScript only. No backend changes.

**Files:**
- Rename: `frontend/src/components/CommandCenter.tsx` → `frontend/src/components/MatchWeek.tsx`
- Modify: `frontend/src/App.tsx` (import, render call, offseason routing collapse)
- (No file deletion — this is a rename, not a recreation)

**Verification gates:**
- `cd frontend && npm run build` exits 0
- `python -m pytest -q` exits 0
- Manual smoke: app loads on Match Week tab, all three modes render correctly for their save state, sim button still works, offseason flow still reaches `Offseason` content.

---

- [ ] **Step 1: Confirm Subplan 01 is merged**

Run: `git log --oneline -5`
Expected: a recent commit referencing "subplan 01" / "cut Hub, Tactics, Schedule, News tabs". If not present, STOP — Subplan 01 must merge first.

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 2: Rename `CommandCenter.tsx` → `MatchWeek.tsx`**

```bash
git mv frontend/src/components/CommandCenter.tsx frontend/src/components/MatchWeek.tsx
```

- [ ] **Step 3: Rename the exported function inside the file**

In `frontend/src/components/MatchWeek.tsx`, find:

```ts
export function CommandCenter({ onOpenReplay }: { onOpenReplay?: (matchId: string) => void }) {
```

Replace with:

```ts
type MatchWeekMode = 'pre-sim' | 'post-sim' | 'offseason';

export function MatchWeek({ onOpenReplay, mode }: { onOpenReplay?: (matchId: string) => void; mode: MatchWeekMode }) {
```

- [ ] **Step 4: Add the mode-router scaffold inside the component**

At the top of the component body (right after the existing `useState` declarations and before any data fetching), insert a placeholder that the upcoming steps will refine. For now, leave the existing render path in place — we will branch on `mode` in Step 7.

- [ ] **Step 5: Extract the existing render JSX into a helper named `renderPreSimMode`**

Find the `return (...)` block at the bottom of the component (currently starts around the original line 96 with `<div ... data-testid="weekly-command-center">`). Cut the entire JSX block and paste it into a new function defined inside the component body:

```tsx
const renderPreSimMode = () => {
  if (loading && !data) return <StatusMessage title="Loading match week">Opening the weekly desk.</StatusMessage>;
  if (error) return <StatusMessage title="Match week unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return null;

  const plan = data.plan;
  const dashboard = result?.dashboard || data.latest_dashboard;

  return (
    /* the existing JSX block, unchanged */
  );
};
```

Move the `if (loading...) / if (error) / if (!data) / const plan / const dashboard` lines from the top-level component body INTO this helper as shown above. They should no longer execute at the component top level (mode detection comes first now).

- [ ] **Step 6: Add stub renderers for `post-sim` and `offseason`**

Below `renderPreSimMode`, add:

```tsx
const renderPostSimMode = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }} data-testid="match-week-post-sim">
    <PageHeader eyebrow="Match Week" title="Aftermath" description="Match results — full layout in Wave 2." />
    <div className="dm-panel">
      <p>Post-sim aftermath stub. Subplan 06 will replace this with sequenced reveal blocks (Headline, Match Card, Player Growth, Standings Shift, Recruit Reactions).</p>
      {result && (
        <ActionButton onClick={() => { setResult(null); load(); }}>Advance to Next Week</ActionButton>
      )}
    </div>
  </div>
);

const renderOffseasonMode = () => (
  <div data-testid="match-week-offseason">
    {/* The Offseason component is rendered by the parent App in offseason save states.
        This stub exists for completeness; in Wave 1 the parent still routes offseason
        to <Offseason /> directly above the tab system. Subplan 02 step 9 collapses
        that into MatchWeek so this stub becomes the actual offseason content. */}
    <PageHeader eyebrow="Match Week" title="Offseason" description="Offseason mode — implementation lives in Subplan 02 step 9 + Wave 3 ceremony subplan." />
  </div>
);
```

You'll need to import `ActionButton` if it isn't already (it is — see existing imports).

- [ ] **Step 7: Replace the component's main return with mode-routing**

At the bottom of the component, replace whatever is now there with:

```tsx
  if (mode === 'offseason') return renderOffseasonMode();
  if (mode === 'post-sim') return renderPostSimMode();
  return renderPreSimMode();
}
```

- [ ] **Step 8: Update `App.tsx` import and render**

In `frontend/src/App.tsx`:

Replace import line:
```ts
import { CommandCenter } from './components/CommandCenter';
```
with:
```ts
import { MatchWeek } from './components/MatchWeek';
```

Replace render line (around line 224 after Subplan 01):
```tsx
{!commandReplay && !commandReplayLoading && activeTab === 'command' && <CommandCenter onOpenReplay={openCommandReplay} />}
```
with:
```tsx
{!commandReplay && !commandReplayLoading && activeTab === 'command' && (
  <MatchWeek
    onOpenReplay={openCommandReplay}
    mode={result ? 'post-sim' : 'pre-sim'}
  />
)}
```

The `result` reference here doesn't exist in `App.tsx`'s scope — instead, lift the post-sim signal. For Wave 1 simplicity, we use a session-only flag:

Add to `App.tsx` state (near the other useState calls, around line 51-53):

```ts
const [postSimThisSession, setPostSimThisSession] = useState(false);
```

Then pass it down:

```tsx
<MatchWeek
  onOpenReplay={openCommandReplay}
  mode={postSimThisSession ? 'post-sim' : 'pre-sim'}
  onSimComplete={() => setPostSimThisSession(true)}
  onAdvanceWeek={() => setPostSimThisSession(false)}
/>
```

Update the `MatchWeek` props type accordingly:

```ts
export function MatchWeek({
  onOpenReplay,
  mode,
  onSimComplete,
  onAdvanceWeek,
}: {
  onOpenReplay?: (matchId: string) => void;
  mode: MatchWeekMode;
  onSimComplete?: () => void;
  onAdvanceWeek?: () => void;
}) {
```

In the existing `simulate` function inside `MatchWeek`, after `setResult(payload)`, also call `onSimComplete?.()`. In `renderPostSimMode`, the Advance button calls `onAdvanceWeek?.()` (in addition to existing `setResult(null); load();`).

- [ ] **Step 9: Collapse the `OFFSEASON_STATES` branch into Match Week**

In `App.tsx`, find the block starting around line 130 (`if (screen === 'offseason')`). That branch currently renders `<Offseason />` directly, bypassing the tab system.

Replace the offseason `screen` value's render path so it ALSO uses the tab shell, but forces `activeTab = 'command'` and passes `mode='offseason'` to `MatchWeek`. Inside `MatchWeek`'s `renderOffseasonMode`, render the existing `<Offseason />` component as the content:

In `MatchWeek.tsx`:
```ts
import { Offseason } from './Offseason';

const renderOffseasonMode = () => (
  <div data-testid="match-week-offseason">
    <Offseason />
  </div>
);
```

In `App.tsx`, remove the entire `if (screen === 'offseason') { return ( ... ); }` block (lines 130-168 approximately). Instead, fold offseason detection into the mode prop:

```tsx
<MatchWeek
  onOpenReplay={openCommandReplay}
  mode={
    screen === 'offseason' ? 'offseason'
    : postSimThisSession ? 'post-sim'
    : 'pre-sim'
  }
  onSimComplete={() => setPostSimThisSession(true)}
  onAdvanceWeek={() => setPostSimThisSession(false)}
/>
```

When `screen === 'offseason'`, force `activeTab` to `'command'` so the tab rail stays consistent (offseason routes show the Match Week tab as active):

Just before the main `return`, add:
```tsx
const effectiveActiveTab: Tab = screen === 'offseason' ? 'command' : activeTab;
```
And replace `activeTab` with `effectiveActiveTab` everywhere it appears in the JSX rendering branches and the nav button `className` logic. (Don't replace it in the `setActiveTab` calls — those still write to the underlying state.)

- [ ] **Step 10: Run TypeScript build**

Run: `cd frontend && npm run build`
Expected: PASS.

If failures occur, common causes:
- Missing import for `Offseason` in `MatchWeek.tsx` (Step 9)
- Type mismatch on `MatchWeekMode` in `App.tsx` (verify spelling)
- Stale reference to `<CommandCenter>` left somewhere (search the file)

- [ ] **Step 11: Run Python test suite**

Run: `python -m pytest -q`
Expected: PASS (no Python touched, suite must remain green).

- [ ] **Step 12: Manual smoke test — three modes**

Start backend + frontend (`python -m dodgeball_sim` and `cd frontend && npm run dev`).

For each save state:
- **In-season pre-sim**: load a save mid-season, before simming the week. Match Week tab should render the existing CommandCenter UI (now inside `renderPreSimMode`). Sim button works.
- **In-season post-sim**: click Sim. After completion, the Match Week pane should switch to the post-sim stub (`data-testid="match-week-post-sim"`). The Advance to Next Week button returns to pre-sim.
- **Offseason**: load (or advance to) a save in `season_complete_offseason_beat` etc. Match Week tab should render the offseason stub which embeds the existing `<Offseason />` component.

If any mode fails to render, fix at the source of the bad mode-detection logic in App.tsx.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/MatchWeek.tsx
git commit -m "feat(ui): convert CommandCenter to state-driven Match Week shell (Wave 1 subplan 02)

Renames CommandCenter.tsx to MatchWeek.tsx and routes between three modes
(pre-sim, post-sim, offseason) from a single component. Pre-sim retains
existing CommandCenter UI verbatim during Wave 1; post-sim is a stub for
Wave 2's Aftermath blocks; offseason embeds the existing Offseason flow,
removing the parallel IA branch in App.tsx.

Refs docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md"
```
