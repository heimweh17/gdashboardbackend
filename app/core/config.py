from datetime import timedelta
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
	secret_key: str = Field(default=os.getenv("SECRET_KEY", "dev-secret-change-me"))
	access_token_expire_minutes: int = 60 * 24  # 24 hours
	jwt_algorithm: str = "HS256"
	sqlalchemy_database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./geo.db"))
	upload_dir: str = Field(default=os.getenv("UPLOAD_DIR", "storage/uploads"))

	@property
	def access_token_expires(self) -> timedelta:
		return timedelta(minutes=self.access_token_expire_minutes)


settings = Settings()


