"""
FastAPI Application - Transit Scheduler
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar routers
from app.api import gtfs

# Crear aplicación FastAPI
app = FastAPI(
    title="Transit Scheduler API",
    version="1.0.0",
    description="Sistema de programación de rutas de transporte público"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    from app.database import engine
    from sqlalchemy import text
    
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
    
    # Intentar crear tablas (no crashea si falla)
    try:
        from app.database import Base, engine
        from app.models import gtfs_models
        
        print("🔧 Creando tablas en base de datos...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas/verificadas")
    except Exception as e:
        print(f"⚠️ No se pudieron crear tablas: {e}")
        print("⚠️ La API funcionará pero no podrás usar la base de datos")


@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutar al cerrar la aplicación"""
    print("👋 Transit Scheduler API detenida")