from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "3.0."
    cors_origins: list = ["*"]
    database_url: str  # Required - set in .env or environment variable
    jwt_secret_key: str  # Required - set in .env or environment variable
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    order_cutoff_hours: int = 36
    firebase_credentials_path: str # Required - set in .env or environment variable
    encryption_key: str  # Required - set in .env or environment variable

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()
