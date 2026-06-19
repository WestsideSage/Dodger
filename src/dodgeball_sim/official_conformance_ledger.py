"""Three-state honesty ledger for V11 official-rules conformance (WT-19).

This module is the *single honest source* for which USA Dodgeball 2026.1 rule
sections the official engine actually enforces, versus only announces, versus
does not implement at all. The WT-18 player-facing ruleset copy and the
CONTEXT official-mode taxonomy are intended to read their enforcement claims
from here so the copy and the conformance ledger never disagree.

Why this exists
---------------
``tests/test_official_conformance_matrix.py`` historically only proved that a
section's test *file* existed and contained the substring ``"def test_"``. That
stays green even when behaviour silently drifts, and -- worse -- it cannot tell
the difference between a rule the *live autonomous engine* genuinely resolves
and a rule that has a passing **module-level** unit test but is never invoked by
:func:`dodgeball_sim.official_engine.run_autonomous_game`. No Blocking is the
canonical trap: ``tests/test_official_no_blocking.py`` is green and section 27
maps to it, yet the live loop only *activates/announces* No Blocking and never
calls :func:`dodgeball_sim.no_blocking.resolve_contact_with_held_ball`.

The three states (see the WT-18/WT-19/WT-20 governing notes)
------------------------------------------------------------
``ENFORCED``
    Genuinely outcome-affecting in the live official engine / official
    resolution. A real, named, behaviour-asserting test exists.
``ANNOUNCED_ONLY``
    Surfaced or activated (an event is emitted, a flag is set, config is
    threaded into the replay payload) but the resolution does **not** change
    what it does. The module-level helper may exist and be unit-tested in
    isolation; the live autonomous loop does not consult it.
``ABSENT``
    Not present in the official engine at all.

"Complete conformance" is claimable **only** for ``ENFORCED`` sections. The
``ANNOUNCED_ONLY`` and ``ABSENT`` rows are recorded with their state and a
candid note -- surfaced, not hidden -- and belong to the deferred **WT-20
"Official Live Rules"** milestone. Recording a section as announced-only or
absent here is *not* a licence to wire new engine enforcement (that is WT-20);
it is the honest alternative to over-claiming.

Source of truth for the section list: the V11 conformance matrix in
``docs/archive/specs/v11/2026-05-20-v11-official-usad-rules/implementation-plan.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Tuple


class EnforcementState(str, Enum):
    """How real a rule section's behaviour is in the *live* official engine."""

    #: Outcome-affecting in the live engine / official resolution.
    ENFORCED = "enforced"
    #: Surfaced/activated but not outcome-affecting (resolution ignores it).
    ANNOUNCED_ONLY = "announced-only"
    #: Not implemented in the official engine at all.
    ABSENT = "absent"


@dataclass(frozen=True)
class NamedTest:
    """A specific, named, behaviour-asserting test that backs a section.

    ``home`` is the test filename under ``tests/`` and ``function`` is the
    exact ``def test_...`` name expected to live in that file. The ledger test
    asserts both that the file exists and that it defines this function, so a
    rename or deletion fails loudly instead of drifting silently.
    """

    home: str
    function: str


@dataclass(frozen=True)
class SectionLedgerEntry:
    """One V11 rule section's honest conformance record."""

    section: str
    title: str
    scope: str  # "must-have" or "partial-core", mirroring the V11 matrix.
    state: EnforcementState
    named_tests: Tuple[NamedTest, ...]
    note: str = ""

    @property
    def is_enforced(self) -> bool:
        return self.state is EnforcementState.ENFORCED


# Convenience aliases so the table below stays readable.
_ENFORCED = EnforcementState.ENFORCED
_ANNOUNCED = EnforcementState.ANNOUNCED_ONLY
_ABSENT = EnforcementState.ABSENT


def _t(home: str, function: str) -> NamedTest:
    return NamedTest(home=home, function=function)


