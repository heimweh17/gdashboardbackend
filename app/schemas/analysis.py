from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeParams(BaseModel):
	grid_cell_size: float = Field(default=0.01, gt=0)
	dbscan_eps: Optional[float] = Field(default=None, gt=0, description="Neighborhood radius in degrees (optional).")
	dbscan_eps_km: Optional[float] = Field(default=1.0, gt=0, description="Neighborhood radius in kilometers (preferred).")
	dbscan_min_samples: int = Field(default=5, ge=1)
	category_field: Optional[str] = Field(default="category")


class AnalysisRunOut(BaseModel):
	id: int
	dataset_id: int
	user_id: int
	params_json: str
	result_json: str
	created_at: datetime

	class Config:
		from_attributes = True


class AnalysisResult(BaseModel):
	summary: Dict[str, Any]
	grid_density: Dict[str, Any]
	clustering: Dict[str, Any]


