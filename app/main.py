from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import engine
from app.models import gtfs_models
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import engine
from app.models import gtfs_models
# Importa todos tus routers
from app.api import gtfs, kml, csv, admin_web, admin
from app.api import routes_api # Asegúrate que este esté importado
from app.api import export_gtfs # Asegúrate que este esté importado
from app.api import gtfs, kml, csv, admin_web, admin, routes_api, export_gtfs, scheduling  # ← AÑADIR scheduling

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# --- CONFIGURACIÓN DE CORS ---
# Lista de orígenes permitidos. Asegúrate de que SÍ incluye el puerto de tu frontend.
# Si tu frontend corre en 5173, debe estar aquí.
origins = [
    "http://localhost:5173", # Puerto por defecto de Vite
    "http://localhost:3000", # Puerto común para React (por si acaso)
    # Puedes añadir más orígenes si es necesario (ej. tu URL de despliegue)
]

# Si ALLOWED_ORIGINS está definido en tu config, úsalo, si no, usa la lista de arriba
allowed_origins_setting = getattr(settings, "ALLOWED_ORIGINS", origins)

print(f"🔧 Configurando CORS para permitir orígenes: {allowed_origins_setting}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Incluir routers ---
# Asegúrate de que todos tus routers estén incluidos UNA SOLA VEZ
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(csv.router)
app.include_router(admin_web.router)
app.include_router(admin.router)
app.include_router(routes_api.router) # El router para /routes/create-with-kml
app.include_router(export_gtfs.router)
app.include_router(scheduling.router)  # ← AÑADIR ESTA LÍNEA

@app.on_event("startup")
def create_tables():
    # ... (sin cambios)
    try:
        logging.info("Verificando/creando tablas...")
        gtfs_models.Base.metadata.create_all(bind=engine)
        from app.models import scheduling_models
        scheduling_models.Base.metadata.create_all(bind=engine)
        logging.info("Tablas OK.")
    except Exception as e:
        logging.error("Error al verificar/crear tablas: %s", e)