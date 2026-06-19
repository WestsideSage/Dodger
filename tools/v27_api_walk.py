"""V27 Phase 7 — API-level walk (the owner's final acceptance is the browser walk).

Starts a throwaway prod server on port 8010 from an ISOLATED temp working dir
(so the owner's running game on 8000 and its saves are never touched), drives one
pyramid season to the offseason, and confirms the new V27 event + Worlds-crowning
payloads come through the real /api/offseason/beat endpoint UN-STRIPPED — the live
strip-trap check. Purges the walk save on the way out.

Run: python tools/v27_api_walk.py
"""
from __future__ import annotations

import os
import sys
import threading
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

# 1. Isolate saves: chdir to a temp dir BEFORE importing the server so its
#    SAVES_DIR / DEFAULT_DB_PATH land here, never in the owner's repo.
_TMP = Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "v27walk"
_TMP.mkdir(parents=True, exist_ok=True)
os.chdir(_TMP)

import uvicorn  # noqa: E402

from dodgeball_sim.server import (  # noqa: E402
    LAUNCH_TOKEN,
    LAUNCH_TOKEN_HEADER,
    app,
)

PORT = 8010
BASE = f"http://127.0.0.1:{PORT}"
SAVE_NAME = "v27_walk_phase7"


def _request(method: str, path: str, body=None, timeout=120):
    data = None
    headers = {LAUNCH_TOKEN_HEADER: LAUNCH_TOKEN}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def _post(path: str, body=None, timeout=120):
    return _request("POST", path, body, timeout)


def _get(path: str, timeout=60):
    return _request("GET", path, None, timeout)


def _wait_for_server(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            _get("/api/launch-token", timeout=3)
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.3)
    raise RuntimeError(f"server did not bind on {PORT}: {last_exc}")


def _purge_save(save_name: str) -> None:
    try:
        _post("/api/saves/unload", {}, timeout=30)
    except Exception:
        pass
    for fname in (f"{save_name}.db", f"{save_name}.db-wal", f"{save_name}.db-shm"):
        p = _TMP / fname
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass  # Windows may hold the file briefly after unload


def _drive_one_season(seed: int):
    """Create a pyramid takeover (aurora) for the given seed, fast-forward to
    the offseason, and walk the beats. Returns (events_payload, crowning_payload)
    — either may be None. Purges the save."""
    save_name = f"{SAVE_NAME}_{seed}"
    _purge_save(save_name)  # clear any stale file from a prior run
    body = _post(
        "/api/saves/new",
        {"name": save_name, "club_id": "aurora", "root_seed": seed},
    )
    print(f"[walk] career created (aurora takeover, pyramid, seed={seed})")

    ff = _post(
        "/api/command-center/fast-forward",
        {"stop_point": "offseason"},
        timeout=300,
    )
    print(
        f"[walk] fast-forward: weeks={ff.get('weeks_simulated')} "
        f"stop={ff.get('stop_reason')} state={ff.get('next_state')}"
    )

    # If fast-forward stopped short (e.g. the user is in the postseason and
    # must play their matches), keep simulating weeks until the offseason beat
    # appears.
    beat = {}
    for _ in range(40):
        try:
            beat = _get("/api/offseason/beat")
        except RuntimeError:
            beat = {}
        if beat.get("key") is not None:
            break
        _post("/api/command-center/simulate", timeout=120)

    seen_events = None
    seen_crowning = None
    if beat.get("key") is None:
        beat = _get("/api/offseason/beat")
    steps = 0
    while beat.get("key") is not None and steps < 30:
        key = beat.get("key")
        payload = beat.get("payload") or {}
        if key == "events":
            seen_events = payload
            keys = [e.get("event_key") for e in payload.get("events", [])]
            print(f"[walk]   EVENTS beat fired. events={keys}")
        if key == "worlds_champion":
            seen_crowning = payload
            print(
                f"[walk]   WORLDS_CHAMPION beat fired. "
                f"is_first={payload.get('is_first')} "
                f"champion={payload.get('champion_name')}"
            )
        if seen_events is not None and seen_crowning is not None:
            break
        if key == "schedule_reveal":
            break
        try:
            beat = _post("/api/offseason/advance", timeout=120)
        except RuntimeError as exc:
            print(f"[walk]   advance blocked at {key}: {exc}")
            break
        steps += 1

    # Purge this season's save before the next attempt.
    _purge_save(save_name)
    return seen_events, seen_crowning


