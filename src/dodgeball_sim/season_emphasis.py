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

from dataclasses import dataclass


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


__all__ = ["SeasonEmphasis"]
