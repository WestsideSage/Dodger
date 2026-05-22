from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import Player, PlayerArchetype
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

_ARCHETYPE_TITLES = {
    PlayerArchetype.THROWER: "Thrower",
    PlayerArchetype.CATCHER: "Catcher",
    PlayerArchetype.BALL_HAWK: "Ball Hawk",
    PlayerArchetype.DODGER_ANCHOR: "Dodger Anchor",
    PlayerArchetype.THROWER_CATCHER: "Thrower / Catcher",
    PlayerArchetype.THROWER_DODGER: "Thrower / Dodger",
    PlayerArchetype.CATCHER_HAWK: "Catcher / Ball Hawk",
    PlayerArchetype.HAWK_DODGER: "Ball Hawk / Dodger",
}

_ARCHETYPE_PREFIXES = {
    PlayerArchetype.THROWER: ("Laser", "Scope", "Needle", "Bullseye", "Crosshair", "Pinpoint", "Zero", "Tracer"),
    PlayerArchetype.CATCHER: ("Magnet", "Snare", "Clamp", "Latch", "Vice", "Snarl", "Anchor", "Lock"),
    PlayerArchetype.BALL_HAWK: ("Brick", "Atlas", "Boiler", "Granite", "Bastion", "Bulwark", "Rampart", "Slab"),
    PlayerArchetype.DODGER_ANCHOR: ("Ghost", "Slip", "Shadow", "Drift", "Vapor", "Phantom", "Mirage", "Fade"),
    PlayerArchetype.THROWER_CATCHER: ("Switch", "Fuse", "Pulse", "Circuit", "Relay", "Toggle", "Amp", "Coil"),
    PlayerArchetype.THROWER_DODGER: ("Storm", "Dart", "Flash", "Strike", "Pulse", "Whirl", "Vector", "Crash"),
    PlayerArchetype.CATCHER_HAWK: ("Pounce", "Snare", "Magnet", "Claw", "Vise", "Lattice", "Echo", "Field"),
    PlayerArchetype.HAWK_DODGER: ("Drift", "Phantom", "Glide", "Veil", "Whisper", "Shadow", "Loop", "Ghost"),
}

_ARCHETYPE_SUFFIXES = {
    PlayerArchetype.THROWER: ("Shot", "Line", "Eye", "Lock", "Mark", "Aim", "Strike", "Target"),
    PlayerArchetype.CATCHER: ("Hands", "Trap", "Net", "Hook", "Grip", "Catch", "Snatch", "Reel"),
    PlayerArchetype.BALL_HAWK: ("Wall", "Tank", "Forge", "Guard", "Plate", "Shield", "Dome", "Citadel"),
    PlayerArchetype.DODGER_ANCHOR: ("Step", "Mist", "Glide", "Fade", "Wind", "Trace", "Pass", "Whisper"),
    PlayerArchetype.THROWER_CATCHER: ("Wave", "Spark", "Flux", "Charge", "Current", "Surge", "Volt", "Arc"),
    PlayerArchetype.THROWER_DODGER: ("Rush", "Burst", "Flash", "Spiral", "Swing", "Strike", "Counter", "Volt"),
    PlayerArchetype.CATCHER_HAWK: ("Hook", "Field", "Snatch", "Grid", "Clamp", "Current", "Orbit", "Latch"),
    PlayerArchetype.HAWK_DODGER: ("Loop", "Shade", "Trace", "Slip", "Mist", "Ghost", "Whisper", "Drift"),
}


def classify_archetype(player: Player) -> str:
    return player.archetype.display_name


def generate_nickname(player: Player, rng: DeterministicRNG) -> str:
    """Generate a deterministic nickname using the caller-provided RNG."""
    archetype = player.archetype
    prefix = _seeded_choice(
        _ARCHETYPE_PREFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype.value}:prefix",
    )
    suffix = _seeded_choice(
        _ARCHETYPE_SUFFIXES[archetype],
        rng,
        f"{player.id}:{player.name}:{archetype.value}:suffix",
    )
    last_name = _last_name_token(player.name)
    style_roll = _seeded_index(rng, f"{player.id}:{player.name}:{archetype.value}:style", 3)
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
        title=_ARCHETYPE_TITLES[player.archetype],
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
