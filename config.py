from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Product Management API"
    app_version: str = "1.0.0"
    
    # CORS
    cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
