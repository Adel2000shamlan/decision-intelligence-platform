"""Immutable, validated domain value objects.

These objects deliberately contain validation and normalization only. They have no
persistence, API, or infrastructure concerns, making them safe to reuse across
all domain modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from .errors import InvalidDomainData


_DECIMAL_ZERO = Decimal("0")
_MONEY_QUANT = Decimal("0.01")
_PERCENT_QUANT = Decimal("0.01")


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise InvalidDomainData(f"{field} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise InvalidDomainData(f"{field} must be numeric") from None
    if not result.is_finite():
        raise InvalidDomainData(f"{field} must be finite")
    return result


def _text(value: Any, field: str, max_length: int = 300) -> str:
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field} must be a string")
    value = value.strip()
    if not value:
        raise InvalidDomainData(f"{field} is required")
    if len(value) > max_length:
        raise InvalidDomainData(f"{field} exceeds {max_length} characters")
    return value


@dataclass(frozen=True, slots=True)
class Money:
    """Non-negative monetary amount with a three-letter ISO-style currency code."""

    amount: Decimal
    currency: str = "EGP"

    def __post_init__(self) -> None:
        amount = _decimal(self.amount, "amount").quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        currency = self.currency.strip().upper() if isinstance(self.currency, str) else ""
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise InvalidDomainData("currency must be a three-letter code")
        if amount < _DECIMAL_ZERO:
            raise InvalidDomainData("amount must be >= 0")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)

    @classmethod
    def zero(cls, currency: str = "EGP") -> "Money":
        return cls(Decimal("0.00"), currency)

    def add(self, other: "Money") -> "Money":
        self._same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        self._same_currency(other)
        result = self.amount - other.amount
        if result < 0:
            raise InvalidDomainData("money subtraction cannot produce a negative amount")
        return Money(result, self.currency)

    def multiply(self, factor: Any) -> "Money":
        factor_d = _decimal(factor, "factor")
        if factor_d < 0:
            raise InvalidDomainData("factor must be >= 0")
        return Money(self.amount * factor_d, self.currency)

    def _same_currency(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise InvalidDomainData("money operation requires Money")
        if self.currency != other.currency:
            raise InvalidDomainData("currency mismatch")

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True, slots=True)
class Probability:
    """Probability represented as a decimal fraction in [0, 1]."""

    value: float

    def __post_init__(self) -> None:
        value = _decimal(self.value, "probability")
        if not Decimal("0") <= value <= Decimal("1"):
            raise InvalidDomainData("probability must be 0..1")
        object.__setattr__(self, "value", float(value))

    @property
    def percentage(self) -> float:
        return self.value * 100.0

    @classmethod
    def from_percentage(cls, value: Any) -> "Probability":
        pct = _decimal(value, "probability percentage")
        if not Decimal("0") <= pct <= Decimal("100"):
            raise InvalidDomainData("probability percentage must be 0..100")
        return cls(float(pct / Decimal("100")))


@dataclass(frozen=True, slots=True)
class Percentage:
    """Percentage represented on the domain's human-facing 0..100 scale."""

    value: Decimal

    def __post_init__(self) -> None:
        value = _decimal(self.value, "percentage").quantize(_PERCENT_QUANT, rounding=ROUND_HALF_UP)
        if not Decimal("0") <= value <= Decimal("100"):
            raise InvalidDomainData("percentage must be 0..100")
        object.__setattr__(self, "value", value)

    @classmethod
    def from_fraction(cls, fraction: Any) -> "Percentage":
        value = _decimal(fraction, "fraction")
        if not Decimal("0") <= value <= Decimal("1"):
            raise InvalidDomainData("fraction must be 0..1")
        return cls(value * Decimal("100"))

    @property
    def fraction(self) -> Decimal:
        return self.value / Decimal("100")


@dataclass(frozen=True, slots=True)
class Score:
    """Bounded score, normally used for health/readiness/performance metrics."""

    value: Decimal
    minimum: Decimal = Decimal("0")
    maximum: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        value = _decimal(self.value, "score")
        minimum = _decimal(self.minimum, "score minimum")
        maximum = _decimal(self.maximum, "score maximum")
        if minimum >= maximum:
            raise InvalidDomainData("score minimum must be less than maximum")
        if not minimum <= value <= maximum:
            raise InvalidDomainData(f"score must be {minimum}..{maximum}")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    @classmethod
    def health(cls, value: Any) -> "Score":
        return cls(value, Decimal("0"), Decimal("100"))

    @property
    def normalized(self) -> float:
        return float((self.value - self.minimum) / (self.maximum - self.minimum))


@dataclass(frozen=True, slots=True)
class NonNegativeNumber:
    """Finite number constrained to be >= 0."""

    value: Decimal

    def __post_init__(self) -> None:
        value = _decimal(self.value, "value")
        if value < 0:
            raise InvalidDomainData("value must be >= 0")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class Identifier:
    """Validated UUID wrapper for domain boundaries."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, "value", UUID(str(self.value)))
            except (ValueError, AttributeError, TypeError):
                raise InvalidDomainData("identifier must be a valid UUID") from None


@dataclass(frozen=True, slots=True)
class Name:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _text(self.value, "name", 200))


@dataclass(frozen=True, slots=True)
class Description:
    value: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidDomainData("description must be a string")
        value = self.value.strip()
        if len(value) > 2000:
            raise InvalidDomainData("description exceeds 2000 characters")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class Slug:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower() if isinstance(self.value, str) else ""
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise InvalidDomainData("slug must contain lowercase letters, numbers and single hyphens")
        if len(value) > 100:
            raise InvalidDomainData("slug exceeds 100 characters")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower() if isinstance(self.value, str) else ""
        if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise InvalidDomainData("invalid email address")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class URL:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip() if isinstance(self.value, str) else ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise InvalidDomainData("URL must use http or https and contain a host")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive calendar date range."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or isinstance(self.start, datetime):
            raise InvalidDomainData("start must be a date")
        if not isinstance(self.end, date) or isinstance(self.end, datetime):
            raise InvalidDomainData("end must be a date")
        if self.end < self.start:
            raise InvalidDomainData("end cannot precede start")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end
