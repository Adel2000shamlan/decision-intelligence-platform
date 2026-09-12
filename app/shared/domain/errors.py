class DomainError(Exception):
    """Base class for errors originating in the domain layer."""


class InvalidDomainData(DomainError): pass
class InvalidStateTransition(DomainError): pass
class BusinessRuleViolation(DomainError): pass
class EntityNotFound(DomainError): pass
class UnauthorizedDomainAction(DomainError): pass
