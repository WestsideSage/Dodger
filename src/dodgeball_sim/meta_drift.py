"""V28 The Weather — Phase 2: emergent meta (ecosystem tactic drift).

AI programs drift toward the prior season's winning ``CoachPolicy`` dimensions
(computed from real match data via ``winning_tactics``), with a deterministic
contrarian fraction that drifts AWAY (the anti-solvedness mechanism — no
permanent solve). The overlay is a per-club cumulative bias stored in
``v28_tactic_drift_json`` (a single ``dynasty_state`` key mapping club_id →
{dimension → {value → score}}). ``tactic_drift_for`` resolves the overlay to
the drifted target values, consumed by ``ai_tactics.get_ai_tactics`` as a
learned bias after the intent override (precedence: archetype base → intent
override → drift bias).

``meta.py``/MetaPatch stays retired — the drift is computed from data, never an
injected dial. New seed namespace ``v28_meta_drift`` only. Pyramid-gated;
legacy single-league saves stay byte-identical. The user club is never drifted.
The drift only changes AI ``CoachPolicy`` (a real policy the engine already
consumes — no special math), so determinism is preserved.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, Optional

from .config import DEFAULT_WEATHER, WeatherConfig
from .rng import DeterministicRNG, derive_seed

_DRIFT_STATE_KEY = "v28_tactic_drift_json"

# CoachPolicy dimensions tracked for drift (same as meta_journalism).
_POLICY_DIMENSIONS = (
    "approach",
    "target_focus",
    "catch_posture",
    "rush_commit",
    "rush_target",
)

# The threshold a dimension's top-value score must exceed for the drift to
# "take hold" and override the base policy. With drift_rate=0.15, it takes
# ~4 offseasons of consistent winning to cross 0.5 — tactics drift but don't
# snap in one offseason.
_DRIFT_THRESHOLD = 0.5


def _is_playoff(match_id: str, season_id: str) -> bool:
    return match_id.startswith(f"{season_id}_p_")


def winning_tactics(
    conn: sqlite3.Connection, season_id: str
) -> Dict[str, str]:
    """Return, per CoachPolicy dimension, which value won most official matches.

    Reads ``team_policies`` from ``official_score_json`` and compares each
    club's policy to ``winner_club_id``. Playoff match-ids are excluded.
    Returns ``{}`` when there are no division memberships (legacy saves) or no
    official matches.
    """
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return {}

    rows = conn.execute(
        """
        SELECT match_id, official_score_json, winner_club_id
        FROM match_records
        WHERE season_id = ? AND official_score_json IS NOT NULL
        """,
        (season_id,),
    ).fetchall()

    # dimension → value → win count
    win_counts: Dict[str, Dict[str, int]] = {d: {} for d in _POLICY_DIMENSIONS}

    for r in rows:
        if _is_playoff(r["match_id"], season_id):
            continue
        try:
            score = json.loads(r["official_score_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        policies = score.get("team_policies") or {}
        winner = r["winner_club_id"]
        if not winner:
            continue
        winner_policy = policies.get(winner)
        if not isinstance(winner_policy, dict):
            continue
        for dim in _POLICY_DIMENSIONS:
            val = winner_policy.get(dim)
            if val is None:
                continue
            win_counts[dim][val] = win_counts[dim].get(val, 0) + 1

    result: Dict[str, str] = {}
    for dim, counts in win_counts.items():
        if counts:
            result[dim] = max(counts, key=counts.get)
    return result


def _load_drift_store(conn: sqlite3.Connection) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load the full drift store: club_id → {dimension → {value → score}}."""
    from .persistence import get_state

    raw = get_state(conn, _DRIFT_STATE_KEY)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_drift_store(conn: sqlite3.Connection, store: Dict[str, Any]) -> None:
    from .persistence import set_state

    set_state(conn, _DRIFT_STATE_KEY, json.dumps(store))


def _all_ai_clubs(conn: sqlite3.Connection, user_club_id: Optional[str]) -> list[str]:
    """All club ids except the user club."""
    from .persistence import load_clubs

    return [cid for cid in load_clubs(conn) if cid != user_club_id]


