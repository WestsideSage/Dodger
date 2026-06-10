"""V19 ceiling-scarcity gates (owner philosophy, 2026-06-10).

"OVR should be a reward and monument to the effort it took to build the
roster": most prospects are honest Low/Mid-ceiling projects, Elite (90+)
effective ceilings are very rare but findable through scouting (the STAR
trajectory IS the find), and Generational prospects (96+, a guaranteed
future Hall-of-Famer arc) appear roughly once every few classes. Before
this tune, every scouted prospect carried a NORMAL-trajectory floor of 72,
signings were floored at potential 70, and ceilings rolled uniform 55-96 —
the V18 sweeps measured signings averaging ~85-87 effective potential and
the whole league converging to high-80s OVR once development delivered.

These pins are distributional (deterministic seeds, exact counts) — the
same role as WT-7 frozen baselines: a silent revert to ceiling abundance
fails here.
"""
from __future__ import annotations

from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.development import _TRAJECTORY_POTENTIAL_FLOOR
from dodgeball_sim.recruitment import generate_prospect_pool
from dodgeball_sim.rng import DeterministicRNG, derive_seed

N_CLASSES = 12
ROOT_SEED = 20260610


def _effective_potentials() -> list[tuple[float, str]]:
    """(effective potential, trajectory) for every prospect across classes.

    Mirrors the shipping signing path: stored potential = best hidden rating
    + 8 (recruitment.sign_prospect_to_club), raised by the trajectory floor
    development actually applies.
    """
    rows: list[tuple[float, str]] = []
    for class_year in range(1, N_CLASSES + 1):
        rng = DeterministicRNG(derive_seed(ROOT_SEED, "scarcity_probe", str(class_year)))
        pool = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
        for prospect in pool:
            stored = min(100.0, max(prospect.hidden_ratings.values()) + 8.0)
            floor = _TRAJECTORY_POTENTIAL_FLOOR.get(prospect.hidden_trajectory)
            effective = max(stored, floor) if floor is not None else stored
            rows.append((effective, prospect.hidden_trajectory))
    return rows


class TestCeilingScarcity:
    def test_most_prospects_are_low_or_mid_ceiling(self):
        rows = _effective_potentials()
        below_80 = sum(1 for eff, _ in rows if eff < 80.0)
        assert below_80 / len(rows) >= 0.60, (
            f"only {below_80}/{len(rows)} prospects below an 80 ceiling — "
            "the league will converge elite again"
        )
        mean_eff = sum(eff for eff, _ in rows) / len(rows)
        assert mean_eff <= 78.0, f"mean effective ceiling {mean_eff:.1f} — too generous"

    def test_elite_ceilings_are_rare_but_findable(self):
        rows = _effective_potentials()
        elite_per_class = sum(1 for eff, _ in rows if eff >= 90.0) / N_CLASSES
        assert 0.25 <= elite_per_class <= 1.8, (
            f"Elite+ (90+) ceilings average {elite_per_class:.2f}/class — "
            "must be very rare but still findable"
        )

    def test_generational_prospects_are_once_every_few_years(self):
        rows = _effective_potentials()
        generational = sum(1 for eff, _ in rows if eff >= 96.0)
        # ~1 per 4 classes at the 0.01 share; allow 0.5-3 per 12 classes
        # before the pin trips (deterministic seeds — exact, not flaky).
        assert 1 <= generational <= 4, (
            f"{generational} Generational (96+) ceilings across {N_CLASSES} "
            "classes — target is roughly one every few years"
        )

    def test_generational_trajectory_is_the_guarantee(self):
        # The GENERATIONAL label must mean what it says: a 96+ effective
        # ceiling (the future-HoF promise), regardless of the natural roll.
        rows = _effective_potentials()
        gen_rows = [eff for eff, traj in rows if traj == "GENERATIONAL"]
        assert gen_rows, "12 seeded classes produced zero GENERATIONAL draws"
        assert all(eff >= 96.0 for eff in gen_rows)

    def test_normal_trajectory_promises_nothing(self):
        assert _TRAJECTORY_POTENTIAL_FLOOR["NORMAL"] is None, (
            "the NORMAL floor is the everyone-gets-Mid+ inflation leak"
        )

    def test_every_class_still_has_something_worth_scouting(self):
        # Scarcity must not mean emptiness: across the sweep, High-tier (82+)
        # effective ceilings keep appearing (IMPACT share + natural rolls).
        rows = _effective_potentials()
        high_total = sum(1 for eff, _ in rows if eff >= 82.0)
        assert high_total >= N_CLASSES, (
            f"only {high_total} High-tier (82+) ceilings across {N_CLASSES} "
            "classes — scouting has nothing to find"
        )
