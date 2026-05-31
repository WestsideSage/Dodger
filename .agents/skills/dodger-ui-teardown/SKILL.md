---
name: dodger-ui-teardown
description: Use for Dodgeball Manager UI/UX audits, frontend debugging, spacing/padding review, copy critique, accessibility checks, and Phase 8 design brief verification.
---

When auditing Dodgeball Manager UI:

1. Treat the product as desktop-first.
2. Primary audit viewport: 1440x900.
3. Required desktop stress viewport: 1366x768.
4. Minimum supported desktop viewport: 1280x720.
5. Large desktop polish viewport: 1920x1080.
6. Mobile viewports are non-goals unless Maurice explicitly requests them.
7. If checking mobile, only report catastrophic breakage such as unusable navigation, total horizontal overflow, or blocked critical actions. Do not redesign for mobile.
8. Prioritize:
   - desktop information density
   - management-sim dashboard clarity
   - scanability across panels
   - hierarchy above the fold
   - spacing rhythm
   - table/card readability
   - keyboard/mouse interaction
   - copy clarity
   - semantic markup and accessibility
9. Do not collapse rich desktop layouts into mobile-style stacked cards unless the desktop viewport truly requires it.