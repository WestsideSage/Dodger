"""V27 The Calendar — Phase 4: Ruleset Invitationals (Cloth Classic / No-Sting Open).

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 4). An invitational
runs an auto-simmed knockout under a NON-foam ruleset
(``OfficialEngineAdapter(RulesetSelection.OFFICIAL_CLOTH/_NO_STING)``); invite by
fame (prestige) + standing; champion gets a purse + a one-season prospect-
showcase warmth in the V26 recruiting-credibility channel. Match-ids encode the
round so the engine clock is right (the trap). Pyramid-gated; legacy saves stay
byte-identical (no invitationals, no warmth, no purse).

Architecture guardrails (non-negotiable):
- Non-foam engine only (cloth / no-sting via ``OfficialEngineAdapter``); the
  foam league + Domestic Cup are untouched.
- ``decide_cloth_game_by_active_count`` is NEVER called on a foam match (the
  engine guards it on ``profile.material == CLOTH``).
- New seed namespace ``v27_invitational``; idempotent purses + warmth.
- V26 warmth coexists with a media credibility bonus in the same offseason
  (summed, not clobbered) and both reset next offseason.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_EVENTS
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_prestige,
    load_clubs,
    load_cup_bracket,
    save_club_prestige,
    set_state,
)
from dodgeball_sim.rulesets import RulesetSelection
from dodgeball_sim.rng import derive_seed

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


def _seed_prestige(conn, club_ids, score):
    """Give a set of clubs a prestige score (the fame gate input)."""
    for cid in club_ids:
        save_club_prestige(conn, cid, score)
    conn.commit()


def _some_invitees(conn, n=8):
    """The first n club ids (deterministic invitee set for the pure runner tests)."""
    clubs = list(load_clubs(conn).values())
    return [c.club_id for c in clubs[:n]]


# ---------------------------------------------------------------------------
# Task 4.1 — invitationals.run_invitational (cloth / no-sting knockout)
# ---------------------------------------------------------------------------


class TestRunInvitational:
    def test_cloth_knockout_resolves_to_a_valid_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
        )

        assert result is not None
        assert result.champion_club_id in invitees
        assert result.ruleset == "official_cloth"
        # The bracket has at least the final + a semifinal round.
        rounds = {row.round for row in result.bracket}
        assert "Final" in rounds
        assert result.bracket  # played matches recorded

    def test_no_sting_knockout_resolves_to_a_valid_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_NO_STING, invitees, _SEED
        )

        assert result is not None
        assert result.champion_club_id in invitees
        assert result.ruleset == "official_no_sting"

    def test_match_ids_encode_the_round_so_the_engine_clock_is_right(self):
        """The official engine derives the match clock from match_id substrings:
        ``semifinal`` -> 30 min, ``final`` -> 40 min, else 24 min. Knockout
        match-ids must encode the round label so each round gets the right
        clock. Captures the match_ids actually passed to the engine."""
        from dodgeball_sim import invitationals

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        captured = []
        real_simulate = invitationals.simulate_match

        def spy(scheduled, *args, **kwargs):
            captured.append(str(scheduled.match_id))
            return real_simulate(scheduled, *args, **kwargs)

        invitationals.simulate_match = spy
        try:
            invitationals.run_invitational(
                conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
            )
        finally:
            invitationals.simulate_match = real_simulate

        # An 8-club bracket: round 1 = quarterfinal (24 min, no label match),
        # round 2 = semifinal (30 min), round 3 = final (40 min). At least one
        # semifinal and exactly one final match-id must encode the label so the
        # engine clock resolves correctly.
        assert any("semifinal" in mid for mid in captured), captured
        assert any("final" in mid and "semifinal" not in mid for mid in captured), captured

    def test_foam_league_and_cup_untouched(self):
        """Running an invitational never creates a cup bracket, never adds
        league match_records, and never touches the foam cup state."""
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)
        records_before = conn.execute(
            "SELECT COUNT(*) AS n FROM match_records"
        ).fetchone()["n"]

        run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
        )

        # No cup bracket is created by the invitational.
        assert load_cup_bracket(conn, season_id) is None
        # No league match_records are persisted (the invitational is pure sim;
        # only the event result is recorded).
        records_after = conn.execute(
            "SELECT COUNT(*) AS n FROM match_records"
        ).fetchone()["n"]
        assert records_after == records_before

    def test_decide_cloth_game_never_called_on_a_foam_match(self):
        """``decide_cloth_game_by_active_count`` raises on a non-cloth game and
        the engine guards it on ``profile.material == CLOTH``. A foam match must
        never invoke it. Spy on the engine-bound name and run a foam match."""
        import dodgeball_sim.official_engine as oe
        from dodgeball_sim.franchise import simulate_match
        from dodgeball_sim.scheduler import ScheduledMatch
        from dodgeball_sim.persistence import load_club_roster

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        home, away = clubs[0], clubs[1]
        calls = {"n": 0}
        real = oe.decide_cloth_game_by_active_count

        def spy(game):
            calls["n"] += 1
            if game.profile.material.value != "cloth":
                raise AssertionError(
                    "decide_cloth_game_by_active_count called on a non-cloth match"
                )
            return real(game)

        oe.decide_cloth_game_by_active_count = spy
        try:
            scheduled = ScheduledMatch(
                match_id=f"{season_id}_foam_probe_{home.club_id}_vs_{away.club_id}",
                season_id=season_id,
                week=200,
                home_club_id=home.club_id,
                away_club_id=away.club_id,
            )
            simulate_match(
                scheduled=scheduled,
                home_club=home,
                away_club=away,
                home_roster=load_club_roster(conn, home.club_id),
                away_roster=load_club_roster(conn, away.club_id),
                root_seed=_SEED,
                ruleset_selection="official_foam",
            )
        finally:
            oe.decide_cloth_game_by_active_count = real

        assert calls["n"] == 0, "foam match invoked decide_cloth_game_by_active_count"

    def test_decide_cloth_game_never_called_on_a_no_sting_invitational(self):
        """A no-sting invitational runs the full knockout without ever invoking
        the cloth-only game-decision helper."""
        import dodgeball_sim.official_engine as oe
        from dodgeball_sim import invitationals

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)
        calls = {"n": 0}
        real = oe.decide_cloth_game_by_active_count

        def spy(game):
            calls["n"] += 1
            raise AssertionError(
                "decide_cloth_game_by_active_count called during a no-sting invitational"
            )

        oe.decide_cloth_game_by_active_count = spy
        try:
            invitationals.run_invitational(
                conn, season_id, RulesetSelection.OFFICIAL_NO_STING, invitees, _SEED
            )
        finally:
            oe.decide_cloth_game_by_active_count = real

        assert calls["n"] == 0

    def test_determinism_same_seed_same_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn1, sid1 = _pyramid_career()
        r1 = run_invitational(
            conn1, sid1, RulesetSelection.OFFICIAL_CLOTH, _some_invitees(conn1, 8), _SEED
        )
        conn2, sid2 = _pyramid_career()
        r2 = run_invitational(
            conn2, sid2, RulesetSelection.OFFICIAL_CLOTH, _some_invitees(conn2, 8), _SEED
        )
        assert r1.champion_club_id == r2.champion_club_id
        assert [b.__dict__ for b in r1.bracket] == [b.__dict__ for b in r2.bracket]

    def test_too_few_invitees_is_a_no_op(self):
        """Fewer than 2 invitees cannot form a bracket — returns None, no event."""
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, [], _SEED
        )
        assert result is None


# ---------------------------------------------------------------------------
# Task 4.2 — Cloth Classic / No-Sting Open wired (invite + purse + warmth)
# ---------------------------------------------------------------------------


def _seed_qualified_field(conn, n=8, score=25, below=5):
    """Give the first n clubs prestige >= the fame gate, and the rest prestige
    below it, so the fame fence is meaningful. Returns the qualified club ids."""
    clubs = list(load_clubs(conn).values())
    qualified = [c.club_id for c in clubs[:n]]
    _seed_prestige(conn, qualified, score)
    # Every other club is below the fame gate.
    for c in clubs[n:]:
        save_club_prestige(conn, c.club_id, below)
    conn.commit()
    return qualified


class TestResolveRulesetInvitationals:
    def test_invitationals_invited_by_fame_only_qualified_clubs_appear(self):
        """The invite field is fame-gated: only clubs with prestige >=
        invitational_fame_min appear in either invitational's bracket."""
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.invitationals import resolve_ruleset_invitationals

        conn, season_id = _pyramid_career()
        qualified = _seed_qualified_field(conn, n=8, score=25, below=5)

        resolve_ruleset_invitationals(conn, season_id, _SEED)

        events = load_events(conn, season_id)
        inv_events = [e for e in events if e["event_key"] in ("cloth_classic", "no_sting_open")]
        assert len(inv_events) == 2
        for ev in inv_events:
            bracket_clubs = {
                row["home_club_id"] for row in ev["bracket"]
            } | {row["away_club_id"] for row in ev["bracket"]}
            # Every bracket club was fame-qualified.
            assert bracket_clubs.issubset(set(qualified)), bracket_clubs - set(qualified)

    def test_both_invitationals_resolve_and_record_into_v27_events_json(self):
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.invitationals import resolve_ruleset_invitationals

        conn, season_id = _pyramid_career()
        _seed_qualified_field(conn)

        resolve_ruleset_invitationals(conn, season_id, _SEED)

        events = load_events(conn, season_id)
        keys = {e["event_key"] for e in events}
        assert "cloth_classic" in keys
        assert "no_sting_open" in keys
        for ev in events:
            if ev["event_key"] in ("cloth_classic", "no_sting_open"):
                assert ev["champion_club_id"]
                assert ev["bracket"]

    def test_champion_purse_credited_once_and_idempotent_when_user_wins(self):
        """When the user club wins an invitational, the purse credits the user
        treasury once (idempotent). When an AI club wins, no user purse. Either
        way a re-resolve never double-pays."""
        from dodgeball_sim import invitationals
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.persistence import get_state

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        _seed_qualified_field(conn)

        # Force the user to win BOTH invitationals by stubbing the pure runner
        # to return the user as champion (the purse/warmth wiring is the unit
        # under test; the real engine's winner selection is covered in 4.1).
        from dodgeball_sim.event_calendar import EventResult

        def stub(conn, season_id, ruleset, invitees, root_seed):
            meta = {
                RulesetSelection.OFFICIAL_CLOTH: ("cloth_classic", "Cloth Classic"),
                RulesetSelection.OFFICIAL_NO_STING: ("no_sting_open", "No-Sting Open"),
            }[ruleset]
            return EventResult(
                event_key=meta[0], event_name=meta[1], season_id=season_id,
                champion_club_id=user, champion_club_name="User",
                ruleset=ruleset.value, purse_k=0, bracket=(),
            )

        original = invitationals.run_invitational
        invitationals.run_invitational = stub
        try:
            before = treasury_k(conn)
            invitationals.resolve_ruleset_invitationals(conn, season_id, _SEED)
            after = treasury_k(conn)
            # User won both -> two purses credited.
            expected_purse = 2 * DEFAULT_EVENTS.invitational_purse_champion_k
            assert after - before == expected_purse
            # Both per-event guards fired.
            assert get_state(conn, "v27_cloth_classic_purse_for") == season_id
            assert get_state(conn, "v27_no_sting_open_purse_for") == season_id

            # Re-resolve must NOT double-pay (idempotent).
            invitationals.resolve_ruleset_invitationals(conn, season_id, _SEED)
            assert treasury_k(conn) == after
        finally:
            invitationals.run_invitational = original

    def test_champion_warmth_lands_in_recruiting_credibility_when_user_wins(self):
        """When the user wins an invitational, warmth_credibility is added to
        the V26 recruiting-credibility channel (a SEPARATE key from
        v26_credibility_bonus), so it reaches the user's recruiting score."""
        from dodgeball_sim import invitationals
        from dodgeball_sim.event_calendar import EventResult
        from dodgeball_sim.persistence import get_state
        from dodgeball_sim.recruiting_office import _credibility

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        _seed_qualified_field(conn)
        # The user is stubbed as champion (so need not be fame-qualified); drop
        # the user's prestige to 0 so the credibility base is mid-range and the
        # warmth delta is observable (the score clamps at 100).
        save_club_prestige(conn, user, 0)
        conn.commit()

        base = _credibility(conn, season_id, "aurora", [])["score"]
        assert base < 90  # headroom for the warmth delta to land unclamped

        def stub(conn, season_id, ruleset, invitees, root_seed):
            meta = {
                RulesetSelection.OFFICIAL_CLOTH: ("cloth_classic", "Cloth Classic"),
                RulesetSelection.OFFICIAL_NO_STING: ("no_sting_open", "No-Sting Open"),
            }[ruleset]
            return EventResult(
                event_key=meta[0], event_name=meta[1], season_id=season_id,
                champion_club_id=user, champion_club_name="User",
                ruleset=ruleset.value, purse_k=0, bracket=(),
            )

        original = invitationals.run_invitational
        invitationals.run_invitational = stub
        try:
            invitationals.resolve_ruleset_invitationals(conn, season_id, _SEED)
            warmth = invitationals.invitational_warmth(conn)
            assert warmth == 2 * DEFAULT_EVENTS.warmth_credibility
            after = _credibility(conn, season_id, "aurora", [])["score"]
            assert after - base == warmth
        finally:
            invitationals.run_invitational = original

    def test_no_warmth_no_purse_when_ai_club_wins(self):
        """When an AI club wins (user is not champion), no user purse and no
        warmth lands in the user's recruiting channel."""
        from dodgeball_sim import invitationals
        from dodgeball_sim.event_calendar import EventResult
        from dodgeball_sim.persistence import get_state
        from dodgeball_sim.recruiting_office import _credibility

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        clubs = list(load_clubs(conn).values())
        ai_champ = next(c.club_id for c in clubs if c.club_id != user)
        _seed_qualified_field(conn)

        base = _credibility(conn, season_id, "aurora", [])["score"]
        before = treasury_k(conn)

        def stub(conn, season_id, ruleset, invitees, root_seed):
            meta = {
                RulesetSelection.OFFICIAL_CLOTH: ("cloth_classic", "Cloth Classic"),
                RulesetSelection.OFFICIAL_NO_STING: ("no_sting_open", "No-Sting Open"),
            }[ruleset]
            return EventResult(
                event_key=meta[0], event_name=meta[1], season_id=season_id,
                champion_club_id=ai_champ, champion_club_name="AI",
                ruleset=ruleset.value, purse_k=0, bracket=(),
            )

        original = invitationals.run_invitational
        invitationals.run_invitational = stub
        try:
            invitationals.resolve_ruleset_invitationals(conn, season_id, _SEED)
            assert invitationals.invitational_warmth(conn) == 0
            assert treasury_k(conn) == before
            assert _credibility(conn, season_id, "aurora", [])["score"] == base
        finally:
            invitationals.run_invitational = original

    def test_invitational_event_news_emitted(self):
        from dodgeball_sim.persistence import load_news_headlines
        from dodgeball_sim.invitationals import resolve_ruleset_invitationals

        conn, season_id = _pyramid_career()
        _seed_qualified_field(conn)

        resolve_ruleset_invitationals(conn, season_id, _SEED)

        wire = [h for h in load_news_headlines(conn, season_id) if h["category"] == "event_news"]
        inv_lines = [h for h in wire if "Cloth Classic" in h["headline_text"] or "No-Sting Open" in h["headline_text"]]
        assert len(inv_lines) >= 2

    def test_offseason_init_resolves_invitationals_and_events_beat_active(self):
        """A pyramid offseason init resolves both invitationals (recorded in
        v27_events_json) when a fame-qualified field exists, and the events
        beat is active."""
        import json as _json
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state as _gs,
            load_all_rosters,
            load_clubs,
            load_season,
        )

        conn, season_id = _pyramid_career()
        _seed_qualified_field(conn)
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        events = load_events(conn, season_id)
        keys = {e["event_key"] for e in events}
        assert "cloth_classic" in keys and "no_sting_open" in keys
        active = _json.loads(_gs(conn, "offseason_active_beats_json") or "[]")
        assert "events" in active


