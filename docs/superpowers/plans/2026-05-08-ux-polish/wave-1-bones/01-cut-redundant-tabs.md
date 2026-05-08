# Subplan 01: Cut Redundant Tabs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Read `../00-MAIN.md` before starting. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reduce the top-level IA from 8 tabs to 4 by removing Hub, Tactics, Schedule, and News, leaving Match Week (still named `command` for now), Roster, Dynasty Office, and Standings.

**Architecture:** Pure subtraction. No content is preserved during this subplan — the killed tabs' redistributions land in later subplans (Wave 2 + Wave 3). This subplan is intentionally lossy in user-facing capability; that's acceptable because the killed surfaces were redundant or low-value (per grilling synthesis).

**Tech Stack:** React/TypeScript only. No backend changes. No new dependencies.

**Files:**
- Modify: `frontend/src/App.tsx` (tab list, type union, kicker map, imports, conditional renders)
- Modify: `frontend/src/components/LeagueContext.tsx` (delete `Schedule` and `NewsWire` exports; keep `Standings`)
- Delete: `frontend/src/components/Hub.tsx`
- Delete: `frontend/src/components/Tactics.tsx`

**Verification gates:**
- `cd frontend && npm run build` exits 0
- `python -m pytest -q` exits 0 (no Python should be touched, but suite must remain green)
- Manual smoke: load app, confirm only 4 tabs render in left rail, each click loads correct surface

---

- [ ] **Step 1: Confirm baseline build is green**

Run: `cd frontend && npm run build`
Expected: PASS (vite + tsc both succeed)

If baseline fails, STOP and report — do not begin destructive changes on a broken baseline.

- [ ] **Step 2: Update the `Tab` type union in `App.tsx`**

In `frontend/src/App.tsx` line 14, replace:

```ts
type Tab = 'command' | 'hub' | 'dynasty' | 'roster' | 'tactics' | 'standings' | 'schedule' | 'news';
```

With:

```ts
type Tab = 'command' | 'dynasty' | 'roster' | 'standings';
```

- [ ] **Step 3: Update the `tabs` array in `App.tsx`**

In `frontend/src/App.tsx` lines 22-31, replace the entire `const tabs` block with:

```ts
const tabs: Array<{ id: Tab; label: string; short: string }> = [
  { id: 'command', label: 'Match Week', short: 'Week' },
  { id: 'dynasty', label: 'Dynasty Office', short: 'Program' },
  { id: 'roster', label: 'Roster', short: 'Team' },
  { id: 'standings', label: 'Standings', short: 'Table' },
];
```

Note: `command` retains its id for backward compatibility with URL `?tab=command` query params; the visible label changes to "Match Week" because that surface is being repurposed in Subplan 02. The id stays so existing bookmarks don't break.

- [ ] **Step 4: Update the `tabKickers` map in `App.tsx`**

In `frontend/src/App.tsx` lines 33-42, replace the entire `tabKickers` block with:

```ts
const tabKickers: Record<Tab, string> = {
  command: 'WAR ROOM',
  dynasty: 'WAR ROOM',
  roster: 'ROSTER LAB',
  standings: 'LEAGUE OFFICE',
};
```

- [ ] **Step 5: Remove imports for killed components**

In `frontend/src/App.tsx` lines 3-9, replace:

```ts
import { CommandCenter } from './components/CommandCenter';
import { Hub } from './components/Hub';
import { DynastyOffice } from './components/DynastyOffice';
import { NewsWire, Schedule, Standings } from './components/LeagueContext';
import { Offseason } from './components/Offseason';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
import { Tactics } from './components/Tactics';
```

With:

```ts
import { CommandCenter } from './components/CommandCenter';
import { DynastyOffice } from './components/DynastyOffice';
import { Standings } from './components/LeagueContext';
import { Offseason } from './components/Offseason';
import { Roster } from './components/Roster';
import { SaveMenu } from './components/SaveMenu';
```

- [ ] **Step 6: Remove conditional renders for killed tabs**

In `frontend/src/App.tsx` around lines 224-231, replace the block of seven `activeTab === ...` lines with the four surviving conditionals. The exact replacement:

```tsx
          {!commandReplay && !commandReplayLoading && activeTab === 'command' && <CommandCenter onOpenReplay={openCommandReplay} />}
          {!commandReplay && !commandReplayLoading && activeTab === 'dynasty' && <DynastyOffice />}
          {!commandReplay && !commandReplayLoading && activeTab === 'roster' && <Roster />}
          {!commandReplay && !commandReplayLoading && activeTab === 'standings' && <Standings />}
```

(Removes the `hub`, `tactics`, `schedule`, and `news` lines.)

- [ ] **Step 7: Delete `Hub.tsx`**

```bash
rm frontend/src/components/Hub.tsx
```

- [ ] **Step 8: Delete `Tactics.tsx`**

```bash
rm frontend/src/components/Tactics.tsx
```

- [ ] **Step 9: Remove `Schedule` and `NewsWire` exports from `LeagueContext.tsx`**

Open `frontend/src/components/LeagueContext.tsx`. Delete:
- The entire `export function Schedule() { ... }` block (starts around line 172)
- The entire `export function NewsWire() { ... }` block (starts around line 287)
- Any helper functions, constants, or imports that were used ONLY by `Schedule` or `NewsWire` (read the file carefully — keep anything `Standings` references)

If a helper is shared between `Standings` and one of the deleted exports, keep it.

- [ ] **Step 10: Run TypeScript build to catch leftover references**

Run: `cd frontend && npm run build`
Expected: PASS. If fail, the error will identify any stale import or reference (likely in `App.tsx` if Step 5 was incomplete, or in `LeagueContext.tsx` if a helper was wrongly deleted in Step 9). Fix the specific error pointed to and re-run.

- [ ] **Step 11: Run Python test suite to confirm backend untouched**

Run: `python -m pytest -q`
Expected: PASS (full suite green)

- [ ] **Step 12: Manual smoke test**

Run: `python -m dodgeball_sim` in one terminal, `cd frontend && npm run dev` in another.

Open the app in a browser. Verify:
- Left navigation rail shows exactly 4 items: Match Week, Dynasty Office, Roster, Standings
- Clicking each loads its surface without console errors
- A URL like `?tab=hub` defaults gracefully to `command` (Match Week) — see `tabFromUrl()` at line 44-47, which falls back when an unknown tab is passed
- No 404s in the browser network tab from removed routes

- [ ] **Step 13: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/LeagueContext.tsx
git rm frontend/src/components/Hub.tsx frontend/src/components/Tactics.tsx
git commit -m "feat(ui): cut Hub, Tactics, Schedule, News tabs (Wave 1 subplan 01)

Reduces top-level IA from 8 tabs to 4 (Match Week, Dynasty Office, Roster,
Standings). Per UX polish initiative, the cut surfaces are either redundant
with surviving tabs or will be folded into them in subsequent subplans.

Refs docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md"
```
