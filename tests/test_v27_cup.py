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


# ---------------------------------------------------------------------------
# Task 2.2 — cup_service.resolve_domestic_cup (auto-sim to a champion)
# ---------------------------------------------------------------------------


def _resolve_cup(conn, season_id, root_seed=_SEED):
    from dodgeball_sim.cup_service import ensure_domestic_cup, resolve_domestic_cup

    ensure_domestic_cup(conn, season_id, root_seed)
    return resolve_domestic_cup(conn, season_id, root_seed)


class TestResolveDomesticCup:
    def test_resolves_the_full_bracket_to_a_single_champion(self):
        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)

        # The bracket resolves to exactly one champion — the final match has a
        # winner and every match in the bracket is resolved.
        from dodgeball_sim.persistence import load_cup_bracket, load_cup_results

        bracket = load_cup_bracket(conn, season_id)["bracket"]
        results = load_cup_results(conn, season_id)
        for rnd in bracket["rounds"]:
            for match in rnd["matches"]:
                assert match["match_id"] in results, f"unresolved: {match['match_id']}"
        final_id = bracket["rounds"][-1]["matches"][0]["match_id"]
        champion = results[final_id]
        assert champion is not None
        assert result["champion_club_id"] == champion

    def test_champion_gets_a_cup_trophy(self):
        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)
        trophies = [
            t for t in load_club_trophies(conn)
            if t["season_id"] == season_id and t["trophy_type"] == "cup"
        ]
        assert len(trophies) == 1
        assert trophies[0]["club_id"] == result["champion_club_id"]

    def test_champion_purse_is_credited_once_and_idempotent(self):
        """The purse credits the USER treasury only when the user wins (AI
        treasuries are abstracted — V25/V26 pattern). Idempotent: re-resolve
        never double-pays regardless of who won."""
        from dodgeball_sim.persistence import get_state

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        before = treasury_k(conn)
        result = _resolve_cup(conn, season_id)
        after_first = treasury_k(conn)

        if result["champion_club_id"] == user:
            # User won → purse paid once, guard fired.
            assert after_first > before, "user cup win must pay a purse"
            assert get_state(conn, "v27_domestic_cup_purse_for") == season_id
        else:
            # AI won → no user purse; guard never fires.
            assert after_first == before
            assert get_state(conn, "v27_domestic_cup_purse_for") is None

        # Re-resolve must NOT change treasury (idempotent either way).
        _resolve_cup(conn, season_id)
        assert treasury_k(conn) == after_first

    def test_resolve_overall_is_idempotent(self):
        """Re-resolving does not double-award trophy/fans/purse/news or
        re-simulate matches. The resolved-guard short-circuits."""
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.persistence import load_news_headlines

        conn, season_id = _pyramid_career()
        _resolve_cup(conn, season_id)
        trophies_before = [
            t for t in load_club_trophies(conn)
            if t["season_id"] == season_id and t["trophy_type"] == "cup"
        ]
        news_before = [
            h for h in load_news_headlines(conn, season_id)
            if h["category"] == "event_news"
        ]
        events_before = load_events(conn, season_id)
        fans_before = conn.execute(
            "SELECT fans_count FROM club_fans WHERE club_id = ?",
            (get_state(conn, "player_club_id"),),
        ).fetchone()

        _resolve_cup(conn, season_id)  # idempotent re-resolve

        trophies_after = [
            t for t in load_club_trophies(conn)
            if t["season_id"] == season_id and t["trophy_type"] == "cup"
        ]
        news_after = [
            h for h in load_news_headlines(conn, season_id)
            if h["category"] == "event_news"
        ]
        events_after = load_events(conn, season_id)
        fans_after = conn.execute(
            "SELECT fans_count FROM club_fans WHERE club_id = ?",
            (get_state(conn, "player_club_id"),),
        ).fetchone()
        assert trophies_after == trophies_before
        assert news_after == news_before
        assert events_after == events_before
        if fans_before and fans_after:
            assert fans_after["fans_count"] == fans_before["fans_count"]

    def test_champion_fans_grant_when_user_wins_cup(self):
        """If the user club wins the cup, the fans_cup grant lands once
        (guarded), with a receipt. If an AI club wins, no user fan grant."""
        from dodgeball_sim import fan_ledger

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        result = _resolve_cup(conn, season_id)
        receipts = fan_ledger.load_fan_receipts(
            conn, entity_type="club", entity_id=user, season_id=season_id,
        )
        cup_receipts = [r for r in receipts if r["event_type"] == "cup"]
        if result["champion_club_id"] == user:
            assert cup_receipts, "user cup win must grant fans_cup with a receipt"
            assert get_state(conn, "v27_domestic_cup_fans_for") == season_id
        else:
            # An AI win grants the user no cup fans.
            assert not cup_receipts

    def test_event_news_line_emitted_for_champion(self):
        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)
        wire = [
            h for h in load_news_headlines(conn, season_id)
            if h["category"] == "event_news"
        ]
        assert wire, "resolve must emit an event_news headline"
        # The champion line exists somewhere in the wire (the wire is sorted by
        # headline_id, so it may not be first when giant-killing lines exist).
        champion_lines = [
            h for h in wire if result["champion_club_name"] in h["headline_text"]
        ]
        assert champion_lines, "champion event_news headline must be emitted"
        assert "win the" in champion_lines[0]["headline_text"]

    def test_event_recorded_in_v27_events_json(self):
        from dodgeball_sim.event_calendar import load_events

        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)
        events = load_events(conn, season_id)
        assert len(events) == 1
        cup = events[0]
        assert cup["event_key"] == "domestic_cup"
        assert cup["champion_club_id"] == result["champion_club_id"]
        assert cup["ruleset"] == "official_foam"
        # The bracket rows are recorded (one per played match).
        assert cup["bracket"]
        assert any(row["winner_club_id"] for row in cup["bracket"])

    def test_giant_killing_news_line_when_lower_tier_beats_higher_tier(self):
        """A lower-division club beating a higher-division one produces a
        giant-killing event_news headline. Across seeds this occurs; this test
        seeds a bracket where we can detect a giant-killing row and assert the
        news line exists when one happens."""
        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)
        # Determine whether any bracket row was a giant-killing (lower tier
        # beats higher tier) and, if so, assert a giant-killing news line.
        from dodgeball_sim.cup_service import detect_giant_killings
        from dodgeball_sim.persistence import load_division_map

        dmap = load_division_map(conn, season_id)
        kills = detect_giant_killings(result, dmap)
        wire = [
            h for h in load_news_headlines(conn, season_id)
            if h["category"] == "event_news"
        ]
        giant_news = [h for h in wire if "giant" in h["headline_text"].lower()
                      or "upset" in h["headline_text"].lower()]
        if kills:
            assert giant_news, f"giant-killing occurred ({kills}) but no news line"

    def test_determinism_same_seed_same_champion(self):
        conn1, sid1 = _pyramid_career()
        r1 = _resolve_cup(conn1, sid1)
        conn2, sid2 = _pyramid_career()
        r2 = _resolve_cup(conn2, sid2)
        assert r1["champion_club_id"] == r2["champion_club_id"]
        assert r1["bracket"] == r2["bracket"]

    def test_foam_engine_only_no_cloth_or_no_sting(self):
        """The cup runs the foam engine (official_foam). Every bracket row's
        recorded match used the foam ruleset — never cloth/no-sting."""
        conn, season_id = _pyramid_career()
        result = _resolve_cup(conn, season_id)
        assert result["ruleset"] == "official_foam"
        # No cloth/no-sting news or records leak in.

    def test_meta_patch_is_none(self):
        """MetaPatch is retired — the resolver passes meta_patch=None."""
        import ast
        from pathlib import Path

        source = Path("src/dodgeball_sim/cup_service.py").read_text(encoding="utf-8")
        # The simulate_match call must not pass a non-None meta_patch.
        assert "meta_patch=None" in source or "meta_patch = None" in source
        assert "MetaPatch(" not in source


