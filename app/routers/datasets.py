from __future__ import annotations
import json
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Dataset, User
from app.routers.auth import get_current_user
from app.schemas.datasets import DatasetList, DatasetOut, UploadResponse
from app.services.parsing import compute_bbox, parse_csv_points, parse_geojson_points


router = APIRouter()


def ensure_upload_dir() -> None:
	os.makedirs(settings.upload_dir, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
	file: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	ensure_upload_dir()
	filename = file.filename or "upload"
	_, ext = os.path.splitext(filename.lower())
	if ext not in [".csv", ".geojson", ".json"]:
		raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or GeoJSON.")

	content = await file.read()
	if ext == ".csv":
		points = parse_csv_points(content)
		file_type = "csv"
	else:
		points = parse_geojson_points(content)
		file_type = "geojson"

	if not points:
		raise HTTPException(status_code=400, detail="No valid points found in file")

	bbox = compute_bbox(points)

	# Save file
	random_suffix = secrets.token_hex(8)
	storage_name = f"{current_user.id}_{random_suffix}{ext}"
	storage_path = os.path.join(settings.upload_dir, storage_name)
	with open(storage_path, "wb") as f:
		f.write(content)

	dataset = Dataset(
		user_id=current_user.id,
		filename=filename,
		file_type=file_type,
		storage_path=storage_path,
		n_points=len(points),
		bbox_json=json.dumps(bbox),
	)
	db.add(dataset)
	db.commit()
	db.refresh(dataset)

	return UploadResponse(
		dataset_id=dataset.id,
		filename=dataset.filename,
		file_type=dataset.file_type,
		n_points=dataset.n_points,
		bbox=bbox,
	)


@router.get("", response_model=DatasetList)
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	items = (
		db.query(Dataset)
		.filter(Dataset.user_id == current_user.id)
		.order_by(Dataset.created_at.desc())
		.all()
	)
	return DatasetList(items=items)


