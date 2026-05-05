from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .records import RecordBroken
from .rivalries import RivalryRecord, compute_rivalry_score
from .rng import DeterministicRNG, derive_seed


@dataclass(frozen=True)
class MatchdayResult:
    match_id: str
    season_id: str
    week: int
    winner_club_id: str
    winner_club_name: str
    loser_club_id: str
    loser_club_name: str
    winner_score: int
    loser_score: int
    winner_pre_match_overall: float
    loser_pre_match_overall: float
    milestone_player_id: str | None = None
    milestone_player_name: str = ""
    milestone_label: str = ""
    milestone_value: int = 0
    rookie_player_id: str | None = None
    rookie_player_name: str = ""
    rookie_club_name: str = ""
    retirement_player_id: str | None = None
    retirement_player_name: str = ""
    flashpoint_text: str = ""


@dataclass(frozen=True)
class Headline:
    category: str
    priority: int
    text: str
    entity_ids: tuple[str, ...] = field(default_factory=tuple)
    season_id: str = ""
    week: int = 0


_TEMPLATES = {
    "record_broken": (
        "Record Watch: {player_name} set a new {record_type} mark at {value}.",
        "{player_name} rewrites the books - new {record_type} record stands at {value}.",
        "History Made: {player_name} breaks the all-time {record_type} record with {value}.",
        "The {record_type} record falls. {player_name} now holds the mark at {value}.",
        "By the Numbers: {player_name}'s {value} {record_type} eclipses the previous best.",
    ),
    "big_upset": (
        "Upset Alert: {winner_name} stunned {loser_name} {winner_score}-{loser_score} despite a {ovr_gap} OVR gap.",
        "Nobody saw this coming. {winner_name} takes down {loser_name} {winner_score}-{loser_score}.",
        "{loser_name} had the ratings. {winner_name} had the result. Final: {winner_score}-{loser_score}.",
        "{winner_name} erases a {ovr_gap}-point OVR disadvantage and beats {loser_name}.",
        "{winner_name} stuns the wire. {loser_name} drops despite leading on paper by {ovr_gap} OVR.",
    ),
    "rivalry_flashpoint": (
        "Rivalry Boils Over: {winner_name} vs {loser_name} added another chapter when {flashpoint_text}.",
        "Old Wounds: {winner_name} and {loser_name} renewed their feud when {flashpoint_text}.",
        "This one had history. {winner_name} edged {loser_name} in a matchup where {flashpoint_text}.",
        "Another Chapter: {winner_name} pulls ahead in the rivalry ledger after {flashpoint_text}.",
    ),
    "player_milestone": (
        "Milestone Reached: {player_name} hit {value} career {stat_label}.",
        "{player_name} crosses the {value} career {stat_label} threshold. The numbers speak.",
        "By The Books: {player_name} officially joins the {value} {stat_label} club.",
        "Career Watch: {player_name} records career {stat_label} number {value} for {club_name}.",
        "Running History: {player_name}'s {value} {stat_label} moves them into elite company.",
    ),
    "retirement": (
        "Farewell Tour: {player_name} announced a retirement decision.",
        "{player_name} hangs up the jersey. The wire acknowledges the career.",
        "League Note: {player_name} retires. The record stands.",
    ),
    "rookie_debut": (
        "Rookie Watch: {player_name} made a first impression for {club_name}.",
        "New Blood: {player_name} steps onto the court for {club_name} in week {week}.",
        "First Touch: {player_name} logs court time in their {club_name} debut.",
        "{player_name} arrives. {club_name}'s newest recruit entered in week {week}.",
        "The Class Arrives: {player_name} records their first action in a {club_name} uniform.",
    ),
    "match_recap": (
        "Final Whistle: {winner_name} beat {loser_name} {winner_score}-{loser_score}.",
        "{winner_name} {winner_score}, {loser_name} {loser_score}. Week {week} in the books.",
        "Result: {winner_name} over {loser_name}, {winner_score} to {loser_score}.",
        "{winner_name} holds on against {loser_name}. Score: {winner_score}-{loser_score}.",
        "Wrap-Up: {loser_name} falls to {winner_name}, {winner_score}-{loser_score}.",
    ),
}


