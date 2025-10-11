from fastapi import FastAPI
from app.routers import gtfs_router
from app.database import Base, engine

# Crear tablas en la DB
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Transit Scheduler API",
    version="1.0.0"
)

# Routers
app.include_router(gtfs_router.router)
