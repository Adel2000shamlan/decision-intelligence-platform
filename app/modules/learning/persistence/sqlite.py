import sqlite3
from datetime import datetime
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import LearningObservation, LearningOutcomeType
from .repository import LearningRepository


class SQLiteLearningRepository(LearningRepository):
    def __init__(self, connection: sqlite3.Connection | None = None):
        self.connection = connection or sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_observations (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                expected_value REAL,
                actual_value REAL,
                metric TEXT NOT NULL,
                source TEXT NOT NULL,
                notes TEXT,
                observed_at TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_observations_tenant_created
            ON learning_observations(tenant_id, created_at)
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_observations_tenant_decision
            ON learning_observations(tenant_id, decision_id)
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_observations_tenant_metric
            ON learning_observations(tenant_id, metric)
            """
        )
        self.connection.commit()

    def save(self, item: LearningObservation) -> LearningObservation:
        try:
            self.connection.execute(
                """
                INSERT INTO learning_observations (
                    id, tenant_id, decision_id, outcome_type,
                    expected_value, actual_value, metric, source,
                    notes, observed_at, confidence, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    created_at=excluded.created_at
                """,
                (
                    str(item.id),
                    str(item.tenant_id),
                    str(item.decision_id),
                    item.outcome_type.value,
                    item.expected_value,
                    item.actual_value,
                    item.metric,
                    item.source,
                    item.notes,
                    item.observed_at.isoformat(),
                    item.confidence,
                    item.created_at.isoformat(),
                ),
            )
            self.connection.commit()
            return item
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "could not persist learning observation"
            ) from exc

    def get(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> LearningObservation | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM learning_observations
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(observation_id)),
        ).fetchone()

        return self._row(row) if row else None

    def list(
        self,
        tenant_id: UUID,
        *,
        decision_id: UUID | None = None,
        metric: str | None = None,
    ) -> tuple[LearningObservation, ...]:
        query = """
            SELECT *
            FROM learning_observations
            WHERE tenant_id = ?
        """
        params: list[str] = [str(tenant_id)]

        if decision_id is not None:
            query += " AND decision_id = ?"
            params.append(str(decision_id))

        if metric is not None:
            query += " AND metric = ?"
            params.append(metric)

        query += " ORDER BY created_at ASC, id ASC"

        rows = self.connection.execute(query, params).fetchall()
        return tuple(self._row(row) for row in rows)

    def delete(self, tenant_id: UUID, observation_id: UUID) -> None:
        self.connection.execute(
            """
            DELETE FROM learning_observations
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(observation_id)),
        )
        self.connection.commit()

    @staticmethod
    def _row(row: sqlite3.Row) -> LearningObservation:
        return LearningObservation(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            decision_id=UUID(row["decision_id"]),
            outcome_type=LearningOutcomeType(row["outcome_type"]),
            expected_value=row["expected_value"],
            actual_value=row["actual_value"],
            metric=row["metric"],
            source=row["source"],
            notes=row["notes"],
            observed_at=datetime.fromisoformat(row["observed_at"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
