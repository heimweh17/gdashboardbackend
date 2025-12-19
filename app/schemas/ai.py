"""
Schemas for AI insights endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InsightRequest(BaseModel):
	"""Request schema for generating insights."""
	analysis_result: Optional[Dict[str, Any]] = Field(
		None, description="Analysis result object (preferred if available from frontend)"
	)
	analysis_run_id: Optional[int] = Field(None, description="Analysis run ID to fetch from database")
	context: Optional[Dict[str, Any]] = Field(
		None,
		description="Optional context: {city_name?: str, filters?: dict, viewport_bbox?: dict}",
	)


class InsightResponse(BaseModel):
	"""Response schema for AI insights."""
	text: str = Field(..., description="Narrative paragraph")
	highlights: List[str] = Field(..., description="List of key findings")
	meta: Dict[str, Any] = Field(..., description="Metadata: model, generated_at, limit_window_days")

