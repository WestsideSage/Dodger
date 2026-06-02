"""Unit tests for the Manager-Lesson vs improvement-panel dedup.

On an inconclusive loss the aftermath payload can carry BOTH a Manager Lesson
and the post-loss improvement panel. They can name the SAME lever twice:

* lesson ``weakest_role_group`` vs panel ``position_group`` (both derive from
  ``next_best_improvement.weakest_position_group`` over the same roster);
* lesson ``fatigue`` vs panel ``condition`` (both derive from
  ``next_best_improvement.lowest_condition_starter`` over the same lineup).

``use_cases._dedup_lesson_panel`` is the pure presentation step that resolves
this: keep the loss-specific Manager Lesson, drop only the panel item that
names the SAME lever, keep every non-duplicate item, and omit the panel key
entirely if it becomes empty. Levers with no panel counterpart
(``roster_edge`` / ``ignored_recommendation`` / ``no_lever``) leave the panel
untouched.

These exercise the ``_build_aftermath`` assembly logic directly (the dedup is
factored out of that function), with hand-built payload dicts shaped exactly as
``ManagerLesson.as_dict`` and ``build_improvement_panel`` produce them -- no
career DB or resolved match required.
"""

from dodgeball_sim.manager_lesson import (
    FATIGUE,
    IGNORED_RECOMMENDATION,
    NO_LEVER,
    ROSTER_EDGE,
    WEAKEST_ROLE_GROUP,
)
from dodgeball_sim.use_cases import _dedup_lesson_panel


# ---------------------------------------------------------------------------
# Panel-item / lesson factories (shapes mirror the real producers exactly).
# ---------------------------------------------------------------------------


def _position_group_item() -> dict[str, str]:
    return {
        "category": "position_group",
        "title": "Shore up your Wall depth",
        "detail": "Lowest group average at 48 OVR across 3. Target it in recruiting or development.",
    }


def _condition_item() -> dict[str, str]:
    return {
        "category": "condition",
        "title": "Rest Jordan",
        "detail": "Most-depleted starter at 18 stamina. Rotate or rest before fatigue costs you a result.",
    }


def _recruit_item() -> dict[str, str]:
    return {
        "category": "recruit",
        "title": "Warm up Alex",
        "detail": "High fit (78) but only 30% interest. Contact or visit to close the gap.",
    }


def _lesson(code: str) -> dict[str, object]:
    # Minimal but realistically shaped lesson dict (matches ManagerLesson.as_dict).
    return {
        "code": code,
        "title": "Lesson title",
        "sentence": "Lesson sentence.",
        "controllable": code != NO_LEVER,
        "evidence_chips": [],
    }


# ---------------------------------------------------------------------------
# weakest_role_group lesson -> drop the position_group panel item
# ---------------------------------------------------------------------------


def test_weakest_role_group_lesson_drops_position_group_item_keeps_others():
    aftermath = {
        "manager_lesson": _lesson(WEAKEST_ROLE_GROUP),
        "improvement_panel": [_position_group_item(), _condition_item(), _recruit_item()],
    }

    _dedup_lesson_panel(aftermath)

    # Lesson is the loss-specific surface and is always kept.
    assert aftermath["manager_lesson"]["code"] == WEAKEST_ROLE_GROUP
    categories = [item["category"] for item in aftermath["improvement_panel"]]
    # The duplicated position_group item is gone; the OTHER lever (condition)
    # and the recruit item are both kept.
    assert "position_group" not in categories
    assert categories == ["condition", "recruit"]


def test_weakest_role_group_lesson_does_not_touch_condition_or_recruit():
    # When the panel has NO position_group item, weakest_role_group leaves it
    # untouched (nothing to dedup -- it never over-suppresses the other lever).
    aftermath = {
        "manager_lesson": _lesson(WEAKEST_ROLE_GROUP),
        "improvement_panel": [_condition_item(), _recruit_item()],
    }

    _dedup_lesson_panel(aftermath)

    assert aftermath["improvement_panel"] == [_condition_item(), _recruit_item()]


