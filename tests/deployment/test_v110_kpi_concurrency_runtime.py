import os
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.kpi.domain.models import KPI
from app.modules.kpi.persistence.postgres import PostgreSQLKPIRepository


def test_postgres_kpi_optimistic_concurrency():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL is required for PostgreSQL integration test")
    repo = PostgreSQLKPIRepository(dsn)

    tenant = uuid4()
    now = datetime.now(timezone.utc)

    kpi = KPI(
        uuid4(), tenant, "V110 KPI Concurrency", "percent",
        100.0, 50.0, None, now, now, 1
    )
    repo.save(kpi)

    updated = KPI(
        kpi.id, kpi.tenant_id, kpi.name, kpi.unit,
        kpi.target, 60.0, kpi.project_id, kpi.created_at,
        datetime.now(timezone.utc), 2
    )
    repo.save(updated)

    stale = KPI(
        kpi.id, kpi.tenant_id, kpi.name, kpi.unit,
        kpi.target, 70.0, kpi.project_id, kpi.created_at,
        datetime.now(timezone.utc), 2
    )

    try:
        repo.save(stale)
    except RuntimeError as exc:
        assert "optimistic concurrency conflict" in str(exc)
    else:
        raise AssertionError("stale KPI update was incorrectly accepted")