class TestWarmthCoexistenceWithMedia:
    """The V26 media credibility bonus and the V27 invitational warmth both
    feed the recruiting-credibility channel. A naive write to the shared
    v26_credibility_bonus key would clobber (or be clobbered by) a media choice
    in the same offseason. The integration uses a SEPARATE warmth key summed
    into the credibility score alongside media_bonus, and BOTH reset next
    offseason."""

    def test_media_bonus_and_invitational_warmth_sum_in_recruiting_credibility(self):
        from dodgeball_sim import media_events as me
        from dodgeball_sim.invitationals import apply_invitational_warmth
        from dodgeball_sim.recruiting_office import _credibility

        conn, season_id = _pyramid_career()
        base = _credibility(conn, season_id, "aurora", [])["score"]

        # Media choice grants +6 credibility.
        me.cache_media_event(conn, _media_event_by_id("local_feature"))
        me.set_media_choice(conn, "recruits")  # +6 credibility
        me.apply_media_choice(conn, season_id)
        after_media = _credibility(conn, season_id, "aurora", [])["score"]
        assert after_media - base == 6

        # An invitational warmth of +4 lands AFTER the media choice. Both must
        # reach recruiting SUMMED (6 + 4 = 10), not clobbered (4) and not
        # double-counted-media (6).
        apply_invitational_warmth(conn, "cloth_classic", 4, season_id)
        after_both = _credibility(conn, season_id, "aurora", [])["score"]
        assert after_both - base == 10

    def test_warmth_applied_before_media_does_not_clobber_media(self):
        """Order independence: warmth first, then media — both still sum."""
        from dodgeball_sim import media_events as me
        from dodgeball_sim.invitationals import apply_invitational_warmth
        from dodgeball_sim.recruiting_office import _credibility

        conn, season_id = _pyramid_career()
        base = _credibility(conn, season_id, "aurora", [])["score"]

        apply_invitational_warmth(conn, "cloth_classic", 4, season_id)
        me.cache_media_event(conn, _media_event_by_id("local_feature"))
        me.set_media_choice(conn, "recruits")  # +6
        me.apply_media_choice(conn, season_id)
        after_both = _credibility(conn, season_id, "aurora", [])["score"]
        assert after_both - base == 10

    def test_both_reset_next_offseason(self):
        """Both the media bonus and the invitational warmth are one-offseason
        effects: next offseason's init zeroes BOTH before that offseason's
        recruiting runs."""
        from dodgeball_sim import media_events as me
        from dodgeball_sim import invitationals
        from dodgeball_sim.invitationals import apply_invitational_warmth
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_season,
        )

        conn, season_id = _pyramid_career()
        me.cache_media_event(conn, _media_event_by_id("local_feature"))
        me.set_media_choice(conn, "recruits")  # +6
        me.apply_media_choice(conn, season_id)
        apply_invitational_warmth(conn, "cloth_classic", 4, season_id)
        assert me.media_credibility_bonus(conn) == 6
        assert invitationals.invitational_warmth(conn) == 4

        # Advance to offseason N+1 (no prestige seeded -> no invitationals, no
        # media event committed yet, so both must be reset to 0 by init).
        season2 = _next_season(conn)
        initialize_manager_offseason(
            conn, season2, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        assert me.media_credibility_bonus(conn) == 0
        assert invitationals.invitational_warmth(conn) == 0


class TestLegacyByteIdentical:
    def test_legacy_offseason_init_writes_no_invitationals_warmth_or_purse(self):
        """Legacy single-league: no invitationals, no warmth key, no invitational
        purse, no invitational event rows. Byte-identical to a world without
        the V27 invitational wiring."""
        import json as _json
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_season,
        )

        conn, season_id = _legacy_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        # No invitational state keys exist on a legacy world.
        for key in (
            "v27_invitational_warmth",
            "v27_cloth_classic_purse_for",
            "v27_no_sting_open_purse_for",
            "v27_cloth_classic_warmth_for",
            "v27_no_sting_open_warmth_for",
        ):
            assert get_state(conn, key) is None, key
        # The v27_events_json store is either absent or carries no invitational
        # rows (the cup is also absent on legacy). Assert no invitational keys.
        raw = get_state(conn, "v27_events_json")
        if raw:
            rows = _json.loads(raw)
            assert not any(r.get("event_key") in ("cloth_classic", "no_sting_open") for r in rows)
        # The events beat is not active on legacy.
        active = _json.loads(get_state(conn, "offseason_active_beats_json") or "[]")
        assert "events" not in active


