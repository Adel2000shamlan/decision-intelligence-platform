from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import BenchmarkDefinition, BenchmarkObservation
from .mappers import (
    definition_from_row,
    definition_to_row,
    observation_from_row,
    observation_to_row,
)
from .repository import BenchmarkingRepository


class PostgresBenchmarkingRepository(BenchmarkingRepository):
    """PostgreSQL persistence for tenant-scoped benchmarking data."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_definitions (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    metric TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    methodology TEXT NOT NULL,
                    source TEXT NOT NULL,
                    minimum_observations INTEGER NOT NULL,
                    UNIQUE (tenant_id, id)
                );

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_definitions_tenant
                ON benchmark_definitions (tenant_id);

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_definitions_tenant_metric
                ON benchmark_definitions (tenant_id, metric);

                CREATE TABLE IF NOT EXISTS benchmark_observations (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    definition_id UUID NOT NULL,
                    peer_group TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    evidence_id UUID,
                    observed_at TIMESTAMPTZ NOT NULL,
                    FOREIGN KEY (tenant_id, definition_id)
                        REFERENCES benchmark_definitions(tenant_id, id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_observations_tenant
                ON benchmark_observations (tenant_id);

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_observations_tenant_definition
                ON benchmark_observations (tenant_id, definition_id);

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_observations_tenant_peer
                ON benchmark_observations (tenant_id, peer_group);

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_observations_tenant_metric
                ON benchmark_observations (tenant_id, metric);

                CREATE INDEX IF NOT EXISTS
                idx_benchmark_observations_tenant_observed_at
                ON benchmark_observations (tenant_id, observed_at);
                """
            )
        self._connection.commit()

    def save_definition(
        self,
        definition: BenchmarkDefinition,
    ) -> BenchmarkDefinition:
        if not isinstance(definition, BenchmarkDefinition):
            raise BusinessRuleViolation(
                "definition must be a BenchmarkDefinition"
            )

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    definition_to_row(definition),
                )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "duplicate benchmark definition"
            ) from exc

        return definition

    def get_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> BenchmarkDefinition | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM benchmark_definitions
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, definition_id),
            )
            row = cursor.fetchone()

        return None if row is None else definition_from_row(row)

    def list_definitions(
        self,
        tenant_id: UUID,
    ) -> tuple[BenchmarkDefinition, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM benchmark_definitions
                WHERE tenant_id = %s
                ORDER BY id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()

        return tuple(definition_from_row(row) for row in rows)

    def delete_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM benchmark_definitions
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, definition_id),
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
            with self._connection.cursor() as cursor:
                cursor.execute(
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
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    observation_to_row(observation),
                )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "duplicate benchmark observation"
            ) from exc

        return observation

    def get_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> BenchmarkObservation | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM benchmark_observations
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, observation_id),
            )
            row = cursor.fetchone()

        return None if row is None else observation_from_row(row)

    def list_observations(
        self,
        tenant_id: UUID,
        *,
        definition_id: UUID | None = None,
        peer_group: str | None = None,
        metric: str | None = None,
    ) -> tuple[BenchmarkObservation, ...]:
        clauses = ["tenant_id = %s"]
        parameters: list[object] = [tenant_id]

        if definition_id is not None:
            clauses.append("definition_id = %s")
            parameters.append(definition_id)

        if peer_group is not None:
            clauses.append("peer_group = %s")
            parameters.append(peer_group)

        if metric is not None:
            clauses.append("metric = %s")
            parameters.append(metric)

        query = f"""
            SELECT *
            FROM benchmark_observations
            WHERE {' AND '.join(clauses)}
            ORDER BY observed_at, id
        """

        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, tuple(parameters))
            rows = cursor.fetchall()

        return tuple(observation_from_row(row) for row in rows)

    def delete_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM benchmark_observations
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, observation_id),
            )
        self._connection.commit()
