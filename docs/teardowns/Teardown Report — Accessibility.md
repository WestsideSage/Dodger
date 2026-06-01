# Teardown Report — Accessibility and Semantic Markup

## Verdict
Accessibility semantics are uneven and risky in the current frontend. The app has meaningful wins: the PolicyEditor radiogroups are real ARIA radios with arrow-key coverage, standings use real tables, V15 TermTip/EmptyState primitives are tested, and the app shell has keyboard coverage. The risk is concentrated in repeated custom interaction patterns: mouse-only rows, partial modal semantics without focus management, tab-like buttons without tab state, and status/error messages that are visible but not reliably announced. Baseline used: W3C WCAG 2.2 keyboard/status guidance and WAI-ARIA APG dialog/tabs patterns.

## Highest-signal findings

### 1. Roster player rows are mouse-only
- Severity: High
- Evidence: [Roster.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/Roster.tsx:359) renders player `<tr>` elements with `onClick={() => setSelectedPlayer(player)}` but no `tabIndex`, `role`, button, or `onKeyDown`.
- Why it matters: Opening player detail is a core roster workflow. WCAG 2.1.1 expects pointer actions to have keyboard equivalents.
- Reproduction / inspection path: Roster -> click a player row opens PlayerDetailModal; keyboard users cannot focus the row.
- Suggested fix direction: Put a real `<button>` in the player/name cell, or make each row keyboard-focusable with Enter/Space handling and an accessible name.
- Regression gate: Playwright: `page.getByRole('button', { name: /open .* player card/i }).focus(); press Enter; expect dialog`.

### 2. Take-over-program club selection is not keyboard operable
- Severity: High
- Evidence: [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:768) renders club options as clickable `<li>` elements with `onClick`, but no role, tab stop, or key handler.
- Why it matters: Save creation/loading is entry-path functionality. Mouse-only club selection can block keyboard-only users from starting a takeover save.
- Reproduction / inspection path: Save Menu -> New Game -> Take Over a Program -> Club list.
- Suggested fix direction: Use native radio inputs inside a `<fieldset>`, or render each club as a `<button aria-pressed>` / `role="radio"` with roving focus.
- Regression gate: Role-based test that tabs into the club selector, changes selection with keyboard, and submits the save.

### 3. Several form labels are visually present but not programmatically associated
- Severity: Medium
- Evidence: In takeover flow, [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:714) labels Save Name without `htmlFor`; [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:819) labels Ruleset without `htmlFor`. By contrast, build-from-scratch identity fields do use `htmlFor`/`id` in [IdentityStep.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/new-game/IdentityStep.tsx:96).
- Why it matters: Screen reader users need labels bound to inputs, and clicking visible labels should focus the control.
- Reproduction / inspection path: Save Menu -> New Game -> Take Over a Program.
- Suggested fix direction: Add stable `id`s to inputs/selects and matching `htmlFor`; use `fieldset`/`legend` for grouped choices.
- Regression gate: Playwright `getByLabel('Save Name')`, `getByLabel('Ruleset')`, `getByLabel('Club')`.

### 4. Modal/dialog focus behavior is incomplete
- Severity: High
- Evidence: Policy editor overlay has `role="dialog"` and `aria-modal="true"` in [PreSimDashboard.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:877), but no initial focus, focus trap, Escape close, or focus restoration. ProgramModal has Escape close and dialog role in [ProgramModal.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/dynasty/history/ProgramModal.tsx:10), but no trap/restore. PlayerDetailModal has overlay behavior in [PlayerDetailModal.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/PlayerDetailModal.tsx:29) but no `role="dialog"` / `aria-modal`.
- Why it matters: WAI-ARIA APG modal dialogs require focus to move inside, stay inside while open, close predictably, and return to the invoking control.
- Reproduction / inspection path: Open Policy Editor, Program Archive modal, or Player Card; tab repeatedly and close.
- Suggested fix direction: Centralize a Dialog component using native `<dialog>` or a tested focus-lock pattern; set `aria-labelledby`, focus title/close button on open, trap Tab/Shift+Tab, close on Escape, restore trigger focus.
- Regression gate: Playwright focus-loop test for every modal family.

