import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, datasets, analysis, places
from app.db.database import Base, engine
from app.core.config import settings

# ✅ IMPORTANT:
# Make sure all SQLAlchemy models are imported so they register into Base.metadata
# Your models live in app/db/modules.py
from app.db import modules  # noqa: F401


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    """
    app = FastAPI(
        title="Geo Analytics Backend",
        version="0.1.0",
        description="Backend API for a geospatial analytics platform.",
    )

    # CORS: use configured origins (production-ready)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ✅ TEMP (good for your case since you don't care about migrating old data):
    # Auto-create tables on startup for BOTH sqlite and postgres.
    # This prevents "relation users does not exist".
    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)

    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
    app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
    app.include_router(places.router, prefix="/places", tags=["places"])

    return app


app = create_app()
