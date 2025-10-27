# app/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import os # Añadido para os.path


from app.config import settings
from app.database import engine
from app.api import bulk_operations
# Importar modelos GTFS y scheduling
from app.models import gtfs_models, scheduling_models # Importar ambos aquí

# Importa todos tus routers UNA SOLA VEZ
from app.api import (
    gtfs,
    kml,
    csv,
    admin_web,
    admin,
    routes_api,
    export_gtfs,
    scheduling,
    timetables # Asegúrate que timetables.py existe en app/api/
)

# --- Logging Básico ---
# Configura el logging si no lo has hecho ya en otro lugar
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Crear Instancia de FastAPI ---
app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# --- CONFIGURACIÓN DE CORS ---
# Lista de orígenes permitidos (ajusta según necesites)
origins = [
    "http://localhost:5173", # Puerto por defecto de Vite
    "http://localhost:3000", # Otro puerto común de frontend
    # Añade aquí la URL de tu frontend desplegado si es diferente
]

# Usar la configuración de settings si existe, sino la lista 'origins'
allowed_origins_setting = getattr(settings, "ALLOWED_ORIGINS", origins)

logger.info(f"🔧 Configurando CORS para permitir orígenes: {allowed_origins_setting}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_setting, # Usar la variable correcta
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos
    allow_headers=["*"], # Permite todos los encabezados
)

# --- Incluir routers de la API ---
# Incluir cada router UNA SOLA VEZ
logger.info("Including API routers...")
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(csv.router)
app.include_router(admin_web.router)
app.include_router(admin.router)
app.include_router(routes_api.router)
app.include_router(export_gtfs.router)
app.include_router(scheduling.router)
app.include_router(timetables.router) # Router para los horarios encadenados
app.include_router(bulk_operations.router)
logger.info("All API routers included.")

# --- Evento Startup para Crear Tablas ---
@app.on_event("startup")
def create_tables():
    """Verifica y crea las tablas de la base de datos al iniciar."""
    try:
        logger.info("Verificando/creando tablas GTFS...")
        gtfs_models.Base.metadata.create_all(bind=engine)
        logger.info("Verificando/creando tablas Scheduling...")
        # Asegúrate que scheduling_models fue importado correctamente arriba
        scheduling_models.Base.metadata.create_all(bind=engine)
        logger.info("Tablas OK.")
    except Exception as e:
        logger.error(f"Error al verificar/crear tablas: {e}", exc_info=True)
        # Considera si quieres que la app falle al iniciar si la BD no funciona
        # raise RuntimeError("Database table creation failed.") from e

# --- Ruta Raíz (Opcional) ---
# Puedes mantener o quitar la ruta raíz dependiendo de si sirves el frontend desde aquí
@app.get("/")
async def read_root():
    """Ruta raíz simple para verificar que el backend está activo."""
    return {"message": f"Welcome to {settings.API_TITLE} v{settings.API_VERSION}"}

# --- Servir Frontend (Opcional - Comentado por ahora) ---
# Si usas Vite Dev Server con proxy o sirves el frontend por separado (ej. Nginx),
# las siguientes líneas para servir estáticos desde FastAPI podrían no ser necesarias
# o necesitar ajustes para producción.

# static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
# if os.path.exists(static_dir):
#     from fastapi.staticfiles import StaticFiles
#     from fastapi.templating import Jinja2Templates
#     app.mount("/static_frontend", StaticFiles(directory=static_dir), name="static_frontend")
#     templates = Jinja2Templates(directory=static_dir)
#     logger.info(f"Mounted static directory: {static_dir} at /static_frontend")

#     @app.get("/{full_path:path}", include_in_schema=False) # Excluir de /docs
#     async def serve_frontend_entry(request: Request, full_path: str):
#         """Sirve el index.html del frontend para rutas no manejadas por la API."""
#         logger.debug(f"Attempting to serve path: {full_path}")
#         index_path = os.path.join(static_dir, "index.html")
#         if os.path.exists(index_path):
#             return templates.TemplateResponse("index.html", {"request": request})
#         else:
#              logger.error(f"Error: index.html not found at {index_path}")
#              raise HTTPException(status_code=404, detail="Frontend entry point not found")
# else:
#     logger.warning(f"Static directory for frontend not found: {static_dir}")


logger.info("FastAPI application setup complete.")