"""WT-9 + WT-10 — the editor-saved lineup must reach the simulated match, and
the inline /simulate override must be validated.

Governing principle (ADR 0002): the six the player SEES must be the six that
PLAYS, and the saved plan/history must match the canonical event log.

WT-9 repro: the Roster Lineup Editor persists ``lineup_default`` (via
``update_manual_lineup_payload``), but a weekly command plan persisted *earlier*
embeds its own ``lineup.player_ids``. The sim path writes that embedded six as a
``match_lineup_override`` — which outranks ``lineup_default`` — so a newer editor
edit was silently shadowed (promote a starter, lock, still field the old six).
``refresh_weekly_plan_context`` now re-resolves the fielded six from the current
``lineup_default`` on every plan reuse, so the editor's choice reaches both the
pre-sim briefing and the engine.

WT-10: the inline ``update["lineup_player_ids"]`` override previously wrote
straight into the plan with no validation, so a non-roster / duplicate /
wrong-count set could be persisted and later lie about the fielded six. It is
now routed through the same validator the editor uses (``apply_manual_lineup``);
an invalid set raises ``LineupViolation`` *before* any persistence.
"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.command_center import build_command_center_state, _lineup_warnings
from dodgeball_sim.command_week_service import (
    command_center_payload,
    save_command_center_plan_payload,
)
from dodgeball_sim.lineup import LineupViolation
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    load_clubs,
    load_command_history,
    load_lineup_default,
    load_weekly_command_plan,
    save_club,
)
from dodgeball_sim.use_cases import simulate_week
from dodgeball_sim.web_status_service import update_manual_lineup_payload

from .factories import make_player


# The curated career ships a 6-player roster (no bench), so any valid lineup is
# the same SET of six and an editor edit can only reorder it — the resolver
# fields the first six regardless of order, making such an edit undetectable.
# To reproduce "promote a *bench* player into the fielded six" (the only edit
# that changes which six PLAY), we append four bench players to the user club.
_BENCH_IDS = ["bench_0", "bench_1", "bench_2", "bench_3"]


def _career_with_bench() -> tuple[sqlite3.Connection, str]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    club_id = get_state(conn, "player_club_id")
    roster = load_club_roster(conn, club_id)
    bench = [
        make_player(pid, accuracy=95, power=95, dodge=95, catch=95)
        for pid in _BENCH_IDS
    ]
    save_club(conn, load_clubs(conn)[club_id], list(roster) + bench)
    conn.commit()
    return conn, club_id


def _fielded_six(conn: sqlite3.Connection, match_id: str, club_id: str) -> list[str]:
    """The canonical fielded six for ``club_id`` from the engine's own record.

    ``player_match_stats`` is keyed by ``record.{home,away}_active_player_ids``
    (see ``extract_match_stats``) — i.e. exactly the six the engine activated,
    not the whole roster. This is the event-log-adjacent truth ADR 0002 wants.
    """
    rows = conn.execute(
        "SELECT player_id FROM player_match_stats WHERE match_id = ? AND club_id = ?",
        (match_id, club_id),
    ).fetchall()
    return sorted(row["player_id"] for row in rows)


# --------------------------------------------------------------------------
# WT-9 — the editor-saved lineup reaches the sim and the recap/history.
# --------------------------------------------------------------------------


def test_editor_saved_lineup_overrides_stale_plan_and_is_fielded():
    conn, club_id = _career_with_bench()

    # Lineup A: the six original starters (no bench). This becomes the STALE six.
    lineup_a = ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "aurora_6"]
    update_manual_lineup_payload(conn, lineup_a)
    conn.commit()

    # Persist a weekly command plan NOW, so it embeds six A. This is the real
    # condition for the bug: the open plan predates the next editor edit.
    save_command_center_plan_payload(conn, {"intent": "Balanced"})
    state = build_command_center_state(conn)
    stale_plan = load_weekly_command_plan(conn, state["season_id"], state["week"], club_id)
    assert stale_plan["lineup"]["player_ids"] == lineup_a  # plan carries the stale six

    # Editor now saves six B: two bench players promoted in for two starters, so
    # B differs from A in the fielded SET (not merely order).
    lineup_b = ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "bench_0", "bench_1"]
    update_manual_lineup_payload(conn, lineup_b)
    conn.commit()
    assert load_lineup_default(conn, club_id)[:6] == lineup_b

    # ADR 0002 "SEES" half: the pre-sim command-center briefing the player reads
    # must already show six B, not the stale plan's A. Same choke point
    # (refresh_weekly_plan_context) feeds this and the sim, so they cannot
    # diverge; this locks that the shown six is re-resolved on plain reload.
    seen = command_center_payload(conn)["plan"]["lineup"]["player_ids"]
    assert seen == lineup_b

    # Simulate WITHOUT re-passing the lineup — exactly what the live frontend
    # does (it never sends lineup_player_ids to /simulate).
    result = simulate_week(conn, update=None)
    assert result["status"] == "success"
    match_id = result["dashboard"]["match_id"]

    # The ENGINE fielded six B (the editor's choice), not the stale plan's six A.
    assert _fielded_six(conn, match_id, club_id) == sorted(lineup_b)
    # Guard the discriminator: without the fix this is the stale A.
    assert _fielded_six(conn, match_id, club_id) != sorted(lineup_a)

    # The recap/history records six B too — the saved plan must not lie.
    history = load_command_history(conn, state["season_id"])
    assert history, "a command-history row should have been saved"
    assert history[-1]["plan"]["lineup"]["player_ids"] == lineup_b
    # And the returned plan (what the recap renders from) agrees.
    assert result["plan"]["lineup"]["player_ids"] == lineup_b


# --------------------------------------------------------------------------
# WT-10 — the inline /simulate override is validated; invalid -> reject,
# persist nothing.
# --------------------------------------------------------------------------


def _baseline_plan_ids(conn: sqlite3.Connection, club_id: str) -> tuple[str, int, list[str], int]:
    """Persist a known-good baseline plan, return its identity + content so a
    test can prove a rejected simulate mutated NOTHING."""
    lineup_a = ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "aurora_6"]
    update_manual_lineup_payload(conn, lineup_a)
    conn.commit()
    save_command_center_plan_payload(conn, {"intent": "Balanced"})
    state = build_command_center_state(conn)
    plan = load_weekly_command_plan(conn, state["season_id"], state["week"], club_id)
    history_len = len(load_command_history(conn, state["season_id"]))
    return state["season_id"], state["week"], plan["lineup"]["player_ids"], history_len


def _assert_rejected_and_nothing_persisted(bad_ids: list[str], expected_reason: str) -> None:
    conn, club_id = _career_with_bench()
    season_id, week, before_lineup, before_history = _baseline_plan_ids(conn, club_id)

    raised: LineupViolation | None = None
    try:
        simulate_week(conn, update={"lineup_player_ids": bad_ids})
    except LineupViolation as exc:
        raised = exc

    # Rejected with the stable machine-readable reason tag the route maps to 400.
    assert raised is not None, f"expected LineupViolation for {expected_reason}"
    assert raised.reason == expected_reason

    # Persist NOTHING: the saved plan's lineup is untouched, no history row was
    # added, and no match was recorded. The raise happens before the first
    # write (save_weekly_command_plan), so the route would return 400 with an
    # unchanged save.
    after_lineup = load_weekly_command_plan(conn, season_id, week, club_id)["lineup"]["player_ids"]
    assert after_lineup == before_lineup
    assert len(load_command_history(conn, season_id)) == before_history
    assert conn.execute("SELECT COUNT(*) AS c FROM match_records").fetchone()["c"] == 0


def test_inline_lineup_with_non_roster_id_is_rejected_and_persists_nothing():
    _assert_rejected_and_nothing_persisted(
        ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "GHOST_999"],
        expected_reason="not_on_roster",
    )


def test_inline_lineup_with_duplicate_is_rejected_and_persists_nothing():
    _assert_rejected_and_nothing_persisted(
        ["aurora_1", "aurora_1", "aurora_3", "aurora_4", "aurora_5", "aurora_6"],
        expected_reason="duplicate",
    )


def test_inline_lineup_with_wrong_count_is_rejected_and_persists_nothing():
    _assert_rejected_and_nothing_persisted(
        ["aurora_1", "aurora_2", "aurora_3"],
        expected_reason="position_count",
    )


def test_inline_lineup_with_valid_six_is_fielded_via_simulate_override():
    """The valid inline-override path still works: an explicit, valid six passed
    to simulate is the one fielded (this is the deliberate in-week override that
    must outrank the re-resolved lineup_default)."""
    conn, club_id = _career_with_bench()

    # Editor default is the original six; the inline override promotes bench.
    update_manual_lineup_payload(
        conn, ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "aurora_6"]
    )
    conn.commit()
    save_command_center_plan_payload(conn, {"intent": "Balanced"})

    override_six = ["aurora_1", "aurora_2", "aurora_3", "bench_0", "bench_1", "bench_2"]
    result = simulate_week(conn, update={"lineup_player_ids": override_six})
    match_id = result["dashboard"]["match_id"]

    assert _fielded_six(conn, match_id, club_id) == sorted(override_six)
    # The persisted plan + recap reflect the override the engine actually used,
    # and player_ids/players stay mutually consistent (no half-updated dict).
    assert result["plan"]["lineup"]["player_ids"] == override_six
    assert [p["id"] for p in result["plan"]["lineup"]["players"]] == override_six


# --------------------------------------------------------------------------
# WT-9 follow-up (adversarial finding) — re-resolving the fielded six must also
# recompute the sibling readiness `warnings`, or the briefing + persisted history
# keep describing the STALE six (naming players who are not starting).
# --------------------------------------------------------------------------


def test_warnings_track_the_fielded_six_after_a_lineup_edit():
    conn, club_id = _career_with_bench()

    # A deliberately weak player (overall well under 55) the editor will field.
    weak = make_player("bench_weak", accuracy=35, power=35, dodge=35, catch=35)
    save_club(conn, load_clubs(conn)[club_id], list(load_club_roster(conn, club_id)) + [weak])
    conn.commit()

    # Six A: the original strong starters, no weak player. Persist a plan under
    # "Win Now" NOW, so its warnings are computed for six A.
    lineup_a = ["aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "aurora_6"]
    update_manual_lineup_payload(conn, lineup_a)
    conn.commit()
    save_command_center_plan_payload(conn, {"intent": "Win Now"})

    # Editor saves six B: five strong bench + the weak player, sharing only
    # aurora_1 with A. Under "Win Now" a sub-55 STARTER is flagged "weak starter".
    lineup_b = ["bench_0", "bench_1", "bench_2", "bench_3", "bench_weak", "aurora_1"]
    update_manual_lineup_payload(conn, lineup_b)
    conn.commit()

    payload = command_center_payload(conn)
    assert payload["plan"]["lineup"]["player_ids"] == lineup_b

    warnings = payload["plan"]["warnings"]
    # The discriminator: "Bench_Weak ... weak starter" can only be produced when
    # bench_weak is a STARTER (six B). A stale warnings set (computed for six A,
    # which has no bench_weak) could NEVER contain it — so this assertion is the
    # exact thing that fails on the pre-fix (stale-warnings) behavior.
    assert any("Bench_Weak" in w for w in warnings), warnings
    # Invariant: the shown warnings equal a fresh recompute for the fielded six.
    roster = list(load_club_roster(conn, club_id))
    assert warnings == _lineup_warnings(roster, lineup_b, "Win Now", payload["plan"].get("tactics") or {})


def test_simulate_route_maps_invalid_inline_lineup_to_400():
    """WT-10 route mapping: an invalid inline lineup override surfaces as a clean
    400 (the LineupViolation.reason tag) at /api/command-center/simulate, not an
    uncaught 500 — mirroring the /api/lineup precedent."""
    conn, _club_id = _career_with_bench()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app, raise_server_exceptions=False)
        resp = client.post(
            "/api/command-center/simulate",
            json={
                "lineup_player_ids": [
                    "aurora_1", "aurora_2", "aurora_3", "aurora_4", "aurora_5", "GHOST_999"
                ]
            },
        )
    finally:
        server.app.dependency_overrides.clear()

    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "not_on_roster"
