from dataclasses import dataclass
from typing import Any
class ConcurrencyError(RuntimeError): pass
class DuplicateError(RuntimeError): pass
class NotFoundError(LookupError): pass
@dataclass(frozen=True)
class RepositoryResult:
    entity: Any
    version: int
