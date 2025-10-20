"""
API Endpoints para administración CRUD de tablas GTFS
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.models.gtfs_models import (
    Agency, Route, Stop, Trip, StopTime, Calendar,
    FareAttribute, FareRule, FeedInfo, Shape
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================
# SCHEMAS PARA CRUD
# ============================================

class GenericUpdate(BaseModel):
    data: Dict[str, Any]


# ============================================
# ENDPOINTS DE LECTURA
# ============================================

@router.get("/stops")
async def get_all_stops(limit: int = 10000, db: Session = Depends(get_db)):
    """Obtener todas las paradas (sin límite por defecto)"""
    stops = db.query(Stop).limit(limit).all()
    return [
        {
            "stop_id": s.stop_id,
            "stop_name": s.stop_name,
            "stop_lat": float(s.stop_lat),
            "stop_lon": float(s.stop_lon),
            "wheelchair_boarding": s.wheelchair_boarding
        }
        for s in stops
    ]


@router.get("/routes")
async def get_all_routes(limit: int = 10000, db: Session = Depends(get_db)):
    """Obtener todas las rutas (sin límite por defecto)"""
    routes = db.query(Route).limit(limit).all()
    return [
        {
            "route_id": r.route_id,
            "route_short_name": r.route_short_name,
            "route_long_name": r.route_long_name,
            "route_type": r.route_type,
            "route_color": r.route_color,
            "route_text_color": r.route_text_color,
            "agency_id": r.agency_id
        }
        for r in routes
    ]


@router.get("/shapes")
async def get_all_shapes_summary(db: Session = Depends(get_db)):
    """Obtener resumen de todos los shapes"""
    from sqlalchemy import func
    
    shapes = db.query(
        Shape.shape_id,
        func.count(Shape.id).label('point_count'),
        func.max(Shape.shape_dist_traveled).label('total_distance')
    ).group_by(Shape.shape_id).all()
    
    return [
        {
            "shape_id": s.shape_id,
            "point_count": s.point_count,
            "total_distance": float(s.total_distance) if s.total_distance else 0
        }
        for s in shapes
    ]


@router.get("/shapes/{shape_id}/points")
async def get_shape_points(shape_id: str, db: Session = Depends(get_db)):
    """Obtener todos los puntos de un shape específico"""
    shapes = db.query(Shape).filter(
        Shape.shape_id == shape_id
    ).order_by(Shape.shape_pt_sequence).all()
    
    if not shapes:
        raise HTTPException(status_code=404, detail="Shape no encontrado")
    
    return [
        {
            "id": s.id,
            "shape_id": s.shape_id,
            "shape_pt_sequence": s.shape_pt_sequence,
            "shape_pt_lat": float(s.shape_pt_lat),
            "shape_pt_lon": float(s.shape_pt_lon),
            "shape_dist_traveled": float(s.shape_dist_traveled) if s.shape_dist_traveled else 0
        }
        for s in shapes
    ]


@router.get("/routes/{route_id}/stops")
async def get_route_stops(route_id: str, db: Session = Depends(get_db)):
    """
    Obtener todas las paradas de una ruta específica
    Busca en stop_times para encontrar las paradas asociadas
    """
    # Obtener trips de esta ruta
    trips = db.query(Trip).filter(Trip.route_id == route_id).all()
    
    if not trips:
        return {"route_id": route_id, "stops": []}
    
    # Obtener stop_times de estos trips
    trip_ids = [t.trip_id for t in trips]
    
    # Query para obtener paradas únicas con su información
    from sqlalchemy import distinct
    
    stop_times = db.query(StopTime).filter(
        StopTime.trip_id.in_(trip_ids)
    ).all()
    
    # Obtener IDs únicos de paradas
    unique_stop_ids = list(set(st.stop_id for st in stop_times))
    
    # Obtener información completa de las paradas
    stops = db.query(Stop).filter(Stop.stop_id.in_(unique_stop_ids)).all()
    
    return {
        "route_id": route_id,
        "stops": [
            {
                "stop_id": s.stop_id,
                "stop_name": s.stop_name,
                "stop_lat": float(s.stop_lat),
                "stop_lon": float(s.stop_lon)
            }
            for s in stops
        ]
    }
async def get_route_shape(route_id: str, db: Session = Depends(get_db)):
    """
    Obtener el shape de una ruta específica
    Busca en trips para encontrar el shape_id asociado
    """
    # Buscar un trip de esta ruta que tenga shape_id
    trip = db.query(Trip).filter(
        Trip.route_id == route_id,
        Trip.shape_id.isnot(None)
    ).first()
    
    if not trip or not trip.shape_id:
        return {"route_id": route_id, "has_shape": False, "points": []}
    
    # Obtener puntos del shape
    shapes = db.query(Shape).filter(
        Shape.shape_id == trip.shape_id
    ).order_by(Shape.shape_pt_sequence).all()
    
    return {
        "route_id": route_id,
        "shape_id": trip.shape_id,
        "has_shape": True,
        "points": [
            {
                "lat": float(s.shape_pt_lat),
                "lon": float(s.shape_pt_lon),
                "sequence": s.shape_pt_sequence
            }
            for s in shapes
        ]
    }


@router.get("/agency")
async def get_agencies(db: Session = Depends(get_db)):
    """Obtener todas las agencias"""
    agencies = db.query(Agency).all()
    return [
        {
            "agency_id": a.agency_id,
            "agency_name": a.agency_name,
            "agency_url": a.agency_url,
            "agency_timezone": a.agency_timezone,
            "agency_phone": a.agency_phone
        }
        for a in agencies
    ]


@router.get("/trips")
async def get_trips(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
    """Obtener trips (sin límite por defecto)"""
    trips = db.query(Trip).offset(skip).limit(limit).all()
    return [
        {
            "trip_id": t.trip_id,
            "route_id": t.route_id,
            "service_id": t.service_id,
            "trip_headsign": t.trip_headsign,
            "direction_id": t.direction_id,
            "block_id": t.block_id,
            "shape_id": t.shape_id
        }
        for t in trips
    ]


@router.get("/stop_times")
async def get_stop_times(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
    """Obtener stop_times (sin límite por defecto)"""
    stop_times = db.query(StopTime).offset(skip).limit(limit).all()
    return [
        {
            "id": st.id,
            "trip_id": st.trip_id,
            "stop_id": st.stop_id,
            "arrival_time": str(st.arrival_time),
            "departure_time": str(st.departure_time),
            "stop_sequence": st.stop_sequence
        }
        for st in stop_times
    ]


@router.get("/calendar")
async def get_calendar(db: Session = Depends(get_db)):
    """Obtener calendarios"""
    calendars = db.query(Calendar).all()
    return [
        {
            "service_id": c.service_id,
            "monday": c.monday,
            "tuesday": c.tuesday,
            "wednesday": c.wednesday,
            "thursday": c.thursday,
            "friday": c.friday,
            "saturday": c.saturday,
            "sunday": c.sunday,
            "start_date": str(c.start_date),
            "end_date": str(c.end_date)
        }
        for c in calendars
    ]


@router.get("/fare_attributes")
async def get_fare_attributes(db: Session = Depends(get_db)):
    """Obtener fare_attributes"""
    fares = db.query(FareAttribute).all()
    return [
        {
            "fare_id": f.fare_id,
            "price": float(f.price),
            "currency_type": f.currency_type,
            "payment_method": f.payment_method,
            "transfers": f.transfers
        }
        for f in fares
    ]


@router.get("/fare_rules")
async def get_fare_rules(db: Session = Depends(get_db)):
    """Obtener fare_rules"""
    rules = db.query(FareRule).all()
    return [
        {
            "id": r.id,
            "fare_id": r.fare_id,
            "route_id": r.route_id
        }
        for r in rules
    ]


@router.get("/feed_info")
async def get_feed_info(db: Session = Depends(get_db)):
    """Obtener feed_info"""
    info = db.query(FeedInfo).first()
    if not info:
        return []
    
    return [{
        "feed_publisher_name": info.feed_publisher_name,
        "feed_publisher_url": info.feed_publisher_url,
        "feed_lang": info.feed_lang,
        "feed_start_date": str(info.feed_start_date),
        "feed_end_date": str(info.feed_end_date)
    }]


# ============================================
# ENDPOINTS DE ESCRITURA (CRUD)
# ============================================

@router.post("/stops")
async def create_stop(stop: Dict[str, Any], db: Session = Depends(get_db)):
    """Crear una nueva parada"""
    new_stop = Stop(**stop)
    db.add(new_stop)
    db.commit()
    db.refresh(new_stop)
    return {"success": True, "stop_id": new_stop.stop_id}


@router.put("/stops/{stop_id}")
async def update_stop(stop_id: int, update_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Actualizar una parada"""
    try:
        db_stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
        if not db_stop:
            raise HTTPException(status_code=404, detail="Stop no encontrado")
        
        # Actualizar solo campos válidos
        for key, value in update_data.items():
            if hasattr(db_stop, key) and key != 'stop_id':  # No actualizar PK
                # Convertir tipos si es necesario
                if key in ['stop_lat', 'stop_lon'] and value:
                    setattr(db_stop, key, float(value))
                elif key == 'wheelchair_boarding' and value:
                    setattr(db_stop, key, int(value))
                else:
                    setattr(db_stop, key, value)
        
        db.commit()
        db.refresh(db_stop)
        return {"success": True, "message": "Stop actualizado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stops/{stop_id}")
