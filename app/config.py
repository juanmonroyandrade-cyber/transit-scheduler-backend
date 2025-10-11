"""
Configuración de la aplicación
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuración general de la app"""
    
    # Database
    DATABASE_URL: str
    
    # API
    API_TITLE: str = "Transit Scheduler API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Sistema de programación de rutas de transporte público"
    
    # Security
    SECRET_KEY: str = "default-secret-key-change-in-production"
    
    # CORS (permitir acceso desde frontend)
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-frontend-domain.vercel.app"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings()