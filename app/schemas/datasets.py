from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class DatasetOut(BaseModel):
	id: int
	filename: str
	file_type: str
	n_points: int
	bbox_json: str
	created_at: datetime

	class Config:
		from_attributes = True


class DatasetList(BaseModel):
	items: List[DatasetOut]


class UploadResponse(BaseModel):
	dataset_id: int
	filename: str
	file_type: str
	n_points: int
	bbox: dict


