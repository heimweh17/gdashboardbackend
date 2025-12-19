from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.core.config import settings


# SQLite specific: check_same_thread=False required for SQLite with multiple threads
# Postgres: use connection pooling
connect_args = {}
if settings.sqlalchemy_database_url.startswith("sqlite"):
	connect_args = {"check_same_thread": False}
elif settings.sqlalchemy_database_url.startswith("postgresql"):
	# Postgres connection pooling settings
	connect_args = {}

engine = create_engine(
	settings.sqlalchemy_database_url,
	connect_args=connect_args,
	pool_pre_ping=True,
	# Postgres: enable connection pooling
	pool_size=5 if not settings.sqlalchemy_database_url.startswith("sqlite") else None,
	max_overflow=10 if not settings.sqlalchemy_database_url.startswith("sqlite") else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


