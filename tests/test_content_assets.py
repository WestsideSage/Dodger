from __future__ import annotations

import json
from pathlib import Path


def test_club_lore_asset_contains_eight_canonical_clubs():
    path = Path("src/dodgeball_sim/content/club_lore.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload) == 8
    assert {row["club_id"] for row in payload} == {
        "aurora_jets",
        "lunar_pilots",
        "nebula_sentinels",
        "vanguard_storm",
        "echo_orbit",
        "blaze_flux",
        "atlas_surge",
        "circuit_hawks",
    }
    assert all(row["lore"] and row["tagline"] for row in payload)