# ---------------------------------------------------------------------------
# Phase 5 — Midseason International (MSI) + Founders' Exhibition
# ---------------------------------------------------------------------------


from dodgeball_sim.season import StandingsRow  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    load_division_memberships,
    save_standings,
)


def _division_clubs(conn, season_id, division_id):
    """Club ids seated in a given division this season (by division_id)."""
    return [
        m.club_id
        for m in load_division_memberships(conn, season_id)
        if m.division_id == division_id
    ]


def _seed_standings(conn, season_id, points_by_club):
    """Write season_standings rows giving each club a points total (and zero
    elsewhere). Controls the load_standings ranking (points-desc)."""
    rows = []
    clubs = load_clubs(conn)
    for cid in clubs:
        rows.append(StandingsRow(
            club_id=cid, wins=0, losses=0, draws=0,
            elimination_differential=0,
            points=int(points_by_club.get(cid, 0)),
        ))
    save_standings(conn, season_id, rows)
    conn.commit()


def _seed_fans(conn, fans_by_club, season_id):
    """Set each club's fan count via the receipted ledger (V26)."""
    from dodgeball_sim import fan_ledger

    for cid, n in fans_by_club.items():
        fan_ledger.add_fans(conn, cid, int(n), season_id, "test", f"+{n} test fans")
    conn.commit()


