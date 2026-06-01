# Teardown Report — Documentation and Source-of-Truth Drift

## Verdict
The docs are useful but uneven and currently agent-risky. The main read order exists, the retired worktree warning is clear, and milestone history is mostly preserved. The risk is concentrated in phase/status drift: V14 is still presented as active implementation work even though source/tests show its tasks landed, V15 is shipped but its archived plans still carry mobile-first gates, and several top-level status links still point to old pre-archive paths. Pare MCP was not available in this session, so I used normal read-only shell inspection.

## Highest-signal findings

### Finding 1
- Severity: High
- Evidence: [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:18) says the active follow-up is Section 4 desktop-first redesign and V15 has shipped; [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:72) still says “V14 … is in progress”; [docs/specs/MILESTONES.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/MILESTONES.md:55) also marks V14 in progress while [docs/specs/MILESTONES.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/MILESTONES.md:56) marks V15 shipped.
- Why it matters: a new agent cannot confidently tell whether the next implementation target is V14, V15 follow-up, Section 4, or the archetype naming spec.
- Reproduction / inspection path: read `docs/STATUS.md` “Current Phase” and “Open Work And Known Gaps,” then compare `docs/specs/MILESTONES.md` rows V14/V15.
- Suggested fix direction: formally close V14 in STATUS/MILESTONES, state that V14 tasks were completed or folded into V15, and name the single active current work item.
- Verification gate: `rg -n "V14.*in progress|Current active follow-up|V15" docs/STATUS.md docs/specs/MILESTONES.md`.

### Finding 2
- Severity: High
- Evidence: [docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/sprint-plan.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/sprint-plan.md:9) says “READY FOR CLAUDE IMPLEMENTATION,” with open tasks through line 89. Source/tests show those tasks exist now: [src/dodgeball_sim/match_explanation.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/match_explanation.py:3), [src/dodgeball_sim/tactical_diff.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/tactical_diff.py:1), [tests/e2e/v14-legibility.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/v14-legibility.spec.ts:5), [tests/test_liability_tags.py](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/test_liability_tags.py:1).
- Why it matters: this is the clearest “shipped work described as pending” trap.
- Reproduction / inspection path: compare V14 sprint tasks against `rg -n "V14|PrimaryFactor|tactical diff|liability" src frontend tests`.
- Suggested fix direction: archive the V14 sprint plan or prepend a shipped/superseded note pointing to STATUS, V15, and current tests.
- Verification gate: no active doc under `docs/specs/` should say V14 is ready for implementation.

### Finding 3
- Severity: High
- Evidence: [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:34), [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:46), [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:47), [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:48), [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:51), and [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:52) point to paths that no longer exist after archival. The files exist under `docs/archive/...`.
- Why it matters: STATUS is the current-state source of truth, so broken links there are high-leverage confusion.
- Reproduction / inspection path: extract backticked `docs/...` paths from `docs/STATUS.md` and run `Test-Path`; the missing active paths correspond to archived files.
- Suggested fix direction: repoint STATUS links to `docs/archive/plans/...`, `docs/archive/specs/...`, `docs/archive/specs/superpowers/...`, and `docs/archive/qa/...`.
- Verification gate: a path-check script over root docs returns no missing real doc references, excluding intentional templates.

### Finding 4
- Severity: Medium
- Evidence: root [AGENTS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/AGENTS.md:67) says current implementation facts belong in STATUS, not root/model docs. [docs/README.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/README.md:8) says AGENTS contains “current implementation facts.” [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:79) repeats the same “current facts” claim for AGENTS. GEMINI says shipped milestone retros/learnings use `docs/retrospectives` and `docs/learnings` [GEMINI.md](/C:/GPT5-Projects/Dodgeball%20Simulator/GEMINI.md:59), while README sends dated artifacts to `docs/archive/retrospectives` and `docs/archive/learnings` [docs/README.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/README.md:37).
- Why it matters: source-of-truth drift starts in the docs that are supposed to prevent it.
- Reproduction / inspection path: compare AGENTS “Anti-Staleness Rule,” README “Authority Order,” STATUS “Sources Of Truth,” and GEMINI “Note on Document Destinations.”
- Suggested fix direction: make README/STATUS say AGENTS owns durable rules and architecture only; reconcile retrospective/learnings destination policy.
- Verification gate: `rg -n "current implementation facts|current facts|docs/retrospectives|docs/learnings|docs/archive/learnings" AGENTS.md CLAUDE.md GEMINI.md docs/README.md docs/STATUS.md`.

