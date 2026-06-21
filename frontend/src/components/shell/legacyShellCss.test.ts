import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';

const css = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../index.css'), 'utf8',
);

describe('legacy shell/landing/boot CSS removed (Phase 1)', () => {
  // The FULL dead dm-shell family enumerated in Fix 1 (every dm-shell selector
  // found across the base rules + the four mixed @media blocks: 1283, 4984, 5063,
  // 5193). Substring `includes` is intentional: asserting `.dm-left-nav` absent
  // also proves `.dm-left-nav-logo`/`.dm-left-nav nav[…]` are gone; `.dm-nav-item`
  // also covers `.dm-nav-item:hover`/`.dm-nav-item-active`. The explicit label/
  // header/dot/active entries make the guard self-documenting even so.
  for (const sel of [
    // legacy (non-dm) shell/landing/boot
    '.app-shell', '.left-nav', '.nav-item', '.broadcast-header', '.content-area',
    '.landing-shell', '.landing-card', '.landing-monogram', '.app-boot', '.court-pulse',
    // dead dm-SHELL family (Fix 1 — complete list)
    '.dm-app-shell', '.dm-left-nav', '.dm-left-nav-logo',
    '.dm-nav-item', '.dm-nav-item-active', '.dm-nav-dot',
    '.dm-nav-label-short', '.dm-nav-label-full', '.dm-broadcast-header',
    '.dm-workspace', '.dm-content',
  ]) {
    it(`no longer defines ${sel}`, () => {
      // Selector must not appear as a rule head (allow it inside comments only by
      // requiring a following { on the same logical rule — simplest: absent entirely).
      expect(css.includes(sel)).toBe(false);
    });
  }
  // Guard against over-deletion: the LIVE non-shell dm families that START with
  // `.dm-` but are NOT shell must SURVIVE (they live inside the same mixed @media
  // blocks the dm-shell rules were carved out of). Their owner phases reskin them.
  // (`.dm-kicker` was migrated to components/chrome.module.css and removed here.)
  for (const liveSel of ['.dm-replay-controls', '.dm-hub-hero', '.dm-command-report-lane']) {
    it(`keeps the live non-shell ${liveSel}`, () => {
      expect(css).toContain(liveSel);
    });
  }
  it('keeps the P6/P2 siblings in the 720px breakpoint', () => {
    expect(css).toContain('.fallout-grid');
    expect(css).toContain('.cc-body');
  });
});
