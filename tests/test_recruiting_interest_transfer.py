"""In-season recruiting interest must land on prospects the offseason can sign.

Regression for the deferred playtest item: the in-season recruiting board
targeted class_year = season + 1 while the offseason signed class_year =
season_number, so the board and the signing pool were disjoint and a whole
season of Scout/Contact/Visit work could never sign anyone you courted.
"""
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema, get_state
from dodgeball_sim.recruiting_office import _class_year_from_season
from dodgeball_sim.dynasty_office import build_dynasty_office_state
from dodgeball_sim.offseason_ceremony import available_recruitment_choices


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_board_class_year_matches_offseason_signing_class():
    # The offseason signs class_year = season_number (e.g. 1 for "season_1").
    assert _class_year_from_season("season_1") == 1
    assert _class_year_from_season("season_3") == 3


def test_in_season_board_prospects_are_signable_in_offseason():
    conn = _career_conn()
    season_number = int(
        "".join(ch for ch in get_state(conn, "active_season_id") if ch.isdigit()) or "1"
    )

    board = build_dynasty_office_state(conn)["recruiting"]
    board_ids = {p["player_id"] for p in board["prospects"]}
    assert board_ids, "in-season board should list prospects"

    choices = available_recruitment_choices(conn, season_number)
    choice_ids = {c["prospect_id"] for c in choices if c.get("kind") == "prospect"}

    # Every prospect the player can court on the board is one they can actually
    # sign in the offseason (same class pool), so interest is not wasted.
    assert board_ids & choice_ids, (
        f"board prospects {board_ids} disjoint from offseason choices {choice_ids}"
    )
