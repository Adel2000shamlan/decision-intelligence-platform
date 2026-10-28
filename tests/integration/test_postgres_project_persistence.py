"""PostgreSQL acceptance tests for project persistence and tenant isolation."""
from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.modules.project.domain.models import Project
from app.modules.project.persistence.postgres import (
    PostgreSQLProjectRepository,
    ProjectConcurrencyError,
    ProjectNotFound,
)

DATABASE_URL = os.getenv("DATABASE_URL", "")
requires_postgres = pytest.mark.skipif(
    not DATABASE_URL.startswith(("postgresql://", "postgres://")),
    reason="requires a real PostgreSQL DATABASE_URL",
)


@requires_postgres
def test_project_persistence_and_cross_tenant_update_protection():
    repository = PostgreSQLProjectRepository(DATABASE_URL)
    token = uuid4().hex
    organization_id = uuid4()
    other_organization_id = uuid4()
    project = Project(
        organization_id=organization_id,
        name=f"project-{token}",
    )
    inserted = False

    try:
        repository.save(project, expected_version=0)
        inserted = True

        independent = PostgreSQLProjectRepository(DATABASE_URL)
        loaded = independent.get_by_id(project.id, organization_id)

        assert loaded is not None
        assert loaded.name == project.name
        assert loaded.version == 1
        assert independent.get_by_id(
            project.id, other_organization_id
        ) is None

        spoofed = Project(
            organization_id=other_organization_id,
            name=f"spoof-{token}",
            id=project.id,
            version=1,
        )

        with pytest.raises(ProjectNotFound):
            independent.save(spoofed, expected_version=1)

        preserved = repository.get_by_id(project.id, organization_id)
        assert preserved is not None
        assert preserved.organization_id == organization_id
        assert preserved.name == project.name
        assert preserved.version == 1
    finally:
        if inserted:
            repository.delete(project.id, organization_id)


@requires_postgres
def test_project_rejects_stale_update_between_repositories():
    repository = PostgreSQLProjectRepository(DATABASE_URL)
    token = uuid4().hex
    organization_id = uuid4()
    project = Project(
        organization_id=organization_id,
        name=f"version-{token}",
    )
    inserted = False

    try:
        repository.save(project, expected_version=0)
        inserted = True

        first = PostgreSQLProjectRepository(DATABASE_URL)
        second = PostgreSQLProjectRepository(DATABASE_URL)

        current_copy = first.get_by_id(project.id, organization_id)
        stale_copy = second.get_by_id(project.id, organization_id)

        assert current_copy is not None
        assert stale_copy is not None

        current_copy.rename(f"updated-{token}")
        first.save(current_copy, expected_version=1)

        stale_copy.rename(f"stale-{token}")
        with pytest.raises(ProjectConcurrencyError):
            second.save(stale_copy, expected_version=1)

        final = repository.get_by_id(project.id, organization_id)
        assert final is not None
        assert final.name == f"updated-{token}"
        assert final.version == 2
    finally:
        if inserted:
            repository.delete(project.id, organization_id)
