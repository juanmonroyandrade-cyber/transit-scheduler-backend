"""
Configuración de la base de datos SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Obtener URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está definida en el archivo .env")

# Crear engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Cambiar a True para debug
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_size=5,
    max_overflow=10
)

# Session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
Base = declarative_base()


# Dependency para FastAPI
def get_db():
    """
    Dependency que provee una sesión de base de datos
    Se cierra automáticamente después de cada request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()