from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import LearningObservation, LearningOutcomeType
from .repository import LearningRepository


class PostgresLearningRepository(LearningRepository):
    def __init__(self, connection: psycopg.Connection):
        self.connection = connection
        self._initialize()

    def _initialize(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_observations (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    decision_id UUID NOT NULL,
                    outcome_type TEXT NOT NULL,
                    expected_value DOUBLE PRECISION,
                    actual_value DOUBLE PRECISION,
                    metric TEXT NOT NULL,
                    source TEXT NOT NULL,
                    notes TEXT,
                    observed_at TIMESTAMPTZ NOT NULL,
                    confidence DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL,
                    source_event_id UUID
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE learning_observations
                ADD COLUMN IF NOT EXISTS source_event_id UUID
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_learning_observations_tenant_created
                ON learning_observations(tenant_id, created_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_learning_observations_tenant_decision
                ON learning_observations(tenant_id, decision_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_learning_observations_tenant_metric
                ON learning_observations(tenant_id, metric)
                """
            )

            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                uq_learning_observations_tenant_source_event
                ON learning_observations(tenant_id, source_event_id)
                WHERE source_event_id IS NOT NULL
                """
            )

        self.connection.commit()

    def save(self, item: LearningObservation) -> LearningObservation:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO learning_observations (
                        id,
                        tenant_id,
                        decision_id,
                        outcome_type,
                        expected_value,
                        actual_value,
                        metric,
                        source,
                        notes,
                        observed_at,
                        confidence,
                        created_at,
                        source_event_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        tenant_id=excluded.tenant_id,
                        decision_id=excluded.decision_id,
                        outcome_type=excluded.outcome_type,
                        expected_value=excluded.expected_value,
                        actual_value=excluded.actual_value,
                        metric=excluded.metric,
                        source=excluded.source,
                        notes=excluded.notes,
                        observed_at=excluded.observed_at,
                        confidence=excluded.confidence,
                        created_at=excluded.created_at,
                        source_event_id=excluded.source_event_id
                    """,
                    (
                        item.id,
                        item.tenant_id,
                        item.decision_id,
                        item.outcome_type.value,
                        item.expected_value,
                        item.actual_value,
                        item.metric,
                        item.source,
                        item.notes,
                        item.observed_at,
                        item.confidence,
                        item.created_at,
                        item.source_event_id,
                    ),
                )

            self.connection.commit()
            return item

        except psycopg.IntegrityError as exc:
            self.connection.rollback()
            raise BusinessRuleViolation(
                "could not persist learning observation"
            ) from exc

    def get(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> LearningObservation | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    tenant_id,
                    decision_id,
                    outcome_type,
                    expected_value,
                    actual_value,
                    metric,
                    source,
                    notes,
                    observed_at,
                    confidence,
                    created_at,
                    source_event_id
                FROM learning_observations
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, observation_id),
            )
            row = cursor.fetchone()

        return self._row(row) if row else None

    def get_by_source_event_id(
        self,
        tenant_id: UUID,
        source_event_id: UUID,
    ) -> LearningObservation | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    tenant_id,
                    decision_id,
                    outcome_type,
                    expected_value,
                    actual_value,
                    metric,
                    source,
                    notes,
                    observed_at,
                    confidence,
                    created_at,
                    source_event_id
                FROM learning_observations
                WHERE tenant_id = %s AND source_event_id = %s
                """,
                (tenant_id, source_event_id),
            )
            row = cursor.fetchone()

        return self._row(row) if row else None

    def list(
        self,
        tenant_id: UUID,
        *,
        decision_id: UUID | None = None,
        metric: str | None = None,
    ) -> tuple[LearningObservation, ...]:
        query = """
            SELECT
                id,
                tenant_id,
                decision_id,
                outcome_type,
                expected_value,
                actual_value,
                metric,
                source,
                notes,
                observed_at,
                confidence,
                created_at,
                source_event_id
            FROM learning_observations
            WHERE tenant_id = %s
        """

        params: list[object] = [tenant_id]

        if decision_id is not None:
            query += " AND decision_id = %s"
            params.append(decision_id)

        if metric is not None:
            query += " AND metric = %s"
            params.append(metric)

        query += " ORDER BY created_at ASC, id ASC"

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return tuple(self._row(row) for row in rows)

    def delete(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM learning_observations
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, observation_id),
            )

        self.connection.commit()

    @staticmethod
    def _row(row) -> LearningObservation:
        return LearningObservation(
            id=row[0],
            tenant_id=row[1],
            decision_id=row[2],
            outcome_type=LearningOutcomeType(row[3]),
            expected_value=row[4],
            actual_value=row[5],
            metric=row[6],
            source=row[7],
            notes=row[8],
            observed_at=row[9],
            confidence=row[10],
            created_at=row[11],
            source_event_id=row[12],
        )
