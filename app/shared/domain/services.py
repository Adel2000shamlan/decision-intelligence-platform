from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from uuid import UUID
from .errors import BusinessRuleViolation, EntityNotFound

T = TypeVar('T')

class DomainService(Protocol):
    """Marker contract: domain services coordinate domain behavior without infrastructure."""

@dataclass(frozen=True, slots=True)
class ServiceResult(Generic[T]):
    entity: T
    events: tuple[object, ...] = ()

class DomainServiceBase:
    """Small framework-independent base for deterministic domain orchestration."""
    @staticmethod
    def require(found: T | None, entity_name: str, entity_id: UUID) -> T:
        if found is None:
            raise EntityNotFound(f'{entity_name} not found: {entity_id}')
        return found

    @staticmethod
    def collect(entity: T) -> ServiceResult[T]:
        pull = getattr(entity, 'pull_events', None)
        events = tuple(pull()) if callable(pull) else ()
        return ServiceResult(entity, events)

    @staticmethod
    def ensure_version(entity: object, expected_version: int | None) -> None:
        if expected_version is not None:
            checker = getattr(entity, 'assert_version', None)
            if callable(checker):
                checker(expected_version)
            elif getattr(entity, 'version', None) != expected_version:
                raise BusinessRuleViolation('optimistic concurrency conflict')

class RiskScoreService:
    def calculate(self, probability, impact):
        if not 0 <= probability <= 1 or impact < 0:
            raise BusinessRuleViolation('invalid risk inputs')
        return probability * impact

class DecisionReadinessService:
    def evaluate(self, decision):
        required=('objective','options','scenarios','risks')
        return all(getattr(decision,k,None) for k in required)
