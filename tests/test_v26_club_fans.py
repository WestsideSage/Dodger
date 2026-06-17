"""V26 The Crowd — Phase 2: fan tables + append-only fan ledger + club fan gains."""
import sqlite3

from dodgeball_sim.persistence import CURRENT_SCHEMA_VERSION, create_schema
from dodgeball_sim import fan_ledger as fl


def _conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


# --- Task 2.1: schema migration -------------------------------------------------

def test_schema_is_v19_with_fan_tables():
    assert CURRENT_SCHEMA_VERSION == 19
    conn = _conn()
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"club_fans", "player_fans", "fan_ledger"} <= tables


def test_migration_is_idempotent():
    conn = _conn()
    create_schema(conn)  # second run must not error
    assert CURRENT_SCHEMA_VERSION == 19


# --- Task 2.2: append-only ledger -----------------------------------------------

def test_add_fans_bumps_total_and_writes_a_receipt():
    conn = _conn()
    assert fl.club_fans(conn, "aurora") == 0
    total = fl.add_fans(conn, "aurora", 400, "season_1", "promotion", "+400 after the promotion final")
    assert total == 400 and fl.club_fans(conn, "aurora") == 400
    receipts = fl.load_fan_receipts(conn, entity_type="club", entity_id="aurora")
    assert len(receipts) == 1
    assert receipts[0]["delta"] == 400 and receipts[0]["running_total"] == 400
    assert "promotion final" in receipts[0]["receipt"]


def test_running_total_accumulates_across_receipts():
    conn = _conn()
    fl.add_fans(conn, "aurora", 100, "season_1", "win", "won")
    fl.add_fans(conn, "aurora", 250, "season_1", "title", "champions")
    assert fl.club_fans(conn, "aurora") == 350
    receipts = fl.load_fan_receipts(conn, entity_type="club", entity_id="aurora")
    assert [r["running_total"] for r in receipts] == [100, 350]


def test_player_followers_are_independent():
    conn = _conn()
    fl.add_followers(conn, "star", 500, "season_1", "mvp", "Season MVP")
    assert fl.player_followers(conn, "star") == 500
    assert fl.club_fans(conn, "star") == 0  # different ledger


# --- Task 2.3: club fan gains + web prestige growth -----------------------------

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_FANS as FAN
from dodgeball_sim.persistence import get_state, load_club_prestige, save_standings
from dodgeball_sim.season import StandingsRow
from dodgeball_sim import fan_economy as fe

_SEED = 20260617


def _pyramid_career(wins=5):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    season_id = get_state(conn, "active_season_id")
    rows = [
        StandingsRow(club_id=("aurora" if i == 0 else f"r{i}"),
                     wins=(wins if i == 0 else 1), losses=0, draws=0,
                     elimination_differential=0, points=(wins if i == 0 else 1) * 3)
        for i in range(7)
    ]
    save_standings(conn, season_id, rows)
    conn.commit()
    return conn, season_id


def test_club_fans_for_event_is_ordered_by_prestige_of_the_event():
    assert fe.club_fans_for_event("worlds_win") > fe.club_fans_for_event("title")
    assert fe.club_fans_for_event("title") > fe.club_fans_for_event("win")
    assert fe.club_fans_for_event("unknown") == 0


def test_award_season_fans_from_wins_receipt_audit():
    conn, season_id = _pyramid_career(wins=5)
    fe.award_season_fans(conn, season_id)
    assert fl.club_fans(conn, "aurora") == 5 * FAN.fans_per_win
    receipts = fl.load_fan_receipts(conn, entity_type="club", entity_id="aurora")
    # Receipt audit: the ledger deltas sum exactly to the running total.
    assert sum(r["delta"] for r in receipts) == fl.club_fans(conn, "aurora")
    assert any("wins" in r["receipt"] for r in receipts)
    # Idempotent — a second rollup adds nothing.
    fe.award_season_fans(conn, season_id)
    assert fl.club_fans(conn, "aurora") == 5 * FAN.fans_per_win


def test_prestige_grows_on_web_and_is_idempotent():
    conn, season_id = _pyramid_career(wins=5)
    before = load_club_prestige(conn, "aurora")
    fe.grow_prestige_for_season(conn, season_id)
    after = load_club_prestige(conn, "aurora")
    assert after > before  # the champion (rank 0) gains wins + 5
    fe.grow_prestige_for_season(conn, season_id)
    assert load_club_prestige(conn, "aurora") == after  # idempotent
