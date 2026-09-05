"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, nodes, workflows
from app.config import get_settings
from app.core.errors import register_exception_handlers

API_PREFIX = "/api"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FlowForge API",
        description="Visual workflow automation platform for developers.",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(nodes.router, prefix=API_PREFIX)
    app.include_router(workflows.router, prefix=API_PREFIX)
    return app


app = create_app()
