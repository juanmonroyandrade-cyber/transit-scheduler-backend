from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.gtfs_importer import GTFSImporter
from app.models.gtfs_models import Route, Stop

router = APIRouter(prefix="/gtfs", tags=["GTFS"])

@router.post("/import")
async def import_gtfs(
    file: UploadFile = File(...),
    agency_name: Optional[str] = Form(None, description="Nombre de la agencia (opcional)"),
    db: Session = Depends(get_db)
):
    try:
        importer = GTFSImporter(db)
        result = importer.import_gtfs(file.file, agency_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/routes")
async def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    return routes

@router.get("/stops")
async def get_stops(db: Session = Depends(get_db)):
    stops = db.query(Stop).all()
    return stops