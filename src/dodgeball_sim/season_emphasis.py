"""V28 The Weather — Phase 3: officiating points of emphasis.

A seasonal League Bulletin shifts catch / block call tendencies within the
rulebook's discretion space. The shift is carried by :class:`SeasonEmphasis` (a
frozen dataclass threaded as a SEPARATE argument into the match runner — NOT a
field on the frozen ``RulesetProfile``: ruleset = sourced USAD fidelity;
emphasis = sim-design weather, cleanly separated). The deltas adjust the
EXISTING catch / block sigmoid bias BEFORE the existing roll (NO new RNG draw),
so ``SeasonEmphasis()`` (all deltas 0.0) is byte-identical to pre-V28. The shift
is applied symmetrically (every throw shares the same shaded bias) and, when it
flips a call, logged as a ``RuleDiscretionEvent(selection_basis='emphasis_<season>')``.

Phase 3.3 adds the selection / persistence / journalism layer:
``select_season_emphasis`` picks a bounded emphasis deterministically (the
``v28_season_emphasis`` seed stream), ``generate_officiating_bulletin`` persists
``v28_season_emphasis_json`` + writes a ``league_bulletin`` news headline, and
``load_season_emphasis`` resolves the active emphasis for the match runner.
Pyramid-gated; legacy single-league saves stay byte-identical. ``meta.py`` /
MetaPatch stays retired — the emphasis is sourced within the discretion space and
logged, never an injected stat-dial.

Spec: docs/specs/2026-06-17-v28-the-weather-spec.md (Phase 3).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .config import DEFAULT_WEATHER, WeatherConfig
from .rng import DeterministicRNG, derive_seed

# The per-season emphasis store: ``{season_id: {catch_delta, block_delta,
# announcement, selection_basis}}`` in ``dynasty_state``. Presence of a season's
# key is the idempotency guard (a season is selected exactly once).
_EMPHASIS_STATE_KEY = "v28_season_emphasis_json"

# The bulletin menu: (dimension, sign, announcement). ``sign`` * the bound gives
# the bounded delta. A positive catch sign rewards catches (more lenient); a
# negative sign gives throwers room (tighter catches). ``none`` leaves both
# deltas 0.0 (a "called straight" season — byte-identical to pre-V28). Every
# entry carries an announcement so the preseason bulletin is always informative.
_EMPHASIS_MENU = (
    ("catch", +1, "Points of emphasis: officials will reward clean catches this "
     "season — a caught ball flips possession, so go up and take it."),
    ("catch", -1, "Points of emphasis: officials are giving throwers room this "
     "season — borderline catches are judged tighter."),
    ("block", +1, "Points of emphasis: a held ball earns the benefit of the doubt "
     "on blocks this season — walling up is rewarded."),
    ("block", -1, "Points of emphasis: officials are discouraging walling up this "
     "season — blocks are judged tighter."),
    ("none", 0, "Points of emphasis: none this season — officials will call it "
     "straight."),
)


@dataclass(frozen=True)
class SeasonEmphasis:
    """A season's officiating points of emphasis (sim-design weather).

    ``catch_delta`` / ``block_delta`` shift the EXISTING catch / block sigmoid
    bias before the existing roll (bounded by ``WeatherConfig.emphasis_*_delta_max``):
    a positive ``catch_delta`` makes catches more lenient (higher catch rate), a
    positive ``block_delta`` makes held-ball blocks more lenient. All deltas 0.0
    (the default) is a true no-op ⇒ byte-identical to pre-V28. ``announcement`` is
    the human-facing bulletin text; ``selection_basis`` tags the logged
    ``RuleDiscretionEvent`` (``'emphasis_<season>'``).
    """

    catch_delta: float = 0.0
    block_delta: float = 0.0
    announcement: str = ""
    selection_basis: str = "emphasis"


def _load_store(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    from .persistence import get_state

    raw = get_state(conn, _EMPHASIS_STATE_KEY)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_store(conn: sqlite3.Connection, store: Dict[str, Any]) -> None:
    from .persistence import set_state

    set_state(conn, _EMPHASIS_STATE_KEY, json.dumps(store))


def _from_record(rec: Dict[str, Any]) -> SeasonEmphasis:
    return SeasonEmphasis(
        catch_delta=float(rec.get("catch_delta", 0.0)),
        block_delta=float(rec.get("block_delta", 0.0)),
        announcement=rec.get("announcement", ""),
        selection_basis=rec.get("selection_basis", "emphasis"),
    )


def select_season_emphasis(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    *,
    config: WeatherConfig = DEFAULT_WEATHER,
) -> SeasonEmphasis:
    """Deterministically select (and persist) a season's bounded emphasis.

    Idempotent per season — the store's per-season key is the guard, so a second
    call returns the stored emphasis unchanged. Pyramid-gated; legacy single-league
    saves get ``SeasonEmphasis()`` (byte-identical). The deltas are bounded by
    ``WeatherConfig.emphasis_*_delta_max``; the ``v28_season_emphasis`` seed stream
    is new, so it never perturbs ``v28_meta_drift`` determinism.
    """
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return SeasonEmphasis()

    store = _load_store(conn)
    if season_id in store:
        return _from_record(store[season_id])

    rng = DeterministicRNG(derive_seed(root_seed, "v28_season_emphasis", season_id))
    dimension, sign, announcement = rng.choice(list(_EMPHASIS_MENU))
    catch_delta = sign * config.emphasis_catch_delta_max if dimension == "catch" else 0.0
    block_delta = sign * config.emphasis_block_delta_max if dimension == "block" else 0.0
    emphasis = SeasonEmphasis(
        catch_delta=catch_delta,
        block_delta=block_delta,
        announcement=announcement,
        selection_basis=f"emphasis_{season_id}",
    )
    store[season_id] = {
        "catch_delta": catch_delta,
        "block_delta": block_delta,
        "announcement": announcement,
        "selection_basis": emphasis.selection_basis,
    }
    _save_store(conn, store)
    conn.commit()
    return emphasis


def generate_officiating_bulletin(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    *,
    config: WeatherConfig = DEFAULT_WEATHER,
) -> None:
    """Select the season's emphasis and write its preseason ``league_bulletin``
    headline (week 0). Idempotent via the stable ``headline_id`` + the selection
    guard. Pyramid-gated; a no-op on legacy single-league saves.
    """
    from .persistence import save_news_headlines
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return

    emphasis = select_season_emphasis(conn, season_id, root_seed, config=config)
    if not emphasis.announcement:
        return
    save_news_headlines(conn, season_id, 0, [{
        "headline_id": f"emphasis_{season_id}",
        "category": "league_bulletin",
        "headline_text": emphasis.announcement,
        "entity_ids": [],
    }])
    conn.commit()


def load_season_emphasis(
    conn: sqlite3.Connection, season_id: Optional[str] = None
) -> SeasonEmphasis:
    """Resolve the active (or given) season's emphasis for the match runner.

    Read-only and defensive: returns ``SeasonEmphasis()`` (byte-identical) for the
    user-world default, an unselected season, or any read error — so the hot match
    path can never raise or shift a legacy save.
    """
    try:
        from .persistence import get_state

        if season_id is None:
            season_id = get_state(conn, "active_season_id")
        if not season_id:
            return SeasonEmphasis()
        rec = _load_store(conn).get(season_id)
        return _from_record(rec) if rec else SeasonEmphasis()
    except Exception:
        return SeasonEmphasis()


__all__ = [
    "SeasonEmphasis",
    "select_season_emphasis",
    "generate_officiating_bulletin",
    "load_season_emphasis",
]
