"""WT-14: build-from-scratch must reject duplicate / invalid / out-of-range
founding rosters BEFORE writing any save, and must never leave a partial .db.

The old code appended one player per *matching* id with no de-duplication and no
upper bound, so a request listing the same id six times produced a permanently
corrupt save (one player occupying six roster slots). These tests pin the
fix: validation happens up front, and every rejection leaves the saves
directory empty (no partial .db, no temp/WAL sidecars).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dodgeball_sim.persistence import connect, load_club_roster
from dodgeball_sim.save_service import (
    SaveServiceError,
    build_from_scratch_save,
    starting_prospects_payload,
)


def _prospect_ids() -> list[str]:
    return [p["player_id"] for p in starting_prospects_payload()["prospects"]]


def _request(save_name: str, roster_ids) -> dict:
    return {
        "save_name": save_name,
        "club_name": "Validators",
        "city": "Testville",
        "colors": "#FF0000,#000000",
        "coach_name": "Test Coach",
        "coach_backstory": "Tactical Mastermind",
        "roster_player_ids": roster_ids,
        "root_seed": 20260426,
    }


def _all_files(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir()) if directory.exists() else []


def _assert_no_db_left(directory: Path) -> None:
    """The strongest WT-14 guard: not even a temp/WAL sidecar may remain."""
    leftovers = _all_files(directory)
    assert leftovers == [], f"rejection left files behind: {leftovers}"


def test_build_from_scratch_happy_path_writes_single_clean_save(tmp_path):
    ids = _prospect_ids()
    result = build_from_scratch_save(tmp_path, _request("happy", ids[:10]))

    assert result["status"] == "ok"
    assert _all_files(tmp_path) == ["happy.db"], "atomic build left sidecars/temp"

    conn = connect(result["path"])
    try:
        roster = load_club_roster(conn, "happy")
    finally:
        conn.close()
    assert len(roster) == 10
    # Distinct ids -> no duplicated player occupying multiple slots.
    assert len({p.id for p in roster}) == 10


def test_duplicate_ids_rejected_and_no_db_left(tmp_path):
    ids = _prospect_ids()
    duplicated = [ids[0]] * 6

    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("dupes", duplicated))

    assert exc.value.status_code == 400
    assert "duplicate" in exc.value.detail.lower()
    _assert_no_db_left(tmp_path)


def test_partial_duplicate_still_rejected(tmp_path):
    """A valid-length list that smuggles in one repeat is still corruption."""
    ids = _prospect_ids()
    roster = ids[:6] + [ids[0]]  # 7 entries, one repeated

    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("partialdupe", roster))

    assert exc.value.status_code == 400
    _assert_no_db_left(tmp_path)


def test_unknown_ids_rejected_and_no_db_left(tmp_path):
    ids = _prospect_ids()
    roster = ids[:5] + ["this_id_is_not_in_the_pool"]

    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("bogus", roster))

    assert exc.value.status_code == 400
    assert "unknown" in exc.value.detail.lower()
    _assert_no_db_left(tmp_path)


def test_too_few_unique_ids_rejected_and_no_db_left(tmp_path):
    ids = _prospect_ids()

    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("toofew", ids[:5]))

    assert exc.value.status_code == 400
    assert "at least 6" in exc.value.detail.lower()
    _assert_no_db_left(tmp_path)


def test_too_many_ids_rejected_and_no_db_left(tmp_path):
    ids = _prospect_ids()

    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("toomany", ids[:11]))

    assert exc.value.status_code == 400
    assert "more than 10" in exc.value.detail.lower()
    _assert_no_db_left(tmp_path)


def test_non_list_roster_rejected_and_no_db_left(tmp_path):
    with pytest.raises(SaveServiceError) as exc:
        build_from_scratch_save(tmp_path, _request("notalist", "not-a-list"))

    assert exc.value.status_code == 400
    _assert_no_db_left(tmp_path)


def test_six_unique_ids_is_accepted(tmp_path):
    """The minimum legal founding roster (exactly 6 unique) must succeed."""
    ids = _prospect_ids()
    result = build_from_scratch_save(tmp_path, _request("minsix", ids[:6]))

    assert result["status"] == "ok"
    conn = connect(result["path"])
    try:
        roster = load_club_roster(conn, "minsix")
    finally:
        conn.close()
    assert len(roster) == 6
