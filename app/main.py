import asyncio
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from core.config import get_settings
from core.logger import setup_logging

# Initialize settings and global singleton logging
settings = get_settings()
setup_logging(settings.log_level)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import get_settings
from services.telegram_bot import setup_webhook, stop_telegram_polling


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    app.state.settings = settings
    
    # Automatically register webhook on startup
    await setup_webhook()
    
    yield
    
    # Cleanup bot session on shutdown
    await stop_telegram_polling()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SentinelAI",
        version="0.1.0",
        description="Personal control plane for backend observability and AI workflows.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
