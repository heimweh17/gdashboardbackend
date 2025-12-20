from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.routers.auth import get_current_user
from app.db.models import User
from app.routers.ai import router as ai_router

# ------------------------
# AI Microservice App
# ------------------------

def create_ai_app() -> FastAPI:
    app = FastAPI(
        title="Geo Dashboard AI Service",
        description="Dedicated microservice for AI-powered geospatial insights",
        version="0.1.0",
    )

    # CORS (same frontend as main backend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount AI router
    app.include_router(
        ai_router,
        prefix="/ai",
        tags=["AI Insights"],
    )

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "ai",
            "model": settings.gemini_model,
        }

    return app


app = create_ai_app()