# ---------------------------------------------------------------------------
# fatigue lesson -> drop the condition panel item
# ---------------------------------------------------------------------------


def test_fatigue_lesson_drops_condition_item_keeps_others():
    aftermath = {
        "manager_lesson": _lesson(FATIGUE),
        "improvement_panel": [_position_group_item(), _condition_item(), _recruit_item()],
    }

    _dedup_lesson_panel(aftermath)

    assert aftermath["manager_lesson"]["code"] == FATIGUE
    categories = [item["category"] for item in aftermath["improvement_panel"]]
    # Only the condition duplicate is dropped; position_group + recruit stay.
    assert "condition" not in categories
    assert categories == ["position_group", "recruit"]


# ---------------------------------------------------------------------------
# Levers with no panel counterpart -> panel unchanged
# ---------------------------------------------------------------------------


def test_roster_edge_lesson_leaves_panel_unchanged():
    panel = [_position_group_item(), _condition_item(), _recruit_item()]
    aftermath = {"manager_lesson": _lesson(ROSTER_EDGE), "improvement_panel": list(panel)}

    _dedup_lesson_panel(aftermath)

    assert aftermath["improvement_panel"] == panel


def test_ignored_recommendation_lesson_leaves_panel_unchanged():
    panel = [_position_group_item(), _condition_item(), _recruit_item()]
    aftermath = {
        "manager_lesson": _lesson(IGNORED_RECOMMENDATION),
        "improvement_panel": list(panel),
    }

    _dedup_lesson_panel(aftermath)

    assert aftermath["improvement_panel"] == panel


def test_no_lever_lesson_leaves_panel_unchanged():
    panel = [_position_group_item(), _condition_item(), _recruit_item()]
    aftermath = {"manager_lesson": _lesson(NO_LEVER), "improvement_panel": list(panel)}

    _dedup_lesson_panel(aftermath)

    assert aftermath["improvement_panel"] == panel


# ---------------------------------------------------------------------------
# Panel becomes empty after dedup -> omit the key entirely
# ---------------------------------------------------------------------------


def test_panel_with_only_duplicate_position_group_is_omitted():
    aftermath = {
        "manager_lesson": _lesson(WEAKEST_ROLE_GROUP),
        "improvement_panel": [_position_group_item()],
    }

    _dedup_lesson_panel(aftermath)

    # The whole key is dropped rather than surfacing an empty panel.
    assert "improvement_panel" not in aftermath
    # The lesson still stands.
    assert aftermath["manager_lesson"]["code"] == WEAKEST_ROLE_GROUP


def test_panel_with_only_duplicate_condition_is_omitted():
    aftermath = {
        "manager_lesson": _lesson(FATIGUE),
        "improvement_panel": [_condition_item()],
    }

    _dedup_lesson_panel(aftermath)

    assert "improvement_panel" not in aftermath


# ---------------------------------------------------------------------------
# No-op guards: missing keys, conclusive loss (no lesson), empty panel
# ---------------------------------------------------------------------------


def test_no_manager_lesson_leaves_panel_unchanged():
    # Conclusive loss: the Primary Factor answered it, so no Manager Lesson is
    # assembled. The panel must pass through untouched.
    panel = [_position_group_item(), _condition_item(), _recruit_item()]
    aftermath = {"improvement_panel": list(panel)}

    _dedup_lesson_panel(aftermath)

    assert aftermath["improvement_panel"] == panel


def test_no_panel_is_a_noop():
    # Lesson present but no panel (e.g. panel build failed/returned empty).
    aftermath = {"manager_lesson": _lesson(WEAKEST_ROLE_GROUP)}

    _dedup_lesson_panel(aftermath)  # must not raise

    assert "improvement_panel" not in aftermath
    assert aftermath["manager_lesson"]["code"] == WEAKEST_ROLE_GROUP


def test_empty_payload_is_a_noop():
    aftermath: dict[str, object] = {}

    _dedup_lesson_panel(aftermath)  # must not raise

    assert aftermath == {}
