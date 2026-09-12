from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.modules.organization.api.router import router as organization_router
from app.modules.project.api.router import router as project_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(organization_router)
api_router.include_router(project_router)
