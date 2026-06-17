"""V26 The Crowd — the web facilities office.

Facilities are PERMANENT user-owned buildings bought with treasury (the V24
Scouting-Network upgrade pattern), stored as a per-user-club list in
``dynasty_state``. The legacy per-season CLI ``club_facilities`` path is left
untouched. Stadium + Merch Center feed the fan economy (matchday + merch
income, Phase 4); Training Hall + the development labs feed development.
"""
from __future__ import annotations

import json
from typing import Any, List

from .config import DEFAULT_FACILITIES, FacilityConfig
from .facilities import FACILITY_DEFINITIONS, FacilityType

_OWNED_KEY = "v26_owned_facilities_json"


def owned_facilities(conn, config: FacilityConfig = DEFAULT_FACILITIES) -> List[str]:
    """The user club's permanently-built facilities (empty on legacy saves)."""
    from .persistence import get_state

    raw = get_state(conn, _OWNED_KEY)
    try:
        owned = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        owned = []
    return [f for f in owned if isinstance(f, str)]


def facility_catalog(conn, config: FacilityConfig = DEFAULT_FACILITIES) -> list[dict[str, Any]]:
    from .economy import treasury_k

    owned = set(owned_facilities(conn, config))
    treasury = treasury_k(conn)
    rows: list[dict[str, Any]] = []
    for key in config.web_catalog:
        defn = FACILITY_DEFINITIONS[FacilityType(key)]
        cost = int(config.treasury_cost_k[key])
        is_owned = key in owned
        rows.append({
            "facility_type": key,
            "display_name": defn.display_name,
            "category": defn.category,
            "treasury_cost_k": cost,
            "owned": is_owned,
            "can_afford": (not is_owned) and treasury >= cost,
        })
    return rows


def buy_facility(conn, facility_type: str, config: FacilityConfig = DEFAULT_FACILITIES) -> dict[str, Any]:
    """Spend treasury to build a facility permanently (refuses off-pyramid, when
    short, when already owned, or off-catalog)."""
    from .economy import set_treasury_k, treasury_k
    from .persistence import set_state
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        raise ValueError("Facilities are a pyramid-world feature.")
    if facility_type not in config.web_catalog:
        raise ValueError(f"{facility_type} is not available to build.")
    owned = owned_facilities(conn, config)
    if facility_type in owned:
        raise ValueError("You already own that facility.")
    cost = int(config.treasury_cost_k[facility_type])
    treasury = treasury_k(conn)
    if treasury < cost:
        name = FACILITY_DEFINITIONS[FacilityType(facility_type)].display_name
        raise ValueError(f"Building the {name} costs ${cost}k; your treasury holds ${treasury}k.")
    set_treasury_k(conn, treasury - cost)
    owned.append(facility_type)
    set_state(conn, _OWNED_KEY, json.dumps(owned))
    conn.commit()
    return {
        "owned": owned, "cost_k": cost,
        "treasury_k": treasury - cost, "facility_type": facility_type,
    }


def facilities_state(conn, config: FacilityConfig = DEFAULT_FACILITIES) -> dict[str, Any]:
    from .economy import treasury_k

    return {
        "catalog": facility_catalog(conn, config),
        "owned": owned_facilities(conn, config),
        "treasury_k": treasury_k(conn),
    }


__all__ = ["owned_facilities", "facility_catalog", "buy_facility", "facilities_state"]
