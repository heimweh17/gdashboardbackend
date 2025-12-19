from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest, Token, UserCreate, UserOut


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[Session, Depends(get_db)],
) -> User:
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
		email: str | None = payload.get("sub")
		if email is None:
			raise credentials_exception
	except JWTError:
		raise credentials_exception

	user = db.query(User).filter(User.email == email).first()
	if user is None:
		raise credentials_exception
	return user


@router.post("/register", response_model=UserOut, status_code=201)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
	existing = db.query(User).filter(User.email == payload.email).first()
	if existing:
		raise HTTPException(status_code=400, detail="Email already registered")
    
	user = User(
		email=payload.email,
		password_hash=hash_password(payload.password),
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.email == form_data.username).first()
	if not user or not verify_password(form_data.password, user.password_hash):
		raise HTTPException(status_code=401, detail="Incorrect email or password")
	access_token = create_access_token(user.email)
	return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
	return current_user


