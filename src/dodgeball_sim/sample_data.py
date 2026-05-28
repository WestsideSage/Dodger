from __future__ import annotations

from typing import List

from .archetype_derivation import derive_archetype
from .league import Club
from .models import CoachPolicy, MatchSetup, Player, PlayerRatings, PlayerTraits, Team
from .setup_loader import describe_matchup


def _player(
    player_id: str,
    name: str,
    *,
    accuracy: float,
    power: float,
    dodge: float,
    catch: float,
    stamina: float = 60.0,
) -> Player:
    ratings = PlayerRatings(
        accuracy=accuracy,
        power=power,
        dodge=dodge,
        catch=catch,
        stamina=stamina,
    ).apply_bounds()
    return Player(
        id=player_id,
        name=name,
        ratings=ratings,
        archetype=derive_archetype(ratings),
        traits=PlayerTraits(),
    )


def _team(
    team_id: str,
    name: str,
    players: List[Player],
    *,
    policy: CoachPolicy,
    chemistry: float,
) -> Team:
    return Team(id=team_id, name=name, players=tuple(players), coach_policy=policy, chemistry=chemistry)


_AURORA = Club(
    club_id="aurora",
    name="Aurora Sentinels",
    colors="teal/charcoal",
    home_region="Northwest",
    founded_year=1998,
    coach_policy=CoachPolicy(
        approach="mixed",
        target_focus="their_stars",
        catch_posture="opportunistic",
        rush_commit="balanced",
        rush_target="center",
    ),
    primary_color="#2E5E5C",
    secondary_color="#1F2933",
    venue_name="Aurora Field House",
    tagline="Calculated aggression and deep scouting tradition",
)

_LUNAR = Club(
    club_id="lunar",
    name="Lunar Syndicate",
    colors="silver/navy",
    home_region="Northeast",
    founded_year=2002,
    coach_policy=CoachPolicy(
        approach="patient",
        target_focus="spread",
        catch_posture="play_safe",
        rush_commit="hold_back",
        rush_target="nearest",
    ),
    primary_color="#5C6F8A",
    secondary_color="#0F1A2E",
    venue_name="Arc Pavilion",
    tagline="Patience, attrition, and an ironclad defensive system",
)

_NORTHWOOD = Club(
    club_id="northwood",
    name="Northwood Ironclads",
    colors="brick/cream",
    home_region="Midwest",
    founded_year=1985,
    coach_policy=CoachPolicy(
        approach="aggressive",
        target_focus="their_stars",
        catch_posture="opportunistic",
        rush_commit="all_in",
        rush_target="strongest_side",
    ),
    primary_color="#B75A3A",
    secondary_color="#F4F1EA",
    venue_name="Wrecker Yard",
    tagline="Relentless tempo and unapologetic power throwing",
)

_HARBOR = Club(
    club_id="harbor",
    name="Harbor Tidebreakers",
    colors="navy/gold",
    home_region="Coastal",
    founded_year=1990,
    coach_policy=CoachPolicy(
        approach="patient",
        target_focus="spread",
        catch_posture="go_for_catches",
        rush_commit="hold_back",
        rush_target="center",
    ),
    primary_color="#1F3A5F",
    secondary_color="#D6A23A",
    venue_name="Anchorage Hall",
    tagline="A punishing defensive grind built on league-best catchers",
)

_GRANITE = Club(
    club_id="granite",
    name="Granite Specters",
    colors="sage/charcoal",
    home_region="Mountain",
    founded_year=2010,
    coach_policy=CoachPolicy(
        approach="mixed",
        target_focus="ball_holders",
        catch_posture="opportunistic",
        rush_commit="balanced",
        rush_target="strongest_side",
    ),
    primary_color="#8FA87E",
    secondary_color="#242428",
    venue_name="Granite Arena",
    tagline="Swarm tactics and deep rotation pressure",
)

_SOLSTICE = Club(
    club_id="solstice",
    name="Solstice Flare",
    colors="mustard/black",
    home_region="South",
    founded_year=2005,
    coach_policy=CoachPolicy(
        approach="aggressive",
        target_focus="their_stars",
        catch_posture="play_safe",
        rush_commit="balanced",
        rush_target="center",
    ),
    primary_color="#D6A23A",
    secondary_color="#242428",
    venue_name="Ember Court",
    tagline="Surgical sniper control and accuracy-focused recruitment",
)


def curated_clubs() -> List[Club]:
    """Return the v1 curated cast in display order."""
    return [_AURORA, _LUNAR, _NORTHWOOD, _HARBOR, _GRANITE, _SOLSTICE]


