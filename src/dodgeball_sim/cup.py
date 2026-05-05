from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Iterable

from .rng import DeterministicRNG


@dataclass(frozen=True)
class CupEntrant:
    club_id: str | None = None
    source_match_id: str | None = None

    def __post_init__(self) -> None:
        has_club = self.club_id is not None
        has_source = self.source_match_id is not None
        if has_club == has_source:
            raise ValueError("CupEntrant must reference exactly one source")


@dataclass(frozen=True)
class CupMatch:
    match_id: str
    round_number: int
    slot_number: int
    side_a: CupEntrant
    side_b: CupEntrant | None
    auto_advance_club_id: str | None = None

    def __post_init__(self) -> None:
        if self.round_number < 1:
            raise ValueError("round_number must be at least 1")
        if self.slot_number < 1:
            raise ValueError("slot_number must be at least 1")
        if self.side_b is None:
            if self.auto_advance_club_id != self.side_a.club_id:
                raise ValueError("bye matches must auto-advance the remaining club")
        elif self.auto_advance_club_id is not None:
            raise ValueError("non-bye matches cannot auto-advance")

    @property
    def is_bye(self) -> bool:
        return self.side_b is None


@dataclass(frozen=True)
class CupRound:
    round_number: int
    matches: tuple[CupMatch, ...]


@dataclass(frozen=True)
class CupBracket:
    club_ids: tuple[str, ...]
    rounds: tuple[CupRound, ...]

    @property
    def total_rounds(self) -> int:
        return len(self.rounds)

    @property
    def opening_round(self) -> CupRound:
        return self.rounds[0]

    @property
    def opening_byes(self) -> tuple[str, ...]:
        return tuple(
            match.auto_advance_club_id
            for match in self.opening_round.matches
            if match.auto_advance_club_id is not None
        )

    @property
    def final_match_id(self) -> str:
        return self.rounds[-1].matches[0].match_id


def generate_cup_bracket(
    club_ids: Iterable[str],
    rng: DeterministicRNG,
) -> CupBracket:
    entrants = _normalize_club_ids(club_ids)
    shuffled = tuple(rng.shuffle(list(entrants)))
    bracket_size = _next_power_of_two(len(shuffled))
    first_round_slots = bracket_size // 2
    byes = bracket_size - len(shuffled)

    first_round_matches: list[CupMatch] = []
    club_index = 0
    for slot_number in range(1, first_round_slots + 1):
        side_a = CupEntrant(club_id=shuffled[club_index])
        club_index += 1
        if slot_number <= byes:
            first_round_matches.append(
                CupMatch(
                    match_id=_match_id(1, slot_number),
                    round_number=1,
                    slot_number=slot_number,
                    side_a=side_a,
                    side_b=None,
                    auto_advance_club_id=side_a.club_id,
                )
            )
            continue

        side_b = CupEntrant(club_id=shuffled[club_index])
        club_index += 1
        first_round_matches.append(
            CupMatch(
                match_id=_match_id(1, slot_number),
                round_number=1,
                slot_number=slot_number,
                side_a=side_a,
                side_b=side_b,
            )
        )

    rounds: list[CupRound] = [CupRound(round_number=1, matches=tuple(first_round_matches))]
    previous_round = first_round_matches

    for round_number in range(2, int(log2(bracket_size)) + 1):
        next_round_matches: list[CupMatch] = []
        for match_index in range(0, len(previous_round), 2):
            slot_number = (match_index // 2) + 1
            next_round_matches.append(
                CupMatch(
                    match_id=_match_id(round_number, slot_number),
                    round_number=round_number,
                    slot_number=slot_number,
                    side_a=CupEntrant(source_match_id=previous_round[match_index].match_id),
                    side_b=CupEntrant(source_match_id=previous_round[match_index + 1].match_id),
                )
            )
        rounds.append(CupRound(round_number=round_number, matches=tuple(next_round_matches)))
        previous_round = next_round_matches

    return CupBracket(club_ids=shuffled, rounds=tuple(rounds))


def _normalize_club_ids(club_ids: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for club_id in club_ids:
        value = str(club_id).strip()
        if not value:
            raise ValueError("club_ids must not contain blank values")
        if value in seen:
            raise ValueError(f"club_ids must be unique: {value!r}")
        normalized.append(value)
        seen.add(value)

    if len(normalized) < 2:
        raise ValueError("At least two clubs are required for a cup bracket")
    return tuple(normalized)


def _next_power_of_two(value: int) -> int:
    return 1 if value <= 1 else 2 ** ceil(log2(value))


def _match_id(round_number: int, slot_number: int) -> str:
    return f"cup_r{round_number}_m{slot_number}"


__all__ = [
    "CupBracket",
    "CupEntrant",
    "CupMatch",
    "CupRound",
    "generate_cup_bracket",
]
