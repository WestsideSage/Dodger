from __future__ import annotations

from typing import Any


TIER1_REGISTER: dict[str, str] = {
    "policy.approach.aggressive.label": "Aggressive",
    "policy.approach.aggressive.preview": "Aggressive - team throws first and accepts the extra heat.",
    "policy.approach.patient.label": "Patient",
    "policy.approach.patient.preview": "Patient - team waits for the clean opening before forcing the play.",
    "policy.approach.mixed.label": "Mixed",
    "policy.approach.mixed.preview": "Mixed - team balances early pressure with possession control.",
    "policy.target_focus.their_stars.label": "Their stars",
    "policy.target_focus.their_stars.preview": "Their stars - hunt the players who carry the opponent's ceiling.",
    "policy.target_focus.ball_holders.label": "Ball-holders",
    "policy.target_focus.ball_holders.preview": "Ball-holders - pressure whoever is controlling possession right now.",
    "policy.target_focus.spread.label": "Spread",
    "policy.target_focus.spread.preview": "Spread - make the whole line feel the pressure instead of one target.",
    "policy.catch_posture.go_for_catches.label": "Go for catches",
    "policy.catch_posture.go_for_catches.preview": "Go for catches - trust hands and timing to steal bodies back.",
    "policy.catch_posture.play_safe.label": "Play safe",
    "policy.catch_posture.play_safe.preview": "Play safe - value survival first and refuse low-percentage grabs.",
    "policy.catch_posture.opportunistic.label": "Opportunistic",
    "policy.catch_posture.opportunistic.preview": "Opportunistic - take the catch when it is there, not before.",
    "policy.rush_commit.all_in.label": "All in",
    "policy.rush_commit.all_in.preview": "All in - send the whole front to win the opening ball race.",
    "policy.rush_commit.balanced.label": "Balanced",
    "policy.rush_commit.balanced.preview": "Balanced - contest the rush without emptying the back line.",
    "policy.rush_commit.hold_back.label": "Hold back",
    "policy.rush_commit.hold_back.preview": "Hold back - protect bodies first and concede some opening chaos.",
    "policy.rush_target.nearest.label": "Nearest",
    "policy.rush_target.nearest.preview": "Nearest - each runner grabs the easiest live ball first.",
    "policy.rush_target.strongest_side.label": "Strongest side",
    "policy.rush_target.strongest_side.preview": "Strongest side - flood the side where the ball count favors the rush.",
    "policy.rush_target.center.label": "Center",
    "policy.rush_target.center.preview": "Center - collapse toward the middle to own the central lane.",
    "moment.dramatic_catch.headline": "{catcher} plucks one clean and {returning} is back on.",
    "moment.dramatic_catch.body": "{catcher} plucked it clean and {returning} sprinted straight back in.",
    "moment.dramatic_catch.beat": "{catcher} plucks it and {returning} is back on.",
    "moment.late_game_escape.headline": "{survivor} is alone against {attacker_count}.",
    "moment.late_game_escape.body": "{survivor} was left alone and still kept the point alive against {attacker_count}.",
    "moment.late_game_escape.beat": "{survivor} is down to a solo stand against {attacker_count}.",
    "moment.one_v_one_finale.headline": "{a} vs {b} - last two standing.",
    "moment.one_v_one_finale.body": "{a} and {b} were locked in a 1v1 duel as the final player standing for each side.",
    "moment.one_v_one_finale.beat": "{a} vs {b} - last two standing.",
    "moment.gassed_collapse.headline": "{player} is gassed and the legs are gone.",
    "moment.gassed_collapse.body": "{player} hit the red and the body finally gave out.",
    "moment.gassed_collapse.beat": "{player} is gassed - body gave out.",
    "moment.flood_throw.headline": "{team} sends a wall - {count} throws at once.",
    "moment.flood_throw.body": "{team} sent a wall of pressure with {count} throws in the same burst.",
    "moment.flood_throw.beat": "{team} sends a wall - {count} throws.",
    "moment.comeback.headline": "{team} were down {deficit} and clawed it back with {catches} catches.",
    "moment.comeback.body": "{team} were down {deficit} bodies and fought all the way back, sparked by {catches} catches.",
    "moment.comeback.beat": "{team} climb back from {deficit} down.",
    "banner.late_game_escape": "{survivor} is alone against {attacker_count}.",
    "banner.one_v_one_finale": "{a} vs {b} - last two standing.",
    "card.comeback": "{team} were down {deficit} - clawed it back with {catches} catches.",
    "broadcast.rivalry_tag": "Rivalry Game",
    "broadcast.playoff_final.title": "Title Game",
    "broadcast.playoff_semifinal.title": "Win Or Go Home",
    "broadcast.highlight.opening": "Opening Crack",
    "broadcast.highlight.swing": "Momentum Swing",
    "broadcast.highlight.finish": "Winning Play",
    "broadcast.commentary.record_eliminations": "{player} already owns the league career eliminations mark and just added another.",
    "broadcast.commentary.record_catches": "{player} already owns the league career catches mark and just stole another body.",
    "broadcast.commentary.record_dodges": "{player} already owns the league career dodges mark and just slipped another throw.",
}


def for_tier(tier: int) -> dict[str, str]:
    if tier != 1:
        raise KeyError(f"Unsupported voice register tier: {tier}")
    return dict(TIER1_REGISTER)


def tier1(key: str, **fmt: Any) -> str:
    if key not in TIER1_REGISTER:
        raise KeyError(key)
    template = TIER1_REGISTER[key]
    if fmt:
        return template.format_map(fmt)
    if "{" in template:
        return template.format_map(fmt)
    return template


__all__ = ["TIER1_REGISTER", "for_tier", "tier1"]
