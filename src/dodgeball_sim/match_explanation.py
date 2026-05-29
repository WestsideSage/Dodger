"""Deterministic post-match "Primary Factor" explanation contract.

V14 Task 1. Given a fully-resolved match (box score, recognition moments,
narrative deficit timeline, and lineup-liability facts) this module ranks the
highest-leverage *supported* reason a match went the way it did and returns a
single ``PrimaryFactor`` plus the ranked candidates it considered.

Hard rules (mirrors AGENTS.md / sprint-plan constraints):

* Read-only over already-resolved data. Nothing here changes match outcomes,
  randomness, or balance. The event log remains canon.
* Every claim is backed by a number that is actually present in the inputs
  (catch totals, gassed-collapse moments, flood-throw moments, the deficit
  timeline, eliminated liabilities). No narrative invention.
* When the evidence is weak (close match, no dominant disparity) we fall back
  to "upset variance / no dominant factor" and soften the language so we never
  assert false causality.

The function is intentionally pure (primitive inputs only) so the ranking and
tie-break rules can be unit-tested without spinning up a match or a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

# ---------------------------------------------------------------------------
# Factor codes
# ---------------------------------------------------------------------------
LATE_STAMINA_COLLAPSE = "late_stamina_collapse"
CATCH_DISPARITY = "catch_disparity"
FLOOD_THROWS_PUNISHED = "flood_throws_punished"
OPENING_RUSH_DEFICIT = "opening_rush_deficit"
LIABILITY_INVOLVEMENT = "liability_involvement"
UPSET_VARIANCE = "upset_variance"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# Minimum leverage weight a candidate must reach to be treated as a *dominant*
# factor. Below this we fall back to the upset/variance explanation.
_MIN_DOMINANT_WEIGHT = 2.0

# Deterministic final tie-break order (lower index wins ties on weight and
# finality). Catch disparity leads because it is the canonical "massive
# disparity" example in the sprint plan.
_CODE_PRIORITY = (
    CATCH_DISPARITY,
    LATE_STAMINA_COLLAPSE,
    FLOOD_THROWS_PUNISHED,
    OPENING_RUSH_DEFICIT,
    LIABILITY_INVOLVEMENT,
)


@dataclass(frozen=True)
class PrimaryFactor:
    """Backend contract surfaced to the Aftermath UI.

    ``code`` is a stable machine key; ``title``/``sentence`` are display copy;
    ``confidence`` is one of high/medium/low (drives softer language and a UI
    badge); ``evidence_chips`` are short proof tokens (e.g. ``"Catches 5-2"``).
    """

    code: str
    title: str
    sentence: str
    confidence: str
    evidence_chips: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "sentence": self.sentence,
            "confidence": self.confidence,
            "evidence_chips": list(self.evidence_chips),
        }


@dataclass(frozen=True)
class _Candidate:
    code: str
    weight: float  # leverage magnitude, comparable across codes
    finality: int  # tick of the decisive evidence; later outweighs earlier
    factor: PrimaryFactor


@dataclass(frozen=True)
class MatchExplanation:
    primary_factor: PrimaryFactor
    considered: tuple[PrimaryFactor, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "primary_factor": self.primary_factor.as_dict(),
            "considered": [factor.as_dict() for factor in self.considered],
        }


# ---------------------------------------------------------------------------
# Deficit timeline — replays player_out state-diffs to recover when (and how
# deeply) the player team trailed. Mirrors replay_proof.derive_narrative_beats
# but also captures the tick of the worst deficit and an "early game" reading,
# both of which the opening-rush factor needs. Exposed so callers/tests can
# share a single source of truth.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeficitTimeline:
    largest_deficit: int
    deficit_low_tick: int
    eliminated_by_club: dict[str, tuple[str, ...]]


def deficit_timeline(
    match_result: Any,
    *,
    player_club_id: str,
    opponent_club_id: str,
) -> DeficitTimeline:
    teams = (getattr(match_result, "box_score", {}) or {}).get("teams", {}) or {}
    player_living = int(((teams.get(player_club_id) or {}).get("totals") or {}).get("living") or 0)
    opp_living = int(((teams.get(opponent_club_id) or {}).get("totals") or {}).get("living") or 0)

    events = getattr(match_result, "events", ()) or ()
    eliminated: dict[str, list[str]] = {player_club_id: [], opponent_club_id: []}
    total_player_outs = 0
    total_opponent_outs = 0
    for event in events:
        player_out = _player_out(event)
        if player_out is None:
            continue
        team_id = str(player_out.get("team", ""))
        pid = str(player_out.get("player_id", ""))
        if team_id == player_club_id:
            total_player_outs += 1
            if pid:
                eliminated[player_club_id].append(pid)
        elif team_id == opponent_club_id:
            total_opponent_outs += 1
            if pid:
                eliminated[opponent_club_id].append(pid)

    player_active = player_living + total_player_outs
    opponent_active = opp_living + total_opponent_outs
    largest_deficit = 0
    deficit_low_tick = 0
    for event in events:
        player_out = _player_out(event)
        if player_out is None:
            continue
        team_id = str(player_out.get("team", ""))
        if team_id == player_club_id:
            player_active -= 1
        elif team_id == opponent_club_id:
            opponent_active -= 1
        diff = player_active - opponent_active
        if diff < 0 and -diff > largest_deficit:
            largest_deficit = -diff
            deficit_low_tick = int(getattr(event, "tick", 0) or 0)

    return DeficitTimeline(
        largest_deficit=largest_deficit,
        deficit_low_tick=deficit_low_tick,
        eliminated_by_club={
            player_club_id: tuple(eliminated[player_club_id]),
            opponent_club_id: tuple(eliminated[opponent_club_id]),
        },
    )


def _player_out(event: Any) -> Mapping[str, Any] | None:
    state_diff = getattr(event, "state_diff", None)
    if not isinstance(state_diff, Mapping):
        return None
    player_out = state_diff.get("player_out")
    return player_out if isinstance(player_out, Mapping) else None


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def derive_match_explanation(
    *,
    result: str,
    player_survivors: int,
    opponent_survivors: int,
    player_catches: int,
    opponent_catches: int,
    moment_events: Sequence[Any] = (),
    player_club_id: str = "",
    opponent_club_id: str = "",
    largest_deficit: int = 0,
    deficit_low_tick: int = 0,
    final_tick: int = 0,
    name_map: Mapping[str, str] | None = None,
    liabilities: Sequence[Mapping[str, Any]] = (),
) -> MatchExplanation:
    """Rank supported factors and return the dominant one (or a soft fallback).

    Parameters are all already-resolved primitives so the logic is pure.

    ``result`` is from the player's perspective ("Win"/"Loss"/"Draw").
    ``liabilities`` is a sequence of ``{name, role_name, archetype,
    on_player_team, eliminated}`` dicts describing active lineup liabilities
    that were eliminated during the match.
    """

    names = dict(name_map or {})
    candidates: list[_Candidate] = []

    losing_id = ""
    if result == "Loss":
        losing_id = player_club_id
    elif result == "Win":
        losing_id = opponent_club_id

    _add_catch_disparity(
        candidates,
        result=result,
        player_catches=player_catches,
        opponent_catches=opponent_catches,
    )
    _add_late_stamina_collapse(
        candidates,
        moment_events=moment_events,
        result=result,
        losing_id=losing_id,
        player_club_id=player_club_id,
        final_tick=final_tick,
        names=names,
    )
    _add_flood_throws(
        candidates,
        moment_events=moment_events,
        result=result,
        losing_id=losing_id,
        player_club_id=player_club_id,
        player_catches=player_catches,
        opponent_catches=opponent_catches,
    )
    _add_opening_rush_deficit(
        candidates,
        result=result,
        largest_deficit=largest_deficit,
        deficit_low_tick=deficit_low_tick,
        final_tick=final_tick,
    )
    _add_liability_involvement(
        candidates,
        result=result,
        liabilities=liabilities,
    )

    # Deterministic ranking: leverage weight desc, then chronological finality
    # desc (late events outweigh early), then fixed category priority.
    candidates.sort(
        key=lambda c: (
            -c.weight,
            -c.finality,
            _CODE_PRIORITY.index(c.code) if c.code in _CODE_PRIORITY else len(_CODE_PRIORITY),
        )
    )

    # Fallback to "no dominant factor" when there is nothing supported at all,
    # or when the strongest signal is weak *and* the match was close (margin of
    # one survivor). A weak-but-real factor in a non-close result still beats a
    # blank "variance" shrug, and its low confidence already softens the copy.
    margin = abs(player_survivors - opponent_survivors)
    top = candidates[0] if candidates else None
    use_fallback = top is None or (top.weight < _MIN_DOMINANT_WEIGHT and margin <= 1)
    if use_fallback:
        primary = _upset_variance_factor(
            result=result,
            player_survivors=player_survivors,
            opponent_survivors=opponent_survivors,
        )
        considered = tuple([c.factor for c in candidates[:3]])
        return MatchExplanation(primary_factor=primary, considered=considered)

    considered = tuple(c.factor for c in candidates[:3])
    return MatchExplanation(primary_factor=top.factor, considered=considered)


# ---------------------------------------------------------------------------
# Per-factor builders
# ---------------------------------------------------------------------------


def _add_catch_disparity(
    candidates: list[_Candidate],
    *,
    result: str,
    player_catches: int,
    opponent_catches: int,
) -> None:
    diff = player_catches - opponent_catches
    mag = abs(diff)
    if mag < 1:
        return
    favors_player = diff > 0
    # Only claim catches *decided* the match when the catch advantage aligns
    # with the outcome. A team that out-caught and still lost did not lose
    # because of catches, so we don't assert that causality.
    if result == "Win" and not favors_player:
        return
    if result == "Loss" and favors_player:
        return

    if mag >= 3:
        confidence = CONFIDENCE_HIGH
    elif mag == 2:
        confidence = CONFIDENCE_MEDIUM
    else:
        confidence = CONFIDENCE_LOW

    chips = (f"Catches {player_catches}-{opponent_catches}", f"+{mag} catch swing")
    soft = confidence == CONFIDENCE_LOW
    if favors_player:
        sentence = (
            "Catches may have been the edge — your squad pulled down "
            f"{player_catches} returns to their {opponent_catches}."
            if soft
            else
            "Catching decided it: your squad pulled down "
            f"{player_catches} returns to their {opponent_catches}, flipping bodies back onto the court."
        )
    else:
        sentence = (
            "Their catching may have tilted it — they answered with "
            f"{opponent_catches} returns to your {player_catches}."
            if soft
            else
            "Their catching decided it: they pulled down "
            f"{opponent_catches} returns to your {player_catches} and kept reloading the court."
        )
    candidates.append(
        _Candidate(
            code=CATCH_DISPARITY,
            weight=float(mag),
            finality=0,  # catches accrue match-long; never wins a finality tie
            factor=PrimaryFactor(
                code=CATCH_DISPARITY,
                title="Catch disparity",
                sentence=sentence,
                confidence=confidence,
                evidence_chips=chips,
            ),
        )
    )


def _add_late_stamina_collapse(
    candidates: list[_Candidate],
    *,
    moment_events: Sequence[Any],
    result: str,
    losing_id: str,
    player_club_id: str,
    final_tick: int,
    names: Mapping[str, str],
) -> None:
    gassed = [m for m in moment_events if _kind(m) == "gassed_collapse"]
    if not gassed:
        return
    # On a decisive result, only collapses on the losing side plausibly
    # explain the loss. On a draw, any collapse is fair game.
    if losing_id:
        relevant = [m for m in gassed if str(getattr(m, "team_id", "")) == losing_id]
    else:
        relevant = gassed
    if not relevant:
        return
    latest = max(relevant, key=lambda m: int(getattr(m, "tick", 0) or 0))
    tick = int(getattr(latest, "tick", 0) or 0)
    late = final_tick > 0 and tick >= 0.6 * final_tick
    weight = 2.0 + (0.5 if len(relevant) > 1 else 0.0)
    if late:
        confidence = CONFIDENCE_HIGH
    elif final_tick > 0 and tick >= 0.4 * final_tick:
        confidence = CONFIDENCE_MEDIUM
    else:
        confidence = CONFIDENCE_LOW

    pid = str(getattr(latest, "player_id", ""))
    player_name = names.get(pid, pid or "A key player")
    pct = int(round(float(getattr(latest, "fatigue_pct", 0.0) or 0.0) * 100))
    chips = [f"Gassed: {player_name} ({pct}%)"]
    if len(relevant) > 1:
        chips.append(f"{len(relevant)} collapses")

    collapse_is_player = str(getattr(latest, "team_id", "")) == player_club_id
    soft = confidence == CONFIDENCE_LOW
    if collapse_is_player:
        sentence = (
            f"Stamina may have cost you late — {player_name} emptied the tank ({pct}%) before the finish."
            if soft
            else
            f"Your legs went late: {player_name} collapsed gassed at {pct}% with the match still live, and the squad couldn't cover the gap."
        )
    else:
        sentence = (
            f"You may have outlasted them — {player_name} folded gassed ({pct}%) down the stretch."
            if soft
            else
            f"You outlasted them: {player_name} collapsed gassed at {pct}% late, and your fresher legs closed it out."
        )
    candidates.append(
        _Candidate(
            code=LATE_STAMINA_COLLAPSE,
            weight=weight,
            finality=tick,
            factor=PrimaryFactor(
                code=LATE_STAMINA_COLLAPSE,
                title="Late stamina collapse",
                sentence=sentence,
                confidence=confidence,
                evidence_chips=tuple(chips),
            ),
        )
    )


def _add_flood_throws(
    candidates: list[_Candidate],
    *,
    moment_events: Sequence[Any],
    result: str,
    losing_id: str,
    player_club_id: str,
    player_catches: int,
    opponent_catches: int,
) -> None:
    floods = [m for m in moment_events if _kind(m) == "flood_throw"]
    if not floods:
        return
    for flood in sorted(floods, key=lambda m: int(getattr(m, "tick", 0) or 0), reverse=True):
        flooder = str(getattr(flood, "thrower_team_id", ""))
        # The flood was "punished" only if the *other* side actually caught
        # balls (returns are the punishment in this engine). Two teams only,
        # so the punisher is whichever side did not throw the flood.
        punisher_catches = opponent_catches if flooder == player_club_id else player_catches
        if punisher_catches <= 0:
            continue
        # Align with the result: a punished flood only explains the outcome
        # when the flooder is the losing side (or it's a draw).
        if losing_id and flooder != losing_id:
            continue
        tick = int(getattr(flood, "tick", 0) or 0)
        count = len(getattr(flood, "thrower_ids", ()) or ())
        confidence = CONFIDENCE_MEDIUM if punisher_catches >= 2 else CONFIDENCE_LOW
        flooder_is_player = flooder == player_club_id
        soft = confidence == CONFIDENCE_LOW
        chips = (f"Flood throw x{count}", f"{punisher_catches} returns punished")
        if flooder_is_player:
            sentence = (
                f"Over-throwing may have backfired — a {count}-ball flood gave them {punisher_catches} catch returns."
                if soft
                else
                f"Your flood throws were punished: a {count}-ball volley handed them {punisher_catches} catch returns and swung the count."
            )
        else:
            sentence = (
                f"You may have capitalised on their over-throwing — their {count}-ball flood gave you {punisher_catches} returns."
                if soft
                else
                f"You punished their flood: their {count}-ball volley gave you {punisher_catches} catch returns that reloaded your side."
            )
        candidates.append(
            _Candidate(
                code=FLOOD_THROWS_PUNISHED,
                weight=1.5 + (0.5 if punisher_catches >= 3 else 0.0),
                finality=tick,
                factor=PrimaryFactor(
                    code=FLOOD_THROWS_PUNISHED,
                    title="Flood throws punished",
                    sentence=sentence,
                    confidence=confidence,
                    evidence_chips=chips,
                ),
            )
        )
        return  # one flood candidate (the latest punished one) is enough


def _add_opening_rush_deficit(
    candidates: list[_Candidate],
    *,
    result: str,
    largest_deficit: int,
    deficit_low_tick: int,
    final_tick: int,
) -> None:
    if result == "Win":
        return
    if largest_deficit < 2:
        return
    # "Opening rush" specifically means the hole opened early. A late deficit
    # is the *result* of other factors, not an opening-rush cause.
    early = final_tick > 0 and deficit_low_tick <= 0.4 * final_tick
    if not early:
        return
    confidence = CONFIDENCE_HIGH if largest_deficit >= 3 else CONFIDENCE_MEDIUM
    chips = (f"Down {largest_deficit} early", f"Low point @ tick {deficit_low_tick}")
    sentence = (
        f"You fell behind early: an opening rush put you down {largest_deficit} bodies before you could settle, "
        "and chasing it shaped the rest of the match."
    )
    candidates.append(
        _Candidate(
            code=OPENING_RUSH_DEFICIT,
            weight=float(largest_deficit) * 0.9,
            finality=deficit_low_tick,
            factor=PrimaryFactor(
                code=OPENING_RUSH_DEFICIT,
                title="Opening rush deficit",
                sentence=sentence,
                confidence=confidence,
                evidence_chips=chips,
            ),
        )
    )


def _add_liability_involvement(
    candidates: list[_Candidate],
    *,
    result: str,
    liabilities: Sequence[Mapping[str, Any]],
) -> None:
    if result == "Win":
        return
    eliminated = [
        liab
        for liab in liabilities
        if liab.get("on_player_team") and liab.get("eliminated")
    ]
    if not eliminated:
        return
    first = eliminated[0]
    name = str(first.get("name", "A starter"))
    role = str(first.get("role_name", "role"))
    archetype = str(first.get("archetype", "archetype"))
    count = len(eliminated)
    chips = [f"Liability: {name} ({role})"]
    if count > 1:
        chips.append(f"{count} mismatched starters")
    # Deliberately soft / "involvement" language: proven *exploitation* is the
    # job of the replay liability tags (Task 5), not this summary factor.
    sentence = (
        f"A lineup mismatch was in the mix — {name} played out of role as {role} "
        f"({archetype}) and was eliminated, a fit problem worth addressing."
    )
    candidates.append(
        _Candidate(
            code=LIABILITY_INVOLVEMENT,
            weight=1.0 + 0.5 * (count - 1),
            finality=0,
            factor=PrimaryFactor(
                code=LIABILITY_INVOLVEMENT,
                title="Lineup liability involved",
                sentence=sentence,
                confidence=CONFIDENCE_LOW,
                evidence_chips=tuple(chips),
            ),
        )
    )


def _upset_variance_factor(
    *,
    result: str,
    player_survivors: int,
    opponent_survivors: int,
) -> PrimaryFactor:
    margin = abs(player_survivors - opponent_survivors)
    chips = (f"Survivors {player_survivors}-{opponent_survivors}", f"Margin {margin}")
    if result == "Win":
        sentence = (
            "No single factor dominated — this one came down to the margins, "
            "and the squad found enough on the day to edge it."
        )
    elif result == "Loss":
        sentence = (
            "No single factor dominated — it stayed close throughout and the "
            "variance went against you. There's no one thing to fix here."
        )
    else:
        sentence = (
            "Honors even with no dominant factor — the two sides traded blows "
            "and neither edge held."
        )
    return PrimaryFactor(
        code=UPSET_VARIANCE,
        title="No dominant factor",
        sentence=sentence,
        confidence=CONFIDENCE_LOW,
        evidence_chips=chips,
    )


def _kind(moment: Any) -> str:
    kind = getattr(moment, "kind", None)
    return getattr(kind, "value", kind) if kind is not None else ""


__all__ = [
    "PrimaryFactor",
    "MatchExplanation",
    "DeficitTimeline",
    "derive_match_explanation",
    "deficit_timeline",
    "LATE_STAMINA_COLLAPSE",
    "CATCH_DISPARITY",
    "FLOOD_THROWS_PUNISHED",
    "OPENING_RUSH_DEFICIT",
    "LIABILITY_INVOLVEMENT",
    "UPSET_VARIANCE",
]
