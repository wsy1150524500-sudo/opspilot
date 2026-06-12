from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ops_agent.web.routers import system, logs, ssh, ai


def create_app() -> FastAPI:
    app = FastAPI(title="CLI Ops Agent API", version="1.0.0")
    # TODO: Tighten CORS origins before non-local deployment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(logs.router, prefix="/api/v1")
    app.include_router(ssh.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
