"""V27 The Calendar — Phase 2: the web home for the Domestic Cup.

The dormant pure-bracket model in ``cup.py`` (kept import-pure per
``test_cup_module_has_no_db_boundary_imports``) gets a web home here. All
DB + sim wiring lives in this module; ``cup.py`` stays pure. The CLI's
``_simulate_next_cup_round`` / ``_award_cup_champion_if_ready`` /
``_pick_cup_winner`` (in ``dynasty_cli.py``) are the reference implementation —
their logic is MIRRORED here, never imported (the CLI carries print deps).

Architecture guardrails (non-negotiable):
- Foam engine only (the standard ``simulate_match`` path; no cloth/no-sting).
- New seed namespace ``v27_cup``: ``derive_seed(root_seed, 'v27_cup', season_id)``.
- ``cup_id = f"{season_id}_domestic_cup"`` (distinct from the legacy CLI cup).
- ``meta_patch=None`` (MetaPatch is retired; do not revive it).
- Pyramid-gated by the caller; legacy single-league saves never reach this.
- Purses + fans idempotent via per-event guards (the V26 pattern).
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List

from .cup import CupBracket, generate_cup_bracket
from .rng import DeterministicRNG, derive_seed


_DOMESTIC_CUP_EVENT_KEY = "domestic_cup"
_DOMESTIC_CUP_NAME = "Domestic Cup"
_CUP_ID_SUFFIX = "_domestic_cup"
_RESOLVED_GUARD = "v27_domestic_cup_resolved_for"
_FANS_GUARD = "v27_domestic_cup_fans_for"


def _cup_id(season_id: str) -> str:
    return f"{season_id}{_CUP_ID_SUFFIX}"


def _cup_bracket_to_payload(bracket: CupBracket) -> dict:
    """Serialize a ``CupBracket`` to the dict shape ``load_cup_bracket`` returns.

    Mirrors ``dynasty_cli._cup_bracket_to_payload`` (the CLI private helper) —
    replicated here so ``cup_service`` never imports the CLI.
    """
    return {
        "club_ids": list(bracket.club_ids),
        "rounds": [
            {
                "round_number": round_.round_number,
                "matches": [
                    {
                        "match_id": match.match_id,
                        "round_number": match.round_number,
                        "slot_number": match.slot_number,
                        "side_a": {
                            "club_id": match.side_a.club_id,
                            "source_match_id": match.side_a.source_match_id,
                        },
                        "side_b": None
                        if match.side_b is None
                        else {
                            "club_id": match.side_b.club_id,
                            "source_match_id": match.side_b.source_match_id,
                        },
                        "auto_advance_club_id": match.auto_advance_club_id,
                    }
                    for match in round_.matches
                ],
            }
            for round_ in bracket.rounds
        ],
    }


def _division_club_ids(conn: sqlite3.Connection, season_id: str) -> List[str]:
    """All club ids with a division seat this season (the 28-club pyramid)."""
    from .persistence import load_division_memberships

    return [m.club_id for m in load_division_memberships(conn, season_id)]


def ensure_domestic_cup(
    conn: sqlite3.Connection, season_id: str, root_seed: int
) -> dict:
    """Generate + persist the cross-division Domestic Cup bracket, once.

    Idempotent: if a bracket already exists for this season it is returned
    as-is (never regenerated/overwritten). The bracket covers ALL division
    clubs (the 28-club pyramid), seeded deterministically via the ``v27_cup``
    namespace. Bye matches have their auto-advance winners persisted as cup
    results so the resolver can walk the bracket without special-casing byes.

    Returns the persisted bracket row (``{"cup_id", "season_id", "bracket"}``).
    """
    from .persistence import (
        load_cup_bracket,
        save_cup_bracket,
        save_cup_result,
    )

    existing = load_cup_bracket(conn, season_id)
    if existing is not None:
        return existing

    club_ids = _division_club_ids(conn, season_id)
    if len(club_ids) < 2:
        # A season with fewer than 2 division seats cannot form a cup bracket
        # (e.g. a transition/test season before memberships are saved). No-op
        # rather than raise — the events beat simply shows no cup that season.
        return None
    bracket = generate_cup_bracket(
        sorted(club_ids),
        DeterministicRNG(derive_seed(root_seed, "v27_cup", season_id)),
    )
    cup_id = _cup_id(season_id)
    payload = _cup_bracket_to_payload(bracket)
    save_cup_bracket(conn, cup_id, season_id, payload)

    # Persist bye (auto-advance) results up front so the resolver walks a
    # uniformly-populated results map (mirrors the CLI's _ensure_season_artifacts).
    for round_payload in payload["rounds"]:
        for match in round_payload["matches"]:
            if match["auto_advance_club_id"]:
                save_cup_result(
                    conn,
                    cup_id,
                    int(round_payload["round_number"]),
                    str(match["match_id"]),
                    str(match["auto_advance_club_id"]),
                )
    conn.commit()
    return load_cup_bracket(conn, season_id)


# ---------------------------------------------------------------------------
# Task 2.2 — resolve the bracket to a champion through the real foam engine
# ---------------------------------------------------------------------------


def _cup_resolve_side(side: dict | None, results: dict) -> str | None:
    """Resolve one side of a cup match to a club id (mirrors the CLI helper)."""
    if side is None:
        return None
    club_id = side.get("club_id")
    if club_id:
        return str(club_id)
    source_match_id = side.get("source_match_id")
    if source_match_id:
        return results.get(str(source_match_id))
    return None


def _pick_cup_winner(record, rosters: dict) -> tuple[str, str | None]:
    """Deterministic winner pick — no draws (mirrors the CLI helper).

    The foam engine can return a None winner (time-cap tie); the cup must
    always advance someone, so survivor count decides, then overall skill,
    then a seeded alphabetical tiebreak.
    """
    if record.result.winner_team_id is not None:
        return record.result.winner_team_id, None
    home_score = record.result.box_score["teams"][record.home_club_id]["totals"]["living"]
    away_score = record.result.box_score["teams"][record.away_club_id]["totals"]["living"]
    if home_score != away_score:
        return (
            record.home_club_id if home_score > away_score else record.away_club_id,
            "survivor tiebreak",
        )
    home_ovr = sum(player.overall_skill() for player in rosters[record.home_club_id])
    away_ovr = sum(player.overall_skill() for player in rosters[record.away_club_id])
    if home_ovr != away_ovr:
        return (
            record.home_club_id if home_ovr > away_ovr else record.away_club_id,
            "overall tiebreak",
        )
    return min(record.home_club_id, record.away_club_id), "seeded tiebreak"


def _round_label(round_number: int, total_rounds: int) -> str:
    if round_number == total_rounds:
        return "Final"
    if round_number == total_rounds - 1:
        return "Semifinal"
    if round_number == total_rounds - 2:
        return "Quarterfinal"
    return f"Round {round_number}"


def detect_giant_killings(result: dict, division_map: dict) -> list[dict]:
    """Return the bracket rows where a lower-tier club (higher tier number =
    lower division) beat a higher-tier club. ``division_map`` is
    ``load_division_map(conn, season_id)`` → ``{club_id: DivisionMembership}``.

    Tier is the domestic climb order (1 = Premier); a "giant-killing" is a
    winner whose tier is strictly greater (lower division) than the loser's.
    Cross-tier only — same-tier upsets are not giant-killings.
    """
    kills: list[dict] = []
    for row in result.get("bracket", []):
        winner = row.get("winner_club_id")
        home = row.get("home_club_id")
        away = row.get("away_club_id")
        loser = home if winner == away else away
        if winner is None or loser is None:
            continue
        w_seat = division_map.get(winner)
        l_seat = division_map.get(loser)
        if w_seat is None or l_seat is None:
            continue
        if w_seat.tier > l_seat.tier:
            kills.append({
                "round": row.get("round"),
                "winner_club_id": winner,
                "loser_club_id": loser,
                "winner_tier": w_seat.tier,
                "loser_tier": l_seat.tier,
            })
    return kills


def resolve_domestic_cup(
    conn: sqlite3.Connection, season_id: str, root_seed: int
) -> dict:
    """Auto-sim the Domestic Cup bracket to a single champion through the real
    foam engine, then award the trophy + fans + purse + news + record the event.

    Idempotent on the ``v27_domestic_cup_resolved_for`` guard (holds season_id):
    a re-call returns the already-recorded event result without re-simulating,
    re-awarding, or re-paying. Foam engine only (``official_foam``);
    ``meta_patch=None`` (MetaPatch is retired). The champion's purse is
    tier-scaled (the champion's own division tier) and paid via the idempotent
    ``apply_event_purse``; a fan grant lands only when the USER club wins
    (fans are a user-program feature — V26), guarded per-event. A giant-killing
    news line is emitted when a lower-tier club beats a higher-tier one.

    Returns the recorded event-result dict (the shape stored in
    ``v27_events_json``): ``{event_key, event_name, season_id, champion_club_id,
    champion_club_name, ruleset, purse_k, bracket}``.
    """
    from .config import DEFAULT_EVENTS
    from .event_calendar import (
        EventBracketRow,
        EventResult,
        apply_event_purse,
        emit_event_news,
        load_events,
        record_event,
    )
    from .franchise import MatchRecord, simulate_match
    from .persistence import (
        get_state,
        load_club_roster,
        load_clubs,
        load_cup_bracket,
        load_cup_results,
        load_division_map,
        save_club_trophy,
        save_cup_result,
        save_news_headlines,
        set_state,
    )
    from .scheduler import ScheduledMatch
    from .world import pyramid_world_active

    cup_id = _cup_id(season_id)
    row = load_cup_bracket(conn, season_id)
    if row is None:
        # No bracket (ensure_domestic_cup no-op'd — e.g. a season with < 2
        # division seats). Nothing to resolve; no event recorded.
        return None
    bracket = row["bracket"]
    total_rounds = len(bracket["rounds"])
    final_match_id = bracket["rounds"][-1]["matches"][0]["match_id"]

    # Idempotent: if already resolved this season, return the recorded result.
    guard = _RESOLVED_GUARD
    if get_state(conn, guard) == season_id:
        recorded = [e for e in load_events(conn, season_id)
                    if e.get("event_key") == _DOMESTIC_CUP_EVENT_KEY]
        if recorded:
            return recorded[0]

    clubs = load_clubs(conn)
    rosters = {cid: load_club_roster(conn, cid) for cid in clubs}
    division_map = load_division_map(conn, season_id)
    player_club_id = get_state(conn, "player_club_id") or ""

    results = load_cup_results(conn, season_id)
    bracket_rows: list[dict] = []
    giant_killings: list[dict] = []

    # Walk rounds in order; resolve every unresolved match through the foam engine.
    for round_payload in bracket["rounds"]:
        round_number = int(round_payload["round_number"])
        for match in round_payload["matches"]:
            match_id = str(match["match_id"])
            if match_id in results:
                continue  # already resolved (a prior call, or a persisted bye)
            if match["auto_advance_club_id"]:
                winner = str(match["auto_advance_club_id"])
                save_cup_result(conn, cup_id, round_number, match_id, winner)
                results[match_id] = winner
                continue
            club_a_id = _cup_resolve_side(match["side_a"], results)
            club_b_id = _cup_resolve_side(match["side_b"], results)
            if club_a_id is None or club_b_id is None:
                continue
            scheduled = ScheduledMatch(
                match_id=f"{season_id}_{match_id}_{club_a_id}_vs_{club_b_id}",
                season_id=season_id,
                week=90 + round_number,
                home_club_id=club_a_id,
                away_club_id=club_b_id,
            )
            record, _ = simulate_match(
                scheduled=scheduled,
                home_club=clubs[club_a_id],
                away_club=clubs[club_b_id],
                home_roster=rosters[club_a_id],
                away_roster=rosters[club_b_id],
                root_seed=derive_seed(
                    root_seed, "v27_cup_round", season_id, match_id
                ),
                config_version="phase1.v1",
                difficulty="pro",
                meta_patch=None,
                ruleset_selection="official_foam",
            )
            winner_id, _tiebreak = _pick_cup_winner(record, rosters)
            save_cup_result(conn, cup_id, round_number, match_id, winner_id)
            results[match_id] = winner_id
            bracket_rows.append({
                "round": _round_label(round_number, total_rounds),
                "home_club_id": club_a_id,
                "away_club_id": club_b_id,
                "winner_club_id": winner_id,
                "home_club_name": clubs[club_a_id].name,
                "away_club_name": clubs[club_b_id].name,
            })

    champion_club_id = results[final_match_id]
    champion_club_name = clubs[champion_club_id].name
    champion_seat = division_map.get(champion_club_id)
    champion_tier = champion_seat.tier if champion_seat else 3
    purse_k = int(DEFAULT_EVENTS.cup_purse_champion_k.get(champion_tier, 60))

    # Build the full bracket-row list (played matches only — byes carry no row).
    # Re-derive rows from the resolved results so the recorded bracket reflects
    # the actual simmed matchups (home/away = side_a/side_b resolution order).
    resolved_rows: list[EventBracketRow] = []
    giant_killings = []
    for round_payload in bracket["rounds"]:
        round_number = int(round_payload["round_number"])
        for match in round_payload["matches"]:
            if match["auto_advance_club_id"]:
                continue
            match_id = str(match["match_id"])
            winner = results.get(match_id)
            if winner is None:
                continue
            home_id = _cup_resolve_side(match["side_a"], results)
            away_id = _cup_resolve_side(match["side_b"], results)
            if home_id is None or away_id is None:
                continue
            resolved_rows.append(EventBracketRow(
                round=_round_label(round_number, total_rounds),
                home_club_id=home_id,
                away_club_id=away_id,
                winner_club_id=winner,
                home_club_name=clubs[home_id].name,
                away_club_name=clubs[away_id].name,
            ))
            loser = home_id if winner == away_id else away_id
            w_seat = division_map.get(winner)
            l_seat = division_map.get(loser)
            if w_seat and l_seat and w_seat.tier > l_seat.tier:
                giant_killings.append({
                    "winner": winner, "loser": loser,
                    "winner_name": clubs[winner].name, "loser_name": clubs[loser].name,
                    "winner_tier": w_seat.tier, "loser_tier": l_seat.tier,
                    "round": _round_label(round_number, total_rounds),
                })

    # Award the trophy (idempotent at the persistence layer via INSERT OR REPLACE,
    # but the resolved guard above prevents re-entry).
    save_club_trophy(conn, champion_club_id, "cup", season_id)

    # Purse: credit the USER treasury only if the user won (fans/purse are a
    # user-program feature; AI treasuries are abstracted). Idempotent.
    purse_receipt = None
    if champion_club_id == player_club_id:
        purse_receipt = apply_event_purse(
            conn, _DOMESTIC_CUP_EVENT_KEY, purse_k, season_id
        )

    # Fans: grant the user club fans_cup only if the user won (guarded per-event).
    if champion_club_id == player_club_id and pyramid_world_active(conn):
        if get_state(conn, _FANS_GUARD) != season_id:
            from . import fan_ledger
            from .config import DEFAULT_FANS
            from .fan_economy import club_fans_for_event

            grant = club_fans_for_event("cup", DEFAULT_FANS)
            if grant > 0:
                fan_ledger.add_fans(
                    conn, player_club_id, grant, season_id, "cup",
                    f"+{grant} for winning the Domestic Cup",
                )
            set_state(conn, _FANS_GUARD, season_id)

    # Record the event in v27_events_json (idempotent — record_event replaces
    # any existing row for this event_key this season).
    result = EventResult(
        event_key=_DOMESTIC_CUP_EVENT_KEY,
        event_name=_DOMESTIC_CUP_NAME,
        season_id=season_id,
        champion_club_id=champion_club_id,
        champion_club_name=champion_club_name,
        ruleset="official_foam",
        purse_k=purse_k if champion_club_id == player_club_id else 0,
        bracket=tuple(resolved_rows),
    )
    record_event(conn, season_id, result)

    # News: the champion headline + a giant-killing line when one occurred.
    headlines = []
    headlines.append({
        "headline_id": f"event_{_DOMESTIC_CUP_EVENT_KEY}_{season_id}",
        "category": "event_news",
        "headline_text": f"{champion_club_name} win the {_DOMESTIC_CUP_NAME}!",
        "entity_ids": [champion_club_id],
    })
    for kill in giant_killings:
        headlines.append({
            "headline_id": f"event_{_DOMESTIC_CUP_EVENT_KEY}_giant_{season_id}_{kill['winner']}",
            "category": "event_news",
            "headline_text": (
                f"Giant-killing! {kill['winner_name']} (D{kill['winner_tier']}) "
                f"upset {kill['loser_name']} (D{kill['loser_tier']}) in the "
                f"{_DOMESTIC_CUP_NAME} {kill['round']}."
            ),
            "entity_ids": [kill["winner"], kill["loser"]],
        })
    save_news_headlines(conn, season_id, 0, headlines)

    # Mark resolved (the idempotent guard — re-calls short-circuit above).
    set_state(conn, guard, season_id)
    conn.commit()

    from dataclasses import asdict
    return {
        "event_key": _DOMESTIC_CUP_EVENT_KEY,
        "event_name": _DOMESTIC_CUP_NAME,
        "season_id": season_id,
        "champion_club_id": champion_club_id,
        "champion_club_name": champion_club_name,
        "ruleset": "official_foam",
        "purse_k": purse_k if champion_club_id == player_club_id else 0,
        "bracket": [asdict(r) for r in resolved_rows],
    }


__all__ = [
    "ensure_domestic_cup",
    "resolve_domestic_cup",
    "detect_giant_killings",
    "run_foam_knockout",
]


# ---------------------------------------------------------------------------
# Shared foam knockout runner (MSI / Founders' Exhibition)
# ---------------------------------------------------------------------------


def _foam_resolve_side(side, results: dict) -> str | None:
    """Resolve one side of a pure ``CupEntrant`` bracket match to a club id."""
    if side is None:
        return None
    if side.club_id:
        return str(side.club_id)
    if side.source_match_id:
        return results.get(str(side.source_match_id))
    return None


def _round_slug(label: str) -> str:
    return label.lower().replace(" ", "_")


def _foam_knockout_match_id(
    *, event_key: str, season_id: str, label: str, slot: int,
    home_id: str, away_id: str,
) -> str:
    """A foam knockout match-id that ENCODES THE ROUND LABEL so
    ``run_autonomous_match``'s clock resolution picks the right clock (the
    trap — ``final`` -> 40 min, ``semifinal`` -> 30 min, else 24 min)."""
    slug = _round_slug(label)
    return f"{event_key}_{season_id}_{slug}_m{slot}_{home_id}_vs_{away_id}"


def run_foam_knockout(
    conn: sqlite3.Connection,
    season_id: str,
    event_key: str,
    event_name: str,
    invitees: List[str],
    root_seed: int,
    seed_namespace: str,
    meta: dict | None = None,
):
    """Auto-sim a single-elimination FOAM knockout to one champion through the
    real foam engine (``simulate_match`` + ``official_foam``), resolving the
    pure ``generate_cup_bracket`` structure IN MEMORY (no ``cup_brackets`` row
    — MSI / Founders' are not the Domestic Cup). Mirrors the cup resolver's
    foam path: match-ids encode the round label (the clock trap), draws are
    impossible (survivor count -> overall skill -> seeded alphabetical
    tiebreak via ``_pick_cup_winner``).

    Returns an :class:`EventResult` (champion + bracket rows, ``purse_k=0``
    — the caller awards any purse), or ``None`` when fewer than 2 invitees
    cannot form a bracket. Pure sim: no match_records persisted (the event is
    not a league fixture); only the caller records the returned result.

    Deterministic per ``(root_seed, season_id, invitees, seed_namespace)``.
    Foam-only (``official_foam``); ``meta_patch=None`` (MetaPatch is retired).
    """
    from .cup import generate_cup_bracket
    from .event_calendar import EventBracketRow, EventResult
    from .franchise import simulate_match
    from .persistence import load_club_roster, load_clubs
    from .scheduler import ScheduledMatch

    if len(invitees) < 2:
        return None

    bracket = generate_cup_bracket(
        sorted(str(cid) for cid in invitees),
        DeterministicRNG(derive_seed(root_seed, seed_namespace, season_id)),
    )
    clubs = load_clubs(conn)
    rosters = {cid: load_club_roster(conn, cid) for cid in clubs}
    total_rounds = bracket.total_rounds
    results: dict[str, str] = {}
    bracket_rows: list[EventBracketRow] = []

    for round_ in bracket.rounds:
        round_number = round_.round_number
        label = _round_label(round_number, total_rounds)
        for slot_index, match in enumerate(round_.matches, start=1):
            match_id = match.match_id
            if match.is_bye:
                results[match_id] = str(match.auto_advance_club_id)
                continue
            home_id = _foam_resolve_side(match.side_a, results)
            away_id = _foam_resolve_side(match.side_b, results)
            if home_id is None or away_id is None:
                continue
            scheduled = ScheduledMatch(
                match_id=_foam_knockout_match_id(
                    event_key=event_key, season_id=season_id, label=label,
                    slot=slot_index, home_id=home_id, away_id=away_id,
                ),
                season_id=season_id,
                week=110 + round_number,
                home_club_id=home_id,
                away_club_id=away_id,
            )
            record, _ = simulate_match(
                scheduled=scheduled,
                home_club=clubs[home_id],
                away_club=clubs[away_id],
                home_roster=rosters[home_id],
                away_roster=rosters[away_id],
                root_seed=derive_seed(
                    root_seed, f"{seed_namespace}_match", season_id,
                    scheduled.match_id,
                ),
                config_version="phase1.v1",
                difficulty="pro",
                meta_patch=None,
                ruleset_selection="official_foam",
            )
            winner_id, _tiebreak = _pick_cup_winner(record, rosters)
            results[match_id] = winner_id
            bracket_rows.append(EventBracketRow(
                round=label,
                home_club_id=home_id,
                away_club_id=away_id,
                winner_club_id=winner_id,
                home_club_name=clubs[home_id].name,
                away_club_name=clubs[away_id].name,
            ))

    champion_club_id = results[bracket.final_match_id]
    return EventResult(
        event_key=event_key,
        event_name=event_name,
        season_id=season_id,
        champion_club_id=champion_club_id,
        champion_club_name=clubs[champion_club_id].name,
        ruleset="official_foam",
        purse_k=0,
        bracket=tuple(bracket_rows),
        meta=dict(meta) if meta else {},
    )