class TestMsiInvitees:
    def test_returns_exactly_the_premier_leader_and_circuit_leader(self):
        """msi_invitees returns exactly two clubs: the Premier leader + the
        Circuit leader, each the best-ranked club within its division."""
        from dodgeball_sim.invitationals import msi_invitees
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        # Make the first premier club and the second circuit club the leaders.
        points = {premier[0]: 30, circuit[1]: 25}
        _seed_standings(conn, season_id, points)

        invitees = msi_invitees(conn, season_id)

        assert len(invitees) == 2
        assert invitees[0] == premier[0]
        assert invitees[1] == circuit[1]

    def test_keys_on_division_id_not_tier_the_landmine(self):
        """Premier and Circuit are BOTH tier 1. Naive tier==1 filtering would
        grab both divisions' clubs mixed and rank them together. Construct
        standings where the top-2 tier-1 clubs by points are BOTH Circuit clubs
        — a tier-based selector would return two Circuit clubs. Keying on
        division_id must still return one Premier + one Circuit leader."""
        from dodgeball_sim.invitationals import msi_invitees
        from dodgeball_sim.persistence import load_division_map
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        # Two Circuit clubs occupy the top-2 tier-1 spots; the Premier leader
        # is 3rd overall but 1st within Premier.
        points = {circuit[0]: 40, circuit[1]: 35, premier[0]: 20}
        _seed_standings(conn, season_id, points)

        invitees = msi_invitees(conn, season_id)

        dmap = load_division_map(conn, season_id)
        assert len(invitees) == 2
        divisions = {dmap[c].division_id for c in invitees}
        assert divisions == {PREMIER.division_id, CIRCUIT.division_id}
        # The Premier invitee is the Premier leader (premier[0]); the Circuit
        # invitee is the Circuit leader (circuit[0], the top tier-1 club).
        assert invitees[0] == premier[0]
        assert invitees[1] == circuit[0]

    def test_empty_when_either_division_has_no_seat(self):
        from dodgeball_sim.invitationals import msi_invitees

        conn, season_id = _legacy_career()
        # Legacy single-league has no division memberships.
        assert msi_invitees(conn, season_id) == []


