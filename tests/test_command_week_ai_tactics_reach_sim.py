"""WT-11: a persisted AI archetype tactic must reach the simulated match.

The secondary simulate path (``run_simulation_command``, used by the /api/sim*
routes and the playoff sim) loaded ``clubs`` once, then called
``prepare_ai_plans_for_matches`` — which persists fresh ``coach_policy`` rows for
the AI clubs — and finally simulated using the *stale* ``clubs`` dict. A rival
therefore looked adaptive in the persisted data but played its base coach policy
on court, violating decision traceability (the plan shown is not the plan that
runs).

This test pins the fix: it persists an AI club's weekly plan whose tactics
diverge from that club's current base policy, runs ``run_simulation_command``,
and asserts the engine received the *applied* tactic — not the base policy — at
the exact boundary where the match consumes ``club.coach_policy``.
"""
import sqlite3

from dodgeball_sim import command_week_service
from dodgeball_sim.ai_program_manager import build_ai_weekly_plan
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.command_week_service import run_simulation_command
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_clubs,
    load_season,
    save_weekly_command_plan,
)


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_persisted_ai_tactic_reaches_simulated_match(monkeypatch):
    conn = _career_conn()
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)

    # ``lunar`` is a deterministic AI club whose week-1 game (granite_vs_lunar)
    # is simulated under mode="week". Its base policy approach is "patient".
    ai_club_id = "lunar"
    base_policy = load_clubs(conn)[ai_club_id].coach_policy.as_dict()
    assert base_policy["approach"] == "patient", base_policy  # guards determinism

    # Persist an AI weekly plan whose approach diverges from the base policy.
    # ``_apply_command_plan_to_match`` merges plan tactics onto the base, so this
    # single divergent field is what must show up in the engine's clubs dict.
    applied_approach = "aggressive"
    assert applied_approach != base_policy["approach"]  # discriminating
    ai_club = load_clubs(conn)[ai_club_id]
    ai_plan = build_ai_weekly_plan(
        season_id=season_id,
        week=1,
        club=ai_club,
        roster=[],  # lineup not exercised; tactics is what we assert
        standings_row=None,
        total_weeks=season.total_weeks(),
    )
    ai_plan["tactics"] = {**ai_plan["tactics"], "approach": applied_approach}
    save_weekly_command_plan(conn, ai_plan)
    conn.commit()

    # Spy on the engine-facing simulate call to capture the clubs dict it sees.
    # Patch in command_week_service's namespace (it imports the symbol at module
    # top) and call through so standings/cursor side effects still run.
    real_simulate = command_week_service.simulate_scheduled_match
    seen_policies: dict[str, dict] = {}

    def _spy(conn_arg, *, scheduled, clubs, rosters, root_seed, difficulty):
        for cid, club in clubs.items():
            seen_policies[cid] = club.coach_policy.as_dict()
        return real_simulate(
            conn_arg,
            scheduled=scheduled,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )

    monkeypatch.setattr(command_week_service, "simulate_scheduled_match", _spy)

    result = run_simulation_command(conn, {"mode": "week"})

    assert result["status"] == "success"
    assert result["simulated_count"] >= 1
    # The engine must have seen lunar at all (its match was simulated)...
    assert ai_club_id in seen_policies, seen_policies
    # ...and with the APPLIED approach, not the stale base policy. Under the bug
    # this is "patient" (stale clubs dict); under the fix it is "aggressive".
    assert seen_policies[ai_club_id]["approach"] == applied_approach