async def delete_stop(stop_id: int, db: Session = Depends(get_db)):
    """Eliminar una parada"""
    try:
        db_stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
        if not db_stop:
            raise HTTPException(status_code=404, detail="Stop no encontrado")
        
        db.delete(db_stop)
        db.commit()
        return {"success": True, "message": "Stop eliminado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routes")
async def create_route(route_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Crear una nueva ruta"""
    try:
        # Validar que tenga route_id
        if 'route_id' not in route_data:
            raise HTTPException(status_code=400, detail="route_id es requerido")
        
        # Verificar que no exista
        existing = db.query(Route).filter(Route.route_id == route_data['route_id']).first()
        if existing:
            raise HTTPException(status_code=400, detail="route_id ya existe")
        
        new_route = Route(**route_data)
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        return {"success": True, "route_id": new_route.route_id, "message": "Ruta creada"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/routes/{route_id}")
async def update_route(route_id: str, update_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Actualizar una ruta"""
    try:
        db_route = db.query(Route).filter(Route.route_id == route_id).first()
        if not db_route:
            raise HTTPException(status_code=404, detail="Route no encontrado")
        
        for key, value in update_data.items():
            if hasattr(db_route, key) and key != 'route_id':
                # Convertir tipos
                if key == 'route_type' and value:
                    setattr(db_route, key, int(value))
                else:
                    setattr(db_route, key, value)
        
        db.commit()
        db.refresh(db_route)
        return {"success": True, "message": "Ruta actualizada"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, db: Session = Depends(get_db)):
    """Eliminar una ruta"""
    try:
        db_route = db.query(Route).filter(Route.route_id == route_id).first()
        if not db_route:
            raise HTTPException(status_code=404, detail="Route no encontrado")
        
        db.delete(db_route)
        db.commit()
        return {"success": True, "message": "Ruta eliminada"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS GENÉRICOS PARA OTRAS TABLAS
# ============================================

@router.delete("/trips/{trip_id}")
async def delete_trip(trip_id: str, db: Session = Depends(get_db)):
    """Eliminar un trip"""
    db_trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip no encontrado")
    
    db.delete(db_trip)
    db.commit()
    return {"success": True}


@router.delete("/stop_times/{id}")
async def delete_stop_time(id: int, db: Session = Depends(get_db)):
    """Eliminar un stop_time"""
    db_st = db.query(StopTime).filter(StopTime.id == id).first()
    if not db_st:
        raise HTTPException(status_code=404, detail="StopTime no encontrado")
    
    db.delete(db_st)
    db.commit()
    return {"success": True}