_TEAM_A = _team(
    "aurora",
    "Aurora Sentinels",
    [
        _player("aurora_captain", "Marcus Vance", accuracy=78, power=72, dodge=60, catch=55),
        _player("aurora_scout", "Elena Cross", accuracy=68, power=52, dodge=64, catch=58),
        _player("aurora_rookie", "Jamal Hayes", accuracy=60, power=50, dodge=52, catch=65),
    ],
    policy=_AURORA.coach_policy,
    chemistry=0.58,
)

_TEAM_B = _team(
    "lunar",
    "Lunar Syndicate",
    [
        _player("lunar_captain", "Sarah Ives", accuracy=75, power=70, dodge=57, catch=50),
        _player("lunar_anchor", "David Mercer", accuracy=65, power=60, dodge=62, catch=70),
        _player("lunar_spotter", "Chloe Bridges", accuracy=55, power=48, dodge=58, catch=60),
    ],
    policy=_LUNAR.coach_policy,
    chemistry=0.52,
)


def sample_match_setup() -> MatchSetup:
    """Return the canonical sample matchup for demos/CLI."""

    return MatchSetup(team_a=_TEAM_A, team_b=_TEAM_B, config_version="phase1.v1")


def describe_sample_matchup() -> str:
    return describe_matchup(sample_match_setup())


def scripted_blowout_loss(
    *,
    player_survivors: int,
    opponent_survivors: int,
    player_first_in_box: bool = True,
    player_club_id: str = "aurora",
    opponent_club_id: str = "lunar",
) -> tuple["MatchResult", str, str]:
    """Build a fully-resolved ``MatchResult`` for testing postgame copy.

    The match has no real events beyond ``match_start`` / ``match_end``; the
    box score is hand-built to carry the desired final survivor counts. The
    winner is decided purely by survivor counts (ties yield ``None``).

    Parameters
    ----------
    player_survivors / opponent_survivors:
        Final survivor counts that should appear in the box score totals.
    player_first_in_box:
        Whether the player team's id is the first key in
        ``box_score["teams"]``. Use ``False`` to exercise the regression
        where the player team was not the first key and the headline
        fallback flipped the perspective.

    Returns
    -------
    (result, player_club_id, opponent_club_id)
    """

    from .engine import MatchResult
    from .events import MatchEvent

    if player_survivors == opponent_survivors:
        winner_id: str | None = None
    elif player_survivors > opponent_survivors:
        winner_id = player_club_id
    else:
        winner_id = opponent_club_id

    def _team_box(name: str, living: int) -> dict:
        return {
            "name": name,
            "totals": {"living": living, "catches": 0, "outs_recorded": 0},
            "players": {},
        }

    player_box = _team_box("Aurora Sentinels", player_survivors)
    opponent_box = _team_box("Lunar Syndicate", opponent_survivors)

    teams: dict[str, dict] = {}
    if player_first_in_box:
        teams[player_club_id] = player_box
        teams[opponent_club_id] = opponent_box
    else:
        teams[opponent_club_id] = opponent_box
        teams[player_club_id] = player_box

    box_score = {"teams": teams, "winner": winner_id}

    events = (
        MatchEvent(
            event_id=0,
            tick=0,
            seed=7,
            event_type="match_start",
            phase="init",
            actors={"team_a": player_club_id, "team_b": opponent_club_id},
            context={
                "config_version": "phase1.v1",
                "difficulty": "pro",
                "meta_patch": None,
                "team_policies": {
                    player_club_id: CoachPolicy().as_dict(),
                    opponent_club_id: CoachPolicy().as_dict(),
                },
            },
            probabilities={},
            rolls={},
            outcome={"message": "start"},
            state_diff={},
        ),
        MatchEvent(
            event_id=1,
            tick=1,
            seed=7,
            event_type="match_end",
            phase="complete",
            actors={"winner": winner_id},
            context={"reason": "elimination", "moment_events": []},
            probabilities={},
            rolls={},
            outcome={"winner": winner_id},
            state_diff={},
        ),
    )

    result = MatchResult(
        events=events,
        winner_team_id=winner_id,
        box_score=box_score,
        final_tick=1,
        seed=7,
        config_version="phase1.v1",
    )
    return result, player_club_id, opponent_club_id


def scripted_shutout_win(
    *,
    home_score: int,
    away_score: int,
    player_club_id: str = "aurora",
    opponent_club_id: str = "lunar",
):
    """Build a fully-resolved ``MatchResult`` for a shutout-win scenario.

    Convention: ``home_score`` is the player team's survivor count and
    ``away_score`` is the opponent's. Returns ``(result, player_club_id,
    opponent_club_id)`` mirroring ``scripted_blowout_loss`` so postgame
    copy tests can assert against either perspective.
    """

    return scripted_blowout_loss(
        player_survivors=home_score,
        opponent_survivors=away_score,
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
    )


