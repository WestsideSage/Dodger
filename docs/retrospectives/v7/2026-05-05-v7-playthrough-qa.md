# V7 Playthrough QA: Watchable Match Proof Loop

Date: 2026-05-05
Branch / worktree: `feature/codex-next-task` / `Dodgeball Simulator.worktrees/codex`

## Verdict

V7 passes the pre-QA implementation gate. The proof loop is playable in browser, derives evidence from saved match events, and preserves the existing fast result / continue flow.

## What Was Tested

- Created a fresh `V7 QA` save from the browser.
- Accepted the recommended Command Center plan.
- Simulated a Command Center week.
- Opened the saved command match through the new `Open Replay Proof` dashboard action.
- Verified the replay report shows result, tactic, fatigue, liability, key-play, and command-plan evidence lanes.
- Navigated multiple key plays from the replay proof list and next-key controls.
- Verified proof inspector sections for odds and rolls, decision context, tactic context, fatigue, and liability.
- Used the Hub `Play Next Match` flow to confirm direct user-match replay still opens and acknowledges normally.

## Gate Results

- Functional: Pass.
- Playable: Pass.
- AI Playthrough: Pass.
- Simulation Honesty: Pass. Evidence is derived from saved events, roster snapshots, player stats, and command history; no outcome rerun or hidden explanation layer was added.
- Documentation: Pass.

## Issues Found And Fixed

- V7 proof fields were not implemented despite the milestone plan existing.
- Command Center dashboard did not link back to replay proof, so plan-to-replay continuity was incomplete.
- Clean WSL dev setup could not run server tests because `httpx` was missing from dev extras.
- WSL runtime setup was incomplete for frontend/browser work: Node was current only through `nvm`, but non-interactive agent shells still resolved `/usr/bin/node` 18; Chrome and Tkinter were also missing.
- Follow-up report implementation: replay proof summaries, proof tags, tactic copy, fatigue copy, and liability copy were aligned with the V7 narrative pack without changing engine outcomes.
- Follow-up maintenance implementation: pytest now excludes root and frontend `node_modules` folders from collection.

## Verification

- `TMPDIR=/tmp .venv/bin/python -m pytest -q`
  - Result: pass, full suite.
- `npm run lint`
  - Result: pass.
- `npm run build`
  - Result: pass.
- Follow-up 2026-05-06:
  - `TMPDIR=/tmp .venv/bin/python -m pytest tests/test_replay_proof.py tests/test_server.py -q`
    - Result: pass.
  - `TMPDIR=/tmp .venv/bin/python -m pytest -q`
    - Result: pass, full suite.
  - `npm run lint`
    - Result: pass.
  - `npm run build`
    - Result: pass.
- Browser playthrough via Playwright CLI against:
  - Frontend: `http://127.0.0.1:5173/`
  - Backend: `http://127.0.0.1:8000/`

## Environment Notes

- WSL Node now resolves to `v24.15.0` / npm `11.12.1` through `~/.local/bin` wrappers.
- WSL frontend dependencies were refreshed so Linux native optional packages are present.
- Google Chrome was installed for WSL browser playthroughs.
- `python3-tk` was installed so legacy Tkinter-importing tests can collect under WSL.
