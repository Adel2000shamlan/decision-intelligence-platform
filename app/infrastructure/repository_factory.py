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
