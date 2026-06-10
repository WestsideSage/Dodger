"""Conformance ledger (WT-19): every V11 must-have / partial-core section maps
to a NAMED, behaviour-asserting test plus an honest enforcement *state*.

This replaces the old existence-only check. The old test only proved a
section's test *file* existed and contained the substring ``"def test_"``,
which stayed green even when behaviour drifted and -- worse -- could not tell a
rule the live engine genuinely resolves apart from one that merely has a
passing module-level unit test (e.g. No Blocking, which is activated/announced
but never resolved by the autonomous loop).

The three-state honesty ledger lives in
:mod:`dodgeball_sim.official_conformance_ledger` (the single source the WT-18
copy and the CONTEXT official-mode taxonomy read from). Here we assert the
contract that keeps it honest:

* every V11 matrix section is recorded in the ledger (no silent drop / addition);
* every ``ENFORCED`` section names real test functions that actually exist in
  their home files (file exists AND defines that ``def test_...``);
* ``ANNOUNCED_ONLY`` / ``ABSENT`` sections are recorded with their state and a
  note, and are NOT asserted as enforced -- "complete conformance" is claimable
  only for the enforced set;
* no section is simultaneously claimed ``ENFORCED`` and lacking a named
  behavioural test (the integrity invariant).

Per Phase 5 this test does NOT wire any engine enforcement; announced-only /
absent rows are surfaced honestly and belong to the deferred WT-20 milestone.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

import pytest

from dodgeball_sim.official_conformance_ledger import (
    LEDGER,
    EnforcementState,
    ledger_by_section,
)


REPO_TESTS = Path(__file__).parent


# The authoritative V11 conformance-matrix section list, from
# docs/archive/specs/v11/2026-05-20-v11-official-usad-rules/implementation-plan.md
# (the "Conformance Matrix" table). The ledger must cover exactly these rows.
V11_MATRIX_SECTIONS = frozenset(
    {
        "1",
        "4",
        "6",
        "9",
        "11",
        "13",
        "14",
        "16",
        "17",
        "18",
        "20",
        "21",
        "22",
        "23",
        "24-core",
        "25",
        "27",
    }
)


@lru_cache(maxsize=None)
def _defined_test_functions(home: str) -> frozenset[str]:
    """Return the set of ``def test_...`` names defined in a tests/ file.

    Parsed with :mod:`ast` so we match real function *definitions*, not the
    substring ``"def test_"`` appearing in a string/comment somewhere.
    """

    path = REPO_TESTS / home
    if not path.exists():
        return frozenset()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            names.add(node.name)
    return frozenset(names)


def test_ledger_covers_exactly_the_v11_matrix_sections():
    """The ledger and the V11 matrix must agree on the section set."""

    ledger_sections = frozenset(ledger_by_section())
    missing = V11_MATRIX_SECTIONS - ledger_sections
    extra = ledger_sections - V11_MATRIX_SECTIONS
    assert not missing, f"V11 matrix sections absent from the ledger: {sorted(missing)}"
    assert not extra, f"Ledger has sections not in the V11 matrix: {sorted(extra)}"


def test_every_section_has_a_recognised_enforcement_state():
    for entry in LEDGER:
        assert isinstance(entry.state, EnforcementState), entry.section


@pytest.mark.parametrize("entry", LEDGER, ids=lambda e: e.section)
def test_enforced_sections_map_to_real_named_behavioural_tests(entry):
    """Each ENFORCED section must name >=1 test that actually exists.

    Announced-only / absent sections are intentionally NOT asserted as
    enforced; this is the honest surfacing of WT-20 scope, not a gap to fill
    with engine wiring in Phase 5.
    """

    if entry.state is not EnforcementState.ENFORCED:
        # Surfaced, not hidden: an announced-only / absent row must still carry
        # a candid note so the state is explained rather than buried.
        assert entry.note.strip(), (
            f"Section {entry.section} is {entry.state.value} but has no explanatory note"
        )
        return

    assert entry.named_tests, (
        f"Section {entry.section} is claimed ENFORCED but names no test"
    )
    for nt in entry.named_tests:
        defined = _defined_test_functions(nt.home)
        assert defined, f"Section {entry.section}: missing/empty test home {nt.home}"
        assert nt.function in defined, (
            f"Section {entry.section}: {nt.home} does not define {nt.function}() "
            f"(named-test drift). Defined tests: {sorted(defined)}"
        )


def test_no_section_is_enforced_without_a_named_behavioural_test():
    """Integrity invariant: enforced + un-tested may never coexist."""

    offenders = [
        entry.section
        for entry in LEDGER
        if entry.state is EnforcementState.ENFORCED and not entry.named_tests
    ]
    assert not offenders, (
        "Sections claimed ENFORCED with no named behavioural test: " f"{offenders}"
    )


def test_complete_conformance_is_claimable_only_for_enforced_sections():
    """The honesty contract: announced-only / absent rows exist and are labelled.

    This guards against a future edit that quietly relabels a not-yet-wired
    section as enforced. When a section genuinely flips it must come with the
    engine wiring AND its own behavioural test -- which makes this
    assertion's expectation update a deliberate, reviewed act.
    """

    states = {entry.section: entry.state for entry in LEDGER}
    # WT-20 (2026-06-10, owner-greenlit) wired the No Blocking resolution into
    # run_autonomous_game with behavioural gates (test_wt20_live_rules.py:
    # block branch disabled while active, balls-do-not-reset, match-end
    # source) — section 27 is now ENFORCED. This flip is the deliberate,
    # reviewed act the previous revision of this test demanded.
    assert states["27"] is EnforcementState.ENFORCED
    # 24-core stays announced-only as a row: the held-ball forfeiture half IS
    # live (see the SPLIT note + test_wt20_live_rules.py), but the
    # entering-player micro-fouls are still module-level only.
    assert states["24-core"] is EnforcementState.ANNOUNCED_ONLY

    enforced = {s for s, st in states.items() if st is EnforcementState.ENFORCED}
    not_enforced = {s for s, st in states.items() if st is not EnforcementState.ENFORCED}
    assert enforced.isdisjoint(not_enforced)
    # There is genuine enforced coverage (the ledger is not vacuously honest).
    assert enforced, "No section is enforced -- the ledger would be vacuous"
