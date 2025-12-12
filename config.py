from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "1.0.0"
    
    cors_origins: list = ["*"]
    
    model_config = ConfigDict(
        env_file=".env",
        env_File_encoding="utf-8",)

settings = Settings()