### 5. Status and error messages are not consistently exposed to assistive tech
- Severity: Medium
- Evidence: shared [StatusMessage](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/ui.tsx:187) renders a plain `<div>` with no `role="status"` or `role="alert"`. SaveMenu top-level error in [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:291) and StartingRecruitmentStep load error in [StartingRecruitmentStep.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/new-game/StartingRecruitmentStep.tsx:203) are also plain visible blocks. Some newer errors are correct, e.g. [IdentityStep.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/new-game/IdentityStep.tsx:107).
- Why it matters: WCAG 4.1.3 expects status/error messages to be programmatically determinable when focus does not move.
- Reproduction / inspection path: API failure/loading states across roster, standings, office, save menu, recruitment loading.
- Suggested fix direction: `StatusMessage` should map `danger/warning` to `role="alert"` and normal loading/empty states to `role="status"` where appropriate.
- Regression gate: Component test or Playwright assertion for `getByRole('alert')` on API error and `getByRole('status')` on loading/empty states.

### 6. Tabs and segmented controls expose visual selection inconsistently
- Severity: Medium
- Evidence: SaveMenu “Load Game / New Game” buttons in [SaveMenu.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/SaveMenu.tsx:245), Roster “Detailed / Compact” buttons in [Roster.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/Roster.tsx:269), Dynasty Office tabs in [DynastyOffice.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/DynastyOffice.tsx:190), and PlayerDetailModal tabs in [PlayerDetailModal.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/PlayerDetailModal.tsx:74) rely on active classes/color, not `aria-selected`, `aria-pressed`, or tabpanel relationships. Ceremony signing filters do use `role="tab"`/`aria-selected` in [Ceremonies.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/ceremonies/Ceremonies.tsx:652), but lack `aria-controls` / `tabpanel`.
- Why it matters: Screen reader users need the active view state, and keyboard users benefit from predictable tab/segmented-control behavior.
- Reproduction / inspection path: Save Menu, Roster, Dynasty Office, Player Card, Class Report signing filter.
- Suggested fix direction: Use `aria-pressed` for two-state view toggles; use full APG tablist/tab/tabpanel semantics for true tabs.
- Regression gate: Role tests asserting selected state changes after keyboard activation.

### 7. Readiness chips rely on `title` for important detail
- Severity: Medium
- Evidence: readiness gates in [PreSimDashboard.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/match-week/command-center/PreSimDashboard.tsx:716) put `check.detail` only in `title`.
- Why it matters: Tooltips/title text are not reliable for keyboard, touch, or screen reader users. Readiness gates determine whether the player can lock/simulate.
- Reproduction / inspection path: Command Center -> Sim Lock -> readiness chips.
- Suggested fix direction: Render the detail as visible helper text or expose it through `aria-label`/`aria-describedby`; keep the visible `ok/pend` text.
- Regression gate: Assert each readiness chip has an accessible name including ready/pending and the blocking reason.

### 8. Playoff bracket and records/HOF are readable but not fully structured
- Severity: Low
- Evidence: Playoff bracket uses headings, ordered seeds, and text cards in [PlayoffBracket.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/standings/PlayoffBracket.tsx:130), but match cards are generic divs. Records/HOF lists in [LeagueView.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/dynasty/history/LeagueView.tsx:149) are visually list-like div stacks, not lists/tables.
- Why it matters: This is not a keyboard blocker, but structured lists/tables would improve screen-reader scanning for historical/statistical content.
- Reproduction / inspection path: Standings -> playoff bracket; Dynasty Office -> History -> League.
- Suggested fix direction: Use `<ol>/<li>` for bracket rounds/cards and records/HOF lists, or `<table>` where columns are genuinely tabular.
- Regression gate: Role tests for list/listitem or table/row coverage.

## Accessibility Checklist

