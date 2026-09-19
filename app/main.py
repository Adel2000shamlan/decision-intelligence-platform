from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.database import Database
from app.infrastructure.migrations import apply_initial
from app.infrastructure.repository_factory import (
    create_organization_repository,
    create_project_repository,
)
from app.api.app import router
from app.api.security import security_headers_middleware
from app.api.v1.router import api_router
from app.modules.authentication.api import router as auth_router
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
from app.modules.decision.api import router as decision_router
from app.modules.organization.api.router import (
    configure_service as configure_organization_service,
)
from app.modules.organization.application.service import OrganizationApplicationService
from app.modules.project.api.router import (
    configure_repository as configure_project_repository,
)
from app.modules.risk.api import router as risk_router


@asynccontextmanager
async def lifespan(app):
    with Database().transaction() as conn:
        apply_initial(conn)

        organization_repository = create_organization_repository()
        project_repository = create_project_repository()

        configure_organization_service(
            OrganizationApplicationService(organization_repository)
        )
        configure_project_repository(project_repository)

        developer_service = DeveloperService(
            create_developer_repository(conn)
        )
        configure_developer_service(developer_service)

        resource_resolver = DeveloperResourceResolver(
            organization_repository=organization_repository,
            project_repository=project_repository,
            decision_repository=decision_router._app.repository,
            risk_repository=risk_router._repo,
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

        yield


app = FastAPI(
    title="Decision Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")
app.include_router(developer_router, prefix="/api/v1")
app.include_router(developer_resource_router, prefix="/api/v1")
app.middleware("http")(security_headers_middleware)
