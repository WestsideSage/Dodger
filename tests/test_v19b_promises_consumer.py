"""V19b promises — the revived lane is mechanical (owner decision log §1.2).

Promise results were evaluated and stored with evidence but consumed by
nothing. The loop is now closed: kept/broken promises feed program
credibility (kept +4, broken -6, capped ±15), credibility sets prospect
interest, and interest strengthens the contested Signing Day offer — so a
manager who breaks promises genuinely finds recruiting harder.
"""
from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema, get_state, set_state
from dodgeball_sim.recruiting_office import PROMISE_STATE_KEY, _credibility


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", 20260610)
    conn.commit()
    return conn


def _score(conn) -> tuple[int, list[str]]:
    season_id = get_state(conn, "active_season_id")
    cred = _credibility(conn, season_id, "aurora", history=[])
    return int(cred["score"]), list(cred["evidence"])


def _seed_promises(conn, *, kept: int, broken: int) -> None:
    rows = []
    for i in range(kept):
        rows.append({
            "player_id": f"kept_{i}", "promise_type": "contender_path",
            "status": "fulfilled", "result": "fulfilled",
            "result_season_id": "season_1", "evidence": "Club reached the playoffs.",
        })
    for i in range(broken):
        rows.append({
            "player_id": f"broken_{i}", "promise_type": "early_playing_time",
            "status": "broken", "result": "broken",
            "result_season_id": "season_1", "evidence": "Player appeared in only 2 matches.",
        })
    set_state(conn, PROMISE_STATE_KEY, json.dumps(rows))
    conn.commit()


def test_kept_promises_raise_credibility_and_broken_cost_more():
    conn = _conn()
    base, base_evidence = _score(conn)
    assert not any("Promise record" in line for line in base_evidence)

    _seed_promises(conn, kept=2, broken=0)
    kept_score, kept_evidence = _score(conn)
    assert kept_score == base + 8
    assert any("2 kept, 0 broken" in line for line in kept_evidence)

    _seed_promises(conn, kept=0, broken=2)
    broken_score, broken_evidence = _score(conn)
    assert broken_score == base - 12  # broken promises cost more than kept earn
    assert any("0 kept, 2 broken" in line for line in broken_evidence)


def test_promise_record_is_capped():
    conn = _conn()
    base, _ = _score(conn)
    _seed_promises(conn, kept=10, broken=0)
    capped, _ = _score(conn)
    assert capped == base + 15  # +4 each, capped at +15
