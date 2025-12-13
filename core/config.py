from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "2.0.0"
    cors_origins: list = ["*"]
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    class Config:
        env_file = ".env"

settings = Settings()
