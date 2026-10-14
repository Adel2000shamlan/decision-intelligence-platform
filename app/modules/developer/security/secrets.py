from __future__ import annotations

from dataclasses import dataclass
import secrets

from app.modules.authentication.security import (
    PasswordHash,
    PasswordHasher,
    PasswordSecurityPolicy,
)


@dataclass(frozen=True)
class DeveloperSecret:
    raw: str
    hash: PasswordHash


class DeveloperSecretHasher:
    """
    Security boundary for long-lived Developer API client secrets.

    Raw secrets are generated only at creation/rotation time.
    Persistent storage must contain only the PasswordHash representation.
    """

    def __init__(
        self,
        hasher: PasswordHasher | None = None,
    ) -> None:
        self.hasher = hasher or PasswordHasher(
            PasswordSecurityPolicy(
                min_length=32,
                max_length=128,
                iterations=310_000,
                salt_bytes=16,
            )
        )

    def generate(self) -> DeveloperSecret:
        raw = secrets.token_urlsafe(48)
        return DeveloperSecret(
            raw=raw,
            hash=self.hasher.hash(raw),
        )

    def verify(
        self,
        raw: str,
        stored: PasswordHash,
    ) -> bool:
        if not isinstance(raw, str):
            return False
        return self.hasher.verify(raw, stored)

    def encode(self, stored: PasswordHash) -> str:
        return stored.encoded()

    def decode(self, encoded: str) -> PasswordHash:
        if not isinstance(encoded, str):
            raise ValueError("encoded secret hash must be text")

        parts = encoded.split("$")
        if len(parts) != 4:
            raise ValueError("invalid encoded secret hash")

        algorithm, iterations, salt, digest = parts

        if algorithm != "pbkdf2_sha256":
            raise ValueError("unsupported secret hash algorithm")

        try:
            parsed_iterations = int(iterations)
        except ValueError as exc:
            raise ValueError("invalid secret hash iterations") from exc

        if parsed_iterations < 1:
            raise ValueError("invalid secret hash iterations")

        if not salt or not digest:
            raise ValueError("invalid encoded secret hash")

        return PasswordHash(
            algorithm=algorithm,
            iterations=parsed_iterations,
            salt=salt,
            digest=digest,
        )
