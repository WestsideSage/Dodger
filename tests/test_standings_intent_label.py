"""Bug #7: the standings "Plan" column must label a club's program intent with
the same vocabulary the command center uses to SET it.

A player who picks the command-center tile labeled "Aggressive" stores intent
"Win Now"; the standings previously surfaced the raw "Win Now", so one decision
read as two different words across screens (an ADR-0002 faithfulness break).
`_intent_display_label` translates the stored intent to the command-center
display label, with verbatim passthrough for unmapped intents (mirroring the
frontend's `intentLabels.get(x) ?? x` fallback).
"""

from dodgeball_sim.command_center import INTENTS
from dodgeball_sim.web_status_service import _intent_display_label


def test_player_facing_intents_use_command_center_labels():
    # These four are the player-selectable tiles in PreSimDashboard `approaches`.
    assert _intent_display_label("Win Now") == "Aggressive"
    assert _intent_display_label("Prepare For Playoffs") == "Control"
    assert _intent_display_label("Preserve Health") == "Defensive"
    assert _intent_display_label("Balanced") == "Balanced"


def test_ai_only_and_unknown_intents_pass_through_verbatim():
    # "Develop Youth" is an AI-only intent with no command-center tile; the
    # command center itself falls back to the raw string, so standings must too
    # (inventing a label here would make the two surfaces disagree).
    assert _intent_display_label("Develop Youth") == "Develop Youth"
    # Any future / unrecognized intent is surfaced unchanged rather than blanked.
    assert _intent_display_label("Some Future Intent") == "Some Future Intent"


def test_every_canonical_intent_yields_a_nonblank_label():
    # Drift guard: every intent the engine can actually store must map to a
    # non-empty display string (never a blank "Plan" badge in standings).
    for intent in INTENTS:
        label = _intent_display_label(intent)
        assert isinstance(label, str) and label.strip(), intent