def scripted_match(
    *,
    selected_plan: str,
    final_score: tuple[int, int],
    player_club_id: str = "aurora",
    opponent_club_id: str = "lunar",
):
    """Build a fully-resolved ``MatchResult`` with a chosen plan + score.

    ``selected_plan`` is the player-facing plan label (e.g. "Defensive",
    "Aggressive") — stored on the start event's team-policy snapshot so
    aftermath generators that consult ``team_policies`` see the same
    value the user saw at the command-center. ``final_score`` is
    ``(player_survivors, opponent_survivors)``.

    Returns ``(result, player_club_id, opponent_club_id)``.
    """

    player_survivors, opponent_survivors = final_score
    result, _player, _opponent = scripted_blowout_loss(
        player_survivors=player_survivors,
        opponent_survivors=opponent_survivors,
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
    )
    # Stash the selected plan label on the match-start context so any
    # consumer that walks ``events[0].context["selected_plan_label"]``
    # can recover the user's choice without re-deriving from intent.
    if result.events:
        result.events[0].context["selected_plan_label"] = selected_plan
    return result, player_club_id, opponent_club_id


def scripted_tied_semifinal(
    *,
    home_seed: int,
    away_seed: int,
    regulation_score: tuple[int, int],
    home_club_id: str = "aurora",
    away_club_id: str = "lunar",
):
    """Build a scripted semifinal stub for playoff-resolution tests.

    Returns a lightweight namespace carrying just the fields
    ``resolve_playoff_match`` needs (home/away club ids, the seeds they
    entered the bracket with, and the regulation survivor counts). The
    intent is to mirror the shape of a finalised regular match without
    pulling in the full ``MatchRecord``/``MatchResult`` plumbing.
    """

    from types import SimpleNamespace

    home_survivors, away_survivors = regulation_score
    if home_survivors > away_survivors:
        regulation_winner_id: str | None = home_club_id
    elif away_survivors > home_survivors:
        regulation_winner_id = away_club_id
    else:
        regulation_winner_id = None

    return SimpleNamespace(
        match_id=f"sample_semifinal_{home_club_id}_{away_club_id}",
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        home_seed=home_seed,
        away_seed=away_seed,
        home_survivors=home_survivors,
        away_survivors=away_survivors,
        regulation_winner_id=regulation_winner_id,
    )


def club_with_bench_star(
    *,
    bench_player_id: str,
    bench_ovr: int,
    club_id: str = "aurora",
):
    """Build a 7-player club fixture with a high-OVR player on the bench.

    Used by Task 2 (Lineup Editor) tests to exercise the manual override
    pipeline. Returns a lightweight namespace carrying ``club_id`` and a
    ``roster`` sequence — enough for ``apply_manual_lineup`` and the
    ``save_lineup_default`` persistence call without dragging the full
    ``Club``/``Team`` plumbing into the test.

    The five "p2".."p6" starters are deliberately middling so the bench star
    is unambiguously the highest-OVR player; ``apply_manual_lineup`` is
    structural, but downstream resolvers sort the backfill by OVR.
    """

    from types import SimpleNamespace

    # Approximate target OVR by setting all four core ratings to the same
    # value. The exact OVR depends on ``overall_skill`` but using a uniform
    # rating gives us a deterministic, easy-to-reason-about baseline.
    bench_rating = float(bench_ovr)
    bench_player = _player(
        bench_player_id,
        "Ezra Prism",
        accuracy=bench_rating,
        power=bench_rating,
        dodge=bench_rating,
        catch=bench_rating,
    )

    # Six "filler" starters at a middling rating so the bench star clearly
    # outranks them on OVR ordering. ``p1``..``p6`` ids keep tests legible.
    starters: List[Player] = [
        _player(
            f"p{i}",
            f"Filler {i}",
            accuracy=55.0,
            power=55.0,
            dodge=55.0,
            catch=55.0,
        )
        for i in range(1, 7)
    ]

    roster: List[Player] = starters + [bench_player]
    return SimpleNamespace(club_id=club_id, roster=roster)


__all__ = [
    "club_with_bench_star",
    "curated_clubs",
    "sample_match_setup",
    "describe_sample_matchup",
    "scripted_blowout_loss",
    "scripted_match",
    "scripted_shutout_win",
    "scripted_tied_semifinal",
]
