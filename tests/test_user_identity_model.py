from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.identity.domain.models import User, UserCreated, UserStatus
from app.shared.domain.errors import InvalidDomainData


def test_user_identity_normalizes_email_and_name() -> None:
    user = User.create(" USER@Example.COM ", "  Adel Shamlan  ")
    assert user.email_address == "user@example.com"
    assert user.name == "Adel Shamlan"
    assert user.status is UserStatus.ACTIVE
    assert user.version == 1


def test_user_identity_has_stable_uuid_and_creation_event() -> None:
    actor = uuid4()
    user = User.create("user@example.com", "User", actor_id=actor)
    events = user.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], UserCreated)
    assert events[0].aggregate_id == user.id
    assert events[0].actor_id == actor


def test_user_identity_rejects_invalid_email() -> None:
    with pytest.raises(InvalidDomainData):
        User("not-an-email", "User")


def test_user_identity_rejects_invalid_status() -> None:
    with pytest.raises(InvalidDomainData):
        User("user@example.com", "User", status="deleted")


def test_user_identity_invariants_and_timestamp_boundary() -> None:
    now = datetime.now(timezone.utc)
    user = User("user@example.com", "User", created_at=now, updated_at=now)
    user.validate_invariants()


def test_user_identity_does_not_contain_credentials_or_tokens() -> None:
    user = User("user@example.com", "User")
    assert not hasattr(user, "password")
    assert not hasattr(user, "password_hash")
    assert not hasattr(user, "access_token")
    assert not hasattr(user, "refresh_token")
