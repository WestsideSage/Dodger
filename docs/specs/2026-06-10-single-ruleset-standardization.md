# Single-Ruleset Standardization — foam-official is the one way to play

Date: 2026-06-10. Owner decision (Maurice), recorded verbatim in spirit:
the Foam / No-Sting / Cloth / Generic split is overkill for a video game —
the divisions differ mainly by real-world ball material, "something that
will only be experienced in real life," and a newbie cannot make that
choice meaningfully. Pick the most relevant ruleset, make it the standard,
fold in what must stay. Accepted reasoning: the choice at career creation
was newbie-hostile decision fatigue with retention cost and no gameplay
payoff a player could feel.

## The decision

1. **Foam-official (`official_foam`) is the standard play experience.**
   It was already the default since Phase 4b (D4), it is USA Dodgeball's
   flagship division, and every balance/economy pass since V17 (catch
   economy, WT-20 live rules, V19a consumers, V19b staff preps) was
   measured on it.
2. **The ruleset picker is REMOVED from career creation** — both the
   path-selection screen and the takeover form. Career creation always
   sends `official_foam`. The picker UI is replaced by a single honest
   "How It Plays" card (same ADR-0002-faithful copy the foam option had).
3. **Depth kept, decision removed.** Nothing engine-side is deleted:
   `rulesets.py` profiles (no_sting, cloth, generic), official scoring
   models, the conformance ledger, and every ruleset-parameterized test
   stay. The backend API (`ruleset_selection` on save-create and
   build-from-scratch) still accepts all values — e2e specs and dev tools
   exercise cloth/no-sting through it, and existing saves of any ruleset
   keep working and keep displaying their honest lineage line.

## What this is NOT

- Not a rules-fidelity rollback: enforcement, officiating copy, and the
  conformance matrix are untouched. The fidelity effort's value was the
  enforcement, not the entrance-door picker.
- Not a save migration: legacy generic/cloth/no-sting saves load and play
  exactly as before; SaveMenu still labels them via `rulesetNames.ts`.

## Future use of the retained profiles

The non-foam profiles are candidate material for *flavor events* (e.g. a
"Cloth Invitational" cup week or exhibition modes) where a one-off rules
twist is the point and the player opts in knowingly. Any such feature is
its own milestone; nothing is promised here.

## Touched surfaces (this pass)

- `frontend/src/components/SaveMenu.tsx`: both pickers + the dynamic
  4-way explanation card removed; static foam "How It Plays" card +
  takeover-form ruleset line; creation payloads hard-send
  `official_foam`; `rulesetSelection` state deleted.
- Backend: no changes needed (creation models already defaulted
  `official_foam`; API contract unchanged).
- e2e specs: unchanged — they create careers via the API, which still
  accepts every profile.
