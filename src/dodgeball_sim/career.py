from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SignatureMoment:
    season_id: str
    match_id: str
    label: str
    description: str
    leverage: float
    value: float


@dataclass(frozen=True)
class CareerSummary:
    player_id: str
    player_name: str
    seasons_played: int
    championships: int
    awards_won: int
    total_matches: int
    total_eliminations: int
    total_catches_made: int
    total_dodges_successful: int
    total_times_eliminated: int
    peak_eliminations: int
    signature_moments: tuple[SignatureMoment, ...]

    @property
    def elimination_differential(self) -> int:
        return self.total_eliminations - self.total_times_eliminated

    @property
    def average_eliminations_per_season(self) -> float:
        if self.seasons_played <= 0:
            return 0.0
        return self.total_eliminations / self.seasons_played

    @property
    def legacy_score(self) -> float:
        return round(
            self.total_eliminations * 1.0
            + self.total_catches_made * 1.35
            + self.total_dodges_successful * 0.75
            + self.championships * 18.0
            + self.awards_won * 7.5
            + max(0, self.elimination_differential) * 0.4
            + sum(moment.value * moment.leverage for moment in self.signature_moments) * 1.2,
            2,
        )


@dataclass(frozen=True)
class HallOfFameCase:
    eligible: bool
    inducted: bool
    score: float
    threshold: float
    reasons: tuple[str, ...]


def aggregate_career(
    player_id: str,
    player_name: str,
    season_rows: list[Mapping[str, object]],
    awards: list[Mapping[str, object]] | None = None,
    signature_moments: list[SignatureMoment] | None = None,
) -> CareerSummary:
    """Aggregate plain season mappings into a frozen career summary."""
    awards = list(awards or [])
    moments = tuple(sorted(signature_moments or [], key=_signature_sort_key, reverse=True)[:5])
    seasons_played = len(season_rows)

    return CareerSummary(
        player_id=player_id,
        player_name=player_name,
        seasons_played=seasons_played,
        championships=sum(1 for row in season_rows if _bool_value(row.get("champion", False))),
        awards_won=len(awards),
        total_matches=sum(_int_value(row.get("matches", 0)) for row in season_rows),
        total_eliminations=sum(_int_value(row.get("total_eliminations", 0)) for row in season_rows),
        total_catches_made=sum(_int_value(row.get("total_catches_made", 0)) for row in season_rows),
        total_dodges_successful=sum(_int_value(row.get("total_dodges_successful", 0)) for row in season_rows),
        total_times_eliminated=sum(_int_value(row.get("total_times_eliminated", 0)) for row in season_rows),
        peak_eliminations=max((_int_value(row.get("total_eliminations", 0)) for row in season_rows), default=0),
        signature_moments=moments,
    )


def evaluate_hall_of_fame(summary: CareerSummary) -> HallOfFameCase:
    """Evaluate whether a player's career has crossed the Hall of Fame line."""
    threshold = 120.0
    reasons: list[str] = []
    if summary.seasons_played >= 6:
        reasons.append("longevity")
    if summary.total_eliminations >= 60:
        reasons.append("volume scoring")
    if summary.championships >= 1:
        reasons.append("championship pedigree")
    if summary.awards_won >= 2:
        reasons.append("award recognition")
    if summary.peak_eliminations >= 16:
        reasons.append("elite peak")
    if any(moment.leverage >= 1.5 for moment in summary.signature_moments):
        reasons.append("signature moments")

    score = summary.legacy_score
    eligible = summary.seasons_played >= 4 and (
        summary.total_eliminations >= 35
        or summary.championships >= 1
        or summary.awards_won >= 1
        or score >= threshold
    )
    inducted = eligible and score >= threshold
    return HallOfFameCase(
        eligible=eligible,
        inducted=inducted,
        score=score,
        threshold=threshold,
        reasons=tuple(reasons),
    )


def build_signature_moment(
    *,
    season_id: str,
    match_id: str,
    label: str,
    description: str,
    leverage: float,
    eliminations: int = 0,
    catches: int = 0,
    dodges: int = 0,
    clutch_bonus: float = 0.0,
) -> SignatureMoment:
    value = (
        eliminations * 3.0
        + catches * 3.5
        + dodges * 1.5
        + max(0.0, float(clutch_bonus))
    )
    return SignatureMoment(
        season_id=season_id,
        match_id=match_id,
        label=label,
        description=description,
        leverage=round(max(0.5, float(leverage)), 2),
        value=round(value, 2),
    )


def _signature_sort_key(moment: SignatureMoment) -> tuple[float, float, str, str]:
    return (moment.leverage * moment.value, moment.value, moment.season_id, moment.match_id)


def _int_value(value: object) -> int:
    return int(float(value))


def _bool_value(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "champion"}
    return bool(value)


__all__ = [
    "CareerSummary",
    "HallOfFameCase",
    "SignatureMoment",
    "aggregate_career",
    "build_signature_moment",
    "evaluate_hall_of_fame",
]
