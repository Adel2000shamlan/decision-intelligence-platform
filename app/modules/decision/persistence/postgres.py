from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.decision.domain.models import (
    Decision,
    DecisionPriority,
    DecisionStatus,
    DecisionType,
)
from app.modules.decision.domain.repository import DecisionRepository
from app.shared.domain.errors import BusinessRuleViolation


class PostgreSQLDecisionRepository(DecisionRepository):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    decision_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE(project_id, title_key)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_organization
                ON decisions(organization_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_project
                ON decisions(project_id)
                """
            )

            columns = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'decisions'
                    """
                ).fetchall()
            }

            additions = {
                "description": "TEXT NOT NULL DEFAULT ''",
                "decision_type": "TEXT NOT NULL DEFAULT 'strategic'",
                "priority": "TEXT NOT NULL DEFAULT 'medium'",
            }

            for name, definition in additions.items():
                if name not in columns:
                    conn.execute(
                        f"ALTER TABLE decisions ADD COLUMN {name} {definition}"
                    )

    @staticmethod
    def _title_key(title: str) -> str:
        return title.strip()

    @staticmethod
    def _parse_uuid(value: str) -> UUID:
        return UUID(value)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _row_to_decision(self, row) -> Decision:
        return Decision(
            id=self._parse_uuid(row[0]),
            organization_id=self._parse_uuid(row[1]),
            project_id=self._parse_uuid(row[2]),
            title=row[3],
            description=row[5],
            decision_type=DecisionType(row[6]),
            priority=DecisionPriority(row[7]),
            status=DecisionStatus(row[8]),
            created_at=self._parse_datetime(row[9]),
            updated_at=self._parse_datetime(row[10]),
            version=row[11],
        )

    def get_by_id(self, decision_id: UUID) -> Decision | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id, organization_id, project_id, title, title_key,
                    description, decision_type, priority, status,
                    created_at, updated_at, version
                FROM decisions
                WHERE id = %s
                """,
                (str(decision_id),),
            ).fetchone()

        return self._row_to_decision(row) if row else None

    def list_all(self) -> list[Decision]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT
                    id, organization_id, project_id, title, title_key,
                    description, decision_type, priority, status,
                    created_at, updated_at, version
                FROM decisions
                ORDER BY created_at, id
                """).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def list_by_project(self, project_id: UUID) -> list[Decision]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, organization_id, project_id, title, title_key,
                    description, decision_type, priority, status,
                    created_at, updated_at, version
                FROM decisions
                WHERE project_id = %s
                ORDER BY created_at, id
                """,
                (str(project_id),),
            ).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def list_by_organization(self, organization_id: UUID) -> list[Decision]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, organization_id, project_id, title, title_key,
                    description, decision_type, priority, status,
                    created_at, updated_at, version
                FROM decisions
                WHERE organization_id = %s
                ORDER BY created_at, id
                """,
                (str(organization_id),),
            ).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def exists_by_title(self, project_id: UUID, title: str) -> bool:
        title_key = self._title_key(title)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM decisions
                WHERE project_id = %s
                  AND title_key = %s
                LIMIT 1
                """,
                (str(project_id), title_key),
            ).fetchone()

        return row is not None

    def save(self, decision: Decision) -> Decision:
        decision.validate_invariants()

        title_key = self._title_key(decision.title)

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT
                    organization_id, project_id, title, title_key,
                    description, decision_type, priority, status,
                    created_at, updated_at, version
                FROM decisions
                WHERE id = %s
                """,
                (str(decision.id),),
            ).fetchone()

            if existing is None:
                if decision.version != 1:
                    raise BusinessRuleViolation(
                        "new decision must start at version 1"
                    )

                try:
                    conn.execute(
                        """
                        INSERT INTO decisions (
                            id,
                            organization_id,
                            project_id,
                            title,
                            title_key,
                            description,
                            decision_type,
                            priority,
                            status,
                            created_at,
                            updated_at,
                            version
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            str(decision.id),
                            str(decision.organization_id),
                            str(decision.project_id),
                            decision.title,
                            title_key,
                            decision.description,
                            decision.decision_type.value,
                            decision.priority.value,
                            decision.status.value,
                            decision.created_at.isoformat(),
                            decision.updated_at.isoformat(),
                            decision.version,
                        ),
                    )
                except psycopg.errors.UniqueViolation as exc:
                    raise BusinessRuleViolation(
                        f"decision title already exists in project: "
                        f"{decision.title.strip()}"
                    ) from exc

                return decision

            existing_version = existing[10]

            if existing_version == decision.version:
                existing_state = (
                    existing[0],
                    existing[1],
                    existing[2],
                    existing[3],
                    existing[4],
                    existing[5],
                    existing[6],
                    existing[7],
                    existing[8],
                    existing[9],
                )
                decision_state = (
                    str(decision.organization_id),
                    str(decision.project_id),
                    decision.title,
                    title_key,
                    decision.description,
                    decision.decision_type.value,
                    decision.priority.value,
                    decision.status.value,
                    decision.created_at.isoformat(),
                    decision.updated_at.isoformat(),
                )

                if existing_state == decision_state:
                    return decision

                raise BusinessRuleViolation(
                    f"decision concurrency conflict: "
                    f"version {decision.version}"
                )

            expected_previous_version = decision.version - 1

            if existing_version != expected_previous_version:
                raise BusinessRuleViolation(
                    f"decision concurrency conflict: expected previous "
                    f"version {expected_previous_version}, found "
                    f"{existing_version}"
                )

            try:
                updated = conn.execute(
                    """
                    UPDATE decisions
                    SET
                        organization_id = %s,
                        project_id = %s,
                        title = %s,
                        title_key = %s,
                        description = %s,
                        decision_type = %s,
                        priority = %s,
                        status = %s,
                        created_at = %s,
                        updated_at = %s,
                        version = %s
                    WHERE id = %s
                      AND version = %s
                    """,
                    (
                        str(decision.organization_id),
                        str(decision.project_id),
                        decision.title,
                        title_key,
                        decision.description,
                        decision.decision_type.value,
                        decision.priority.value,
                        decision.status.value,
                        decision.created_at.isoformat(),
                        decision.updated_at.isoformat(),
                        decision.version,
                        str(decision.id),
                        expected_previous_version,
                    ),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise BusinessRuleViolation(
                    f"decision title already exists in project: "
                    f"{decision.title.strip()}"
                ) from exc

            if updated.rowcount != 1:
                raise BusinessRuleViolation(
                    f"decision concurrency conflict: version "
                    f"{expected_previous_version}"
                )

        return decision
