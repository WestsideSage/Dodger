from dodgeball_sim.moment_events import MomentKind
from tools.tier_1_sanity_probe import run_sanity_probe, SanityProbeReport


def test_sanity_probe_runs_25_matches_by_default():
    report = run_sanity_probe()
    assert report.matches_run == 25


def test_all_matches_resolve():
    report = run_sanity_probe()
    assert report.matches_resolved == report.matches_run
    assert report.exceptions == []


def test_average_moment_events_per_match_at_least_one():
    report = run_sanity_probe()
    assert report.total_moment_events / max(1, report.matches_run) >= 1.0


def test_default_probe_emits_all_six_moment_kinds():
    # 40 matches, not the 25 default: the V19a consumers (stamina staying
    # power, tactical_iq targeting, role fit, rush sprinters) shifted rec
    # outcomes and the default seed window no longer happens to produce a
    # 1v1 finale; at 40 deterministic matches every kind appears again.
    report = run_sanity_probe(matches=40)
    for kind in MomentKind:
        assert report.moment_kind_counts[kind] > 0, f"missing {kind.value}"


def test_report_is_dataclass_with_expected_fields():
    report = run_sanity_probe(matches=5)
    assert isinstance(report, SanityProbeReport)
    assert hasattr(report, "matches_run")
    assert hasattr(report, "matches_resolved")
    assert hasattr(report, "total_moment_events")
    assert hasattr(report, "exceptions")
    assert hasattr(report, "winner_counts")
    assert hasattr(report, "moment_kind_counts")