def apply_meta_drift(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    *,
    config: WeatherConfig = DEFAULT_WEATHER,
) -> None:
    """Nudge each AI club's tactic-drift overlay toward the season's winners.

    A deterministic contrarian fraction (on the ``v28_meta_drift`` stream) drifts
    AWAY from the winners instead. Idempotent per season — a season is only
    applied once (guarded by ``v28_drift_applied_for`` state). The user club is
    never drifted. Pyramid-gated; legacy saves are a no-op.
    """
    from .persistence import get_state, set_state
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return

    # Idempotency guard: only apply once per season.
    applied_key = "v28_drift_applied_for"
    applied_for = get_state(conn, applied_key) or ""
    if applied_for == season_id:
        return

    winners = winning_tactics(conn, season_id)
    if not winners:
        # No official matches to learn from — still mark as applied so we don't
        # re-check every time.
        set_state(conn, applied_key, season_id)
        conn.commit()
        return

    user_club_id = get_state(conn, "player_club_id")
    ai_clubs = _all_ai_clubs(conn, user_club_id)
    if not ai_clubs:
        set_state(conn, applied_key, season_id)
        conn.commit()
        return

    store = _load_drift_store(conn)

    # Compute full win counts per dimension so contrarians can push a real
    # alternative (the runner-up) UP, not just the winner DOWN.
    dim_counts: Dict[str, Dict[str, int]] = {d: {} for d in _POLICY_DIMENSIONS}
    rows = conn.execute(
        """
        SELECT match_id, official_score_json, winner_club_id
        FROM match_records
        WHERE season_id = ? AND official_score_json IS NOT NULL
        """,
        (season_id,),
    ).fetchall()
    for r in rows:
        if _is_playoff(r["match_id"], season_id):
            continue
        try:
            score = json.loads(r["official_score_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        policies = score.get("team_policies") or {}
        winner = r["winner_club_id"]
        if not winner:
            continue
        winner_policy = policies.get(winner)
        if not isinstance(winner_policy, dict):
            continue
        for dim in _POLICY_DIMENSIONS:
            val = winner_policy.get(dim)
            if val is not None:
                dim_counts[dim][val] = dim_counts[dim].get(val, 0) + 1

    # Per dimension: the winning value and a runner-up (the second-most-won
    # value, or a deterministic fallback from the enum if only one value won).
    from .models import (
        Approach,
        CatchPosture,
        OpeningRushCommit,
        OpeningRushTarget,
        TargetFocus,
    )

    _DIM_ENUMS = {
        "approach": [e.value for e in Approach],
        "target_focus": [e.value for e in TargetFocus],
        "catch_posture": [e.value for e in CatchPosture],
        "rush_commit": [e.value for e in OpeningRushCommit],
        "rush_target": [e.value for e in OpeningRushTarget],
    }

    def _runner_up(dim: str, winner: str) -> str:
        counts = dim_counts.get(dim, {})
        sorted_vals = sorted(counts, key=counts.get, reverse=True)
        for v in sorted_vals:
            if v != winner:
                return v
        # No runner-up in the data — pick the first enum value that isn't the winner.
        for v in _DIM_ENUMS.get(dim, []):
            if v != winner:
                return v
        return winner

    # Deterministic contrarian selection on the v28_meta_drift stream.
    contrarian_seed = derive_seed(root_seed, "v28_meta_drift", season_id)
    rng = DeterministicRNG(contrarian_seed)
    num_contrarians = int(len(ai_clubs) * config.contrarian_fraction)
    # Shuffle the club list deterministically, pick the first N as contrarians.
    shuffled = rng.shuffle(list(ai_clubs))
    contrarians = set(shuffled[:num_contrarians])

    for club_id in ai_clubs:
        club_store = store.setdefault(club_id, {})
        is_contrarian = club_id in contrarians
        for dim in _POLICY_DIMENSIONS:
            winning_val = winners.get(dim)
            if winning_val is None:
                continue
            dim_store = club_store.setdefault(dim, {})
            if is_contrarian:
                # Contrarian: push a real alternative (the runner-up) UP so the
                # contrarian generation produces a visible alternative tactic,
                # not just a suppressed winner.
                runner = _runner_up(dim, winning_val)
                dim_store[runner] = dim_store.get(runner, 0.0) + config.drift_rate
            else:
                # Conformist: push the winning value UP (drift TOWARD).
                dim_store[winning_val] = dim_store.get(winning_val, 0.0) + config.drift_rate

    _save_drift_store(conn, store)
    set_state(conn, applied_key, season_id)
    conn.commit()


def tactic_drift_for(conn: sqlite3.Connection, club_id: str) -> Dict[str, str]:
    """Resolve the drift overlay for a club to drifted target values.

    Returns ``{dimension: value}`` for dimensions where the top-value score
    exceeds ``_DRIFT_THRESHOLD``. Returns ``{}`` for the user club or when no
    drift has taken hold. This is the overlay read consumed by
    ``ai_tactics.get_ai_tactics``.
    """
    store = _load_drift_store(conn)
    club_store = store.get(club_id)
    if not club_store:
        return {}
    result: Dict[str, str] = {}
    for dim, dim_store in club_store.items():
        if not dim_store:
            continue
        top_val = max(dim_store, key=dim_store.get)
        top_score = dim_store[top_val]
        if top_score >= _DRIFT_THRESHOLD:
            result[dim] = top_val
    return result


__all__ = [
    "winning_tactics",
    "apply_meta_drift",
    "tactic_drift_for",
]
