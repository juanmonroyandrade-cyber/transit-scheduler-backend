from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import engine
from app.models import gtfs_models
from app.api import gtfs, kml, csv, admin_web, admin

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://localhost:3000"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers (sin duplicados)
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(csv.router)
app.include_router(admin_web.router)
app.include_router(admin.router)

@app.on_event("startup")
def create_tables():
    """
    Crea las tablas de la base de datos al iniciar la aplicación.
    """
    try:
        logging.info("Creando todas las tablas en la base de datos...")
        gtfs_models.Base.metadata.create_all(bind=engine)
        logging.info("Tablas creadas exitosamente.")
    except Exception as e:
        logging.error("Error al crear las tablas de la base de datos: %s", e)