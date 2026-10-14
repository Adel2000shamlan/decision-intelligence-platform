from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.business_assessment.domain.models import (
    BusinessAssessment,
    BusinessAssessmentStatus,
)
from app.modules.business_assessment.domain.repository import (
    BusinessAssessmentRepository,
)


class BusinessAssessmentRepositoryError(Exception):
    pass


class BusinessAssessmentNotFound(BusinessAssessmentRepositoryError):
    pass


class BusinessAssessmentConcurrencyError(BusinessAssessmentRepositoryError):
    pass


class BusinessAssessmentDuplicateError(BusinessAssessmentRepositoryError):
    pass


class PostgreSQLBusinessAssessmentRepository(BusinessAssessmentRepository):
    """Durable PostgreSQL repository with optimistic concurrency."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS business_assessments (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    idea_description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK(version >= 1),
                    UNIQUE(organization_id, title_key)
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_business_assessments_org
                ON business_assessments(organization_id)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_business_assessments_org_status
                ON business_assessments(organization_id, status)
                """
            )

    @staticmethod
    def _key(title):
        return title.strip().casefold()

    @staticmethod
    def _row(row):
        if row is None:
            return None

        return BusinessAssessment(
            id=UUID(row[0]),
            organization_id=UUID(row[1]),
            title=row[2],
            idea_description=row[4],
            status=BusinessAssessmentStatus(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            version=row[8],
        )

    def get_by_id(self, assessment_id: UUID):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM business_assessments WHERE id=%s",
                (str(assessment_id),),
            ).fetchone()

        return self._row(row)

    def list_by_organization(self, organization_id: UUID):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM business_assessments
                WHERE organization_id=%s
                ORDER BY created_at, id
                """,
                (str(organization_id),),
            ).fetchall()

        return [self._row(row) for row in rows]

    def list_by_status(
        self,
        organization_id: UUID,
        status: BusinessAssessmentStatus,
    ):
        if not isinstance(status, BusinessAssessmentStatus):
            try:
                status = BusinessAssessmentStatus(status)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    "invalid business assessment status"
                ) from exc

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM business_assessments
                WHERE organization_id=%s AND status=%s
                ORDER BY created_at, id
                """,
                (str(organization_id), status.value),
            ).fetchall()

        return [self._row(row) for row in rows]

    def exists_by_title(self, organization_id: UUID, title: str):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM business_assessments
                WHERE organization_id=%s AND title_key=%s
                """,
                (str(organization_id), self._key(title)),
            ).fetchone()

        return row is not None

    def save(self, assessment: BusinessAssessment, expected_version=None):
        assessment.validate_invariants()

        try:
            with self._connect() as conn:
                existing = conn.execute(
                    """
                    SELECT
                        organization_id,
                        title,
                        title_key,
                        idea_description,
                        status,
                        created_at,
                        updated_at,
                        version
                    FROM business_assessments
                    WHERE id=%s
                    """,
                    (str(assessment.id),),
                ).fetchone()

                duplicate = conn.execute(
                    """
                    SELECT id FROM business_assessments
                    WHERE organization_id=%s
                      AND title_key=%s
                      AND id<>%s
                    """,
                    (
                        str(assessment.organization_id),
                        self._key(assessment.title),
                        str(assessment.id),
                    ),
                ).fetchone()

                if duplicate is not None:
                    raise BusinessAssessmentDuplicateError(
                        "assessment title already exists in organization"
                    )

                if existing is None:
                    if assessment.version != 1:
                        raise BusinessAssessmentConcurrencyError(
                            "new business assessment must start at version 1"
                        )

                    if expected_version not in (None, 0):
                        raise BusinessAssessmentConcurrencyError(
                            "assessment does not exist for expected version"
                        )

                    conn.execute(
                        """
                        INSERT INTO business_assessments (
                            id,
                            organization_id,
                            title,
                            title_key,
                            idea_description,
                            status,
                            created_at,
                            updated_at,
                            version
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(assessment.id),
                            str(assessment.organization_id),
                            assessment.title,
                            self._key(assessment.title),
                            assessment.idea_description,
                            assessment.status.value,
                            assessment.created_at.isoformat(),
                            assessment.updated_at.isoformat(),
                            assessment.version,
                        ),
                    )

                else:
                    old = existing[7]

                    if expected_version is not None and old != expected_version:
                        raise BusinessAssessmentConcurrencyError(
                            f"version conflict: expected {expected_version}, actual {old}"
                        )

                    existing_state = (
                        existing[0],
                        existing[1],
                        existing[2],
                        existing[3],
                        existing[4],
                        existing[5],
                        existing[6],
                    )

                    assessment_state = (
                        str(assessment.organization_id),
                        assessment.title,
                        self._key(assessment.title),
                        assessment.idea_description,
                        assessment.status.value,
                        assessment.created_at.isoformat(),
                        assessment.updated_at.isoformat(),
                    )

                    if old == assessment.version:
                        if existing_state == assessment_state:
                            return assessment

                        raise BusinessAssessmentConcurrencyError(
                            f"version conflict: version {assessment.version}"
                        )

                    expected_previous_version = assessment.version - 1

                    if old != expected_previous_version:
                        raise BusinessAssessmentConcurrencyError(
                            "business assessment concurrency conflict: "
                            f"expected previous version {expected_previous_version}, "
                            f"found {old}"
                        )

                    updated = conn.execute(
                        """
                        UPDATE business_assessments
                        SET
                            organization_id=%s,
                            title=%s,
                            title_key=%s,
                            idea_description=%s,
                            status=%s,
                            created_at=%s,
                            updated_at=%s,
                            version=%s
                        WHERE id=%s AND version=%s
                        """,
                        (
                            str(assessment.organization_id),
                            assessment.title,
                            self._key(assessment.title),
                            assessment.idea_description,
                            assessment.status.value,
                            assessment.created_at.isoformat(),
                            assessment.updated_at.isoformat(),
                            assessment.version,
                            str(assessment.id),
                            expected_previous_version,
                        ),
                    )

                    if updated.rowcount != 1:
                        raise BusinessAssessmentConcurrencyError(
                            "concurrent business assessment update detected: "
                            f"version {expected_previous_version}"
                        )

            return assessment

        except psycopg.errors.UniqueViolation as exc:
            raise BusinessAssessmentDuplicateError(str(exc)) from exc

    def close(self):
        """Compatibility no-op; connections are scoped per operation."""
        return None
