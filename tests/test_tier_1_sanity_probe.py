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


def test_report_is_dataclass_with_expected_fields():
    report = run_sanity_probe(matches=5)
    assert isinstance(report, SanityProbeReport)
    assert hasattr(report, "matches_run")
    assert hasattr(report, "matches_resolved")
    assert hasattr(report, "total_moment_events")
    assert hasattr(report, "exceptions")
    assert hasattr(report, "winner_counts")
