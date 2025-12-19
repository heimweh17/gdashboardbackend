from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, datasets, analysis
from app.db.database import Base, engine


def create_app() -> FastAPI:
	"""
	Create and configure the FastAPI application instance.
	"""
	app = FastAPI(
		title="Geo Analytics Backend",
		version="0.1.0",
		description="Backend API for a geospatial analytics platform."
	)

	# CORS (open for dev)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	# Include routers
	app.include_router(auth.router, prefix="/auth", tags=["auth"])
	app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
	app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

	return app


# Create database tables at startup (development convenience)
Base.metadata.create_all(bind=engine)

app = create_app()