class TestResolveMsi:
    def test_foam_knockout_resolves_to_a_champion_in_the_two_leaders(self):
        from dodgeball_sim.invitationals import msi_invitees, resolve_msi
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        _seed_standings(conn, season_id, {premier[0]: 30, circuit[0]: 25})

        result = resolve_msi(conn, season_id, _SEED)

        assert result is not None
        assert result["champion_club_id"] in msi_invitees(conn, season_id)
        # 2 clubs -> a single Final.
        assert any(row["round"] == "Final" for row in result["bracket"])

    def test_champion_gets_purse_prestige_and_worlds_seeding_note(self):
        from dodgeball_sim import cup_service
        from dodgeball_sim.event_calendar import EventResult, load_events
        from dodgeball_sim.invitationals import resolve_msi
        from dodgeball_sim.persistence import get_state, load_club_prestige
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        _seed_standings(conn, season_id, {premier[0]: 30, circuit[0]: 25})

        def stub(conn, sid, event_key, event_name, invitees, root_seed, ns, meta=None):
            return EventResult(
                event_key=event_key, event_name=event_name, season_id=sid,
                champion_club_id=user, champion_club_name="User",
                ruleset="official_foam", purse_k=0, bracket=(),
                meta={"worlds_seeding": True},
            )

        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = stub
        try:
            before_treasury = treasury_k(conn)
            before_prestige = load_club_prestige(conn, user)
            result = resolve_msi(conn, season_id, _SEED)
            assert treasury_k(conn) - before_treasury == DEFAULT_EVENTS.msi_purse_champion_k
            assert load_club_prestige(conn, user) > before_prestige
            # The Worlds-seeding note is recorded in v27_events_json.
            events = load_events(conn, season_id)
            msi = [e for e in events if e["event_key"] == "msi"][0]
            assert msi["meta"].get("worlds_seeding") is True
            # Purse guard fired.
            assert get_state(conn, "v27_msi_purse_for") == season_id
        finally:
            cup_service.run_foam_knockout = original

    def test_resolve_is_idempotent_no_double_pay(self):
        from dodgeball_sim import cup_service
        from dodgeball_sim.event_calendar import EventResult
        from dodgeball_sim.invitationals import resolve_msi
        from dodgeball_sim.persistence import get_state, load_club_prestige
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        _seed_standings(conn, season_id, {premier[0]: 30, circuit[0]: 25})

        def stub(conn, sid, event_key, event_name, invitees, root_seed, ns, meta=None):
            return EventResult(
                event_key=event_key, event_name=event_name, season_id=sid,
                champion_club_id=user, champion_club_name="User",
                ruleset="official_foam", purse_k=0, bracket=(),
                meta={"worlds_seeding": True},
            )

        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = stub
        try:
            resolve_msi(conn, season_id, _SEED)
            after = treasury_k(conn)
            prestige_after = load_club_prestige(conn, user)
            # Re-resolve must not double-pay or re-award prestige.
            resolve_msi(conn, season_id, _SEED)
            assert treasury_k(conn) == after
            assert load_club_prestige(conn, user) == prestige_after
            assert get_state(conn, "v27_msi_resolved_for") == season_id
        finally:
            cup_service.run_foam_knockout = original

    def test_determinism_same_seed_same_champion(self):
        from dodgeball_sim.invitationals import resolve_msi
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn1, sid1 = _pyramid_career()
        p1 = _division_clubs(conn1, sid1, PREMIER.division_id)
        c1 = _division_clubs(conn1, sid1, CIRCUIT.division_id)
        _seed_standings(conn1, sid1, {p1[0]: 30, c1[0]: 25})
        r1 = resolve_msi(conn1, sid1, _SEED)

        conn2, sid2 = _pyramid_career()
        p2 = _division_clubs(conn2, sid2, PREMIER.division_id)
        c2 = _division_clubs(conn2, sid2, CIRCUIT.division_id)
        _seed_standings(conn2, sid2, {p2[0]: 30, c2[0]: 25})
        r2 = resolve_msi(conn2, sid2, _SEED)

        assert r1["champion_club_id"] == r2["champion_club_id"]
        assert r1["bracket"] == r2["bracket"]

    def test_ai_champion_gets_prestige_but_no_user_purse(self):
        from dodgeball_sim import cup_service
        from dodgeball_sim.event_calendar import EventResult
        from dodgeball_sim.invitationals import resolve_msi
        from dodgeball_sim.persistence import get_state, load_club_prestige
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        _seed_standings(conn, season_id, {premier[0]: 30, circuit[0]: 25})
        ai_champ = premier[1]

        def stub(conn, sid, event_key, event_name, invitees, root_seed, ns, meta=None):
            return EventResult(
                event_key=event_key, event_name=event_name, season_id=sid,
                champion_club_id=ai_champ, champion_club_name="AI",
                ruleset="official_foam", purse_k=0, bracket=(),
                meta={"worlds_seeding": True},
            )

        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = stub
        try:
            before = treasury_k(conn)
            ai_prestige_before = load_club_prestige(conn, ai_champ)
            resolve_msi(conn, season_id, _SEED)
            assert treasury_k(conn) == before  # no user purse
            assert load_club_prestige(conn, ai_champ) > ai_prestige_before
            assert get_state(conn, "v27_msi_purse_for") is None
        finally:
            cup_service.run_foam_knockout = original