# ---------------------------------------------------------------------------
# The ledger.
#
# Classifications reflect the shared enforcement truth and were verified against
# the live autonomous engine (``official_engine.run_autonomous_game``) and the
# official resolution path, not merely against the existence of a unit test:
#
#   * ENFORCED rows are rules the live loop actually calls -- ruleset profiles &
#     ball counts (``initial_balls``), ball activation (``activate_ball``),
#     burden *establishment* (``establish_burden``/``burden_event``), the
#     sequence finality + catch-outs-thrower-and-resurrects rule
#     (``resolve_throw`` -> ``SequenceLedger`` -> ``return_player_on_catch``),
#     the catch queue core return, and the elimination -> winner sequence.
#
#   * ANNOUNCED_ONLY rows are activated/surfaced but never consulted by
#     resolution. After WT-20 (2026-06-10) the remaining announced-only
#     surface is: the throw-clock *penalty path* (``foam_failure_forfeit`` /
#     ``cloth_play_n_failure`` exist + are unit-tested, but the autonomous
#     loop throws every <=6s tick whenever a side controls a ball, so the
#     10s/5s failure windows are unreachable by construction — there is
#     nothing for the live loop to enforce) and the 24-core entering-player
#     micro-fouls other than the held-ball forfeiture (which WT-20 wired).
#
#   * WT-20 (2026-06-10, owner-greenlit) wired: No Blocking resolution (the
#     held-ball block branch in official_resolution is disabled while
#     active; balls do not reset; match-end source), Section 24-core
#     held-ball forfeiture on outs + loose-ball retrieval, and opening-rush
#     initiative/holder ordering (disclosed sim-design — opening rush is NOT
#     a sourced USAD rule).
# ---------------------------------------------------------------------------
LEDGER: Tuple[SectionLedgerEntry, ...] = (
    SectionLedgerEntry(
        section="1",
        title="Ruleset profiles, materials, and ball counts",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t("test_official_rulesets.py", "test_foam_profile"),
            _t("test_official_rulesets.py", "test_cloth_profile"),
        ),
        note="Live engine builds the court via initial_balls(profile, ...).",
    ),
    SectionLedgerEntry(
        section="4",
        title="Roster rule / mixed-division gender balance",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_rulesets.py",
                "test_mixed_starters_reject_four_of_one_gender",
            ),
        ),
        note="validate_starters genuinely rejects an illegal starting six.",
    ),
    SectionLedgerEntry(
        section="6",
        title="Game lifecycle: clock, no-blocking trigger, cloth game decision",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_match_lifecycle.py",
                "test_cloth_game_clock_decision_by_active_count",
            ),
            _t(
                "test_official_match_lifecycle.py",
                "test_game_clock_remaining_and_expired",
            ),
        ),
        note=(
            "Engine advances the game clock and resolves the cloth clock-expiry "
            "decision (decide_cloth_game_by_active_count). The foam/no-sting "
            "no-blocking trigger fires here and its resolution is ENFORCED as of "
            "WT-20 (see section 27)."
        ),
    ),
    SectionLedgerEntry(
        section="9",
        title="Match clock durations by round type",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_match_lifecycle.py",
                "test_bracket_match_clock_durations",
            ),
        ),
        note="Bracket/round-robin clock durations drive the match clock the engine ticks.",
    ),
    SectionLedgerEntry(
        section="11",
        title="Ball activation / becoming live",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_ball_state.py",
                "test_activate_ball_marks_held_and_emits_rule_11_event",
            ),
        ),
        note="Engine activates each opening ball via activate_ball before play.",
    ),
    SectionLedgerEntry(
        section="13",
        title="Burden establishment (ball-majority / player-majority / inversion)",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t("test_official_burden.py", "test_foam_burden_by_ball_majority"),
            _t("test_official_burden.py", "test_burden_event_emits_rule_13"),
        ),
        note=(
            "Engine calls establish_burden + burden_event every tick to pick the "
            "offense. SPLIT: burden *establishment* is enforced; the throw-clock "
            "*penalty* path (section 14 below) is announced-only."
        ),
    ),
    SectionLedgerEntry(
        section="14",
        title="Burden reset on valid throw; catch after clock-expiry still outs thrower",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t("test_official_burden.py", "test_valid_throw_resets_burden"),
            _t(
                "test_official_sequence.py",
                "test_catch_after_clock_expiry_still_eliminates_thrower",
            ),
        ),
        note=(
            "The burden RESET-on-valid-throw and the clock-expiry catch ruling are "
            "enforced via sequence finality. The throw-clock FAILURE penalty "
            "(foam_failure_forfeit / cloth_play_n_failure) is module-level only and "
            "is NOT invoked by the live loop -- that penalty path is announced-only "
            "and belongs to WT-20."
        ),
    ),
    SectionLedgerEntry(
        section="16",
        title="Throwing an inactive ball outs the thrower",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_ball_state.py",
                "test_throw_inactive_ball_outs_thrower_and_keeps_ball_inactive",
            ),
        ),
        note="Ball-state guard: only live balls produce valid throws in the engine.",
    ),
    SectionLedgerEntry(
        section="17",
        title="Live-ball throw / invalid release outs thrower",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_ball_state.py",
                "test_throw_inactive_ball_outs_thrower_and_keeps_ball_inactive",
            ),
            _t(
                "test_official_sequence.py",
                "test_invalid_release_outs_thrower_section_25",
            ),
        ),
        note="Engine resolves throws from live balls through the sequence resolver.",
    ),
    SectionLedgerEntry(
        section="18",
        title="A hit is not final until the sequence resolves",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t("test_official_sequence.py", "test_hit_not_final_until_resolution"),
        ),
        note="Engine closes every sequence through SequenceLedger before applying outs.",
    ),
    SectionLedgerEntry(
        section="20",
        title="Sequence finality across balls (second-ball out cannot be un-done)",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_sequence.py",
                "test_second_ball_out_cannot_be_saved_later",
            ),
        ),
        note="Cross-sequence finality is enforced by the SequenceLedger the engine uses.",
    ),
    SectionLedgerEntry(
        section="21",
        title="Block / ricochet (foam saves hit player, cloth does not)",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_sequence.py",
                "test_foam_ricochet_catch_saves_hit_player",
            ),
            _t(
                "test_official_sequence.py",
                "test_cloth_ricochet_catch_does_not_save_hit_player",
            ),
        ),
        note="Ricochet-save material rules are resolved inside sequence finality.",
    ),
    SectionLedgerEntry(
        section="22",
        title="Catch outs the thrower and resurrects a teammate",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_sequence.py",
                "test_foam_ricochet_catch_saves_hit_player",
            ),
            _t(
                "test_official_catch_queue.py",
                "test_catch_returns_first_eligible_queued_player",
            ),
        ),
        note=(
            "Keystone rule. Engine: a catch outs the thrower (sequence) and calls "
            "return_player_on_catch to resurrect the first eligible queued teammate."
        ),
    ),
    SectionLedgerEntry(
        section="23",
        title="Catch queue: re-entry order and starter eligibility",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_catch_queue.py",
                "test_nonstarters_cannot_enter_from_catches",
            ),
            _t(
                "test_official_catch_queue.py",
                "test_catch_returns_first_eligible_queued_player",
            ),
        ),
        note="Engine enqueues outs and returns players through CatchQueueState.",
    ),
    SectionLedgerEntry(
        section="24-core",
        title="Entering-player / held-ball-in-queue micro-fouls",
        scope="partial-core",
        state=_ANNOUNCED,
        named_tests=(
            _t(
                "test_official_ball_state.py",
                "test_queued_player_holding_ball_forfeits_to_opponent",
            ),
            _t(
                "test_official_catch_queue.py",
                "test_out_of_order_entry_sends_player_to_back",
            ),
        ),
        note=(
            "SPLIT (WT-20, 2026-06-10). The held-ball-in-queue forfeiture IS now "
            "live: run_autonomous_game invokes queue_player_holds_ball_forfeit for "
            "every ball an out player still controls, and a loose-ball retrieval "
            "pass re-enters forfeited/free balls each tick "
            "(test_wt20_live_rules.py::test_out_players_forfeit_held_balls_and_loose_balls_reenter). "
            "Still announced-only: entering-player illegal contact before live "
            "(entering_player_touches_ball_before_live), out-of-order entry "
            "(out_of_order_entry), and the 5s entering window (tick_entering) -- "
            "module-level helpers with passing unit tests the live loop never "
            "invokes."
        ),
    ),
    SectionLedgerEntry(
        section="25",
        title="Invalid release (ball never live) outs the thrower only",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_sequence.py",
                "test_invalid_release_outs_thrower_section_25",
            ),
        ),
        note="Invalid-release finality is resolved inside the sequence the engine closes.",
    ),
    SectionLedgerEntry(
        section="27",
        title="No Blocking (held ball becomes a body extension)",
        scope="must-have",
        state=_ENFORCED,
        named_tests=(
            _t(
                "test_official_no_blocking.py",
                "test_no_blocking_activation_logs_section_27_and_source",
            ),
            _t(
                "test_wt20_live_rules.py",
                "test_no_blocking_disables_the_block_branch",
            ),
            _t(
                "test_wt20_live_rules.py",
                "test_no_blocking_activation_says_balls_do_not_reset",
            ),
            _t(
                "test_wt20_live_rules.py",
                "test_match_clock_expiry_activates_match_end_no_blocking",
            ),
        ),
        note=(
            "ENFORCED (WT-20, 2026-06-10, owner-greenlit). Regulation play models "
            "held-ball blocking (official_resolution: a ball-holding catch-decliner "
            "blocks at p~0.74 even-ratings); while No Blocking is active the block "
            "branch is DISABLED, so the held ball genuinely stops protecting. "
            "Activation now carries the SOURCED 'balls do not reset' (the old "
            "three_per_side contradicted the primary source) and the SOURCED "
            "match-end source (match clock expiry -> the current game becomes a "
            "match-end No Blocking game and plays on). HONESTY NOTE: the trigger, "
            "terminal game, and no-reset are primary-source confirmed; what reduced "
            "blocking changes in *resolution* is NOT specified by the source — the "
            "shipped 'remove block protection, change nothing else' resolution is "
            "disclosed sim-design measured in the V17 retro, not a USAD fidelity "
            "claim (Workflow-0 keystone row)."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Rules that are part of the official lineage's player-facing claim surface but
# are NOT V11 must-have sections, recorded so the WT-18 copy can speak to them
# honestly. These are deliberately NOT in LEDGER (they are not V11 conformance
# rows) but are surfaced here as the honest "announced/absent" companion list.
# ---------------------------------------------------------------------------
NON_SECTION_ENFORCEMENT_NOTES: Tuple[Tuple[str, EnforcementState, str], ...] = (
    (
        "throw-clock penalties",
        _ANNOUNCED,
        "The penalty paths (foam_failure_forfeit / cloth_play_n_failure) remain "
        "module-level, and deliberately so: the autonomous loop throws every "
        "<=6s tick whenever a side controls a ball, so the sourced 10s/5s "
        "failure windows are unreachable by construction — the clock is "
        "satisfied structurally, and wiring a penalty that can never fire would "
        "be enforcement theater. Re-examine if the loop ever gains a stalling "
        "action. (WT-20 disposition, 2026-06-10; see section 14 for the "
        "burden-side detail.)",
    ),
    (
        "opening-rush activation",
        _ENFORCED,
        "ENFORCED as DISCLOSED SIM-DESIGN (WT-20, 2026-06-10) — opening rush is "
        "NOT a sourced USAD rule, and the player-facing copy must not present "
        "it as official-rules fidelity. rush_target orders which players "
        "secure the designated balls; rush_commit shades the opening-exchange "
        "catch economy both ways (harder-to-catch rushed throws vs weaker "
        "rushed catch readiness). First offense is a seeded coin flip. "
        "test_wt20_live_rules.py::test_rush_knobs_change_official_outcomes_same_seed.",
    ),
    (
        "officiating points of emphasis",
        _ENFORCED,
        "ENFORCED as DISCLOSED SIM-DESIGN (V28 The Weather) — a seasonal "
        "catch/block leniency shift (SeasonEmphasis) within the rulebook's "
        "discretion space, NOT a sourced USAD rule; the player-facing bulletin "
        "must present it as a point of emphasis, never official-rules fidelity. "
        "It shades the EXISTING catch/block sigmoid bias before the EXISTING roll "
        "with no new RNG draw, applied SYMMETRICALLY to both sides (every throw "
        "shares the same shaded bias), and every call the bounded delta flips is "
        "logged as a DISCRETION event (selection_basis='emphasis_<season>'). The "
        "default SeasonEmphasis() (deltas 0.0) is byte-identical to a no-bulletin "
        "season. test_v28_emphasis.py::TestEmphasisLogging::"
        "test_flips_emit_emphasis_discretion_events.",
    ),
)


def ledger_by_section() -> Mapping[str, SectionLedgerEntry]:
    """Return the ledger keyed by section id."""

    return {entry.section: entry for entry in LEDGER}


def enforced_sections() -> Tuple[str, ...]:
    """Sections for which 'complete conformance' may honestly be claimed."""

    return tuple(e.section for e in LEDGER if e.is_enforced)


def announced_or_absent_sections() -> Tuple[str, ...]:
    """Sections surfaced (not hidden) as not-yet-enforced -- WT-20 milestone scope."""

    return tuple(e.section for e in LEDGER if not e.is_enforced)
