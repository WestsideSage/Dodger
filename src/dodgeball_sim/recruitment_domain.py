from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .rng import DeterministicRNG, derive_seed
from .scouting_center import Prospect


ARCHETYPES = ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")


@dataclass(frozen=True)
class RecruitmentProfile:
    club_id: str
    archetype_priorities: Mapping[str, float]
    risk_tolerance: float
    prestige: float
    playing_time_pitch: float
    evaluation_quality: float


@dataclass(frozen=True)
class RecruitmentBoardRow:
    club_id: str
    player_id: str
    rank: int
    public_score: float
    need_score: float
    preference_score: float
    total_score: float
    visible_reason: str


@dataclass(frozen=True)
class RecruitmentOffer:
    season_id: str
    round_number: int
    club_id: str
    player_id: str
    offer_strength: float
    source: str
    need_score: float
    playing_time_pitch: float
    prestige: float
    round_order_value: float
    visible_reason: str


@dataclass(frozen=True)
class RecruitmentSigning:
    season_id: str
    round_number: int
    club_id: str
    player_id: str
    source: str
    offer_strength: float
    recap_reason: str


@dataclass(frozen=True)
class RecruitmentSnipe:
    season_id: str
    round_number: int
    player_id: str
    winning_club_id: str
    visible_reason: str


@dataclass(frozen=True)
class RecruitmentRoundResult:
    season_id: str
    round_number: int
    signings: tuple[RecruitmentSigning, ...]
    snipes: tuple[RecruitmentSnipe, ...]


def build_recruitment_profile(root_seed: int, club_id: str) -> RecruitmentProfile:
    rng = DeterministicRNG(derive_seed(root_seed, "recruitment_profile", club_id))
    priorities = {archetype: round(rng.roll(0.0, 1.0), 4) for archetype in ARCHETYPES}
    return RecruitmentProfile(
        club_id=club_id,
        archetype_priorities=priorities,
        risk_tolerance=round(rng.roll(0.15, 0.85), 4),
        prestige=round(rng.roll(0.1, 1.0), 4),
        playing_time_pitch=round(rng.roll(0.1, 1.0), 4),
        evaluation_quality=round(rng.roll(0.25, 1.0), 4),
    )


