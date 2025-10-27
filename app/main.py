# app/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.config import settings
from app.database import engine
from app.api import bulk_operations
from app.models import gtfs_models, scheduling_models

# Importar todos los routers
from app.api import (
    gtfs,
    kml,
    csv,
    admin_web,
    admin,
    routes_api,
    export_gtfs,
    scheduling,
    timetables,
    excel_integration  # ✅ NUEVO: Router para integración con Excel
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear instancia de FastAPI
app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

allowed_origins_setting = getattr(settings, "ALLOWED_ORIGINS", origins)
logger.info(f"🔧 Configurando CORS para permitir orígenes: {allowed_origins_setting}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_setting,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
logger.info("Including API routers...")
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(csv.router)
app.include_router(admin_web.router)
app.include_router(admin.router)
app.include_router(routes_api.router)
app.include_router(export_gtfs.router)
app.include_router(scheduling.router)
app.include_router(timetables.router)
app.include_router(bulk_operations.router)
app.include_router(excel_integration.router)  # ✅ NUEVO
logger.info("All API routers included.")

# Evento Startup
@app.on_event("startup")
def create_tables():
    """Verifica y crea las tablas de la base de datos al iniciar."""
    try:
        logger.info("Verificando/creando tablas GTFS...")
        gtfs_models.Base.metadata.create_all(bind=engine)
        logger.info("Verificando/creando tablas Scheduling...")
        scheduling_models.Base.metadata.create_all(bind=engine)
        logger.info("Tablas OK.")
    except Exception as e:
        logger.error(f"Error al verificar/crear tablas: {e}", exc_info=True)

# Ruta Raíz
@app.get("/")
async def read_root():
    """Ruta raíz simple para verificar que el backend está activo."""
    return {"message": f"Welcome to {settings.API_TITLE} v{settings.API_VERSION}"}

logger.info("FastAPI application setup complete.")