# ---------------------------------------------------------------------------
# small helpers reused above
# ---------------------------------------------------------------------------


class TestFoundersInvitees:
    def test_returns_top_n_clubs_by_fan_count(self):
        """founders_invitees returns the top-N clubs by fan_ledger.club_fans
        (DEFAULT_EVENTS.founders_invite_count). Being beloved is the ticket —
        no prestige, no standing."""
        from dodgeball_sim.invitationals import founders_invitees

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        # Give the last N clubs the most fans so the ordering is non-trivial
        # (not just the roster/club-id order).
        top = clubs[-DEFAULT_EVENTS.founders_invite_count:]
        fans = {c.club_id: (1000 + i * 100) for i, c in enumerate(top)}
        # Everyone else gets a small fan count.
        for c in clubs:
            if c.club_id not in fans:
                fans[c.club_id] = 10
        _seed_fans(conn, fans, season_id)

        invitees = founders_invitees(conn, season_id, DEFAULT_EVENTS.founders_invite_count)

        assert len(invitees) == DEFAULT_EVENTS.founders_invite_count
        # The invitees are exactly the high-fan clubs.
        assert set(invitees) == {c.club_id for c in top}
        # Ordered by fan count descending.
        from dodgeball_sim import fan_ledger
        ranks = [fan_ledger.club_fans(conn, c) for c in invitees]
        assert ranks == sorted(ranks, reverse=True)

    def test_ties_broken_deterministically(self):
        """When two clubs have equal fan counts, the tiebreak is deterministic
        (alphabetical by club id) — the same call with the same data returns
        the same order."""
        from dodgeball_sim.invitationals import founders_invitees

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        # Give six clubs identical fan counts so the tiebreak decides.
        tied = clubs[:6]
        fans = {c.club_id: 500 for c in tied}
        for c in clubs:
            if c.club_id not in fans:
                fans[c.club_id] = 0
        _seed_fans(conn, fans, season_id)

        a = founders_invitees(conn, season_id, 5)
        b = founders_invitees(conn, season_id, 5)
        assert a == b
        # Top-5 of the six tied clubs, ordered by the deterministic tiebreak.
        assert len(a) == 5
        assert set(a).issubset({c.club_id for c in tied})

    def test_respects_top_n_argument(self):
        from dodgeball_sim.invitationals import founders_invitees

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        fans = {c.club_id: (i + 1) * 50 for i, c in enumerate(clubs)}
        _seed_fans(conn, fans, season_id)

        assert len(founders_invitees(conn, season_id, 3)) == 3
        assert len(founders_invitees(conn, season_id, 4)) == 4

    def test_fewer_than_two_fan_carriers_is_empty(self):
        from dodgeball_sim.invitationals import founders_invitees

        conn, season_id = _pyramid_career()
        # No fans seeded for any club -> all zero; top-N by zero fans still
        # returns N clubs (the exhibition fields a bracket). But if we ask for
        # top_n < 2, the bracket cannot form.
        assert founders_invitees(conn, season_id, 1) == []


