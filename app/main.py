"""
FastAPI Application - Transit Scheduler
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Importar configuración y base de datos
from app.database import Base, engine, SessionLocal

# Importar modelos ANTES de crear tablas (crítico)
from app.models import gtfs_models

# Importar routers
from app.api import gtfs

# Crear tablas si no existen
print("🔧 Creando tablas en base de datos...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas/verificadas")

# Crear aplicación FastAPI
app = FastAPI(
    title="Transit Scheduler API",
    version="1.0.0",
    description="Sistema de programación de rutas de transporte público"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción especifica dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(gtfs.router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Transit Scheduler API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check con verificación de BD"""
    try:
        # Probar conexión a base de datos
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.on_event("startup")
async def startup_event():
    """Ejecutar al iniciar la aplicación"""
    print("🚀 Transit Scheduler API iniciada")
    print("📍 Versión: 1.0.0")
    print("📚 Documentación: /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutar al cerrar la aplicación"""
    print("👋 Transit Scheduler API detenida")