| Pattern | Expected behavior | Observed behavior | Risk | Fix direction |
|---|---|---|---|---|
| PolicyEditor radio groups | Radiogroup with labelled radios, arrow-key navigation, checked state | Confirmed: `role="radiogroup"`, `role="radio"`, `aria-checked`, roving tab index, e2e arrow-key test | Low | Keep; add disabled-state announcement if needed |
| Match aftermath reveal | Timed reveal can be skipped and respects reduced motion | Confirmed: CeremonyShell has reduced-motion shorter timeout and Skip Reveal button | Low | Add live/status announcement for stage changes only if user testing needs it |
| Replay timeline controls | Collapsible region and readable ordered timeline | Confirmed button uses `aria-expanded`; long timeline gets focusable scroll region | Low | Add `aria-controls` to collapse trigger |
| Action bars and CTAs | Native buttons with clear names and disabled states | Mostly native buttons | Low/Medium | Ensure disabled reasons are visible or described |
| Offseason ceremony beats | Skip/continue operable by button and Space | Confirmed skip path exists | Low | Avoid global click skip causing accidental reveal skip if issue observed |
| Build-from-scratch forms | Labels associated; selections expose state | Identity step mostly strong; roster selection uses button checkbox | Low | Keep label tests; add checkbox count/state tests |
| Save creation/loading | All controls keyboard operable and labelled | Takeover club list and some labels fail | High | Native form controls or ARIA radio pattern |
| Standings tables | Real table with headers; row action keyboard operable | Real table present; row is `tr role="button"` with Enter/Space | Medium | Prefer button inside first cell to preserve row/table semantics |
| Playoff bracket | Bracket readable by round/seed/outcome | Readable, but generic div match cards | Low | Use ordered lists or labelled articles |
| Records/HOF screens | Lists/tables expose history structure | Empty states good; populated records/HOF are div stacks | Low | Use lists or tables |
| Roster/player detail | Rows keyboard operable; modal is proper dialog | Roster rows mouse-only; PlayerDetailModal lacks dialog semantics | High | Button row actions + shared Dialog |
| Modals/dialogs | Initial focus, focus trap, Escape, restore focus | Partial role coverage; no consistent trap/restore | High | Shared modal primitive |
| Error states/alerts | Errors use alert; loading/empty use status | Inconsistent; shared StatusMessage has no role | Medium | Map tone to alert/status |
| Empty states | Programmatically exposed where useful | V15 EmptyState uses `role="status"` | Low | Continue using shared EmptyState |
| Tabs/toggles/disclosures | Selected/pressed state and APG relationships | Inconsistent across SaveMenu/Roster/Dynasty/Player modal | Medium | Use `aria-pressed` or full tablist pattern |
| aria-live regions | Used for meaningful async updates only | Sparse; SimTransition and Policy preview use polite | Low/Medium | Add status roles to actual async results; avoid chatty previews |

## Desktop-first note
All confirmed issues are desktop-critical. They affect keyboard, screen reader, and semantic operability at the supported desktop viewport, not mobile-only layout behavior. I did not propose mobile-first redesigns.

## Confirmed strengths
- PolicyEditor is one of the healthiest controls: [PolicyEditor.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/match-week/command-center/PolicyEditor.tsx:57) implements radiogroups/radios/`aria-checked`, and [tier1_recognition.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/tier1_recognition.spec.ts:39) tests arrow-key movement.
- App shell navigation has explicit keyboard coverage: [App.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/App.tsx:135) keeps the hamburger focusable and restores focus after toggling; [v15-app-shell.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/v15-app-shell.spec.ts:28) tests keyboard operation.
- Standings use a real `<table>` and have keyboard tests for row activation: [LeagueContext.tsx](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/components/LeagueContext.tsx:333), [v15-standings-legibility.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/v15-standings-legibility.spec.ts:39).
- V15 legibility primitives are accessibility-aware: `EmptyState` uses `role="status"`, `PipelineEmblem` uses `role="img"` with an `aria-label`, and e2e coverage verifies TermTip/tooltip behavior in [v15-legibility-surfaces.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/v15-legibility-surfaces.spec.ts:19).
- `npm run lint` completed cleanly.

## Open questions
- Whether to standardize tab-like controls as true APG tabs or as segmented buttons depends on product intent per surface. Roster Detailed/Compact should probably be `aria-pressed`; Dynasty/Player modal likely should be true tabs.
- Whether standings rows should remain row-clickable at all. A dedicated “Open archive” button inside the Club cell would preserve table semantics better.

## Suggested next prompt
Implement a focused accessibility hardening pass: fix save creation club selection/labels, roster row keyboard access, shared dialog focus management, shared status/error roles, and segmented-control selected semantics; add Playwright role-based regression tests for each.

Sources used for baseline: [WCAG 2.2 Keyboard](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), [WCAG 2.2 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [WAI-ARIA APG Modal Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [WAI-ARIA APG Tabs](https://w3c.github.io/wai-website/ARIA/apg/patterns/tabs/).

Goal usage: completed in about 3m 50s.