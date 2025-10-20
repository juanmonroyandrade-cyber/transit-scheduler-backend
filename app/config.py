from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    API_TITLE: str = "Transit Scheduler API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Sistema de programación de rutas de transporte público"
    SECRET_KEY: str
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()