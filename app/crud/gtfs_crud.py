from sqlalchemy.orm import Session
from app.models import gtfs_models as models
from app.schemas import gtfs_schemas as schemas

# Agency
def get_agencies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Agency).offset(skip).limit(limit).all()

def create_agency(db: Session, agency: schemas.AgencyCreate):
    db_agency = models.Agency(**agency.dict())
    db.add(db_agency)
    db.commit()
    db.refresh(db_agency)
    return db_agency

# Route
def get_routes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Route).offset(skip).limit(limit).all()

def create_route(db: Session, route: schemas.RouteCreate):
    db_route = models.Route(**route.dict())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route
