from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.database import Database
from app.infrastructure.migrations import apply_initial
from app.infrastructure.repository_factory import create_organization_repository, create_project_repository
from app.api.security import security_headers_middleware
from app.api.app import router
from app.api.v1.router import api_router
from app.modules.authentication.api import router as auth_router
from app.modules.organization.api.router import configure_service as configure_organization_service
from app.modules.organization.application.service import OrganizationApplicationService
from app.modules.project.api.router import configure_repository as configure_project_repository

@asynccontextmanager
async def lifespan(app):
    with Database().transaction() as conn:
        apply_initial(conn)
    configure_organization_service(OrganizationApplicationService(create_organization_repository()))
    configure_project_repository(create_project_repository())
    yield

app = FastAPI(title="Decision Intelligence Platform", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")
app.middleware("http")(security_headers_middleware)
