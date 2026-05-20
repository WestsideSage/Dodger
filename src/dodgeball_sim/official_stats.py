"""Derive box-score statistics from an OfficialEvent stream.

The integrity contract requires events to be canonical. Box scores must be
*derived* from events, not written separately. This module consumes a
stream of :class:`OfficialEvent` records (from an autonomous official game)
and produces a dict matching the generic engine's ``box_score`` shape so
the frontend, stats persistence, and franchise pipeline don't have to
learn a new shape.

Canonical shape:

.. code-block:: python

    {
        "teams": {
            "<team_id>": {
                "name": str,
                "totals": {"outs_recorded", "hits", "catches", "dodges", "living"},
                "players": {"<player_id>": {"name", "throws", "hits", "catches",
                                            "dodges", "caught", "is_out"}},
            },
        },
        "winner": "<team_id>" | None,
    }
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from .official_events import OfficialEvent, OfficialEventKind


def derive_box_score(
    events: Iterable[OfficialEvent],
    *,
    team_a_id: str,
    team_b_id: str,
    team_a_name: str | None = None,
    team_b_name: str | None = None,
    player_team_map: Mapping[str, str] | None = None,
    player_name_map: Mapping[str, str] | None = None,
    starters_a: Iterable[str] = (),
    starters_b: Iterable[str] = (),
    winner_team_id: str | None = None,
) -> Dict[str, Any]:
    """Return a canonical ``box_score`` derived from an OfficialEvent stream."""

    team_a_name = team_a_name or team_a_id
    team_b_name = team_b_name or team_b_id
    player_name_map = dict(player_name_map or {})
    team_totals = {
        team_a_id: {"outs_recorded": 0, "hits": 0, "catches": 0, "dodges": 0, "living": 0},
        team_b_id: {"outs_recorded": 0, "hits": 0, "catches": 0, "dodges": 0, "living": 0},
    }

    # Seed roster from starters so all expected players appear in the output.
    players: Dict[str, Dict[str, Any]] = {}

    def _ensure(pid: str, team_id: str | None = None) -> Dict[str, Any]:
        if pid not in players:
            players[pid] = {
                "player_id": pid,
                "team_id": team_id,
                "name": player_name_map.get(pid, pid),
                "throws": 0, "hits": 0, "catches": 0,
                "dodges": 0, "caught": 0, "is_out": False,
            }
        elif team_id and players[pid].get("team_id") is None:
            players[pid]["team_id"] = team_id
        return players[pid]

    for pid in starters_a:
        _ensure(pid, team_id=team_a_id)
    for pid in starters_b:
        _ensure(pid, team_id=team_b_id)

    def _other(team_id: str) -> str:
        return team_b_id if team_id == team_a_id else team_a_id

    for event in events:
        if event.kind != OfficialEventKind.SEQUENCE:
            continue
        payload = event.payload or {}
        if payload.get("kind") != "sequence_final":
            continue

        thrower_team = payload.get("thrower_team_id") or (
            event.team_ids[0] if event.team_ids else None
        )
        thrower_id = payload.get("thrower_id")
        outs = list(payload.get("outs", []))
        catches = list(payload.get("catches", []))

        defense_team = _other(thrower_team) if thrower_team in team_totals else None

        if thrower_id:
            t_rec = _ensure(thrower_id, team_id=thrower_team)
            t_rec["throws"] += 1

        for catcher_id in catches:
            c_team = (
                (player_team_map or {}).get(catcher_id) or defense_team
            )
            c_rec = _ensure(catcher_id, team_id=c_team)
            c_rec["catches"] += 1
            if c_team in team_totals:
                team_totals[c_team]["catches"] += 1
            if thrower_id:
                _ensure(thrower_id, team_id=thrower_team)["caught"] += 1

        for pid in outs:
            if player_team_map and pid in player_team_map:
                pteam = player_team_map[pid]
            elif pid == thrower_id:
                pteam = thrower_team
            else:
                pteam = defense_team
            rec = _ensure(pid, team_id=pteam)
            rec["is_out"] = True
            if pteam in team_totals:
                opp = _other(pteam)
                team_totals[opp]["outs_recorded"] += 1
                if not catches and pid != thrower_id:
                    team_totals[opp]["hits"] += 1
                    if thrower_id:
                        _ensure(thrower_id, team_id=thrower_team)["hits"] += 1

    # Compute living counts.
    for pid, rec in players.items():
        if rec.get("team_id") in team_totals and not rec.get("is_out"):
            team_totals[rec["team_id"]]["living"] += 1

    def _players_for(team_id: str) -> Dict[str, Dict[str, Any]]:
        result = {}
        for pid, rec in players.items():
            if rec.get("team_id") != team_id:
                continue
            result[pid] = {
                "name": rec["name"], "throws": rec["throws"],
                "hits": rec["hits"], "catches": rec["catches"],
                "dodges": rec["dodges"], "caught": rec["caught"],
                "is_out": rec["is_out"],
            }
        return result

    return {
        "teams": {
            team_a_id: {
                "name": team_a_name,
                "totals": team_totals[team_a_id],
                "players": _players_for(team_a_id),
            },
            team_b_id: {
                "name": team_b_name,
                "totals": team_totals[team_b_id],
                "players": _players_for(team_b_id),
            },
        },
        "winner": winner_team_id,
    }
