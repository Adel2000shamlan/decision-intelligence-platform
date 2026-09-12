from fastapi import FastAPI
from app.api.app import router
from app.modules.authentication.api import router as auth_router
app=FastAPI(title='Decision Intelligence Platform',version='1.0.0')
app.include_router(router)
app.include_router(auth_router)
