from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

from app.modules.authentication.security import TokenService, TokenType, TokenError


def test_refresh_token_can_only_be_rotated_once_concurrently():
    tokens = TokenService()
    _, old_refresh = tokens.issue(uuid4())

    original_refresh = tokens.refresh
    barrier = Barrier(2)

    def synchronized_refresh(raw, roles=None):
        if raw == old_refresh:
            barrier.wait(timeout=5)
        return original_refresh(raw, roles=roles)

    tokens.refresh = synchronized_refresh

    def attempt_refresh():
        try:
            tokens.refresh(old_refresh)
            return "success"
        except TokenError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt_refresh(), range(2)))

    assert results.count("success") == 1, results
    assert results.count("rejected") == 1, results

    # The original refresh token must remain unusable.
    with __import__("pytest").raises(TokenError):
        tokens.validate(old_refresh, TokenType.REFRESH)


def test_user_revocation_serializes_with_refresh():
    tokens = TokenService()
    user_id = uuid4()
    _, old_refresh = tokens.issue(user_id)

    validated = Event()
    allow_refresh_to_continue = Event()
    revocation_started = Event()
    original_validate = tokens.validate
    original_revoke_user = tokens.revoke_user

    def paused_validate(raw, expected=TokenType.ACCESS):
        record = original_validate(raw, expected)
        if raw == old_refresh and expected is TokenType.REFRESH:
            validated.set()
            assert allow_refresh_to_continue.wait(timeout=10)
        return record

    def synchronized_revoke_user(target_user_id):
        revocation_started.set()
        return original_revoke_user(target_user_id)

    tokens.validate = paused_validate
    tokens.revoke_user = synchronized_revoke_user

    with ThreadPoolExecutor(max_workers=2) as pool:
        refresh_future = pool.submit(tokens.refresh, old_refresh)

        try:
            assert validated.wait(timeout=5), "refresh did not reach validation"
            revoke_future = pool.submit(tokens.revoke_user, user_id)
            assert revocation_started.wait(timeout=5), "revocation did not start"
        finally:
            allow_refresh_to_continue.set()

        result = refresh_future.result(timeout=5)
        revoke_future.result(timeout=5)

    assert result["token_type"] == "bearer"

    with __import__("pytest").raises(TokenError):
        tokens.validate(result["access_token"], TokenType.ACCESS)

    with __import__("pytest").raises(TokenError):
        tokens.validate(result["refresh_token"], TokenType.REFRESH)
