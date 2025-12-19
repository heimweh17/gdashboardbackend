from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlaceBase(BaseModel):
	name: Optional[str] = None
	category: Optional[str] = None
	lat: float = Field(..., ge=-90, le=90, description="Latitude")
	lon: float = Field(..., ge=-180, le=180, description="Longitude")
	notes: Optional[str] = None
	tags: Optional[dict] = None


class PlaceCreate(PlaceBase):
	pass


class PlaceUpdate(BaseModel):
	name: Optional[str] = None
	category: Optional[str] = None
	notes: Optional[str] = None
	tags: Optional[dict] = None


class PlaceOut(PlaceBase):
	id: str
	user_id: int
	created_at: datetime

	class Config:
		from_attributes = True

