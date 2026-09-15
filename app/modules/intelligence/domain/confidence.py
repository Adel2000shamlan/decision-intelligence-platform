from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Confidence:
    value: float
    basis: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)):
            raise ValueError("confidence value must be numeric")

        value = float(self.value)
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence value must be between 0 and 1")

        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("confidence basis is required")

        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", self.basis.strip())
