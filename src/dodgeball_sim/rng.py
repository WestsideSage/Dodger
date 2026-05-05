from __future__ import annotations

import hashlib
import random
from typing import List, Sequence, Tuple, TypeVar

T = TypeVar("T")


class DeterministicRNG:
    """Thin wrapper to keep RNG access explicit and auditable."""

    def __init__(self, seed: int):
        self._seed = int(seed)
        self._random = random.Random(self._seed)

    @property
    def seed(self) -> int:
        return self._seed

    def unit(self) -> float:
        """Return a float in [0,1) in deterministic order."""

        return self._random.random()

    def roll(self, low: float, high: float) -> float:
        return low + (high - low) * self.unit()

    def gauss(self, mu: float, sigma: float) -> float:
        return self._random.gauss(mu, sigma)

    def choice(self, items: Sequence[T]) -> T:
        if not items:
            raise ValueError("Cannot choose from empty sequence")
        idx = int(self.unit() * len(items))
        idx = min(idx, len(items) - 1)
        return items[idx]

    def shuffle(self, items: List[T]) -> List[T]:
        result = list(items)
        self._random.shuffle(result)
        return result


def derive_seed(root_seed: int, namespace: str, *ids: str) -> int:
    """Derive a deterministic namespaced seed from a root seed.

    Adding a new namespace never changes seeds from other namespaces.
    Same inputs always produce the same output.
    """
    key = f"{root_seed}:{namespace}:{':'.join(ids)}"
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2 ** 63)


__all__ = ["DeterministicRNG", "derive_seed"]