from datetime import date
from decimal import Decimal
from uuid import uuid4
import pytest

from app.shared.domain.errors import InvalidDomainData
from app.shared.domain.value_objects import (
    DateRange, Description, EmailAddress, Identifier, Money, Name,
    NonNegativeNumber, Percentage, Probability, Score, Slug, URL,
)


def test_money_normalizes_currency_and_rounds():
    m = Money(Decimal("10.125"), "egp")
    assert m.amount == Decimal("10.13")
    assert m.currency == "EGP"


def test_money_operations_require_same_currency_and_nonnegative_result():
    assert Money("10", "EGP").add(Money("2.25", "EGP")).amount == Decimal("12.25")
    assert Money("10", "EGP").subtract(Money("2", "EGP")).amount == Decimal("8.00")
    with pytest.raises(InvalidDomainData):
        Money("1", "EGP").add(Money("1", "USD"))
    with pytest.raises(InvalidDomainData):
        Money("1", "EGP").subtract(Money("2", "EGP"))


@pytest.mark.parametrize("value", [-1, 1.01, float("nan"), float("inf"), True])
def test_probability_rejects_invalid_values(value):
    with pytest.raises(InvalidDomainData):
        Probability(value)


def test_probability_percentage_conversion():
    p = Probability.from_percentage(25)
    assert p.value == 0.25
    assert p.percentage == 25


def test_percentage_fraction_conversion_and_bounds():
    p = Percentage.from_fraction("0.875")
    assert p.value == Decimal("87.50")
    assert p.fraction == Decimal("0.875")
    with pytest.raises(InvalidDomainData):
        Percentage(101)


def test_score_supports_health_and_normalization():
    s = Score.health("75")
    assert s.value == Decimal("75")
    assert s.normalized == 0.75
    with pytest.raises(InvalidDomainData):
        Score(11, 0, 10)


def test_nonnegative_number_rejects_negative_and_bool():
    assert NonNegativeNumber("12.5").value == Decimal("12.5")
    with pytest.raises(InvalidDomainData):
        NonNegativeNumber(-1)
    with pytest.raises(InvalidDomainData):
        NonNegativeNumber(True)


def test_identifier_accepts_uuid_string_and_is_immutable():
    uid = uuid4()
    assert Identifier(str(uid)).value == uid
    with pytest.raises(Exception):
        Identifier("not-a-uuid")


def test_text_objects_normalize_and_validate():
    assert Name("  Project Alpha  ").value == "Project Alpha"
    assert Description("  hello  ").value == "hello"
    assert Description().value == ""
    with pytest.raises(InvalidDomainData):
        Name("   ")


def test_slug_normalizes_and_rejects_unsafe_forms():
    assert Slug(" My-Project-01 ").value == "my-project-01"
    for value in ["Bad Slug", "-bad", "bad-", "bad--slug", "Bad_Slug"]:
        with pytest.raises(InvalidDomainData):
            Slug(value)


def test_email_and_url_are_validated():
    assert EmailAddress(" User@Example.COM ").value == "user@example.com"
    assert URL("https://example.com/path").value.startswith("https://")
    with pytest.raises(InvalidDomainData):
        EmailAddress("invalid")
    with pytest.raises(InvalidDomainData):
        URL("ftp://example.com")


def test_date_range_is_inclusive():
    r = DateRange(date(2026, 1, 1), date(2026, 1, 3))
    assert r.days == 3
    assert r.contains(date(2026, 1, 2))
    assert not r.contains(date(2026, 1, 4))
    with pytest.raises(InvalidDomainData):
        DateRange(date(2026, 1, 4), date(2026, 1, 3))
