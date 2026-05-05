from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import Player
from .rng import DeterministicRNG


@dataclass(frozen=True)
class IdentityProfile:
    player_id: str
    full_name: str
    archetype: str
    title: str
    nickname: str
    strongest_attribute: str
    secondary_attribute: str


_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("accuracy", "Accuracy"),
    ("power", "Power"),
    ("dodge", "Dodge"),
    ("catch", "Catch"),
    ("stamina", "Stamina"),
)

_ARCHETYPE_ORDER: tuple[str, ...] = (
    "ace sniper",
    "power cannon",
    "escape artist",
    "ball hawk",
    "iron anchor",
    "two-way spark",
)

_ARCHETYPE_TITLES = {
    "ace sniper": "Ace Sniper",
    "power cannon": "Power Cannon",
    "escape artist": "Escape Artist",
    "ball hawk": "Ball Hawk",
    "iron anchor": "Iron Anchor",
    "two-way spark": "Two-Way Spark",
}

_ARCHETYPE_PREFIXES = {
    "ace sniper": ("Laser", "Scope", "Needle", "Bullseye", "Crosshair", "Pinpoint", "Zero", "Tracer"),
    "power cannon": ("Hammer", "Thunder", "Anvil", "Torque", "Crusher", "Rampart", "Battering", "Ironclad"),
    "escape artist": ("Ghost", "Slip", "Shadow", "Drift", "Vapor", "Phantom", "Mirage", "Fade"),
    "ball hawk": ("Magnet", "Snare", "Clamp", "Latch", "Vice", "Snarl", "Anchor", "Lock"),
    "iron anchor": ("Brick", "Atlas", "Boiler", "Granite", "Bastion", "Bulwark", "Rampart", "Slab"),
    "two-way spark": ("Switch", "Fuse", "Pulse", "Circuit", "Relay", "Toggle", "Amp", "Coil"),
}

_ARCHETYPE_SUFFIXES = {
    "ace sniper": ("Shot", "Line", "Eye", "Lock", "Mark", "Aim", "Strike", "Target"),
    "power cannon": ("Arm", "Blast", "Drive", "Core", "Fist", "Slam", "Force", "Impact"),
    "escape artist": ("Step", "Mist", "Glide", "Fade", "Wind", "Trace", "Pass", "Whisper"),
    "ball hawk": ("Hands", "Trap", "Net", "Hook", "Grip", "Catch", "Snatch", "Reel"),
    "iron anchor": ("Wall", "Tank", "Forge", "Guard", "Plate", "Shield", "Dome", "Citadel"),
    "two-way spark": ("Wave", "Spark", "Flux", "Charge", "Current", "Surge", "Volt", "Arc"),
}


def classify_archetype(player: Player) -> str:
    """Return a deterministic player archetype from ratings and traits."""
    ratings = player.ratings
    traits = player.traits
    ordered = sorted(
        (
            ("accuracy", ratings.accuracy),
            ("power", ratings.power),
            ("dodge", ratings.dodge),
            ("catch", ratings.catch),
            ("stamina", ratings.stamina),
        ),
        key=lambda item: (-item[1], item[0]),
    )
    top_name, top_value = ordered[0]
    second_value = ordered[1][1]
    separation = top_value - second_value

    if top_name == "accuracy" and top_value >= 86.0 and separation >= 8.0:
        return "ace sniper"
    if top_name == "power" and top_value >= 86.0 and separation >= 8.0:
        return "power cannon"
    if top_name == "dodge" and top_value >= 84.0 and separation >= 7.0:
        return "escape artist"
    if top_name == "catch" and top_value >= 84.0 and separation >= 8.0:
        return "ball hawk"
    if top_name == "stamina" and top_value >= 84.0 and separation >= 8.0:
        return "iron anchor"

    scores = {
        "ace sniper": (
            ratings.accuracy * 1.6
            + ratings.power * 0.6
            + ratings.catch * 0.2
            + _unit_value(traits.pressure) * 8.0
        ),
        "power cannon": (
            ratings.power * 1.7
            + ratings.stamina * 0.7
            + ratings.accuracy * 0.25
        ),
        "escape artist": (
            ratings.dodge * 1.65
            + ratings.stamina * 0.55
            + _unit_value(traits.consistency) * 7.0
        ),
        "ball hawk": (
            ratings.catch * 1.75
            + ratings.dodge * 0.45
            + _unit_value(traits.consistency) * 6.0
        ),
        "iron anchor": (
            ratings.stamina * 1.45
            + ratings.catch * 0.7
            + ratings.power * 0.35
        ),
        "two-way spark": (
            ratings.accuracy * 0.8
            + ratings.power * 0.8
            + ratings.dodge * 0.8
            + ratings.catch * 0.8
            + ratings.stamina * 0.35
            - separation * 2.0
        ),
    }
    ranked = sorted(
        scores.items(),
        key=lambda item: (-round(item[1], 6), _ARCHETYPE_ORDER.index(item[0])),
    )
    return ranked[0][0]


def generate_nickname(player: Player, rng: DeterministicRNG) -> str:
    """Generate a deterministic nickname using the caller-provided RNG."""
    archetype = classify_archetype(player)
    prefix = _seeded_choice(
        _ARCHETYPE_PREFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype}:prefix",
    )
    suffix = _seeded_choice(
        _ARCHETYPE_SUFFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype}:suffix",
    )
    last_name = _last_name_token(player.name)
    style_roll = _seeded_index(rng, f"{player.id}:{player.name}:{archetype}:style", 3)
    if style_roll % 3 == 0:
        return f"{prefix} {last_name}"
    if style_roll % 3 == 1:
        return f"{prefix} {suffix}"
    return f"{prefix}-{suffix}"


def build_identity_profile(player: Player, rng: DeterministicRNG) -> IdentityProfile:
    archetype = classify_archetype(player)
    strongest, secondary = _top_attributes(player)
    return IdentityProfile(
        player_id=player.id,
        full_name=player.name,
        archetype=archetype,
        title=_ARCHETYPE_TITLES[archetype],
        nickname=generate_nickname(player, rng),
        strongest_attribute=strongest,
        secondary_attribute=secondary,
    )


def _top_attributes(player: Player) -> tuple[str, str]:
    values = [
        ("Accuracy", player.ratings.accuracy),
        ("Power", player.ratings.power),
        ("Dodge", player.ratings.dodge),
        ("Catch", player.ratings.catch),
        ("Stamina", player.ratings.stamina),
    ]
    ordered = sorted(values, key=lambda item: (-item[1], item[0]))
    return ordered[0][0], ordered[1][0]


def _last_name_token(name: str) -> str:
    tokens = [token for token in name.strip().split(" ") if token]
    return tokens[-1] if tokens else "Player"


def _seeded_choice(options: tuple[str, ...], rng: DeterministicRNG, salt: str) -> str:
    return options[_seeded_index(rng, salt, len(options))]


def _seeded_index(rng: DeterministicRNG, salt: str, size: int) -> int:
    digest = hashlib.sha256(f"{rng.seed}:{salt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % size


def _unit_value(value: float) -> float:
    numeric = float(value)
    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, numeric))


__all__ = [
    "IdentityProfile",
    "build_identity_profile",
    "classify_archetype",
    "generate_nickname",
]
