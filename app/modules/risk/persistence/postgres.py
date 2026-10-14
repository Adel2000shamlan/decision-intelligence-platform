from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.risk.domain.models import (
    Risk,
    RiskLevel,
    RiskSource,
    RiskStatus,
)
from app.modules.risk.domain.repository import RiskRepository
from app.shared.domain.errors import BusinessRuleViolation


class PostgreSQLRiskRepository(RiskRepository):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    decision_id TEXT,
                    title TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'human',
                    status TEXT NOT NULL,
                    probability INTEGER,
                    impact INTEGER,
                    score INTEGER,
                    level TEXT,
                    residual_probability INTEGER,
                    residual_impact INTEGER,
                    residual_score INTEGER,
                    residual_level TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE(project_id, title_key)
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_risks_project
                ON risks(project_id)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_risks_decision
                ON risks(decision_id)
                """
            )

            columns = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'risks'
                    """
                ).fetchall()
            }

            additions = {
                "decision_id": "TEXT",
                "description": "TEXT NOT NULL DEFAULT ''",
                "source": "TEXT NOT NULL DEFAULT 'human'",
                "probability": "INTEGER",
                "impact": "INTEGER",
                "score": "INTEGER",
                "level": "TEXT",
                "residual_probability": "INTEGER",
                "residual_impact": "INTEGER",
                "residual_score": "INTEGER",
                "residual_level": "TEXT",
            }

            for name, definition in additions.items():
                if name not in columns:
                    conn.execute(
                        f"ALTER TABLE risks ADD COLUMN {name} {definition}"
                    )

    @staticmethod
    def _title_key(title: str) -> str:
        return title.strip()

    @staticmethod
    def _parse_uuid(value: str | None) -> UUID | None:
        return UUID(value) if value else None

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _row_to_risk(self, row) -> Risk:
        return Risk(
            id=self._parse_uuid(row[0]),
            project_id=self._parse_uuid(row[1]),
            decision_id=self._parse_uuid(row[2]),
            title=row[3],
            description=row[5],
            source=RiskSource(row[6]),
            status=RiskStatus(row[7]),
            probability=row[8],
            impact=row[9],
            score=row[10],
            level=RiskLevel(row[11]) if row[11] else None,
            residual_probability=row[12],
            residual_impact=row[13],
            residual_score=row[14],
            residual_level=RiskLevel(row[15]) if row[15] else None,
            created_at=self._parse_datetime(row[16]),
            updated_at=self._parse_datetime(row[17]),
            version=row[18],
        )

    @staticmethod
    def _select_sql() -> str:
        return """
            SELECT
                id,
                project_id,
                decision_id,
                title,
                title_key,
                description,
                source,
                status,
                probability,
                impact,
                score,
                level,
                residual_probability,
                residual_impact,
                residual_score,
                residual_level,
                created_at,
                updated_at,
                version
            FROM risks
        """

    def get_by_id(self, risk_id: UUID) -> Risk | None:
        with self._connect() as conn:
            row = conn.execute(
                self._select_sql()
                + """
                WHERE id = %s
                """,
                (str(risk_id),),
            ).fetchone()

        return self._row_to_risk(row) if row else None

    def list_by_project(self, project_id: UUID) -> list[Risk]:
        with self._connect() as conn:
            rows = conn.execute(
                self._select_sql()
                + """
                WHERE project_id = %s
                ORDER BY created_at, id
                """,
                (str(project_id),),
            ).fetchall()

        return [self._row_to_risk(row) for row in rows]

    def list_by_decision(self, decision_id: UUID) -> list[Risk]:
        with self._connect() as conn:
            rows = conn.execute(
                self._select_sql()
                + """
                WHERE decision_id = %s
                ORDER BY created_at, id
                """,
                (str(decision_id),),
            ).fetchall()

        return [self._row_to_risk(row) for row in rows]

    def exists_by_title(self, project_id: UUID, title: str) -> bool:
        title_key = self._title_key(title)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM risks
                WHERE project_id = %s
                  AND title_key = %s
                LIMIT 1
                """,
                (str(project_id), title_key),
            ).fetchone()

        return row is not None

    def save(self, risk: Risk) -> Risk:
        risk.validate_invariants()
        title_key = self._title_key(risk.title)

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT
                    project_id,
                    decision_id,
                    title,
                    title_key,
                    description,
                    source,
                    status,
                    probability,
                    impact,
                    score,
                    level,
                    residual_probability,
                    residual_impact,
                    residual_score,
                    residual_level,
                    created_at,
                    updated_at,
                    version
                FROM risks
                WHERE id = %s
                """,
                (str(risk.id),),
            ).fetchone()

            if existing is None:
                if risk.version != 1:
                    raise BusinessRuleViolation(
                        "new risk must start at version 1"
                    )

                try:
                    conn.execute(
                        """
                        INSERT INTO risks (
                            id,
                            project_id,
                            decision_id,
                            title,
                            title_key,
                            description,
                            source,
                            status,
                            probability,
                            impact,
                            score,
                            level,
                            residual_probability,
                            residual_impact,
                            residual_score,
                            residual_level,
                            created_at,
                            updated_at,
                            version
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            str(risk.id),
                            str(risk.project_id),
                            str(risk.decision_id)
                            if risk.decision_id
                            else None,
                            risk.title,
                            title_key,
                            risk.description,
                            risk.source.value,
                            risk.status.value,
                            risk.probability,
                            risk.impact,
                            risk.score,
                            risk.level.value if risk.level else None,
                            risk.residual_probability,
                            risk.residual_impact,
                            risk.residual_score,
                            (
                                risk.residual_level.value
                                if risk.residual_level
                                else None
                            ),
                            risk.created_at.isoformat(),
                            risk.updated_at.isoformat(),
                            risk.version,
                        ),
                    )
                except psycopg.errors.UniqueViolation as exc:
                    raise BusinessRuleViolation(
                        "risk title already exists in project: "
                        f"{risk.title.strip()}"
                    ) from exc

                return risk

            existing_version = existing[17]

            if existing_version == risk.version:
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
                    existing[10],
                    existing[11],
                    existing[12],
                    existing[13],
                    existing[14],
                    existing[15],
                    existing[16],
                )

                risk_state = (
                    str(risk.project_id),
                    str(risk.decision_id)
                    if risk.decision_id
                    else None,
                    risk.title,
                    title_key,
                    risk.description,
                    risk.source.value,
                    risk.status.value,
                    risk.probability,
                    risk.impact,
                    risk.score,
                    risk.level.value if risk.level else None,
                    risk.residual_probability,
                    risk.residual_impact,
                    risk.residual_score,
                    (
                        risk.residual_level.value
                        if risk.residual_level
                        else None
                    ),
                    risk.created_at.isoformat(),
                    risk.updated_at.isoformat(),
                )

                if existing_state == risk_state:
                    return risk

                raise BusinessRuleViolation(
                    f"risk concurrency conflict: version {risk.version}"
                )

            expected_previous_version = risk.version - 1

            if existing_version != expected_previous_version:
                raise BusinessRuleViolation(
                    "risk concurrency conflict: expected previous "
                    f"version {expected_previous_version}, found "
                    f"{existing_version}"
                )

            try:
                updated = conn.execute(
                    """
                    UPDATE risks
                    SET
                        project_id = %s,
                        decision_id = %s,
                        title = %s,
                        title_key = %s,
                        description = %s,
                        source = %s,
                        status = %s,
                        probability = %s,
                        impact = %s,
                        score = %s,
                        level = %s,
                        residual_probability = %s,
                        residual_impact = %s,
                        residual_score = %s,
                        residual_level = %s,
                        created_at = %s,
                        updated_at = %s,
                        version = %s
                    WHERE id = %s
                      AND version = %s
                    """,
                    (
                        str(risk.project_id),
                        str(risk.decision_id)
                        if risk.decision_id
                        else None,
                        risk.title,
                        title_key,
                        risk.description,
                        risk.source.value,
                        risk.status.value,
                        risk.probability,
                        risk.impact,
                        risk.score,
                        risk.level.value if risk.level else None,
                        risk.residual_probability,
                        risk.residual_impact,
                        risk.residual_score,
                        (
                            risk.residual_level.value
                            if risk.residual_level
                            else None
                        ),
                        risk.created_at.isoformat(),
                        risk.updated_at.isoformat(),
                        risk.version,
                        str(risk.id),
                        expected_previous_version,
                    ),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise BusinessRuleViolation(
                    "risk title already exists in project: "
                    f"{risk.title.strip()}"
                ) from exc

            if updated.rowcount != 1:
                raise BusinessRuleViolation(
                    "risk concurrency conflict: version "
                    f"{expected_previous_version}"
                )

        return risk
