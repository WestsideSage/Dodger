from __future__ import annotations

from .command_center import DEFAULT_DEPARTMENT_ORDERS


def get_ai_department_orders(archetype: str, intent: str) -> dict[str, str]:
    orders = dict(DEFAULT_DEPARTMENT_ORDERS)

    if archetype == "Development Factory":
        orders["dev_focus"] = "YOUTH"
        orders["training"] = "fundamentals"
        orders["scouting"] = "prospect scouting"
        if intent == "Preserve Health":
            orders["conditioning"] = "active recovery"
            orders["medical"] = "treatment"

    elif archetype == "Contender":
        orders["dev_focus"] = "VETERAN"
        orders["tactics"] = "film study"
        orders["conditioning"] = "peak performance"
        if intent == "Develop Youth":
            orders["dev_focus"] = "BALANCED"

    elif archetype == "Defensive Specialist":
        orders["tactics"] = "film study"
        orders["conditioning"] = "active recovery"
        orders["culture"] = "pressure management"
        if intent == "Develop Youth":
            orders["dev_focus"] = "YOUTH"

    elif archetype == "Power Throwers":
        orders["training"] = "physicality"
        orders["conditioning"] = "peak performance"
        if intent == "Preserve Health":
            orders["conditioning"] = "active recovery"

    elif archetype == "Aging Veterans":
        orders["dev_focus"] = "VETERAN"
        orders["conditioning"] = "active recovery"
        orders["medical"] = "treatment"
        if intent == "Develop Youth":
            orders["dev_focus"] = "BALANCED"

    elif archetype == "Balanced Rebuild":
        if intent in ("Develop Youth", "Balanced"):
            orders["dev_focus"] = "YOUTH"
        else:
            orders["dev_focus"] = "BALANCED"
        orders["scouting"] = "prospect scouting"

    return orders
