from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "3.0."
    cors_origins: list = ["*"]
    database_url: str = "sqlite+aiosqlite:///./core/breakfast.db"
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    order_cutoff_hours: int = 36
    # Firebase Cloud Messaging - path to service account JSON file
    firebase_credentials_path: str = "firebase_credentials.json"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()
