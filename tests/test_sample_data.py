from dodgeball_sim.sample_data import curated_clubs, sample_match_setup


def test_curated_cast_size():
    clubs = curated_clubs()
    assert len(clubs) == 6


def test_every_curated_club_has_full_identity():
    for club in curated_clubs():
        assert club.primary_color, f"{club.club_id} missing primary_color"
        assert club.secondary_color, f"{club.club_id} missing secondary_color"
        assert club.venue_name, f"{club.club_id} missing venue_name"
        assert club.tagline, f"{club.club_id} missing tagline"


def test_sample_match_setup_still_works():
    setup = sample_match_setup()
    assert setup.team_a.id == "aurora"
    assert setup.team_b.id == "lunar"
    assert len(setup.team_a.players) >= 3
    assert len(setup.team_b.players) >= 3
