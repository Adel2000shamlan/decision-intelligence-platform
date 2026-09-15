from fastapi import FastAPI
from app.api.security import security_headers_middleware
from app.api.app import router
from app.api.v1.router import api_router
from app.modules.authentication.api import router as auth_router
app=FastAPI(title='Decision Intelligence Platform',version='1.0.0')
app.include_router(router)
app.include_router(auth_router)

app.include_router(api_router, prefix='/api/v1')

app.middleware("http")(security_headers_middleware)
