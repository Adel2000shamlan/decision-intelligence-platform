from app.infrastructure.config import settings


def is_postgresql() -> bool:
    return settings.database_url.startswith(("postgresql://", "postgres://"))


def create_organization_repository():
    if is_postgresql():
        from app.modules.organization.persistence.postgres import (
            PostgreSQLOrganizationRepository,
        )
        return PostgreSQLOrganizationRepository(settings.database_url)

    from app.modules.organization.persistence.sqlite import (
        SQLiteOrganizationRepository,
    )
    return SQLiteOrganizationRepository()


def create_project_repository():
    if is_postgresql():
        from app.modules.project.persistence.postgres import (
            PostgreSQLProjectRepository,
        )
        return PostgreSQLProjectRepository(settings.database_url)

    from app.modules.project.persistence.sqlite import SQLiteProjectRepository
    from app.modules.project.application.repository import ProjectRepositoryAdapter

    return ProjectRepositoryAdapter(SQLiteProjectRepository())


def create_agent_repository():
    if is_postgresql():
        from app.modules.agent.persistence.postgres import (
            PostgreSQLAgentRepository,
        )
        return PostgreSQLAgentRepository(settings.database_url)

    from app.modules.agent.persistence.repository import AgentRepository

    return AgentRepository()


def create_knowledge_repository():
    if is_postgresql():
        from app.modules.knowledge.persistence.postgres import (
            PostgreSQLKnowledgeRepository,
        )
        return PostgreSQLKnowledgeRepository(settings.database_url)

    from app.modules.knowledge.persistence.repository import KnowledgeRepository

    return KnowledgeRepository()


def create_kpi_repository():
    if is_postgresql():
        from app.modules.kpi.persistence.postgres import (
            PostgreSQLKPIRepository,
        )
        return PostgreSQLKPIRepository(settings.database_url)

    from app.modules.kpi.persistence.repository import KPIRepository

    return KPIRepository()


def create_business_assessment_repository():
    if is_postgresql():
        from app.modules.business_assessment.persistence.postgres import (
            PostgreSQLBusinessAssessmentRepository,
        )
        return PostgreSQLBusinessAssessmentRepository(settings.database_url)

    from app.modules.business_assessment.persistence.sqlite import (
        SQLiteBusinessAssessmentRepository,
    )
    return SQLiteBusinessAssessmentRepository()


def create_white_label_repository(connection):
    if is_postgresql():
        from app.modules.white_label.persistence.postgres import (
            PostgreSQLWhiteLabelRepository,
        )
        return PostgreSQLWhiteLabelRepository(connection)

    from app.modules.white_label.persistence.sqlite import (
        SQLiteWhiteLabelRepository,
    )
    return SQLiteWhiteLabelRepository(connection)


def create_decision_repository():
    if is_postgresql():
        from app.modules.decision.persistence.postgres import (
            PostgreSQLDecisionRepository,
        )
        return PostgreSQLDecisionRepository(settings.database_url)

    from app.modules.decision.in_memory import InMemoryDecisionRepository

    return InMemoryDecisionRepository()


def create_risk_repository():
    if is_postgresql():
        from app.modules.risk.persistence.postgres import (
            PostgreSQLRiskRepository,
        )
        return PostgreSQLRiskRepository(settings.database_url)

    from app.modules.risk.in_memory import InMemoryRiskRepository

    return InMemoryRiskRepository()


def create_auth_repositories():
    if is_postgresql():
        from app.infrastructure.auth_postgres import (
            PostgreSQLCredentialRepository,
            PostgreSQLTokenRepository,
        )
        from app.infrastructure.authorization_postgres import PostgreSQLRBAC
        from app.modules.identity.persistence.postgres import PostgreSQLUserRepository

        return {
            "users": PostgreSQLUserRepository(settings.database_url),
            "credential_repository": PostgreSQLCredentialRepository(settings.database_url),
            "token_repository": PostgreSQLTokenRepository(settings.database_url),
            "rbac": PostgreSQLRBAC(settings.database_url),
        }

    from app.modules.identity.in_memory import InMemoryUserRepository
    from app.modules.authentication.security import CredentialService, RBAC, TokenService

    return {
        "users": InMemoryUserRepository(),
        "credential_repository": CredentialService().repo,
        "token_repository": TokenService().repo,
        "rbac": RBAC(),
    }
