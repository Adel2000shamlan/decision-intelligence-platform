# V104.03.03 — Project Domain

## Completion sequence
1. V104.03.03.01 Project Entity — completed
2. V104.03.03.02 Project Lifecycle — completed
3. V104.03.03.03 Project Business Rules — completed
4. V104.03.03.04 Project Validation — completed
5. V104.03.03.05 Project Commands — completed
6. V104.03.03.06 Project Events — completed
7. V104.03.03.07 Project Aggregate Boundary — completed
8. V104.03.03.08 Project Repository Contract — completed
9. V104.03.03.09 Project Domain Service — completed
10. V104.03.03.10 Project Domain Errors — completed through shared domain error taxonomy
11. V104.03.03.11 Project Domain Tests — completed
12. V104.03.03.12 Integration Boundary Test — completed
13. V104.03.03.13 Project Definition of Done — completed

## Project lifecycle
- DRAFT -> ACTIVE
- DRAFT -> CANCELLED
- ACTIVE -> COMPLETED
- ACTIVE -> ARCHIVED
- ACTIVE -> CANCELLED
- COMPLETED -> ARCHIVED
- CANCELLED -> ARCHIVED
- ARCHIVED is terminal

## Business rules
- Organization ID is required and must be UUID.
- Project name is required and normalized by trimming.
- Project name has a maximum length of 200 characters.
- A project may be created only under an ACTIVE organization.
- Project names are unique within an organization in the repository policy.
- A real mutation increments version and updates updated_at.
- No-op rename does not increment version.
- Failed lifecycle transitions do not mutate status/version.
- Project owns its state transitions; other domains cannot directly mutate it.

## Commands
- CreateProject
- ActivateProject
- CompleteProject
- ArchiveProject
- CancelProject
- RenameProject

## Events
- ProjectCreated
- ProjectActivated
- ProjectCompleted
- ProjectArchived
- ProjectCancelled
- ProjectRenamed

## Repository contract
- get_by_id
- list_by_organization
- exists_by_name
- save

## Boundary
The Project domain contains no dependency on FastAPI, SQLAlchemy, PostgreSQL, Redis, HTTP clients, or other infrastructure frameworks.
