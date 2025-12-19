from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.core.config import settings


# SQLite specific: check_same_thread=False required for SQLite with multiple threads
engine = create_engine(
	settings.sqlalchemy_database_url,
	connect_args={"check_same_thread": False} if settings.sqlalchemy_database_url.startswith("sqlite") else {},
	pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


