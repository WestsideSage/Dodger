"""Phase 3 (D3) — scout + confirm-lineup readiness gates through the real
command-center persistence path."""
from __future__ import annotations

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.command_week_service import (
    command_center_payload,
    mark_lineup_confirmed,
    mark_opponent_scouted,
    save_command_center_plan_payload,
)
from dodgeball_sim.persistence import connect


def _career_conn(tmp_path):
    conn = connect(tmp_path / "rg.db")
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def _gate(payload, gate_id):
    gates = payload["plan"]["briefing"]["readiness"]["gates"]
    return next(g for g in gates if g["id"] == gate_id)


def test_fresh_week_starts_with_deliberate_gates_unmet(tmp_path):
    conn = _career_conn(tmp_path)
    payload = command_center_payload(conn)
    readiness = payload["plan"]["briefing"]["readiness"]
    assert _gate(payload, "scout")["ready"] is False
    assert _gate(payload, "confirm_lineup")["ready"] is False
    assert readiness["is_ready_to_lock"] is False


def test_scout_action_clears_scout_gate(tmp_path):
    conn = _career_conn(tmp_path)
    payload = mark_opponent_scouted(conn)
    assert _gate(payload, "scout")["ready"] is True
    # Confirm-lineup remains unmet until its own action.
    assert _gate(payload, "confirm_lineup")["ready"] is False


def test_confirm_lineup_action_clears_lineup_gate(tmp_path):
    conn = _career_conn(tmp_path)
    payload = mark_lineup_confirmed(conn)
    assert _gate(payload, "confirm_lineup")["ready"] is True


def test_both_actions_make_plan_ready_to_lock(tmp_path):
    conn = _career_conn(tmp_path)
    mark_opponent_scouted(conn)
    payload = mark_lineup_confirmed(conn)
    assert payload["plan"]["briefing"]["readiness"]["is_ready_to_lock"] is True


def test_flags_survive_a_tactics_save(tmp_path):
    conn = _career_conn(tmp_path)
    mark_opponent_scouted(conn)
    mark_lineup_confirmed(conn)
    # A later in-week save (same intent) must not silently undo the gates.
    payload = save_command_center_plan_payload(conn, {"intent": "Balanced"})
    assert _gate(payload, "scout")["ready"] is True
    assert _gate(payload, "confirm_lineup")["ready"] is True


def test_saving_a_lineup_edit_confirms_the_lineup(tmp_path):
    conn = _career_conn(tmp_path)
    payload = command_center_payload(conn)
    starter_ids = payload["plan"]["lineup"]["player_ids"]
    saved = save_command_center_plan_payload(
        conn, {"lineup_player_ids": starter_ids}
    )
    assert _gate(saved, "confirm_lineup")["ready"] is True
