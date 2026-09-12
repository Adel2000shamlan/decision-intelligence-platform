# Definition of Done — V104.04.01.02

- User lifecycle states are explicitly defined.
- Legal transitions are centralized and graph-validated.
- Illegal transitions are rejected before mutation.
- Terminal archive state is enforced.
- Lifecycle events are emitted with identity, actor and timestamp metadata.
- Aggregate version changes are deterministic.
- Optimistic concurrency is supported by expected version.
- Repository and service boundaries are present.
- Domain invariants and event sequence are validated.
- Lifecycle boundary tests cover legal, illegal, terminal, stale-version and mutation-safety cases.
- Full regression suite passes.
- Python compilation succeeds.
- Release ZIP integrity succeeds.
