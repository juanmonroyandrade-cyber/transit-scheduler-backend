"""
FastAPI Application - Transit Scheduler
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# Configurar CORS (permitir requests desde frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# IMPORTAR ROUTERS
# ============================================
from app.api import gtfs

# Registrar routers
app.include_router(gtfs.router)

# ============================================
# ENDPOINTS BÁSICOS
# ============================================

@app.get("/")
async def root():
    """Endpoint raíz - Verificar que la API está funcionando"""
    return {
        "message": "Transit Scheduler API",
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.database import engine
    try:
        # Probar conexión a base de datos
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# ============================================
# INICIALIZACIÓN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Ejecutar al iniciar la aplicación"""
    print("🚀 Transit Scheduler API iniciada")
    print(f"📍 Versión: {settings.API_VERSION}")

@app.on_event("shutdown")
async def shutdown_event():
    """Ejecutar al cerrar la aplicación"""
    print("👋 Transit Scheduler API detenida")

# ============================================
# Para correr localmente:
# uvicorn app.main:app --reload
# ============================================