# Stale Report Carry-Forward

Date: 2026-05-07
Source: cleanup of untracked V6/V7 draft reports and scratch simulation files.

## Durable Balance Checks

- Retest lineup liability impact in the current engine before relying on it for major player-facing stakes. An older isolated draft suggested liability penalties could be too weak to shift win rates, but the numbers are stale and must be remeasured against current code.
- Retest initial-possession and alternating-throw fatigue effects if match fairness feels off. An older draft suggested the team order might create a small structural advantage, but this is not current evidence.
- If liabilities are meant to matter, prefer an explicit balance pass with measurable acceptance criteria rather than assuming UI warnings alone make the mechanic meaningful.

## Durable Replay Principles

- Replay-proof and post-match report surfaces should stay strictly observational: read persisted event context, roster snapshots, stats, and command history; do not rerun the engine or mutate match state.
- When event context is missing, show an honest empty state instead of generating a fictional causal explanation.
- Narrative copy should remain clinical and evidence-backed. Good replay text explains target selection, tactics, fatigue, liabilities, and command influence only when saved data supports that explanation.

## Tooling Lessons

- Keep local scratch files out of pytest discovery. Root-level copied tests or helper scripts can make main look broken even when the real implementation lives in another worktree.
- Keep generated folders such as `.claude/worktrees`, `node_modules`, `frontend/node_modules`, output, and caches outside Python test collection.
