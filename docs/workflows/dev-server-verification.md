# Dev-server verification (fresh-process guard)

The dev backend can silently keep serving **stale code** after you edit source:
a lingering `uvicorn`/`python -m dodgeball_sim` process keeps the old build bound
to the port. This has already produced *false* "regressions" — a fix looked
broken in the browser only because the screenshot came from an old process.

So no phase may claim "verified" on browser observation alone. Every browser
verification follows the **standing protocol** from the playtest-fixes plan
(`docs/specs/2026-05-29-playtest-fixes-multi-phase-plan.md`, §0):

1. **Fresh-process guard** — restart on a confirmed-new PID (below).
2. **Backend truth first** — assert the change in `pytest` before trusting the UI.
3. **Then browser proof** — capture screenshot / network / snapshot only after 1+2.

## One command for the fresh-process guard

```powershell
pwsh scripts/dev-restart.ps1          # defaults to port 8000
pwsh scripts/dev-restart.ps1 -Port 8000 -TimeoutSeconds 30
```

[`scripts/dev-restart.ps1`](../../scripts/dev-restart.ps1) does the whole ritual
in one shot:

1. Finds and force-kills any process **listening** on the dev port.
2. Starts a fresh backend (`python -m dodgeball_sim`) in the repo root.
3. Waits until the new process is actually listening (fails fast if it exits).
4. Prints the **old PID(s)** it killed and the **new PID**, and exits non-zero if
   they match (i.e. the restart did not take).

Before any browser check, run it and confirm the printed *New PID* differs from
the *Old PID(s)*. That is the proof the server is fresh — the manual equivalent
is `Get-NetTCPConnection -LocalPort 8000` → `Stop-Process` the old PID → restart
→ confirm a distinct new PID.
