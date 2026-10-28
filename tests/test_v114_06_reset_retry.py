from uuid import uuid4

import pytest

from app.modules.authentication.security import (
    CredentialService,
    PasswordPolicyError,
    PasswordResetService,
    PasswordSecurityPolicy,
)


def test_reset_token_can_be_retried_after_password_policy_rejection():
    user_id = uuid4()
    credentials = CredentialService(
        policy=PasswordSecurityPolicy(min_length=8)
    )
    credentials.register(user_id, "OriginalStrong123!")

    service = PasswordResetService(credentials)
    token = service.request(user_id)

    with pytest.raises(PasswordPolicyError):
        service.consume(token, "weak")

    service.consume(token, "ReplacementStrong456!")

    assert credentials.verify(user_id, "ReplacementStrong456!")
