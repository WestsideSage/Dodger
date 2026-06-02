"""Deterministic "Manager Lesson" for an inconclusive loss or draw (WT-32).

The Primary Factor (``match_explanation.py``) answers *what decided the match*
from event-derived evidence. When the match was genuinely close and no single
event-derived factor is supported, that contract honestly returns a soft
"no one thing to fix" inconclusive fallback. That answers the wrong question
for a new player who is really asking **"what could *I* have changed?"**.

This applies equally to an inconclusive **loss** and an inconclusive **draw**:
a draw at an even, close matchup is exactly the "what could I have changed to
edge it?" moment. A win is still out of scope (you got the result), and a
*conclusive* loss/draw is answered by the event-derived Primary Factor.

This module is the *adjacent* answer to that second question. Given the
already-resolved aftermath primitives — the player's ignored advisory
recommendation (if any), the roster strength edge, a fatigue/depleted-starter
signal, and the weakest role group — it returns either a single **controllable**
lesson or, when nothing the player controlled would have changed the result, an
**honest no-lever message**. It is surfaced ONLY when the Primary Factor is
inconclusive; it never folds into, reranks, or replaces the Primary Factor.

Hard faithfulness fences (mirrors WT-32 resolution + ADR 0002):

* **The Primary Factor stays strictly event-derived.** Nothing here touches it.
* **No fabrication.** Every lesson must trace to a real controllable the player
  actually had. When NO controllable signal applies, the lesson honestly says
  "nothing you controlled would have changed this" — it does not invent a lever.
* **Hybrid selection:** an ignored recommendation ALWAYS wins; otherwise the
  strongest controllable signal by a common severity score (fixed priority
  tie-break, mirroring ``match_explanation._CODE_PRIORITY``).
* Read-only over already-resolved primitives. No engine/scoring/golden-log
  change, no new dependency. Pure: primitives in, dataclass out, unit-testable.

The caller (``use_cases`` aftermath site) is responsible for deciding when each
signal *applies* (magnitude thresholds), because "applies" is a data judgement
about real roster numbers, not display copy. This module only ranks and narrates
the signals it is handed, so passing all-empty inputs deterministically yields
the honest no-lever message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .match_explanation import CONFIDENCE_LOW, UPSET_VARIANCE

# ---------------------------------------------------------------------------
# Lesson codes
# ---------------------------------------------------------------------------
IGNORED_RECOMMENDATION = "ignored_recommendation"
ROSTER_EDGE = "roster_edge"
FATIGUE = "fatigue"
WEAKEST_ROLE_GROUP = "weakest_role_group"
NO_LEVER = "no_lever"

# Fixed tie-break order when two controllable signals score the same severity
# (lower index wins). Roster edge leads because squad strength is the most
# directly actionable lever; fatigue (rotate/rest) next; weakest group last as
# the longest-horizon fix. The ignored recommendation is handled separately
# (it always wins) and is not in this list.
_CODE_PRIORITY = (
    ROSTER_EDGE,
    FATIGUE,
    WEAKEST_ROLE_GROUP,
)


@dataclass(frozen=True)
class ManagerLesson:
    """Adjacent aftermath surface — a controllable takeaway, or the honest
    no-lever message. ``controllable`` is ``True`` for a real lever the player
    held and ``False`` for the honest "nothing you controlled" message, so the
    frontend can style/label the two cases distinctly without re-deriving."""

    code: str
    title: str
    sentence: str
    controllable: bool
    evidence_chips: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "sentence": self.sentence,
            "controllable": self.controllable,
            "evidence_chips": list(self.evidence_chips),
        }


def is_inconclusive_factor(*, code: str, confidence: str) -> bool:
    """True only for the genuinely-inconclusive Primary Factor.

    ``_upset_variance_factor`` returns ``UPSET_VARIANCE`` in BOTH its branches:
    the *decisive* branch (a 0-4 set blowout — "the result wasn't close",
    ``medium`` confidence) and the *non-decisive* branch (a true coin-flip —
    "no one thing to fix", ``low`` confidence). Only the latter is inconclusive.
    A decisive blowout is a CONCLUSIVE result and must NOT get a Manager Lesson
    (the squad-strength takeaway already lives in the decisive factor copy)."""

    return code == UPSET_VARIANCE and confidence == CONFIDENCE_LOW


@dataclass(frozen=True)
class _Signal:
    code: str
    severity: float  # common scale across controllable levers; higher = stronger
    factor: ManagerLesson


def derive_manager_lesson(
    *,
    result: str,
    factor_is_inconclusive: bool,
    ignored_recommendation: Mapping[str, Any] | None = None,
    roster_edge: Mapping[str, Any] | None = None,
    fatigue: Mapping[str, Any] | None = None,
    weakest_role_group: Mapping[str, Any] | None = None,
) -> ManagerLesson | None:
    """Return the Manager Lesson for an inconclusive loss or draw, else ``None``.

    Returns ``None`` (no lesson at all) when the result is not an inconclusive
    loss/draw — i.e. the Primary Factor was conclusive, or the result was a win.
    The Manager Lesson answers "what could *I* have changed?", which makes sense
    on a loss OR a draw the engine could not pin on a single event-derived
    factor (a draw at an even matchup is exactly "what could I have changed to
    edge it?"). A win is out of scope: you already got the result.

    When it IS an inconclusive loss/draw, this ALWAYS returns a ``ManagerLesson``:
    a controllable lever when one applies, otherwise the honest no-lever
    message. It never returns ``None`` in that case, so the player always gets a
    truthful answer rather than silence.

    Inputs are already-resolved primitives the caller has decided *apply*:

    * ``ignored_recommendation``: ``{"advised_intent", "selected_intent",
      "reason"}`` — the pre-match advisory the player declined. ALWAYS wins.
    * ``roster_edge``: ``{"net_ovr"}`` — signed net starter OVR (player minus
      opponent). Only pass it when it was genuinely *against* the player.
    * ``fatigue``: ``{"name", "stamina"}`` — the most-depleted starter the
      player could have rested/rotated. Only pass it when genuinely low.
    * ``weakest_role_group``: ``{"archetype", "avg_overall", "count"}`` — the
      thinnest position group. Only pass it when notably below the rest.
    """

    # Gate: a lesson exists ONLY for an inconclusive loss or draw. A conclusive
    # result (decisive variance copy or a real event-derived factor) gets no
    # lesson — the Primary Factor already answered the question. A win is out of
    # scope: "what could I have changed?" is not a question you ask after a win.
    # A draw at an even matchup is explicitly in scope (owner-approved): it is
    # exactly the "what could I have changed to edge it?" moment.
    if result not in ("Loss", "Draw") or not factor_is_inconclusive:
        return None

    # 1) An ignored recommendation ALWAYS wins (resolution rule). It is the most
    #    faithful lever: the player was explicitly advised and chose otherwise.
    if ignored_recommendation:
        lesson = _ignored_recommendation_lesson(ignored_recommendation)
        if lesson is not None:
            return lesson

    # 2) Otherwise the strongest controllable signal by common severity, with a
    #    deterministic fixed-priority tie-break (mirrors match_explanation).
    signals: list[_Signal] = []
    _add_roster_edge(signals, roster_edge)
    _add_fatigue(signals, fatigue)
    _add_weakest_role_group(signals, weakest_role_group, result=result)

    if signals:
        signals.sort(
            key=lambda s: (
                -s.severity,
                _CODE_PRIORITY.index(s.code) if s.code in _CODE_PRIORITY else len(_CODE_PRIORITY),
            )
        )
        return signals[0].factor

    # 3) No controllable signal applied — say so honestly. NEVER fabricate.
    return _no_lever_lesson(result=result)


# ---------------------------------------------------------------------------
# Per-lever builders
# ---------------------------------------------------------------------------


def _ignored_recommendation_lesson(
    rec: Mapping[str, Any],
) -> ManagerLesson | None:
    advised = str(rec.get("advised_intent") or "").strip()
    if not advised:
        return None
    selected = str(rec.get("selected_intent") or "").strip()
    reason = str(rec.get("reason") or "").strip()
    chips = [f"Advised: {advised}"]
    if selected:
        chips.append(f"You ran: {selected}")
    detail = f" {reason}" if reason else ""
    sentence = (
        f"The staff advised switching to {advised} this week and you stuck with "
        f"{selected or 'your plan'}.{detail} It's advisory, not a guarantee — but in a "
        "match this close it's the lever you most clearly held."
        if selected
        else
        f"The staff advised a {advised} approach this week.{detail} It's advisory, "
        "not a guarantee — but in a match this close it's the lever you most clearly held."
    )
    return ManagerLesson(
        code=IGNORED_RECOMMENDATION,
        title="A recommendation you passed on",
        sentence=sentence,
        controllable=True,
        evidence_chips=tuple(chips),
    )


def _add_roster_edge(
    signals: list[_Signal],
    roster_edge: Mapping[str, Any] | None,
) -> None:
    if not roster_edge:
        return
    try:
        net = int(roster_edge.get("net_ovr", 0))
    except (TypeError, ValueError):
        return
    # The caller only passes this when it was against the player, but guard
    # anyway: a non-negative edge is not a controllable shortfall to teach from.
    if net >= 0:
        return
    deficit = -net
    # Severity scaled into the same band as the other levers (see _add_fatigue /
    # _add_weakest_role_group). Net OVR gaps run larger than stamina/group
    # numbers, so divide to keep the scale comparable.
    severity = deficit / 8.0
    chips = (f"Net starter OVR {net:+d}",)
    sentence = (
        f"Your fielded six were out-rated by {deficit} net OVR going in. The match was "
        "too close to pin on any one thing, but closing that gap — through recruiting or "
        "development — is the clearest lever you hold before the rematch."
    )
    signals.append(
        _Signal(
            code=ROSTER_EDGE,
            severity=severity,
            factor=ManagerLesson(
                code=ROSTER_EDGE,
                title="You fielded the lighter squad",
                sentence=sentence,
                controllable=True,
                evidence_chips=chips,
            ),
        )
    )


def _add_fatigue(
    signals: list[_Signal],
    fatigue: Mapping[str, Any] | None,
) -> None:
    if not fatigue:
        return
    name = str(fatigue.get("name") or "").strip()
    try:
        stamina = int(fatigue.get("stamina", 0))
    except (TypeError, ValueError):
        return
    if not name:
        return
    # Lower stamina = more severe. Map a 0..100 stamina onto a comparable band:
    # the closer to empty, the higher the severity.
    severity = (100 - stamina) / 20.0
    chips = (f"{name}: {stamina} stamina",)
    sentence = (
        f"{name} started this one on {stamina} stamina. The match was too close to pin on "
        "any one thing, but fresher legs are a lever you control — rest or rotate a depleted "
        "starter before you sim next time."
    )
    signals.append(
        _Signal(
            code=FATIGUE,
            severity=severity,
            factor=ManagerLesson(
                code=FATIGUE,
                title="You ran a tired starter",
                sentence=sentence,
                controllable=True,
                evidence_chips=chips,
            ),
        )
    )


def _add_weakest_role_group(
    signals: list[_Signal],
    group: Mapping[str, Any] | None,
    *,
    result: str = "Loss",
) -> None:
    if not group:
        return
    archetype = str(group.get("archetype") or "").strip()
    if not archetype:
        return
    try:
        avg_overall = int(group.get("avg_overall", 0))
        count = int(group.get("count", 0))
    except (TypeError, ValueError):
        return
    from .models import archetype_display_name

    display = archetype_display_name(archetype)
    # A thinner / weaker group is a longer-horizon fix, so it carries the lowest
    # base severity of the three levers; lower average OVR raises it modestly.
    severity = max(0.0, (60 - avg_overall) / 30.0)
    chips = (f"{display}: {avg_overall} avg OVR", f"x{count}")
    # Faithfulness (ADR 0002): the result-flavored clause must match what
    # actually happened. A draw didn't "lose" the match; say "decide" instead.
    decided_clause = (
        "It's not what lost this match on its own"
        if result == "Loss"
        else "It's not what kept this match even on its own"
    )
    sentence = (
        f"Your thinnest group is {display} at {avg_overall} average OVR across {count}. "
        f"{decided_clause}, but it's the squad hole most worth "
        "closing in recruiting or development."
    )
    signals.append(
        _Signal(
            code=WEAKEST_ROLE_GROUP,
            severity=severity,
            factor=ManagerLesson(
                code=WEAKEST_ROLE_GROUP,
                title="Your thinnest position group",
                sentence=sentence,
                controllable=True,
                evidence_chips=chips,
            ),
        )
    )


def _no_lever_lesson(*, result: str = "Loss") -> ManagerLesson:
    # Faithfulness (ADR 0002): the closing clause must match the real result. A
    # loss "went the other way"; a draw "stayed level" — never claim the draw
    # was lost.
    closing = (
        "it came down to the margins and went the other way. Run it back."
        if result == "Loss"
        else "it came down to the margins and stayed level. Run it back."
    )
    return ManagerLesson(
        code=NO_LEVER,
        title="Nothing you controlled would have changed this",
        sentence=(
            "Honestly, nothing you controlled would have flipped this one. Your six "
            f"were a fair match, rested, and well-drilled — {closing}"
        ),
        controllable=False,
        evidence_chips=(),
    )


__all__ = [
    "ManagerLesson",
    "derive_manager_lesson",
    "is_inconclusive_factor",
    "IGNORED_RECOMMENDATION",
    "ROSTER_EDGE",
    "FATIGUE",
    "WEAKEST_ROLE_GROUP",
    "NO_LEVER",
]
