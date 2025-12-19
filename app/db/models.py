from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.database import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

	datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
	analysis_runs = relationship("AnalysisRun", back_populates="owner", cascade="all, delete-orphan")


class Dataset(Base):
	__tablename__ = "datasets"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	filename: Mapped[str] = mapped_column(String(512), nullable=False)
	file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # csv | geojson
	storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
	n_points: Mapped[int] = mapped_column(Integer, nullable=False)
	bbox_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

	owner = relationship("User", back_populates="datasets")
	analysis_runs = relationship("AnalysisRun", back_populates="dataset", cascade="all, delete-orphan")


class AnalysisRun(Base):
	__tablename__ = "analysis_runs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	params_json: Mapped[str] = mapped_column(Text, nullable=False)
	result_json: Mapped[str] = mapped_column(Text, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

	dataset = relationship("Dataset", back_populates="analysis_runs")
	owner = relationship("User", back_populates="analysis_runs")