def main() -> int:
    print(f"[walk] working dir: {_TMP}")
    # Clean any stale walk saves from a prior run (Windows may hold them
    # briefly, hence best-effort).
    for f in _TMP.glob("v27_walk_phase7*.db*"):
        try:
            f.unlink()
        except OSError:
            pass
    print(f"[walk] launch token: {LAUNCH_TOKEN[:8]}…")

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_server()
    print(f"[walk] server up on {PORT}")

    try:
        seen_events = None
        seen_crowning = None
        # Sweep a few seeds: the events beat fires on every pyramid offseason,
        # but the Worlds crowning requires the user to WIN Worlds — try a small
        # seed set so a live crowning lands at least once.
        for seed in (20260618, 20260619, 20260620, 20260621, 20260622):
            print(f"\n[walk] --- seed {seed} ---")
            ev, cr = _drive_one_season(seed)
            if ev is not None and seen_events is None:
                seen_events = ev
            if cr is not None:
                seen_crowning = cr
                break  # got a live crowning — stop sweeping
            if seen_events is not None:
                # events already captured; only keep sweeping for the crowning.
                pass

        # 5. Assertions — the strip-trap check.
        ok = True
        print("\n[walk] === STRIP-TRAP CHECK ===")
        if seen_events is None:
            print("[walk] FAIL: the events beat never fired.")
            ok = False
        else:
            assert seen_events.get("beat_key") == "events"
            evs = seen_events.get("events", [])
            assert isinstance(evs, list) and evs, "events list empty"
            print(f"[walk] events payload keys: {sorted(seen_events.keys())}")
            e = evs[0]
            print(f"[walk] first event keys: {sorted(e.keys())}")
            required = (
                "event_key",
                "event_name",
                "season_id",
                "champion_club_id",
                "champion_club_name",
                "ruleset",
                "purse_k",
                "bracket",
                "meta",
            )
            missing = [k for k in required if k not in e]
            if missing:
                print(f"[walk] FAIL: event payload missing {missing} (strip trap!)")
                ok = False
            else:
                print(f"[walk] PASS: events payload carries all fields un-stripped")
                fired = [e["event_key"] for e in evs]
                print(f"[walk] events that fired: {fired}")
            # Bracket row fields.
            if evs and evs[0].get("bracket"):
                row = evs[0]["bracket"][0]
                row_req = (
                    "round",
                    "home_club_id",
                    "away_club_id",
                    "winner_club_id",
                    "home_club_name",
                    "away_club_name",
                )
                row_missing = [k for k in row_req if k not in row]
                if row_missing:
                    print(f"[walk] FAIL: bracket row missing {row_missing}")
                    ok = False
                else:
                    print(f"[walk] PASS: bracket row carries all fields un-stripped")

        if seen_crowning is None:
            print(
                "[walk] NOTE: the worlds_champion beat did not fire this season "
                "(aurora did not win Worlds on this auto-pilot run). The crowning "
                "payload's strip-trap is pinned end-to-end by the TestClient guard "
                "test (tests/test_v27_phase7_frontend_payloads.py), which drives "
                "the real FastAPI serialization stack with a written Worlds ledger."
            )
        else:
            assert seen_crowning.get("beat_key") == "worlds_champion"
            print(f"[walk] crowning payload keys: {sorted(seen_crowning.keys())}")
            req = ("beat_key", "champion_club_id", "champion_name", "season_id", "is_first")
            missing = [k for k in req if k not in seen_crowning]
            if missing:
                print(f"[walk] FAIL: crowning payload missing {missing} (strip trap!)")
                ok = False
            else:
                print(f"[walk] PASS: crowning payload carries all fields un-stripped")

        print(f"\n[walk] RESULT: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        # 6. Purge every walk save + shut down. The owner's saves on 8000 are
        #    in a different working dir and are never touched.
        try:
            _post("/api/saves/unload", {}, timeout=30)
        except Exception:
            pass
        for f in _TMP.glob("v27_walk_phase7*.db*"):
            try:
                f.unlink()
            except OSError:
                pass
        print("[walk] purged all walk saves.")
        server.should_exit = True
        thread.join(timeout=10)
        print("[walk] server shut down.")


if __name__ == "__main__":
    raise SystemExit(main())
