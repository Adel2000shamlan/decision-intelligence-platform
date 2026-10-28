from uuid import uuid4

import pytest

from app.modules.authentication.security import (
    CredentialService,
    PasswordResetService,
    TokenService,
    TokenType,
    TokenError,
)


def test_reset_revocation_failure_does_not_leave_old_password_active():
    user_id = uuid4()
    credentials = CredentialService()
    credentials.register(user_id, "OriginalStrong123!")

    tokens = TokenService()
    access_token, refresh_token = tokens.issue(user_id)

    service = PasswordResetService(credentials, tokens=tokens)
    reset_token = service.request(user_id)

    def fail_revocation(_user_id):
        raise RuntimeError("simulated token revocation failure")

    tokens.revoke_user = fail_revocation

    with pytest.raises(RuntimeError, match="simulated token revocation failure"):
        service.consume(reset_token, "ReplacementStrong456!")

    # The desired invariant: a failed reset must not leave a mixed state.
    assert credentials.verify(user_id, "OriginalStrong123!"), (
        "Original password should remain active if reset fails"
    )
    assert not credentials.verify(user_id, "ReplacementStrong456!"), (
        "Replacement password must not become active after failed reset"
    )
    assert tokens.validate(access_token)
    assert tokens.validate(refresh_token, expected=TokenType.REFRESH)
    assert service.reset.lookup(reset_token) == user_id

def test_reset_partial_revocation_failure_keeps_old_password():
    user_id = uuid4()
    credentials = CredentialService()
    credentials.register(user_id, "OriginalStrong123!")

    tokens = TokenService()
    access_token, refresh_token = tokens.issue(user_id)
    service = PasswordResetService(credentials, tokens=tokens)
    reset_token = service.request(user_id)

    original_revoke_user = tokens.revoke_user

    def revoke_then_fail(target_user_id):
        original_revoke_user(target_user_id)
        raise RuntimeError("simulated failure after revocation")

    tokens.revoke_user = revoke_then_fail

    with pytest.raises(RuntimeError, match="simulated failure after revocation"):
        service.consume(reset_token, "ReplacementStrong456!")

    assert credentials.verify(user_id, "OriginalStrong123!")
    assert not credentials.verify(user_id, "ReplacementStrong456!")
    assert service.reset.lookup(reset_token) == user_id

    with pytest.raises(TokenError):
        tokens.validate(access_token)

    with pytest.raises(TokenError):
        tokens.validate(refresh_token, expected=TokenType.REFRESH)
