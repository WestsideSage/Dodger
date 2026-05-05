from __future__ import annotations

import re

_RAW_ID_RE = re.compile(r"\b[a-z]{2,}_\d{1,4}\b")
_TEMPLATE_RE = re.compile(r"(\{[^}]+\}|<[^>]+>)")
_ACRONYMS = {"mvp": "MVP", "ovr": "OVR", "rng": "RNG", "hof": "HOF"}


def has_unresolved_token(text: str) -> bool:
    """Return True when player-facing copy contains a raw system ID or unresolved template placeholder.

    Call only on label text (award names, player names in reports), not on
    internal IDs, match IDs, or log output.
    """
    return bool(_RAW_ID_RE.search(text) or _TEMPLATE_RE.search(text))


def title_label(text: str) -> str:
    """Normalize compact UI labels while preserving known league acronyms."""
    words = str(text).replace("_", " ").split()
    return " ".join(_ACRONYMS.get(word.lower(), word.capitalize()) for word in words)


__all__ = ["has_unresolved_token", "title_label"]
