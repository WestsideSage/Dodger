"""V27 The Calendar — Phase 6: the Worlds crowning ceremony beat.

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 6, lines ~85/129) and
docs/specs/2026-06-17-v27-the-calendar-sprint-plan.md Task 6.1: a conditional
``worlds_champion`` offseason beat that appears only when the user club won
Worlds this postseason. The first-ever crown gets the elevated ``is_first``
crowning treatment; later crowns a smaller defending-champion beat. Post-summit
stays legacy play — winning Worlds triggers NO new-game-plus / difficulty
ratchet (the vision law).

Pyramid-gated; legacy single-league saves stay byte-identical (no beat).
"""
from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    set_state,
)

_SEED = 20260617


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _legacy_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam"
    )
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _write_worlds_ledger(
    conn: sqlite3.Connection,
    season_id: str,
    *,
    champion_club_id: str,
    runner_up_club_id: str = "rival",
    champion_name: str = "Aurora Sentinels",
    runner_up_name: str = "Rival",
) -> None:
    """Persist a minimal complete postseason ledger with the given Worlds champ."""
    from dodgeball_sim.pyramid_postseason import postseason_ledger_key

    ledger = {
        "season_id": season_id,
        "complete": True,
        "champions": {},
        "runners_up": {},
        "champion_names": {},
        "promotion_playoff": {},
        "promoted": {},
        "relegated": {},
        "worlds": {
            "champion_club_id": champion_club_id,
            "champion_name": champion_name,
            "runner_up_club_id": runner_up_club_id,
            "runner_up_name": runner_up_name,
            "final_match_id": f"{season_id}_p_worlds_final",
        },
    }
    set_state(conn, postseason_ledger_key(season_id), json.dumps(ledger))
    conn.commit()


def _append_worlds_history(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    champion_club_id: str,
    champion_name: str = "Aurora Sentinels",
) -> None:
    from dodgeball_sim.pyramid_postseason import WORLDS_HISTORY_KEY, load_worlds_history

    history = load_worlds_history(conn)
    if not any(e.get("season_id") == season_id for e in history):
        history.append(
            {
                "season_id": season_id,
                "champion_club_id": champion_club_id,
                "champion_name": champion_name,
                "runner_up_club_id": "rival",
                "runner_up_name": "Rival",
                "final_match_id": f"{season_id}_p_worlds_final",
            }
        )
        set_state(conn, WORLDS_HISTORY_KEY, json.dumps(history))
        conn.commit()


# ---------------------------------------------------------------------------
# Task 6.1 — the worlds_champion beat (TDD)
# ---------------------------------------------------------------------------


