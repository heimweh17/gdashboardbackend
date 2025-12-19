from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Place, User
from app.schemas.places import PlaceCreate, PlaceOut, PlaceUpdate
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[PlaceOut])
def list_places(
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db)
):
	"""Get all places for the current user."""
	places = db.query(Place).filter(Place.user_id == current_user.id).order_by(Place.created_at.desc()).all()
	return places


@router.post("/", response_model=PlaceOut, status_code=status.HTTP_201_CREATED)
def create_place(
	place_data: PlaceCreate,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db)
):
	"""Create a new saved place."""
	place = Place(
		user_id=current_user.id,
		name=place_data.name,
		category=place_data.category,
		lat=place_data.lat,
		lon=place_data.lon,
		notes=place_data.notes,
		tags=place_data.tags,
	)
	db.add(place)
	db.commit()
	db.refresh(place)
	return place


@router.get("/{place_id}", response_model=PlaceOut)
def get_place(
	place_id: str,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db)
):
	"""Get a specific place by ID."""
	place = db.query(Place).filter(Place.id == place_id).first()
	if not place:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
	if place.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this place")
	return place


@router.patch("/{place_id}", response_model=PlaceOut)
def update_place(
	place_id: str,
	place_data: PlaceUpdate,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db)
):
	"""Update a saved place."""
	place = db.query(Place).filter(Place.id == place_id).first()
	if not place:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
	if place.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this place")

	# Update only provided fields
	update_data = place_data.model_dump(exclude_unset=True)
	for field, value in update_data.items():
		setattr(place, field, value)

	db.commit()
	db.refresh(place)
	return place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place(
	place_id: str,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db)
):
	"""Delete a saved place."""
	place = db.query(Place).filter(Place.id == place_id).first()
	if not place:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
	if place.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this place")

	db.delete(place)
	db.commit()
	return None

