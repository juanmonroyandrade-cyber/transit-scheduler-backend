from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import gtfs
from app.database import engine
from app.models import gtfs_models
from app.api import gtfs, kml  # Agregar kml
from app.api import gtfs, kml, csv  # ✅ agregar csv
from app.api import admin_web
from app.api import admin
from app.api import gtfs, kml, admin  # Agregar admin



import logging

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", ["http://localhost:3000"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gtfs.router)
app.include_router(kml.router) 
app.include_router(csv.router)  # ✅ nueva línea
app.include_router(admin_web.router)
app.include_router(admin.router)
app.include_router(gtfs.router)
app.include_router(kml.router)
app.include_router(admin.router)  # AGREGAR ESTA LÍNEA


@app.on_event("startup")
def create_tables():
    try:
        gtfs_models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        logging.error("Error creando tablas en DB: %s", e)