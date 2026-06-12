"""V22 Phase 4 — every department head's rating wired to a real effect.

Owner: "go further: wire all six." Before this, only the TRAINING head's
rating did anything mechanical; the other five were advisory surfaces, which
is exactly why staff felt useless from the jump.

One module owns the rating→effect formulas so the engine, the staff tab,
the hiring cards, and the Program Settings copy all read the SAME numbers:

- tactics      → scales the tactics-focus week's effective-TIQ bonus
- conditioning → scales the conditioning-focus week's fatigue-drag relief
- culture      → scales the culture-focus week's courtship-gain multiplier
- scouting     → scales how tightly a Scout action narrows a prospect's band
- medical      → mitigates age-decline in the offseason (recovery fiction)
- training     → offseason development modifier (pre-existing, anchored here)

Every formula is linear in the head's PRIMARY rating, anchored so the
DEFAULT heads land on the legacy flat numbers the game already disclosed
(+18 TIQ, drag halved, ×1.25 courtship, 0.4 band narrowing), and clamped to
a disclosed range. AI clubs have no head table — their preps keep the legacy
flat numbers, which these anchors make equivalent to ~rating-7x staff
(disclosed in the rules copy as "abstracted").
"""
from __future__ import annotations

from .config import DEFAULT_CONFIG


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def tactics_focus_tiq_bonus(rating_primary: float) -> float:
    """Effective-TIQ bonus on a tactics-focus week: 12–24 (default 74 → ~17.8)."""
    return _clamp(12.0 + (float(rating_primary) - 50.0) * 0.24, 12.0, 24.0)


def conditioning_focus_relief(rating_primary: float) -> float:
    """Fatigue-drag relief fraction on a conditioning-focus week: 0.30–0.70
    (default 69 → ~0.45; the legacy flat was 0.50)."""
    return _clamp(0.30 + (float(rating_primary) - 50.0) * 0.008, 0.30, 0.70)


def culture_focus_interest_multiplier(rating_primary: float) -> float:
    """Contact/Visit gain multiplier on a culture-focus week: 1.15–1.40
    (default 68 → 1.24; the legacy flat was 1.25)."""
    return round(_clamp(1.15 + (float(rating_primary) - 50.0) * 0.005, 1.15, 1.40), 3)


def scouting_band_quality(rating_primary: float) -> float:
    """Multiplier on the Scout action's band narrowing: 0.70–1.30
    (default 73 → ~0.98; 1.0 reproduces the legacy narrowing exactly)."""
    return _clamp(0.70 + (float(rating_primary) - 50.0) * 0.012, 0.70, 1.30)


def medical_decline_mitigation(rating_primary: float) -> float:
    """Offseason age-decline mitigation: same shape as the training modifier
    ((rating − 50)/50 × max), consumed by the development decline path."""
    return max(
        0.0,
        (float(rating_primary) - 50.0)
        / 50.0
        * DEFAULT_CONFIG.max_staff_development_modifier,
    )


def training_dev_modifier(rating_primary: float) -> float:
    """Offseason development modifier (pre-existing formula, single home)."""
    return max(
        0.0,
        (float(rating_primary) - 50.0)
        / 50.0
        * DEFAULT_CONFIG.max_staff_development_modifier,
    )


def staff_effect_detail(department: str, rating_primary: float) -> str:
    """The plain-language disclosed number for one head — hiring cards, the
    staff tab, and the founding market all render this string."""
    if department == "tactics":
        return (
            f"Tactics-focus weeks grant +{tactics_focus_tiq_bonus(rating_primary):.0f} "
            "effective Tactical IQ next match (scales 12–24 with this head)."
        )
    if department == "conditioning":
        return (
            f"Conditioning-focus weeks cut the fatigue drag by "
            f"{conditioning_focus_relief(rating_primary) * 100:.0f}% next match "
            "(scales 30–70% with this head)."
        )
    if department == "culture":
        gain_pct = round((culture_focus_interest_multiplier(rating_primary) - 1.0) * 100)
        return (
            f"Culture-focus weeks land Contact/Visit gains +{gain_pct}% stronger "
            "(scales +15% to +40% with this head)."
        )
    if department == "scouting":
        strength_pct = round(scouting_band_quality(rating_primary) * 100)
        return (
            f"Scout actions narrow prospect bands at {strength_pct}% strength "
            "(scales 70% to 130% with this head); scouting-focus weeks still add +1 Scout action."
        )
    if department == "medical":
        return (
            f"Softens veteran age-decline by +{medical_decline_mitigation(rating_primary) * 100:.0f}% "
            "mitigation each offseason (scales with this head)."
        )
    if department == "training":
        return (
            f"+{training_dev_modifier(rating_primary) * 100:.0f}% offseason development "
            "for the whole roster (scales with this head)."
        )
    return "Program recommendations."


__all__ = [
    "conditioning_focus_relief",
    "culture_focus_interest_multiplier",
    "medical_decline_mitigation",
    "scouting_band_quality",
    "staff_effect_detail",
    "tactics_focus_tiq_bonus",
    "training_dev_modifier",
]
