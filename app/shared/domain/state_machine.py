from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Mapping, TypeVar

from .errors import InvalidStateTransition

S = TypeVar('S')

@dataclass(frozen=True, slots=True)
class Transition:
    source: str
    target: str

class StateMachine(Generic[S]):
    """Small deterministic state-machine engine. It never mutates the aggregate."""
    def __init__(self, transitions: Mapping[S, frozenset[S] | set[S] | tuple[S, ...]], terminal: frozenset[S] | set[S] = frozenset()):
        self._transitions = {s: frozenset(ts) for s, ts in transitions.items()}
        self._terminal = frozenset(terminal)

    def allowed_targets(self, current: S) -> frozenset[S]:
        return self._transitions.get(current, frozenset())

    def is_terminal(self, current: S) -> bool:
        return current in self._terminal or not self.allowed_targets(current)

    def can_transition(self, current: S, target: S) -> bool:
        return target in self.allowed_targets(current)

    def transition(self, current: S, target: S) -> S:
        if not self.can_transition(current, target):
            raise InvalidStateTransition(f'{current!s}->{target!s} not allowed')
        return target


def validate_transition_graph(machine: StateMachine[S]) -> None:
    """Reject dangling targets and self-loops unless explicitly represented."""
    states = set(machine._transitions)
    for source, targets in machine._transitions.items():
        missing = set(targets) - states
        if missing:
            raise ValueError(f'dangling transition targets from {source!s}: {missing!r}')

# Compatibility helper retained for earlier callers.
TRANSITIONS = {
    'decision': {'draft': {'validated','cancelled'}, 'validated': {'submitted','cancelled'}, 'submitted': {'approved','rejected','cancelled'}, 'rejected': {'draft','cancelled'}, 'approved': {'active','archived'}, 'active': {'completed','archived'}, 'completed': {'archived'}},
    'project': {'draft': {'active','cancelled'}, 'active': {'completed','archived'}, 'completed': {'archived'}},
    'execution': {'planned': {'active','cancelled'}, 'active': {'paused','completed','cancelled'}, 'paused': {'active','cancelled'}, 'completed': {'archived'}},
}
def transition(kind, current, target):
    targets = TRANSITIONS.get(kind, {}).get(current, set())
    if target not in targets:
        raise InvalidStateTransition(f'{kind}: {current}->{target} not allowed')
    return target
