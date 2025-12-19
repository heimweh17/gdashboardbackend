from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


password_context = CryptContext(schemes=["argon2"], deprecated="auto")
print("DEBUG hashing schemes:", password_context.schemes(), flush=True)

def hash_password(plain_password: str) -> str:
    if plain_password is None:
        raise ValueError("Password is required")

    if not isinstance(plain_password, str):
        plain_password = str(plain_password)

    # bcrypt hard limit: 72 bytes
    pw_bytes = plain_password.encode("utf-8")
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
        plain_password = pw_bytes.decode("utf-8", errors="ignore")

    return password_context.hash(plain_password)



def verify_password(plain_password: str, password_hash: str) -> bool:
	return password_context.verify(plain_password, password_hash)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
	to_encode = {"sub": subject}
	if expires_delta is None:
		expires_delta = settings.access_token_expires
	expire = datetime.now(timezone.utc) + expires_delta
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
	return encoded_jwt