### Finding 5
- Severity: Medium
- Evidence: desktop-first is explicit in [AGENTS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/AGENTS.md:85), [docs/STATUS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/STATUS.md:74), and Section 4 README [docs/specs/2026-05-29-section4-design-briefs/README.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/2026-05-29-section4-design-briefs/README.md:26). But hard mobile gates remain in `npm run e2e` scope: [tests/e2e/v15-no-overflow.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/v15-no-overflow.spec.ts:4), [tests/e2e/mobile-roster-accessibility.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/mobile-roster-accessibility.spec.ts:35), [tests/e2e/maximized-playthrough-qa.spec.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/e2e/maximized-playthrough-qa.spec.ts:61). Active Section 4 also has one leftover 390px requirement in [4.8-records-ratified.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/2026-05-29-section4-design-briefs/4.8-records-ratified.md:100).
- Why it matters: agents will keep spending product budget preserving mobile behavior because the verification suite and one active brief still encode it.
- Reproduction / inspection path: `rg -n "390|375|mobile|desktop-first" docs tests/e2e`.
- Suggested fix direction: keep mobile checks only as optional/catastrophic guardrails or rename them as legacy; remove mobile acceptance language from active briefs.
- Verification gate: e2e/docs should name the supported desktop matrix as the required gate and mobile as optional/non-goal.

### Finding 6
- Severity: Medium
- Evidence: active [docs/specs/2026-05-31-archetype-naming-unification-design.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/2026-05-31-archetype-naming-unification-design.md:13) describes a planned implementation. Source shows it is already implemented: [src/dodgeball_sim/models.py](/C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/models.py:281), [frontend/src/legibility/terms.ts](/C:/GPT5-Projects/Dodgeball%20Simulator/frontend/src/legibility/terms.ts:11), and [tests/test_archetype_enum.py](/C:/GPT5-Projects/Dodgeball%20Simulator/tests/test_archetype_enum.py:33). The spec also links to missing active V15 path [docs/specs/2026-05-31-archetype-naming-unification-design.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/specs/2026-05-31-archetype-naming-unification-design.md:3); the target exists in archive.
- Why it matters: this active spec now looks like pending work but source/tests say it is done.
- Reproduction / inspection path: compare the design doc tasks with `models.py`, `recruitment.py`, `identity.py`, `frontend/src/legibility`.
- Suggested fix direction: archive it or add a shipped banner and move it to archive once current STATUS references the result.
- Verification gate: active `docs/specs/` should contain only genuinely active specs plus roadmap/index/guardrails.

## Drift Map

| Doc | Current claim | Source-of-truth conflict | Recommended action |
|---|---|---|---|
| `docs/STATUS.md` | V15 shipped; Section 4 active; V14 in progress | Source/tests show V14 tasks implemented; MILESTONES also lists V15 shipped | Close V14 and name one active phase |
| `docs/specs/MILESTONES.md` | V14 in progress, V15 shipped | STATUS/source imply V14 should be superseded or closed | Update V14 row status and notes |
| `docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/sprint-plan.md` | Ready for implementation | Code/tests implement the listed tasks | Archive or mark shipped/superseded |
| `docs/STATUS.md` | Links old active spec paths | Files moved to `docs/archive/...` | Repoint broken links |
| `docs/README.md` | AGENTS owns current implementation facts | AGENTS says current implementation facts belong in STATUS | Correct authority language |
| `GEMINI.md` | Shipped retros/learnings use `docs/retrospectives` / `docs/learnings` | README and current tree use `docs/archive/...` | Reconcile destination policy |
| Section 4 briefs | Desktop-first, mobile non-goal | 4.8 still has a 390px CTA requirement | Remove/replace with 1280x720 desktop gate |
| `tests/e2e/*mobile*`, `v15-no-overflow.spec.ts` | Mobile overflow as hard e2e gate | AGENTS/STATUS say mobile is non-goal | Reclassify as optional legacy/catastrophic checks |
| `docs/specs/2026-05-31-archetype-naming-unification-design.md` | Planned design | Source/tests show implementation landed | Archive or mark shipped |

