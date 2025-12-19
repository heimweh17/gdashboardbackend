from __future__ import annotations
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AnalysisRun, Dataset, User
from app.routers.auth import get_current_user
from app.schemas.analysis import AnalyzeParams, AnalysisRunOut
from app.services.analysis import compute_summary, dbscan_clustering, grid_density
from app.services.parsing import parse_csv_points, parse_geojson_points


router = APIRouter()


def _load_points_for_dataset(dataset: Dataset) -> list[dict]:
	with open(dataset.storage_path, "rb") as f:
		content = f.read()
	if dataset.file_type == "csv":
		return parse_csv_points(content)
	else:
		return parse_geojson_points(content)


@router.post("/{dataset_id}/analyze", response_model=AnalysisRunOut)
def analyze_dataset(
	dataset_id: int,
	params: AnalyzeParams,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
	if not dataset:
		raise HTTPException(status_code=404, detail="Dataset not found")

	points = _load_points_for_dataset(dataset)
	if not points:
		raise HTTPException(status_code=400, detail="No points to analyze")

	summary = compute_summary(points, category_field=params.category_field)
	grid = grid_density(points, grid_cell_size=params.grid_cell_size)

	eps_km = params.dbscan_eps_km
	eps_deg = params.dbscan_eps
	clusters = dbscan_clustering(points, eps_km=eps_km, min_samples=params.dbscan_min_samples, eps_degrees=eps_deg)

	result = {
		"summary": summary,
		"grid_density": grid,
		"clustering": clusters,
	}

	run = AnalysisRun(
		dataset_id=dataset.id,
		user_id=current_user.id,
		params_json=params.model_dump_json(),
		result_json=json.dumps(result),
	)
	db.add(run)
	db.commit()
	db.refresh(run)
	return run


@router.get("/{analysis_run_id}", response_model=AnalysisRunOut)
def get_analysis_run(
	analysis_run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
	run = (
		db.query(AnalysisRun)
		.filter(AnalysisRun.id == analysis_run_id, AnalysisRun.user_id == current_user.id)
		.first()
	)
	if not run:
		raise HTTPException(status_code=404, detail="Analysis run not found")
	return run


