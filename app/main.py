from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import api_router
from core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SentinelAI",
        version="0.1.0",
        description="Personal control plane for backend observability and AI workflows.",
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "name": "SentinelAI",
            "status": "ok",
            "provider": settings.model_provider,
        }

    return app


app = create_app()