class TestResolveFounders:
    def _stub_champion(self, champion_id):
        from dodgeball_sim import cup_service
        from dodgeball_sim.event_calendar import EventResult

        def stub(conn, sid, event_key, event_name, invitees, root_seed, ns, meta=None):
            return EventResult(
                event_key=event_key, event_name=event_name, season_id=sid,
                champion_club_id=champion_id, champion_club_name="Champ",
                ruleset="official_foam", purse_k=0, bracket=(),
                meta=dict(meta) if meta else {},
            )

        return stub

    def test_foam_knockout_resolves_to_a_champion(self):
        from dodgeball_sim.invitationals import founders_invitees, resolve_founders

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        fans = {c.club_id: (i + 1) * 100 for i, c in enumerate(clubs)}
        _seed_fans(conn, fans, season_id)

        result = resolve_founders(conn, season_id, _SEED)

        assert result is not None
        assert result["champion_club_id"] in founders_invitees(
            conn, season_id, DEFAULT_EVENTS.founders_invite_count
        )
        assert result["bracket"]

    def test_champion_purse_credited_once_and_idempotent_when_user_wins(self):
        from dodgeball_sim import cup_service
        from dodgeball_sim.invitationals import resolve_founders
        from dodgeball_sim.persistence import get_state

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        clubs = list(load_clubs(conn).values())
        _seed_fans(conn, {c.club_id: 100 for c in clubs}, season_id)

        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = self._stub_champion(user)
        try:
            before = treasury_k(conn)
            resolve_founders(conn, season_id, _SEED)
            assert treasury_k(conn) - before == DEFAULT_EVENTS.founders_purse_champion_k
            assert get_state(conn, "v27_founders_purse_for") == season_id
            after = treasury_k(conn)
            # Re-resolve must NOT double-pay (idempotent).
            resolve_founders(conn, season_id, _SEED)
            assert treasury_k(conn) == after
            assert get_state(conn, "v27_founders_resolved_for") == season_id
        finally:
            cup_service.run_foam_knockout = original

    def test_founders_is_money_only_no_prestige_no_seeding_no_warmth(self):
        """The declared no-seeding property: Founders' is money-only. Winning
        it grants NO prestige, records NO Worlds-seeding marker, and grants NO
        recruiting warmth. Being beloved is the ticket; nothing else."""
        from dodgeball_sim import cup_service, invitationals
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.invitationals import resolve_founders
        from dodgeball_sim.persistence import get_state, load_club_prestige

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        clubs = list(load_clubs(conn).values())
        _seed_fans(conn, {c.club_id: 100 for c in clubs}, season_id)

        prestige_before = load_club_prestige(conn, user)
        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = self._stub_champion(user)
        try:
            resolve_founders(conn, season_id, _SEED)
            # No prestige change.
            assert load_club_prestige(conn, user) == prestige_before
            # No recruiting warmth (the invitational warmth channel is untouched).
            assert invitationals.invitational_warmth(conn) == 0
            # No Worlds-seeding marker on the recorded event (money-only).
            events = load_events(conn, season_id)
            founders = [e for e in events if e["event_key"] == "founders"][0]
            assert not founders["meta"].get("worlds_seeding")
            # No prestige guard fired.
            assert get_state(conn, "v27_founders_prestige_for") is None
        finally:
            cup_service.run_foam_knockout = original

    def test_ai_champion_gets_no_user_purse_and_no_prestige(self):
        from dodgeball_sim import cup_service
        from dodgeball_sim.invitationals import resolve_founders
        from dodgeball_sim.persistence import get_state, load_club_prestige

        conn, season_id = _pyramid_career()
        user = get_state(conn, "player_club_id")
        clubs = list(load_clubs(conn).values())
        ai_champ = next(c.club_id for c in clubs if c.club_id != user)
        _seed_fans(conn, {c.club_id: 100 for c in clubs}, season_id)

        before = treasury_k(conn)
        ai_prestige_before = load_club_prestige(conn, ai_champ)
        original = cup_service.run_foam_knockout
        cup_service.run_foam_knockout = self._stub_champion(ai_champ)
        try:
            resolve_founders(conn, season_id, _SEED)
            assert treasury_k(conn) == before  # no user purse
            assert load_club_prestige(conn, ai_champ) == ai_prestige_before  # no prestige
            assert get_state(conn, "v27_founders_purse_for") is None
        finally:
            cup_service.run_foam_knockout = original

    def test_records_into_v27_events_json_and_surfaces_in_events_beat(self):
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.invitationals import resolve_founders

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        _seed_fans(conn, {c.club_id: 100 for c in clubs}, season_id)

        resolve_founders(conn, season_id, _SEED)
        events = load_events(conn, season_id)
        keys = {e["event_key"] for e in events}
        assert "founders" in keys
        founders = [e for e in events if e["event_key"] == "founders"][0]
        assert founders["champion_club_id"]
        assert founders["event_name"] == "Founders' Exhibition"

    def test_determinism_same_seed_same_champion(self):
        from dodgeball_sim.invitationals import resolve_founders

        conn1, sid1 = _pyramid_career()
        clubs1 = list(load_clubs(conn1).values())
        _seed_fans(conn1, {c.club_id: (i + 1) * 100 for i, c in enumerate(clubs1)}, sid1)
        r1 = resolve_founders(conn1, sid1, _SEED)

        conn2, sid2 = _pyramid_career()
        clubs2 = list(load_clubs(conn2).values())
        _seed_fans(conn2, {c.club_id: (i + 1) * 100 for i, c in enumerate(clubs2)}, sid2)
        r2 = resolve_founders(conn2, sid2, _SEED)

        assert r1["champion_club_id"] == r2["champion_club_id"]
        assert r1["bracket"] == r2["bracket"]