def generate_matchday_news(
    matchday_results: Iterable[MatchdayResult],
    records_broken: Iterable[RecordBroken],
    rivalries: Iterable[RivalryRecord],
) -> list[Headline]:
    results = sorted(matchday_results, key=lambda item: (item.week, item.match_id))
    record_items = sorted(records_broken, key=lambda item: (item.record_type, item.holder_id))
    rivalry_map = {
        frozenset((record.club_a_id, record.club_b_id)): record for record in rivalries
    }
    candidates: list[Headline] = []

    for record in record_items:
        candidates.append(
            Headline(
                category="record_broken",
                priority=100,
                text=_render_template(
                    "record_broken",
                    record.set_in_season,
                    0,
                    record.holder_id,
                    player_name=record.holder_name,
                    record_type=record.record_type.replace("_", " "),
                    value=_render_value(record.new_value),
                ),
                entity_ids=_compact_ids(record.holder_id, record.previous_holder_id),
                season_id=record.set_in_season,
            )
        )

    for result in results:
        upset_gap = result.loser_pre_match_overall - result.winner_pre_match_overall
        if upset_gap >= 8.0:
            candidates.append(
                Headline(
                    category="big_upset",
                    priority=90,
                    text=_render_template(
                        "big_upset",
                        result.season_id,
                        result.week,
                        result.match_id,
                        winner_name=result.winner_club_name,
                        loser_name=result.loser_club_name,
                        winner_score=result.winner_score,
                        loser_score=result.loser_score,
                        ovr_gap=f"{upset_gap:.1f}",
                    ),
                    entity_ids=(result.winner_club_id, result.loser_club_id),
                    season_id=result.season_id,
                    week=result.week,
                )
            )

        rivalry = rivalry_map.get(frozenset((result.winner_club_id, result.loser_club_id)))
        if rivalry is not None:
            rivalry_score = compute_rivalry_score(rivalry)
            if rivalry_score >= 55.0 and result.flashpoint_text.strip():
                candidates.append(
                    Headline(
                        category="rivalry_flashpoint",
                        priority=80,
                        text=_render_template(
                            "rivalry_flashpoint",
                            result.season_id,
                            result.week,
                            result.match_id,
                            winner_name=result.winner_club_name,
                            loser_name=result.loser_club_name,
                            flashpoint_text=result.flashpoint_text.strip(),
                        ),
                        entity_ids=(result.winner_club_id, result.loser_club_id),
                        season_id=result.season_id,
                        week=result.week,
                    )
                )

        if result.milestone_player_id and result.milestone_player_name and result.milestone_label:
            candidates.append(
                Headline(
                    category="player_milestone",
                    priority=70,
                    text=_render_template(
                        "player_milestone",
                        result.season_id,
                        result.week,
                        result.match_id,
                        player_name=result.milestone_player_name,
                        value=result.milestone_value,
                        stat_label=result.milestone_label,
                        club_name=result.winner_club_name,
                    ),
                    entity_ids=(result.milestone_player_id,),
                    season_id=result.season_id,
                    week=result.week,
                )
            )

        if result.rookie_player_id and result.rookie_player_name and result.rookie_club_name:
            candidates.append(
                Headline(
                    category="rookie_debut",
                    priority=60,
                    text=_render_template(
                        "rookie_debut",
                        result.season_id,
                        result.week,
                        result.match_id,
                        player_name=result.rookie_player_name,
                        club_name=result.rookie_club_name,
                        week=result.week,
                    ),
                    entity_ids=(result.rookie_player_id,),
                    season_id=result.season_id,
                    week=result.week,
                )
            )

        if result.retirement_player_id and result.retirement_player_name:
            candidates.append(
                Headline(
                    category="retirement",
                    priority=65,
                    text=_render_template(
                        "retirement",
                        result.season_id,
                        result.week,
                        result.match_id,
                        player_name=result.retirement_player_name,
                    ),
                    entity_ids=(result.retirement_player_id,),
                    season_id=result.season_id,
                    week=result.week,
                )
            )

        candidates.append(
            Headline(
                category="match_recap",
                priority=25,
                text=_render_template(
                    "match_recap",
                    result.season_id,
                    result.week,
                    result.match_id,
                    winner_name=result.winner_club_name,
                    loser_name=result.loser_club_name,
                    winner_score=result.winner_score,
                    loser_score=result.loser_score,
                    week=result.week,
                ),
                entity_ids=(result.winner_club_id, result.loser_club_id),
                season_id=result.season_id,
                week=result.week,
            )
        )

    ordered = sorted(
        candidates,
        key=lambda item: (
            -item.priority,
            item.season_id,
            item.week,
            item.category,
            item.text,
        ),
    )
    return ordered[: max(2, min(3, len(ordered)))]


def _compact_ids(*ids: str | None) -> tuple[str, ...]:
    return tuple(item for item in ids if item)


def _render_value(value: float) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}"


def _render_template(category: str, season_id: str, seed_week: int, item_id: str, **values: object) -> str:
    templates = _TEMPLATES[category]
    rng = DeterministicRNG(derive_seed(20260429, "headline_template", season_id, str(seed_week), item_id, category))
    template = rng.choice(list(templates))
    return template.format(**values)


__all__ = [
    "Headline",
    "MatchdayResult",
    "generate_matchday_news",
]
