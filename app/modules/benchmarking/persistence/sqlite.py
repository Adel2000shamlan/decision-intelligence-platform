from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from .repository import BenchmarkingRepository


class SQLiteBenchmarkingRepository(BenchmarkingRepository):
    """SQLite persistence for tenant-scoped benchmarking data."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS benchmark_definitions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                unit TEXT NOT NULL,
                methodology TEXT NOT NULL,
                source TEXT NOT NULL,
                minimum_observations INTEGER NOT NULL,
                UNIQUE (tenant_id, id)
            );

            CREATE INDEX IF NOT EXISTS idx_benchmark_definitions_tenant
            ON benchmark_definitions (tenant_id);

            CREATE INDEX IF NOT EXISTS idx_benchmark_definitions_tenant_metric
            ON benchmark_definitions (tenant_id, metric);

            CREATE TABLE IF NOT EXISTS benchmark_observations (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                definition_id TEXT NOT NULL,
                peer_group TEXT NOT NULL,
                metric TEXT NOT NULL,
                unit TEXT NOT NULL,
                value REAL NOT NULL,
                status TEXT NOT NULL,
                evidence TEXT NOT NULL,
                evidence_id TEXT,
                observed_at TEXT NOT NULL,
                FOREIGN KEY (tenant_id, definition_id)
                    REFERENCES benchmark_definitions(tenant_id, id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_benchmark_observations_tenant
            ON benchmark_observations (tenant_id);

            CREATE INDEX IF NOT EXISTS idx_benchmark_observations_tenant_definition
            ON benchmark_observations (tenant_id, definition_id);

            CREATE INDEX IF NOT EXISTS idx_benchmark_observations_tenant_peer
            ON benchmark_observations (tenant_id, peer_group);

            CREATE INDEX IF NOT EXISTS idx_benchmark_observations_tenant_metric
            ON benchmark_observations (tenant_id, metric);

            CREATE INDEX IF NOT EXISTS idx_benchmark_observations_tenant_observed_at
            ON benchmark_observations (tenant_id, observed_at);
            """
        )
        self._connection.commit()

    @staticmethod
    def _definition_from_row(
        row: sqlite3.Row,
    ) -> BenchmarkDefinition:
        return BenchmarkDefinition(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            metric=row["metric"],
            unit=row["unit"],
            methodology=row["methodology"],
            source=row["source"],
            minimum_observations=row["minimum_observations"],
        )

    @staticmethod
    def _observation_from_row(
        row: sqlite3.Row,
    ) -> BenchmarkObservation:
        return BenchmarkObservation(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            definition_id=UUID(row["definition_id"]),
            peer_group=row["peer_group"],
            metric=row["metric"],
            unit=row["unit"],
            value=float(row["value"]),
            status=BenchmarkDataStatus(row["status"]),
            evidence=row["evidence"],
            evidence_id=(
                UUID(row["evidence_id"])
                if row["evidence_id"] is not None
                else None
            ),
            observed_at=datetime.fromisoformat(row["observed_at"]),
        )

    def save_definition(
        self,
        definition: BenchmarkDefinition,
    ) -> BenchmarkDefinition:
        if not isinstance(definition, BenchmarkDefinition):
            raise BusinessRuleViolation(
                "definition must be a BenchmarkDefinition"
            )

        try:
            self._connection.execute(
                """
                INSERT INTO benchmark_definitions
                (
                    id,
                    tenant_id,
                    metric,
                    unit,
                    methodology,
                    source,
                    minimum_observations
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(definition.id),
                    str(definition.tenant_id),
                    definition.metric,
                    definition.unit,
                    definition.methodology,
                    definition.source,
                    definition.minimum_observations,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "duplicate benchmark definition"
            ) from exc

        return definition

    def get_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> BenchmarkDefinition | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM benchmark_definitions
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(definition_id)),
        ).fetchone()

        if row is None:
            return None

        return self._definition_from_row(row)

    def list_definitions(
        self,
        tenant_id: UUID,
    ) -> tuple[BenchmarkDefinition, ...]:
        rows = self._connection.execute(
            """
            SELECT *
            FROM benchmark_definitions
            WHERE tenant_id = ?
            ORDER BY id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(
            self._definition_from_row(row)
            for row in rows
        )

    def delete_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> None:
        self._connection.execute(
            """
            DELETE FROM benchmark_definitions
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(definition_id)),
        )
        self._connection.commit()

    def save_observation(
        self,
        observation: BenchmarkObservation,
    ) -> BenchmarkObservation:
        if not isinstance(observation, BenchmarkObservation):
            raise BusinessRuleViolation(
                "observation must be a BenchmarkObservation"
            )

        definition = self.get_definition(
            observation.tenant_id,
            observation.definition_id,
        )

        if definition is None:
            raise BusinessRuleViolation(
                "benchmark definition does not exist"
            )

        try:
            self._connection.execute(
                """
                INSERT INTO benchmark_observations
                (
                    id,
                    tenant_id,
                    definition_id,
                    peer_group,
                    metric,
                    unit,
                    value,
                    status,
                    evidence,
                    evidence_id,
                    observed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(observation.id),
                    str(observation.tenant_id),
                    str(observation.definition_id),
                    observation.peer_group,
                    observation.metric,
                    observation.unit,
                    observation.value,
                    observation.status.value,
                    observation.evidence,
                    (
                        str(observation.evidence_id)
                        if observation.evidence_id is not None
                        else None
                    ),
                    observation.observed_at.isoformat(),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "duplicate benchmark observation"
            ) from exc

        return observation

    def get_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> BenchmarkObservation | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM benchmark_observations
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(observation_id)),
        ).fetchone()

        if row is None:
            return None

        return self._observation_from_row(row)

    def list_observations(
        self,
        tenant_id: UUID,
        *,
        definition_id: UUID | None = None,
        peer_group: str | None = None,
        metric: str | None = None,
    ) -> tuple[BenchmarkObservation, ...]:
        clauses = ["tenant_id = ?"]
        parameters: list[str] = [str(tenant_id)]

        if definition_id is not None:
            clauses.append("definition_id = ?")
            parameters.append(str(definition_id))

        if peer_group is not None:
            clauses.append("peer_group = ?")
            parameters.append(peer_group)

        if metric is not None:
            clauses.append("metric = ?")
            parameters.append(metric)

        query = f"""
            SELECT *
            FROM benchmark_observations
            WHERE {' AND '.join(clauses)}
            ORDER BY observed_at, id
        """

        rows = self._connection.execute(
            query,
            tuple(parameters),
        ).fetchall()

        return tuple(
            self._observation_from_row(row)
            for row in rows
        )

    def delete_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> None:
        self._connection.execute(
            """
            DELETE FROM benchmark_observations
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(observation_id)),
        )
        self._connection.commit()