class TestPhase5WiringAndLegacy:
    def test_offseason_init_resolves_msi_and_founders_on_pyramid(self):
        """A pyramid offseason init resolves MSI (when division leaders exist)
        and Founders' (when fan carriers exist), recording both into
        v27_events_json, and the events beat stays active."""
        import json as _json
        from dodgeball_sim.event_calendar import load_events
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state as _gs,
            load_all_rosters,
            load_clubs,
            load_season,
        )
        from dodgeball_sim.world import CIRCUIT, PREMIER

        conn, season_id = _pyramid_career()
        # Seed standings so MSI has division leaders; seed fans so Founders'
        # has a field.
        premier = _division_clubs(conn, season_id, PREMIER.division_id)
        circuit = _division_clubs(conn, season_id, CIRCUIT.division_id)
        _seed_standings(conn, season_id, {premier[0]: 30, circuit[0]: 25})
        clubs = list(load_clubs(conn).values())
        _seed_fans(conn, {c.club_id: 100 for c in clubs}, season_id)

        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        events = load_events(conn, season_id)
        keys = {e["event_key"] for e in events}
        assert "msi" in keys
        assert "founders" in keys
        active = _json.loads(_gs(conn, "offseason_active_beats_json") or "[]")
        assert "events" in active

    def test_legacy_offseason_init_writes_no_msi_or_founders(self):
        """Legacy single-league byte-identical: no MSI, no Founders', no
        purse, no prestige, no seeding marker, no events beat."""
        import json as _json
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_season,
        )

        conn, season_id = _legacy_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        for key in (
            "v27_msi_resolved_for",
            "v27_msi_purse_for",
            "v27_msi_prestige_for",
            "v27_founders_resolved_for",
            "v27_founders_purse_for",
            "v27_founders_prestige_for",
        ):
            assert get_state(conn, key) is None, key
        raw = get_state(conn, "v27_events_json")
        if raw:
            rows = _json.loads(raw)
            assert not any(
                r.get("event_key") in ("msi", "founders") for r in rows
            )
        active = _json.loads(get_state(conn, "offseason_active_beats_json") or "[]")
        assert "events" not in active


# ---------------------------------------------------------------------------
# small helpers reused above
# ---------------------------------------------------------------------------


def _media_event_by_id(event_id):
    from dodgeball_sim import media_events as me
    for ev in me._CATALOG:
        if ev.event_id == event_id:
            return ev
    raise KeyError(event_id)


def _next_season(conn, root_seed=_SEED):
    from dodgeball_sim.offseason_ceremony import create_next_manager_season
    from dodgeball_sim.persistence import load_clubs

    clubs = load_clubs(conn)
    return create_next_manager_season(clubs, root_seed, season_number=2, year=2)
