"""Pure helper for the post-loss "next best improvement" panel.

Task 11 (2026-05-28 playtest-fixes): after a loss the player was left
with no clear next step. The data to point them somewhere already
exists -- this module ranks it into at most three actionable nudges:
the weakest position group, the most-depleted starter, and the
highest-value recruit still cool on you.

Kept pure (dicts in, list out, no I/O) so the ranking can be pinned by
tests. It invents no new scoring -- callers pass in values the engine
already computes (OVR, stamina, recruit interest/fit).
"""

from __future__ import annotations

from typing import Any

from .models import archetype_display_name


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def weakest_position_group(roster: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Group roster by archetype, return the lowest average-OVR group.

    ``roster`` items: ``{"archetype": str, "overall": int}``. Groups with
    fewer than one member are ignored. Ties break on archetype name for
    determinism.
    """

    groups: dict[str, list[float]] = {}
    for player in roster:
        arch = str(player.get("archetype") or "").strip()
        if not arch:
            continue
        groups.setdefault(arch, []).append(float(player.get("overall", 0)))
    if not groups:
        return None
    arch, ovrs = min(groups.items(), key=lambda kv: (_mean(kv[1]), kv[0]))
    return {"archetype": arch, "avg_overall": round(_mean(ovrs), 1), "count": len(ovrs)}


def strongest_position_group(roster: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Group roster by archetype, return the highest average-OVR group.

    Mirror of :func:`weakest_position_group`; used by the season preview
    to name a roster strength. Ties break on archetype name.
    """

    groups: dict[str, list[float]] = {}
    for player in roster:
        arch = str(player.get("archetype") or "").strip()
        if not arch:
            continue
        groups.setdefault(arch, []).append(float(player.get("overall", 0)))
    if not groups:
        return None
    arch, ovrs = max(groups.items(), key=lambda kv: (_mean(kv[1]), kv[0]))
    return {"archetype": arch, "avg_overall": round(_mean(ovrs), 1), "count": len(ovrs)}


def lowest_condition_starter(starters: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the starter with the lowest stamina. Ties break on name."""

    rated = [s for s in starters if s.get("stamina") is not None]
    if not rated:
        return None
    low = min(rated, key=lambda s: (int(s["stamina"]), str(s.get("name", ""))))
    return {"name": str(low.get("name", "")), "stamina": int(low["stamina"])}


def coolest_critical_recruit(
    recruits: list[dict[str, Any]], *, fit_floor: int = 65
) -> dict[str, Any] | None:
    """Return the highest-fit recruit whose interest is lowest.

    "Critical" = fit at/above ``fit_floor``. Among those, the one with
    the least interest is where a contact/visit pays off most.
    """

    critical = [r for r in recruits if int(r.get("fit_score", 0)) >= fit_floor]
    if not critical:
        return None
    low = min(
        critical,
        key=lambda r: (int(r.get("interest", 0)), str(r.get("name", ""))),
    )
    return {
        "name": str(low.get("name", "")),
        "interest": int(low.get("interest", 0)),
        "fit_score": int(low.get("fit_score", 0)),
    }


def build_improvement_panel(
    *,
    roster: list[dict[str, Any]],
    starters: list[dict[str, Any]],
    recruits: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Assemble up to three suggestions, each ``{category, title, detail}``.

    Missing inputs simply drop that suggestion rather than fabricate one,
    so the panel degrades to fewer cards instead of inventing data.
    """

    out: list[dict[str, str]] = []

    group = weakest_position_group(roster)
    if group is not None:
        out.append(
            {
                "category": "position_group",
                "title": f"Shore up your {archetype_display_name(group['archetype'])} depth",
                "detail": (
                    f"Lowest group average at {group['avg_overall']} OVR "
                    f"across {group['count']}. Target it in recruiting or development."
                ),
            }
        )

    starter = lowest_condition_starter(starters)
    if starter is not None:
        out.append(
            {
                "category": "condition",
                "title": f"Rest {starter['name']}",
                "detail": (
                    f"Most-depleted starter at {starter['stamina']} stamina. "
                    "Rotate or rest before fatigue costs you a result."
                ),
            }
        )

    recruit = coolest_critical_recruit(recruits)
    if recruit is not None:
        out.append(
            {
                "category": "recruit",
                "title": f"Warm up {recruit['name']}",
                "detail": (
                    f"High fit ({recruit['fit_score']}) but only "
                    f"{recruit['interest']}% interest. Contact or visit to close the gap."
                ),
            }
        )

    return out[:3]


__all__ = [
    "build_improvement_panel",
    "weakest_position_group",
    "strongest_position_group",
    "lowest_condition_starter",
    "coolest_critical_recruit",
]
