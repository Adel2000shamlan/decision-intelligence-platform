from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

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


class SQLiteBusinessAssessmentRepository(BusinessAssessmentRepository):
    """Durable SQLite repository with organization-scoped uniqueness and optimistic concurrency."""

    def __init__(self, path=":memory:", connection=None):
        self.conn = connection or sqlite3.connect(
            path,
            check_same_thread=False,
        )
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS business_assessments (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                title TEXT NOT NULL,
                title_key TEXT NOT NULL,
                idea_description TEXT NOT NULL DEFAULT "",
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL CHECK(version >= 1),
                UNIQUE(organization_id, title_key)
            );

            CREATE INDEX IF NOT EXISTS idx_business_assessments_org
                ON business_assessments(organization_id);

            CREATE INDEX IF NOT EXISTS idx_business_assessments_org_status
                ON business_assessments(organization_id, status);
            """
        )
        self.conn.commit()

    @staticmethod
    def _key(title):
        return title.strip().casefold()

    @staticmethod
    def _row(row):
        if row is None:
            return None

        return BusinessAssessment(
            id=UUID(row["id"]),
            organization_id=UUID(row["organization_id"]),
            title=row["title"],
            idea_description=row["idea_description"],
            status=BusinessAssessmentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            version=row["version"],
        )

    def get_by_id(self, assessment_id: UUID):
        row = self.conn.execute(
            "SELECT * FROM business_assessments WHERE id=?",
            (str(assessment_id),),
        ).fetchone()

        return self._row(row)

    def list_by_organization(self, organization_id: UUID):
        rows = self.conn.execute(
            """
            SELECT * FROM business_assessments
            WHERE organization_id=?
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

        rows = self.conn.execute(
            """
            SELECT * FROM business_assessments
            WHERE organization_id=? AND status=?
            ORDER BY created_at, id
            """,
            (str(organization_id), status.value),
        ).fetchall()

        return [self._row(row) for row in rows]

    def exists_by_title(self, organization_id: UUID, title: str):
        row = self.conn.execute(
            """
            SELECT 1 FROM business_assessments
            WHERE organization_id=? AND title_key=?
            """,
            (str(organization_id), self._key(title)),
        ).fetchone()

        return row is not None

    def save(self, assessment: BusinessAssessment, expected_version=None):
        assessment.validate_invariants()

        try:
            existing = self.conn.execute(
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
                WHERE id=?
                """,
                (str(assessment.id),),
            ).fetchone()

            duplicate = self.conn.execute(
                """
                SELECT id FROM business_assessments
                WHERE organization_id=? AND title_key=? AND id<>?
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

                self.conn.execute(
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                old = existing["version"]

                if expected_version is not None and old != expected_version:
                    raise BusinessAssessmentConcurrencyError(
                        f"version conflict: expected {expected_version}, actual {old}"
                    )

                existing_state = (
                    existing["organization_id"],
                    existing["title"],
                    existing["title_key"],
                    existing["idea_description"],
                    existing["status"],
                    existing["created_at"],
                    existing["updated_at"],
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

                current = self.conn.execute(
                    """
                    UPDATE business_assessments
                    SET
                        organization_id=?,
                        title=?,
                        title_key=?,
                        idea_description=?,
                        status=?,
                        created_at=?,
                        updated_at=?,
                        version=?
                    WHERE id=? AND version=?
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

                if current.rowcount != 1:
                    raise BusinessAssessmentConcurrencyError(
                        f"concurrent business assessment update detected: "
                        f"version {expected_previous_version}"
                    )

            self.conn.commit()
            return assessment

        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            raise BusinessAssessmentDuplicateError(str(exc)) from exc

    def close(self):
        self.conn.close()
