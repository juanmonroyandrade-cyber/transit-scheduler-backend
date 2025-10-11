from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas
from app.database import get_db

router = APIRouter(
    prefix="/gtfs",
    tags=["GTFS"]
)

# Agencies
@router.get("/agencies/", response_model=List[schemas.Agency])
def read_agencies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_agencies(db, skip=skip, limit=limit)

@router.post("/agencies/", response_model=schemas.Agency)
def create_agency(agency: schemas.AgencyCreate, db: Session = Depends(get_db)):
    return crud.create_agency(db=db, agency=agency)

# Routes
@router.get("/routes/", response_model=List[schemas.Route])
def read_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_routes(db, skip=skip, limit=limit)

@router.post("/routes/", response_model=schemas.Route)
def create_route(route: schemas.RouteCreate, db: Session = Depends(get_db)):
    return crud.create_route(db=db, route=route)