class TestWorldsChampionBeatClampAndTuple:
    def test_worlds_champion_is_in_the_beat_tuple(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS

        assert "worlds_champion" in OFFSEASON_CEREMONY_BEATS

    def test_max_offseason_beat_index_equals_len_beats_minus_one(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS
        from dodgeball_sim.persistence import _MAX_OFFSEASON_BEAT_INDEX

        assert _MAX_OFFSEASON_BEAT_INDEX == len(OFFSEASON_CEREMONY_BEATS) - 1

    def test_worlds_champion_sits_after_recap(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS

        beats = OFFSEASON_CEREMONY_BEATS
        # Spec: the worlds_champion beat sits "after the recap".
        assert beats.index("worlds_champion") > beats.index("recap")

    def test_pinned_beat_tuple_witness_matches(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS

        assert OFFSEASON_CEREMONY_BEATS == (
            "recap",
            "worlds_champion",
            "champion",
            "awards",
            "events",
            "records_ratified",
            "hof_induction",
            "development",
            "retirements",
            "transfer_period",
            "rookie_class_preview",
            "media_event",
            "recruitment",
            "schedule_reveal",
        )


class TestWorldsCrowningForUser:
    def test_returns_none_when_user_did_not_win_worlds(self):
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="rival")
        assert worlds_crowning_for_user(conn, season_id, "aurora") is None

    def test_returns_none_when_no_ledger_exists(self):
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        assert worlds_crowning_for_user(conn, season_id, "aurora") is None

    def test_is_first_true_on_first_crown(self):
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        crowning = worlds_crowning_for_user(conn, season_id, "aurora")
        assert crowning is not None
        assert crowning["is_first"] is True
        assert crowning["champion_club_id"] == "aurora"
        assert crowning["champion_name"] == "Aurora Sentinels"
        assert crowning["season_id"] == season_id

    def test_is_first_false_on_later_crown(self):
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        # A prior Worlds title for the user club in an EARLIER season (the
        # prior-titles check excludes the current season_id, so the prior
        # entry must be a genuinely different season).
        prior_season_id = "season_0" if season_id == "season_1" else "season_1"
        _append_worlds_history(
            conn, season_id=prior_season_id, champion_club_id="aurora"
        )
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        crowning = worlds_crowning_for_user(conn, season_id, "aurora")
        assert crowning is not None
        assert crowning["is_first"] is False

    def test_is_first_true_when_history_has_other_clubs_only(self):
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        _append_worlds_history(
            conn, season_id="season_1", champion_club_id="rival",
            champion_name="Rival",
        )
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        crowning = worlds_crowning_for_user(conn, season_id, "aurora")
        assert crowning is not None
        assert crowning["is_first"] is True

    def test_is_first_excludes_current_season_entry(self):
        """A history entry for THIS season (the just-won crown) must not flip
        is_first to False — the prior-titles check keys on season_id != current."""
        from dodgeball_sim.pyramid_postseason import worlds_crowning_for_user

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        # Simulate the postseason having already appended this season's entry.
        _append_worlds_history(conn, season_id=season_id, champion_club_id="aurora")
        crowning = worlds_crowning_for_user(conn, season_id, "aurora")
        assert crowning is not None
        assert crowning["is_first"] is True


class TestWorldsChampionBeatPresence:
    def _init_offseason(self, conn, season_id):
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import load_all_rosters, load_clubs, load_season

        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        return json.loads(get_state(conn, "offseason_active_beats_json") or "[]")

    def test_beat_present_when_user_wins_worlds(self):
        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        active = self._init_offseason(conn, season_id)
        assert "worlds_champion" in active

    def test_beat_absent_when_user_does_not_win_worlds(self):
        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="rival")
        active = self._init_offseason(conn, season_id)
        assert "worlds_champion" not in active

    def test_beat_absent_when_no_postseason_ledger(self):
        conn, season_id = _pyramid_career()
        active = self._init_offseason(conn, season_id)
        assert "worlds_champion" not in active

    def test_beat_absent_on_legacy_world_even_if_ledger_somehow_exists(self):
        """Legacy byte-identical: the worlds_champion beat never appears on a
        non-pyramid world, even if a postseason ledger were somehow written."""
        conn, season_id = _legacy_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        active = self._init_offseason(conn, season_id)
        assert "worlds_champion" not in active


class TestWorldsChampionBeatPayload:
    def test_build_beat_payload_first_crown_carries_is_first_true(self):
        from dodgeball_sim.offseason_presentation import build_beat_payload
        from dodgeball_sim.persistence import load_all_rosters, load_clubs

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        payload = build_beat_payload(
            "worlds_champion",
            awards=[], clubs=load_clubs(conn), rosters=load_all_rosters(conn),
            standings=[], ret_rows=[], season=None, season_outcome=None,
            next_preview=None, signed_player_id="", player_club_id="aurora",
            conn=conn,
        )
        assert payload["beat_key"] == "worlds_champion"
        assert payload["is_first"] is True
        assert payload["champion_club_id"] == "aurora"
        assert payload["champion_name"] == "Aurora Sentinels"

    def test_build_beat_payload_defending_crown_carries_is_first_false(self):
        from dodgeball_sim.offseason_presentation import build_beat_payload
        from dodgeball_sim.persistence import load_all_rosters, load_clubs

        conn, season_id = _pyramid_career()
        prior_season_id = "season_0" if season_id == "season_1" else "season_1"
        _append_worlds_history(conn, season_id=prior_season_id, champion_club_id="aurora")
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        payload = build_beat_payload(
            "worlds_champion",
            awards=[], clubs=load_clubs(conn), rosters=load_all_rosters(conn),
            standings=[], ret_rows=[], season=None, season_outcome=None,
            next_preview=None, signed_player_id="", player_club_id="aurora",
            conn=conn,
        )
        assert payload["is_first"] is False

    def test_build_beat_payload_non_champion_returns_empty(self):
        from dodgeball_sim.offseason_presentation import build_beat_payload
        from dodgeball_sim.persistence import load_all_rosters, load_clubs

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="rival")
        payload = build_beat_payload(
            "worlds_champion",
            awards=[], clubs=load_clubs(conn), rosters=load_all_rosters(conn),
            standings=[], ret_rows=[], season=None, season_outcome=None,
            next_preview=None, signed_player_id="", player_club_id="aurora",
            conn=conn,
        )
        # Non-champion: no crowning payload.
        assert payload == {} or payload.get("is_first") is None

    def test_build_offseason_ceremony_beat_renders_worlds_champion_text(self):
        from dodgeball_sim.offseason_ceremony import (
            OFFSEASON_CEREMONY_BEATS,
            build_offseason_ceremony_beat,
        )
        from dodgeball_sim.persistence import load_all_rosters, load_clubs

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        beat = build_offseason_ceremony_beat(
            OFFSEASON_CEREMONY_BEATS.index("worlds_champion"),
            None, load_clubs(conn), load_all_rosters(conn), [], [], "aurora",
            conn=conn,
        )
        assert beat.key == "worlds_champion"
        assert "Aurora Sentinels" in beat.body


class TestNoPostSummitRatchet:
    """Vision law: post-summit is legacy play. Winning Worlds triggers NO
    new-game-plus / difficulty ratchet — the crowning is a presentation beat,
    never a mechanic change."""

    def test_winning_worlds_introduces_no_ngplus_or_difficulty_state(self):
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import load_all_rosters, load_clubs, load_season

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")

        before_keys = {
            row["key"] for row in conn.execute("SELECT key FROM dynasty_state")
        }
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        after_keys = {
            row["key"] for row in conn.execute("SELECT key FROM dynasty_state")
        }
        new_keys = after_keys - before_keys
        forbidden = [
            k for k in new_keys
            if any(
                s in k.lower()
                for s in ("ng_plus", "ratchet", "post_summit", "difficulty",
                          "worlds_bonus")
            )
        ]
        assert forbidden == [], f"ratchet/NG+ keys introduced: {forbidden}"
        # The root seed is the deterministic spine — a crowning must not touch it.
        assert get_state(conn, "root_seed") == str(_SEED)

    def test_crowning_payload_carries_no_ratchet_field(self):
        from dodgeball_sim.offseason_presentation import build_beat_payload
        from dodgeball_sim.persistence import load_all_rosters, load_clubs

        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        payload = build_beat_payload(
            "worlds_champion",
            awards=[], clubs=load_clubs(conn), rosters=load_all_rosters(conn),
            standings=[], ret_rows=[], season=None, season_outcome=None,
            next_preview=None, signed_player_id="", player_club_id="aurora",
            conn=conn,
        )
        # The payload is presentation only (is_first / champion identity). No
        # difficulty / NG+ / post-summit mechanic field may ride along.
        for forbidden in ("ratchet", "ng_plus", "post_summit", "difficulty",
                          "worlds_bonus", "next_difficulty"):
            assert forbidden not in payload
