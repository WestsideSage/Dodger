"""Tier 1 sanity probe — Plan A gate.

Runs N Tier 1 matches end-to-end and asserts that they all resolve,
emit at least one moment event on average, and produce all six moment
kinds at least once.

Plan D introduced `tools/probe_lib.py`; this probe now consumes
`make_match_input` from there. Output is unchanged.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Support both direct script execution and module invocation
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from dodgeball_sim.moment_events import MomentKind
from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import make_match_input


@dataclass
class SanityProbeReport:
    matches_run: int = 0
    matches_resolved: int = 0
    total_moment_events: int = 0
    exceptions: List[str] = field(default_factory=list)
    winner_counts: Counter = field(default_factory=Counter)
    moment_kind_counts: Counter = field(default_factory=Counter)


def run_sanity_probe(matches: int = 25, seed_start: int = 1) -> SanityProbeReport:
    report = SanityProbeReport()
    driver = RecTier1Driver()
    for i in range(matches):
        seed = seed_start + i
        report.matches_run += 1
        try:
            out = driver.run(make_match_input(seed, match_id_prefix="sanity"))
        except Exception as e:  # pragma: no cover - probe-level safety
            report.exceptions.append(f"seed={seed}: {type(e).__name__}: {e}")
            continue
        report.matches_resolved += 1
        report.total_moment_events += len(out.moment_events)
        winner = out.winner_team_id or "draw"
        report.winner_counts[winner] += 1
        report.moment_kind_counts.update(event.kind for event in out.moment_events)
    return report


def main() -> int:
    report = run_sanity_probe()
    print("=== Tier 1 Sanity Probe ===")
    print(f"Matches run:         {report.matches_run}")
    print(f"Matches resolved:    {report.matches_resolved}")
    print(f"Total moment events: {report.total_moment_events}")
    avg = report.total_moment_events / max(1, report.matches_run)
    print(f"Avg moments/match:   {avg:.2f}")
    print(f"Winner counts:       {dict(report.winner_counts)}")
    print(
        "Moment kinds:        "
        f"{ {kind.value: count for kind, count in sorted(report.moment_kind_counts.items(), key=lambda item: item[0].value)} }"
    )
    if report.exceptions:
        print("EXCEPTIONS:")
        for line in report.exceptions:
            print(f"  - {line}")
        return 1
    if avg < 1.0:
        print("FAIL: average moments per match below 1.0")
        return 2
    missing = [kind.value for kind in MomentKind if report.moment_kind_counts[kind] == 0]
    if missing:
        print(f"FAIL: missing moment kinds: {', '.join(missing)}")
        return 3
    print("OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
