from fastapi import APIRouter

from app.api.routes import admin, alerts, health, logs, resume

api_router = APIRouter()
api_router.include_router(alerts.router, tags=["alerts"])
api_router.include_router(resume.router, tags=["resume"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(logs.router, tags=["logs"])
api_router.include_router(admin.router, tags=["admin"])