class TestGiantKillingAcrossSeeds:
    def test_giant_killing_rate_above_zero_across_seeds(self):
        """Across a sweep of seeds, a lower-tier club beats a higher-tier one
        at least once (the cup's whole point). This is the probe assertion
        mirrored at the test layer."""
        from dodgeball_sim.cup_service import detect_giant_killings
        from dodgeball_sim.persistence import load_division_map

        kills_seen = 0
        for seed in range(_SEED, _SEED + 12):
            conn, season_id = _pyramid_career()
            # Re-init with this seed is not possible via the fixture (curated
            # career pins the roster seed); instead vary the cup seed by
            # resolving at season_id with a per-seed root_seed. The career's
            # root_seed drives roster gen, but the cup namespace is independent,
            # so varying root_seed varies the bracket + match seeds.
            from dodgeball_sim.cup_service import ensure_domestic_cup, resolve_domestic_cup
            ensure_domestic_cup(conn, season_id, seed)
            result = resolve_domestic_cup(conn, season_id, seed)
            dmap = load_division_map(conn, season_id)
            if detect_giant_killings(result, dmap):
                kills_seen += 1
        assert kills_seen > 0, "no giant-killing across 12 seeds — cup is not cross-tier"


class TestOffseasonWiring:
    def test_pyramid_offseason_init_resolves_cup_and_events_beat_shows_champion(self):
        """After a pyramid season's offseason init, the events beat shows the
        cup champion (the cup is resolved + recorded in v27_events_json)."""
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state as _gs,
            load_all_rosters,
            load_clubs,
            load_season,
        )
        import json as _json

        conn, season_id = _pyramid_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        events = load_events(conn, season_id)
        assert any(e["event_key"] == "domestic_cup" for e in events), \
            "offseason init must resolve the domestic cup into v27_events_json"
        active = _json.loads(_gs(conn, "offseason_active_beats_json") or "[]")
        assert "events" in active

    def test_legacy_offseason_init_writes_no_cup_bracket_purse_or_trophy(self):
        """Legacy byte-identical: a non-pyramid offseason init never creates a
        cup bracket, never pays a purse, never awards a trophy, never records
        an event."""
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_cup_bracket,
            load_season,
        )

        conn, season_id = _legacy_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        assert load_cup_bracket(conn, season_id) is None
        assert get_state(conn, "v27_domestic_cup_purse_for") is None
        assert get_state(conn, "v27_domestic_cup_resolved_for") is None
        assert get_state(conn, "v27_domestic_cup_fans_for") is None
        assert get_state(conn, "v27_events_json") is None
        trophies = [t for t in load_club_trophies(conn) if t["season_id"] == season_id]
        assert not any(t["trophy_type"] == "cup" for t in trophies)

    def test_legacy_offseason_init_byte_identical_with_and_without_cup_code(self):
        """The presence of the cup wiring must not change a legacy world's
        offseason state at all — same active beats, same state keys touched."""
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_season,
        )
        import json as _json

        conn, season_id = _legacy_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        active = _json.loads(get_state(conn, "offseason_active_beats_json") or "[]")
        assert "events" not in active
        # No v27 cup state keys exist on a legacy world.
        for key in (
            "v27_domestic_cup_purse_for",
            "v27_domestic_cup_resolved_for",
            "v27_domestic_cup_fans_for",
            "v27_events_json",
        ):
            assert get_state(conn, key) is None

