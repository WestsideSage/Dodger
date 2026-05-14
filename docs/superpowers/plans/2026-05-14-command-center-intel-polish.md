# Command Center Intel Panel Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the Opponent Intel panel in PreSimDashboard by replacing a bare `key_matchup` text line with a structured Key Threat card and replacing the plain week timeline rows with styled icon pill cards.

**Architecture:** All changes are contained to a single TSX component and the global CSS file. No backend or API changes. The `key_matchup` string is parsed client-side with a small helper function. Three new CSS class families are introduced; the old `.command-week-timeline-inline` class is removed from the JSX (its CSS rule stays but becomes unused dead code — acceptable).

**Tech Stack:** React 18, TypeScript, plain CSS custom properties (no CSS-in-JS)

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` | Modify | `humanize()` fix, `parseKeyMatchup()` helper, Key Threat card JSX, icon pill timeline JSX |
| `frontend/src/index.css` | Modify | New `.command-threat-card*` classes, new `.command-week-pills` class |

---

## Task 1: Fix `humanize()` to sentence-case

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

Context: `humanize()` currently returns all-lowercase (e.g. `"fundamentals"`). It should return sentence-cased text (e.g. `"Fundamentals"`). This affects the Practice and Development labels in the plan summary and the new timeline pills.

- [ ] **Step 1: Open the file and locate `humanize()`**

It's at line ~18 of `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`:

```typescript
function humanize(value: string | undefined) {
  return value ? value.replaceAll('_', ' ').toLowerCase() : 'not set';
}
```

- [ ] **Step 2: Replace with sentence-cased version**

```typescript
function humanize(value: string | undefined) {
  if (!value) return 'Not set';
  const s = value.replaceAll('_', ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
```

- [ ] **Step 3: Build to verify no TypeScript errors**

Run from `frontend/`:
```
npm run build
```
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "fix: sentence-case humanize() output in PreSimDashboard"
```

---

## Task 2: Add `parseKeyMatchup()` helper and Key Threat Card CSS

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- Modify: `frontend/src/index.css`

The `key_matchup` string arrives as `"Mika Keene, Tactical, 65 OVR"`. We parse it into name / role / ovr. The card layout is a flex row: icon circle · name+role column (flex:1) · OVR stat column (right, separated by a subtle border).

- [ ] **Step 1: Add `parseKeyMatchup()` helper to PreSimDashboard.tsx**

Add this function after the `humanize()` function (around line 22):

```typescript
function parseKeyMatchup(raw: string) {
  const parts = raw.split(',').map(s => s.trim());
  if (parts.length >= 3) {
    const name = parts[0];
    const role = parts[1];
    const ovrMatch = parts[2].match(/(\d+)/);
    return { name, role, ovr: ovrMatch ? ovrMatch[1] : null };
  }
  return { name: raw, role: null, ovr: null };
}
```

- [ ] **Step 2: Add Key Threat Card CSS to index.css**

Add the following block after the `.command-fit-note.is-warning` rule (around line 2736 in `frontend/src/index.css`):

```css
/* Key Threat Card */
.command-threat-card {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  background: rgba(248,113,113,0.07);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 6px;
  padding: 0.7rem 0.9rem;
  margin-bottom: 0.75rem;
}

.command-threat-card-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(248,113,113,0.15);
  font-size: 1rem;
}

.command-threat-card-body {
  flex: 1;
  min-width: 0;
}

.command-threat-card-kicker {
  display: block;
  color: #f87171;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.2rem;
}

.command-threat-card-name {
  display: block;
  color: #f8fafc;
  font-size: 0.9rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.command-threat-card-role {
  display: inline-block;
  background: rgba(30,41,59,0.8);
  color: #94a3b8;
  font-size: 0.62rem;
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.command-threat-card-ovr {
  flex-shrink: 0;
  text-align: center;
  padding-left: 0.85rem;
  border-left: 1px solid rgba(248,113,113,0.2);
}

.command-threat-card-ovr strong {
  display: block;
  color: #f87171;
  font-size: 1.6rem;
  font-weight: 800;
  line-height: 1;
  font-family: var(--font-mono-data);
}

.command-threat-card-ovr span {
  display: block;
  color: #64748b;
  font-size: 0.58rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 0.2rem;
}
```

- [ ] **Step 3: Replace the `key_matchup` paragraph with the Key Threat Card in PreSimDashboard.tsx**

Find this block in the `command-intel-grid` section (around line 310):

```tsx
<p className="command-muted-copy">{details.key_matchup}</p>
```

Replace it with:

```tsx
{(() => {
  const threat = parseKeyMatchup(details.key_matchup);
  return (
    <div className="command-threat-card">
      <div className="command-threat-card-icon">⚠️</div>
      <div className="command-threat-card-body">
        <span className="command-threat-card-kicker">Key Threat</span>
        <span className="command-threat-card-name">{threat.name}</span>
        {threat.role && <span className="command-threat-card-role">{threat.role}</span>}
      </div>
      {threat.ovr && (
        <div className="command-threat-card-ovr">
          <strong>{threat.ovr}</strong>
          <span>OVR</span>
        </div>
      )}
    </div>
  );
})()}
```

- [ ] **Step 4: Add "SCOUTING" kicker label above the recommendation text**

Find the second `command-muted-copy` paragraph (the scouting recommendation, around line 311):

```tsx
<p className="command-muted-copy">{plan.recommendations[0]?.text ?? 'No recommendation returned.'}</p>
```

Replace it with:

```tsx
<p className="command-field-label" style={{ marginBottom: '0.3rem' }}>Scouting</p>
<p className="command-muted-copy">{plan.recommendations[0]?.text ?? 'No recommendation returned.'}</p>
```

- [ ] **Step 5: Build to verify no TypeScript errors**

Run from `frontend/`:
```
npm run build
```
Expected: build succeeds, no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx frontend/src/index.css
git commit -m "feat: add Key Threat card to Opponent Intel panel"
```

---

## Task 3: Replace week timeline with icon pill cards

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- Modify: `frontend/src/index.css`

The current timeline uses `.command-week-timeline.command-week-timeline-inline` — a shared CSS class that applies a plain grid. We replace the JSX with a new `.command-week-pills` container and three pill divs. The old CSS class is removed from the JSX only (the CSS rule stays as dead code, harmless).

- [ ] **Step 1: Add `.command-week-pills` CSS to index.css**

Add after the `.command-threat-card-ovr span` rule added in Task 2:

```css
/* Week Timeline Pill Cards */
.command-week-pills {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.95rem;
}

.command-week-pill {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  background: rgba(30,41,59,0.6);
  border-radius: 6px;
  padding: 0.7rem 0.75rem;
}

.command-week-pill.is-matchday {
  background: rgba(34,211,238,0.08);
  border: 1px solid rgba(34,211,238,0.25);
}

.command-week-pill-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.command-week-pill-label {
  display: block;
  color: #64748b;
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.command-week-pill.is-matchday .command-week-pill-label {
  color: #22d3ee;
}

.command-week-pill-value {
  display: block;
  color: #f8fafc;
  font-weight: 600;
  font-size: 0.74rem;
}
```

- [ ] **Step 2: Replace the timeline JSX in PreSimDashboard.tsx**

Find this block (around line 327):

```tsx
<div className="command-week-timeline command-week-timeline-inline">
  <div><strong>Practice</strong><span>{humanize(plan.department_orders?.training)}</span></div>
  <div><strong>Team Meeting</strong><span>{currentApproach} review</span></div>
  <div><strong>Match Day</strong><span>vs {plan.opponent.name}</span></div>
</div>
```

Replace it with:

```tsx
<div className="command-week-pills">
  <div className="command-week-pill">
    <span className="command-week-pill-icon">🏋️</span>
    <div>
      <span className="command-week-pill-label">Practice</span>
      <span className="command-week-pill-value">{humanize(plan.department_orders?.training)}</span>
    </div>
  </div>
  <div className="command-week-pill">
    <span className="command-week-pill-icon">🎯</span>
    <div>
      <span className="command-week-pill-label">Meeting</span>
      <span className="command-week-pill-value">{currentApproach} Review</span>
    </div>
  </div>
  <div className="command-week-pill is-matchday">
    <span className="command-week-pill-icon">⚡</span>
    <div>
      <span className="command-week-pill-label">Match Day</span>
      <span className="command-week-pill-value">vs {plan.opponent.name}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Build to verify no TypeScript errors**

Run from `frontend/`:
```
npm run build
```
Expected: build succeeds, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx frontend/src/index.css
git commit -m "feat: replace week timeline rows with icon pill cards"
```

---

## Self-Review Notes

- **Spec coverage:** `humanize()` fix ✓ | Key Threat card with OVR stat ✓ | SCOUTING label ✓ | Icon pill timeline ✓ | Graceful degradation for unparseable `key_matchup` ✓ (role and ovr are conditionally rendered)
- **No placeholders** — all code blocks are complete
- **Type consistency** — `parseKeyMatchup` returns `{ name, role, ovr }` consistently used in Task 2 JSX
- **CSS class naming** is consistent across Task 2 and Task 3 additions
