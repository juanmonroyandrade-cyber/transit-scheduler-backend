from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import engine
from app.models import gtfs_models
# Importa todos tus routers
from app.api import gtfs, kml, csv, admin_web, admin 
from app.api import routes_api # ✅ Importa el nuevo router

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    # Asegúrate que tu frontend (ej. localhost:5173) esté aquí
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://localhost:3000"]), 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(csv.router)
app.include_router(admin_web.router)
app.include_router(admin.router)
app.include_router(routes_api.router) # ✅ Añade el nuevo router

@app.on_event("startup")
def create_tables():
    # ... (sin cambios)
    try:
        logging.info("Creando/verificando tablas en la base de datos...")
        gtfs_models.Base.metadata.create_all(bind=engine)
        logging.info("Tablas verificadas/creadas exitosamente.")
    except Exception as e:
        logging.error("Error al crear/verificar las tablas: %s", e)