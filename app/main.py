import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, datasets, analysis, places, ai
from app.db.database import Base, engine
from app.core.config import settings
# Import models to ensure they're registered with Base.metadata
from app.db import models  # noqa: F401


def create_app() -> FastAPI:
	"""
	Create and configure the FastAPI application instance.
	"""
	app = FastAPI(
		title="Geo Analytics Backend",
		version="0.1.0",
		description="Backend API for a geospatial analytics platform."
	)

	# CORS: use configured origins (production-ready)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=settings.cors_origins_list,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	# Include routers
	app.include_router(auth.router, prefix="/auth", tags=["auth"])
	app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
	app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
	app.include_router(places.router, prefix="/places", tags=["places"])
	app.include_router(ai.router, prefix="/ai", tags=["ai"])

	return app


# Create database tables at startup if AUTO_CREATE_TABLES is set
# This is useful for bootstrapping in Railway or development
# In production with migrations, set AUTO_CREATE_TABLES=false or unset
if os.getenv("AUTO_CREATE_TABLES", "").lower() == "true":
	Base.metadata.create_all(bind=engine)

app = create_app()


