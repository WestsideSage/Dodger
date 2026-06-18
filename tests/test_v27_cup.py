"""V27 The Calendar — Phase 2: Domestic Cup (revive cup.py in the web path).

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 2). The dormant
``cup.py`` pure-bracket model (kept import-pure) gets a web home in
``cup_service.py``: a cross-division 28-club foam knockout generated at season
start and auto-simmed to a champion through the real foam engine at the
offseason events pass. Pyramid-gated; legacy single-league saves stay
byte-identical (no cup, no bracket, no purse, no trophy).

Architecture guardrails (non-negotiable):
- ``cup.py`` stays import-pure (``test_cup_module_has_no_db_boundary_imports``).
- ``cup_service`` never imports ``dynasty_cli`` (CLI print deps).
- Foam engine only (the standard ``simulate_match`` path; no cloth/no-sting).
- New seed namespace ``v27_cup``; ``cup_id = f"{season_id}_domestic_cup"``.
- ``meta_patch=None`` (MetaPatch is retired).
- Purses + fans idempotent via per-event guards.
"""
from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_trophies,
    load_clubs,
    load_cup_bracket,
    load_cup_results,
    load_division_memberships,
    load_news_headlines,
    set_state,
)
from dodgeball_sim.rng import DeterministicRNG, derive_seed

_SEED = 20260617


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _legacy_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _division_club_ids(conn, season_id):
    return {m.club_id for m in load_division_memberships(conn, season_id)}


# ---------------------------------------------------------------------------
# Task 2.1 — cup_service.ensure_domestic_cup (cross-division bracket)
# ---------------------------------------------------------------------------


class TestEnsureDomesticCup:
    def test_generates_and_persists_a_cross_division_bracket(self):
        from dodgeball_sim.cup_service import ensure_domestic_cup

        conn, season_id = _pyramid_career()
        division_clubs = _division_club_ids(conn, season_id)

        ensure_domestic_cup(conn, season_id, _SEED)

        row = load_cup_bracket(conn, season_id)
        assert row is not None
        assert row["cup_id"] == f"{season_id}_domestic_cup"
        bracket = row["bracket"]
        # The bracket field covers ALL division clubs (the 28-club pyramid).
        assert set(bracket["club_ids"]) == division_clubs
        assert len(bracket["rounds"]) >= 1

    def test_bracket_is_deterministic_for_the_v27_cup_seed_namespace(self):
        from dodgeball_sim.cup import generate_cup_bracket
        from dodgeball_sim.cup_service import ensure_domestic_cup

        conn, season_id = _pyramid_career()
        ensure_domestic_cup(conn, season_id, _SEED)
        row = load_cup_bracket(conn, season_id)
        bracket = row["bracket"]

        # Re-derive the expected bracket directly from the spec'd seed namespace.
        expected = generate_cup_bracket(
            sorted(_division_club_ids(conn, season_id)),
            DeterministicRNG(derive_seed(_SEED, "v27_cup", season_id)),
        )
        assert list(bracket["club_ids"]) == list(expected.club_ids)
        assert bracket["rounds"][0]["round_number"] == expected.rounds[0].round_number
        # Match-id format is preserved (cup_r{round}_m{slot}).
        assert bracket["rounds"][0]["matches"][0]["match_id"].startswith("cup_r1_m")

    def test_idempotent_second_call_does_not_overwrite(self):
        from dodgeball_sim.cup_service import ensure_domestic_cup

        conn, season_id = _pyramid_career()
        ensure_domestic_cup(conn, season_id, _SEED)
        first = load_cup_bracket(conn, season_id)["bracket"]

        # Corrupt the persisted bracket with a sentinel so a re-run that
        # overwrites would be detectable (a deterministic regenerate would
        # restore the original, hiding a non-idempotent overwrite).
        from dodgeball_sim.persistence import save_cup_bracket

        save_cup_bracket(
            conn,
            f"{season_id}_domestic_cup",
            season_id,
            {"club_ids": ["SENTINEL"], "rounds": []},
        )
        ensure_domestic_cup(conn, season_id, _SEED)
        after = load_cup_bracket(conn, season_id)["bracket"]
        assert after == {"club_ids": ["SENTINEL"], "rounds": []}
        # And the real bracket is recoverable by re-deriving it (sanity).
        assert first["rounds"]  # original was real

    def test_bye_results_are_persisted_for_auto_advance_matches(self):
        from dodgeball_sim.cup_service import ensure_domestic_cup

        conn, season_id = _pyramid_career()
        ensure_domestic_cup(conn, season_id, _SEED)
        row = load_cup_bracket(conn, season_id)
        bracket = row["bracket"]
        results = load_cup_results(conn, season_id)
        # Every bye match in the opening round has a persisted winner.
        for match in bracket["rounds"][0]["matches"]:
            if match["auto_advance_club_id"]:
                assert match["match_id"] in results
                assert results[match["match_id"]] == match["auto_advance_club_id"]


class TestCupModuleImportPurityStillHolds:
    def test_cup_service_does_not_import_dynasty_cli(self):
        import ast
        from pathlib import Path

        source = Path("src/dodgeball_sim/cup_service.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imported.add(mod)
                imported.update(f"{mod}.{alias.name}" for alias in node.names)
        assert not any("dynasty_cli" in name for name in imported)

    def test_cup_module_still_has_no_db_boundary_imports(self):
        from pathlib import Path

        source = Path("src/dodgeball_sim/cup.py").read_text(encoding="utf-8")
        assert "persistence" not in source
        assert "sqlite3" not in source
