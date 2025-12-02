"""FastAPI server for Colima E2B."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from dinbutler.server.routes import sandbox, files, commands
from dinbutler.services.docker_client import get_docker_client
from dinbutler.exceptions import ColimaException

logger = logging.getLogger(__name__)


async def verify_docker_connection():
    """Verify Docker/Colima is available."""
    try:
        client = get_docker_client()
        if not client.ping():
            raise ColimaException(
                "Cannot connect to Docker",
                suggestion="Start Colima with: colima start --vm-type=vz"
            )
        logger.info("Docker connection verified")
    except Exception as e:
        logger.error(f"Docker connection failed: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Colima E2B server...")
    await verify_docker_connection()
    yield
    # Shutdown
    logger.info("Shutting down Colima E2B server...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Colima E2B",
        description="Local E2B-compatible sandbox API using Colima/Docker",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(sandbox.router, prefix="/sandboxes", tags=["sandboxes"])
    app.include_router(files.router, prefix="/sandboxes/{sandbox_id}/files", tags=["files"])
    app.include_router(commands.router, prefix="/sandboxes/{sandbox_id}/commands", tags=["commands"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        try:
            client = get_docker_client()
            docker_ok = client.ping()
        except Exception:
            docker_ok = False

        return {
            "status": "healthy" if docker_ok else "unhealthy",
            "docker": docker_ok,
        }

    return app


# Default app instance
app = create_app()
