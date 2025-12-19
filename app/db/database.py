from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings

connect_args = {}
db_url = settings.sqlalchemy_database_url
print("USING DB:", settings.sqlalchemy_database_url, flush=True)
engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # SQLite: don't use QueuePool params; safest is NullPool (especially on Render)
    engine_kwargs["poolclass"] = NullPool
else:
    # Postgres: connection pooling
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
