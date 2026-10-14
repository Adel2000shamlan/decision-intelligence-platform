from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.config import settings
from app.infrastructure.database import Database
from app.infrastructure.migrations import apply_initial
from app.infrastructure.repository_factory import (
    create_organization_repository,
    create_project_repository,
    create_decision_repository,
    create_risk_repository,
    create_business_assessment_repository,
    create_white_label_repository,
    create_auth_repositories,
)
from app.api.security import security_headers_middleware
from app.api.v1.router import api_router
from app.modules.authentication.api import (
    router as auth_router,
    users as auth_users,
    credentials as auth_credentials,
    tokens as auth_tokens,
    rbac as auth_rbac,
)
from app.modules.developer.api.config import create_developer_repository
from app.modules.developer.api.resources import (
    configure_resource_authorization,
    configure_resource_rate_controller,
    router as developer_resource_router,
)
from app.modules.developer.api.router import (
    configure_service as configure_developer_service,
    router as developer_router,
)
from app.modules.developer.application.service import DeveloperService
from app.modules.developer.authorization.adapter import DeveloperAuthorizationService
from app.modules.developer.usage.rate_control import DeveloperRateController
from app.modules.authorization.domain.models import ExplicitPermissionPolicy
from app.modules.developer.authorization.resource_resolver import (
    DeveloperResourceResolver,
)
from app.modules.decision.api.router import (
    router as decision_router,
    configure_service as configure_decision_service,
)
from app.modules.organization.api.router import (
    configure_service as configure_organization_service,
)
from app.modules.organization.application.service import OrganizationApplicationService
from app.modules.decision.application.implementation import DecisionApplicationService
from app.modules.project.api.router import (
    configure_repository as configure_project_repository,
)
from app.modules.risk.api.router import (
    router as risk_router,
    configure_repository as configure_risk_repository,
)
from app.modules.business_assessment.api.router import (
    router as business_assessment_router,
    configure_repository as configure_business_assessment_repository,
)
from app.modules.authorization.domain.authorization_services import (
    build_authorization_services,
)
from app.modules.white_label.api import (
    configure_service as configure_white_label_service,
    router as white_label_router,
)
from app.modules.white_label.application.service import (
    WhiteLabelApplicationService,
)
import importlib


@asynccontextmanager
async def lifespan(app):
    with Database().transaction() as conn:

        if type(conn).__module__.startswith("sqlite3"):
            apply_initial(conn)
            white_label_migration = importlib.import_module(
                "app.migrations.112_09_001_white_label"
            )
            white_label_migration.apply(conn)

        organization_repository = create_organization_repository()
        project_repository = create_project_repository()
        decision_repository = create_decision_repository()
        risk_repository = create_risk_repository()
        business_assessment_repository = create_business_assessment_repository()

        configure_organization_service(
            OrganizationApplicationService(organization_repository)
        )
        configure_project_repository(project_repository)

        configure_decision_service(
            DecisionApplicationService.from_repository(decision_repository)
        )
        configure_risk_repository(risk_repository)

        configure_business_assessment_repository(
            business_assessment_repository,
            organization_repository=organization_repository,
        )

        white_label_authorization = build_authorization_services(
            policies=(
                ExplicitPermissionPolicy(
                    frozenset(
                        {
                            "organization:read",
                            "organization:create",
                            "organization:update",
                        }
                    )
                ),
            ),
        )

        white_label_service = WhiteLabelApplicationService(
            repository=create_white_label_repository(conn),
            organization_repository=organization_repository,
            authorization=white_label_authorization,
        )
        configure_white_label_service(white_label_service)

        developer_service = DeveloperService(
            create_developer_repository(conn)
        )
        configure_developer_service(developer_service)

        resource_resolver = DeveloperResourceResolver(
            organization_repository=organization_repository,
            project_repository=project_repository,
            decision_repository=decision_repository,
            risk_repository=risk_repository,
        )

        developer_authorization = DeveloperAuthorizationService.create(
            resource_resolver=resource_resolver,
            policies=(
                ExplicitPermissionPolicy(
                    frozenset(
                        {
                            "project:read",
                            "decision:read",
                            "risk:read",
                        }
                    )
                ),
            ),
        )

        configure_resource_authorization(developer_authorization)
        configure_resource_rate_controller(DeveloperRateController())

        if settings.environment.lower() == "production":
            auth_repositories = create_auth_repositories()
            auth_users.configure(auth_repositories["users"])
            auth_credentials.repo = auth_repositories["credential_repository"]
            auth_tokens.repo = auth_repositories["token_repository"]
            auth_rbac.configure(auth_repositories["rbac"])

        yield


app = FastAPI(
    title="Decision Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")
app.include_router(developer_router, prefix="/api/v1")
app.include_router(developer_resource_router, prefix="/api/v1")
app.include_router(white_label_router, prefix="/api/v1")
app.include_router(business_assessment_router, prefix="/api/v1")
app.middleware("http")(security_headers_middleware)
