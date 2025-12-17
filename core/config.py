from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "2.0.1"
    cors_origins: list = ["*"]
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    model_config = ConfigDict(
        env_file=".env",
        env_File_encoding="utf-8",
        extra = "allow")

settings = Settings()
