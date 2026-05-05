from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping


@dataclass(frozen=True)
class RuleSetOverrides:
    catch_revival_enabled: bool | None = None
    balls_in_play: int | None = None
    shot_clock_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.balls_in_play is not None and self.balls_in_play < 1:
            raise ValueError("balls_in_play must be at least 1 when overridden")
        if self.shot_clock_seconds is not None and self.shot_clock_seconds < 1:
            raise ValueError("shot_clock_seconds must be at least 1 when overridden")

    def explicit_values(self) -> dict[str, bool | int]:
        values: dict[str, bool | int] = {}
        if self.catch_revival_enabled is not None:
            values["catch_revival_enabled"] = self.catch_revival_enabled
        if self.balls_in_play is not None:
            values["balls_in_play"] = self.balls_in_play
        if self.shot_clock_seconds is not None:
            values["shot_clock_seconds"] = self.shot_clock_seconds
        return values

    def has_overrides(self) -> bool:
        return bool(self.explicit_values())

    def apply_to(self, base_ruleset: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(base_ruleset)
        merged.update(self.explicit_values())
        return merged


@dataclass(frozen=True)
class MetaPatch:
    patch_id: str
    season_id: str
    name: str
    description: str
    power_stamina_cost_modifier: float = 0.0
    dodge_penalty_modifier: float = 0.0
    fatigue_rate_modifier: float = 0.0
    ruleset_overrides: RuleSetOverrides = field(default_factory=RuleSetOverrides)

    def __post_init__(self) -> None:
        if not self.patch_id.strip():
            raise ValueError("patch_id must not be blank")
        if not self.season_id.strip():
            raise ValueError("season_id must not be blank")
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.description.strip():
            raise ValueError("description must not be blank")

        for field_name in (
            "power_stamina_cost_modifier",
            "dodge_penalty_modifier",
            "fatigue_rate_modifier",
        ):
            value = getattr(self, field_name)
            if not isfinite(value):
                raise ValueError(f"{field_name} must be finite")
            if value <= -1.0:
                raise ValueError(f"{field_name} must be greater than -1.0")

    def modifier_summary(self) -> dict[str, float]:
        return {
            "power_stamina_cost_modifier": self.power_stamina_cost_modifier,
            "dodge_penalty_modifier": self.dodge_penalty_modifier,
            "fatigue_rate_modifier": self.fatigue_rate_modifier,
        }

    def context_payload(self) -> dict[str, Any]:
        return {
            "meta_patch_id": self.patch_id,
            "meta_patch_name": self.name,
            "modifiers": self.modifier_summary(),
            "ruleset_overrides": self.ruleset_overrides.explicit_values(),
        }

    def apply_ruleset(self, base_ruleset: Mapping[str, Any]) -> dict[str, Any]:
        return self.ruleset_overrides.apply_to(base_ruleset)


__all__ = ["MetaPatch", "RuleSetOverrides"]
