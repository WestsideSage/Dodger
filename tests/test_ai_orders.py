from __future__ import annotations

from dodgeball_sim.ai_orders import get_ai_department_orders


def test_contender_orders():
    orders = get_ai_department_orders("Contender", "Balanced")
    assert orders["dev_focus"] == "VETERAN"
    assert orders["tactics"] == "film study"
    assert orders["conditioning"] == "peak performance"


def test_development_factory_orders():
    orders = get_ai_department_orders("Development Factory", "Balanced")
    assert orders["dev_focus"] == "YOUTH"
    assert orders["training"] == "fundamentals"
    assert orders["scouting"] == "prospect scouting"


def test_defensive_specialist_orders():
    orders = get_ai_department_orders("Defensive Specialist", "Balanced")
    assert orders["tactics"] == "film study"
    assert orders["conditioning"] == "active recovery"
    assert orders["culture"] == "pressure management"


def test_aging_veterans_orders():
    orders = get_ai_department_orders("Aging Veterans", "Preserve Health")
    assert orders["dev_focus"] == "VETERAN"
    assert orders["conditioning"] == "active recovery"
    assert orders["medical"] == "treatment"