## Proposed doc patch plan

1. Update `docs/STATUS.md`: replace the V14 “in progress” item with a closed/superseded note and identify the active work as Section 4 plus any current archetype follow-up only if still open.
2. Update `docs/specs/MILESTONES.md`: mark V14 shipped/closed or superseded into V15, keep V15 shipped, and avoid making the index sound like the current backlog.
3. Move or banner the V14 sprint plan and archetype naming design as shipped/superseded.
4. Repoint broken STATUS and active-spec links to archive paths.
5. Normalize source-of-truth wording in README/STATUS/GEMINI around AGENTS, STATUS, MILESTONES, archive destinations.
6. Replace active mobile acceptance criteria with desktop matrix gates; decide separately whether mobile e2e specs remain optional legacy checks.
7. Add a small path-reference check to the docs cleanup workflow, excluding templates and intentionally historical archive internals.

## Preserve / Archive / Delete Recommendations

| File/path | Recommendation | Reason |
|---|---|---|
| `docs/specs/2026-05-28-v14-first-season-retention-sim-legibility/` | Archive | Useful history, but no longer active implementation truth |
| `docs/specs/2026-05-31-archetype-naming-unification-design.md` | Archive or shipped-banner | Implemented in source/tests; still useful as decision record |
| `docs/specs/2026-05-29-section4-design-briefs/` | Preserve active | Current downstream design work; mostly aligned with desktop-first |
| `docs/archive/specs/v15/2026-05-30-v15-systems-legibility/` | Preserve archived | Useful milestone history despite stale mobile gates |
| `tests/e2e/v15-no-overflow.spec.ts` and mobile e2e specs | Reclassify, do not delete blindly | They may still catch catastrophic overflow, but should not define product direction |
| `docs/teardowns/` untracked local reports | Review before commit/archive | Potential generated audit artifacts; not currently in docs map |
| Historical archive docs with old paths | Preserve | Old links are acceptable as history unless linked from active docs as current truth |

## Confirmed strengths

- The root read order exists and is discoverable in [AGENTS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/AGENTS.md:53), [docs/README.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/README.md:6), and model docs.
- Retired worktree guidance is clear in [AGENTS.md](/C:/GPT5-Projects/Dodgeball%20Simulator/AGENTS.md:99) and [docs/workflows/git-worktree-playbook.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/workflows/git-worktree-playbook.md:3).
- Issue-tracker references are accurate: [CLAUDE.md](/C:/GPT5-Projects/Dodgeball%20Simulator/CLAUDE.md:35) names `WestsideSage/Dodger`, [docs/agents/issue-tracker.md](/C:/GPT5-Projects/Dodgeball%20Simulator/docs/agents/issue-tracker.md:14) says infer from remote, and `git remote -v` confirms `https://github.com/WestsideSage/Dodger.git`.
- Section 4 briefs mostly reflect desktop-first constraints clearly via their README and per-brief desktop gates.

## Open questions

- Should V14 be marked “Shipped” as its own milestone, or “Superseded/Folded into V15”? Source proves the tasks landed, but ownership wording is a product-history choice.
- Should mobile e2e checks remain in the default `npm run e2e` gate as catastrophic safety checks, or move to an explicit legacy/optional command?

## Suggested next prompt

“Apply the documentation drift fixes from the teardown report: close/supersede V14, repoint broken active links to archive paths, reconcile source-of-truth wording, archive shipped active specs, and remove remaining active mobile-first acceptance criteria without deleting useful history.”

Goal completed. Usage recorded by the goal tracker: 185,542 tokens over about 3 minutes 18 seconds.