def build_recruitment_board(
    root_seed: int,
    season_id: str,
    profile: RecruitmentProfile,
    prospects: Sequence[Prospect],
    roster_needs: Mapping[str, float],
) -> list[RecruitmentBoardRow]:
    rows: list[RecruitmentBoardRow] = []
    for prospect in sorted(prospects, key=lambda item: item.player_id):
        public_score = _public_score(root_seed, season_id, profile, prospect)
        archetype = prospect.public_archetype_guess
        need_score = round(float(roster_needs.get(archetype, 0.0)) * 4.0, 4)
        preference_score = round(float(profile.archetype_priorities.get(archetype, 0.0)) * 10.0, 4)
        low, high = prospect.public_ratings_band["ovr"]
        uncertainty = max(0.0, float(high - low))
        risk_score = round(float(profile.risk_tolerance) * uncertainty * 0.2, 4)
        total_score = round(public_score + need_score + preference_score + risk_score, 4)
        rows.append(
            RecruitmentBoardRow(
                club_id=profile.club_id,
                player_id=prospect.player_id,
                rank=0,
                public_score=public_score,
                need_score=need_score,
                preference_score=preference_score,
                total_score=total_score,
                visible_reason=f"club need {need_score:.2f}; public fit {preference_score:.2f}",
            )
        )

    ranked = sorted(rows, key=lambda row: (-row.total_score, row.player_id))
    return [
        RecruitmentBoardRow(
            club_id=row.club_id,
            player_id=row.player_id,
            rank=index,
            public_score=row.public_score,
            need_score=row.need_score,
            preference_score=row.preference_score,
            total_score=row.total_score,
            visible_reason=row.visible_reason,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def prepare_ai_offers(
    root_seed: int,
    season_id: str,
    round_number: int,
    profiles: Sequence[RecruitmentProfile],
    boards: Mapping[str, Sequence[RecruitmentBoardRow]],
    signed_player_ids: Sequence[str] = (),
) -> list[RecruitmentOffer]:
    signed = set(signed_player_ids)
    offers: list[RecruitmentOffer] = []
    for profile in sorted(profiles, key=lambda item: item.club_id):
        board = sorted(boards.get(profile.club_id, ()), key=lambda row: (row.rank, row.player_id))
        target = next((row for row in board if row.player_id not in signed), None)
        if target is None:
            continue
        strength_rng = DeterministicRNG(
            derive_seed(
                root_seed,
                "recruitment_offer_strength",
                season_id,
                str(round_number),
                profile.club_id,
                target.player_id,
            )
        )
        round_order_rng = DeterministicRNG(
            derive_seed(root_seed, "recruitment_round_order", season_id, str(round_number), profile.club_id)
        )
        offer_strength = round(
            target.total_score
            + float(profile.prestige) * 5.0
            + float(profile.playing_time_pitch) * 3.0
            + strength_rng.roll(0.0, 2.0),
            4,
        )
        round_order_value = round(round_order_rng.unit(), 8)
        offers.append(
            RecruitmentOffer(
                season_id=season_id,
                round_number=round_number,
                club_id=profile.club_id,
                player_id=target.player_id,
                offer_strength=offer_strength,
                source="ai",
                need_score=target.need_score,
                playing_time_pitch=float(profile.playing_time_pitch),
                prestige=float(profile.prestige),
                round_order_value=round_order_value,
                visible_reason=(
                    f"club need {target.need_score:.2f}; public fit {target.preference_score:.2f}; "
                    f"round priority {round_order_value:.4f}"
                ),
            )
        )
    return offers


def resolve_recruitment_round(
    season_id: str,
    round_number: int,
    prepared_ai_offers: Sequence[RecruitmentOffer],
    user_offer: RecruitmentOffer | None = None,
    shortlist_player_ids: Sequence[str] = (),
) -> RecruitmentRoundResult:
    offers = list(prepared_ai_offers)
    if user_offer is not None:
        offers.append(user_offer)

    grouped: dict[str, list[RecruitmentOffer]] = {}
    for offer in sorted(offers, key=lambda item: (item.player_id, item.club_id, item.source)):
        grouped.setdefault(offer.player_id, []).append(offer)

    signings: list[RecruitmentSigning] = []
    snipes: list[RecruitmentSnipe] = []
    shortlisted = set(shortlist_player_ids)

    for player_id in sorted(grouped):
        player_offers = grouped[player_id]
        winner = sorted(player_offers, key=_resolution_sort_key)[0]
        signings.append(
            RecruitmentSigning(
                season_id=season_id,
                round_number=round_number,
                club_id=winner.club_id,
                player_id=winner.player_id,
                source=winner.source,
                offer_strength=winner.offer_strength,
                recap_reason=winner.visible_reason,
            )
        )
        user_lost = any(offer.source == "user" for offer in player_offers) and winner.source != "user"
        was_shortlisted = player_id in shortlisted and winner.source == "ai"
        if user_lost or was_shortlisted:
            snipes.append(
                RecruitmentSnipe(
                    season_id=season_id,
                    round_number=round_number,
                    player_id=player_id,
                    winning_club_id=winner.club_id,
                    visible_reason=winner.visible_reason,
                )
            )

    return RecruitmentRoundResult(
        season_id=season_id,
        round_number=round_number,
        signings=tuple(signings),
        snipes=tuple(snipes),
    )


def _public_score(
    root_seed: int,
    season_id: str,
    profile: RecruitmentProfile,
    prospect: Prospect,
) -> float:
    low, high = prospect.public_ratings_band["ovr"]
    midpoint = (float(low) + float(high)) / 2.0
    rng = DeterministicRNG(
        derive_seed(
            root_seed,
            "recruitment_public_evaluation_noise",
            season_id,
            profile.club_id,
            prospect.player_id,
        )
    )
    noise_width = (1.0 - _clamp(float(profile.evaluation_quality), 0.0, 1.0)) * 10.0
    return round(midpoint + ((rng.unit() - 0.5) * noise_width), 4)


def _resolution_sort_key(offer: RecruitmentOffer) -> tuple[float, float, float, float, float, str]:
    return (
        -float(offer.offer_strength),
        -float(offer.need_score),
        -float(offer.playing_time_pitch),
        -float(offer.prestige),
        float(offer.round_order_value),
        offer.club_id,
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


__all__ = [
    "RecruitmentProfile",
    "RecruitmentBoardRow",
    "RecruitmentOffer",
    "RecruitmentSigning",
    "RecruitmentSnipe",
    "RecruitmentRoundResult",
    "build_recruitment_profile",
    "build_recruitment_board",
    "prepare_ai_offers",
    "resolve_recruitment_round",
]
