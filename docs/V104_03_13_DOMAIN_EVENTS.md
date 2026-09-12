# V104.03.13 — Domain Events

## Scope
A framework-independent domain-event contract and envelope for events emitted by aggregates.

## Guarantees
- Every event has a stable event id, occurrence time, aggregate id and actor context.
- The envelope records event type, aggregate type/version and correlation/causation metadata.
- Event publication is separated from domain mutation through a publisher port.
- The included publisher is an in-memory test adapter only; no infrastructure transport is assumed.
- Duplicate event ids are ignored by the test publisher, providing deterministic idempotency behavior.
- Existing aggregate event queues remain backward compatible.

## Boundary
This stage does not claim an event bus, outbox, database event store, retries or distributed delivery. Those belong to later infrastructure/event architecture stages.
