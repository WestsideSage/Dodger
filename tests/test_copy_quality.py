from __future__ import annotations

from dodgeball_sim.copy_quality import has_unresolved_token, title_label


def test_has_unresolved_token_detects_raw_ids_and_template_blanks():
    assert has_unresolved_token("MVP: aurora_3")
    assert has_unresolved_token("Winner: {winner}")
    assert has_unresolved_token("Prospect: <name>")


def test_has_unresolved_token_allows_normal_sports_copy():
    assert not has_unresolved_token("MVP: Mara Voss")
    assert not has_unresolved_token("Aurora Sentinels Win The Final")


def test_title_label_normalizes_common_ui_labels():
    assert title_label("sim to next user match") == "Sim To Next User Match"
    assert title_label("mvp") == "MVP"
    assert title_label("hall of fame") == "Hall Of Fame"


def test_league_wire_copy_official_vs_legacy():
    from dodgeball_sim.view_models import build_wire_items
    from dodgeball_sim.league import Club
    from dodgeball_sim.models import CoachPolicy

    clubs = {
        "A": Club("A", "Club A", "red", "North", 2020, CoachPolicy()),
        "B": Club("B", "Club B", "blue", "South", 2020, CoachPolicy()),
    }
    
    # 1. Legacy match row
    legacy_row = {
        "match_id": "m1", "week": 1, "home_club_id": "A", "away_club_id": "B",
        "winner_club_id": "A", "home_survivors": 4, "away_survivors": 0,
    }
    items = build_wire_items([legacy_row], clubs)
    assert items[0].text == "Week 1: Club A beat Club B with 4-0 survivors."

    # 2. Official match row
    official_row = {
        "match_id": "m2", "week": 2, "home_club_id": "A", "away_club_id": "B",
        "winner_club_id": "A", "home_survivors": 1, "away_survivors": 0,
        "scoring_model": "foam", "home_game_points": 8, "away_game_points": 2,
    }
    items = build_wire_items([official_row], clubs)
    assert items[0].text == "Week 2: Club A beat Club B 8-2 on game points."

