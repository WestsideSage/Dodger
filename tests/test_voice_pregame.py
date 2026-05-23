from __future__ import annotations

from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.voice_pregame import render_policy_line


def test_policy_line_uses_default_centroid_copy():
    assert (
        render_policy_line(CoachPolicy())
        == "Today we're Mixed, focused on Spread, and Opportunistic."
    )


def test_policy_line_changes_when_knobs_change():
    line = render_policy_line(
        CoachPolicy(
            approach="aggressive",
            target_focus="their_stars",
            catch_posture="go_for_catches",
        )
    )
    assert "Aggressive" in line
    assert "Their stars" in line
    assert "Go for catches" in line
