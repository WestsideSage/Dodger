from __future__ import annotations

from collections import Counter

from dodgeball_sim.scheduler import generate_round_robin, season_format_summary


def test_generate_round_robin_produces_balanced_single_round_schedule():
    club_ids = ["club_a", "club_b", "club_c", "club_d"]
    schedule = generate_round_robin(
        club_ids=club_ids,
        root_seed=2026,
        season_id="season_2026",
        league_id="league_main",
    )

    assert len(schedule) == 6
    assert all(match.season_id == "season_2026" for match in schedule)
    assert len({match.match_id for match in schedule}) == len(schedule)

    appearance_counts = Counter()
    matchup_pairs = set()
    for match in schedule:
        assert match.home_club_id != match.away_club_id
        appearance_counts[match.home_club_id] += 1
        appearance_counts[match.away_club_id] += 1
        matchup_pairs.add(frozenset((match.home_club_id, match.away_club_id)))

    assert appearance_counts == Counter({club_id: 3 for club_id in club_ids})
    assert len(matchup_pairs) == 6


def test_generate_round_robin_supports_odd_club_count_with_byes():
    club_ids = ["club_a", "club_b", "club_c", "club_d", "club_e"]
    schedule = generate_round_robin(
        club_ids=club_ids,
        root_seed=2026,
        season_id="season_2026",
        league_id="league_main",
    )

    assert len(schedule) == 10
    assert "__bye__" not in {match.home_club_id for match in schedule}
    assert "__bye__" not in {match.away_club_id for match in schedule}
    assert generate_round_robin(club_ids, 2026, "season_2026", "league_main") == schedule

    appearance_counts = Counter()
    matchup_pairs = set()
    for match in schedule:
        appearance_counts[match.home_club_id] += 1
        appearance_counts[match.away_club_id] += 1
        matchup_pairs.add(frozenset((match.home_club_id, match.away_club_id)))

    assert appearance_counts == Counter({club_id: 4 for club_id in club_ids})
    assert len(matchup_pairs) == 10


def test_season_format_summary_documents_playoff_format():
    summary = season_format_summary()
    assert summary["format"] == "round_robin_top4_playoff"
    assert summary["playoffs"] is True
    assert summary["champion_rule"] == "playoff_final"
