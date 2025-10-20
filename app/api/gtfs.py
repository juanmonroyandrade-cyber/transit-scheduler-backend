# app/api/gtfs.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.services.gtfs_importer import GTFSImporter
from app.models.gtfs_models import Route, Stop, Shape, Trip, StopTime

router = APIRouter(prefix="/gtfs", tags=["GTFS"])

# --- Endpoint de importación (sin cambios) ---
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

# --- INICIO DE LA SECCIÓN SÚPER OPTIMIZADA ---

@router.get("/routes-with-details")
async def get_routes_with_details(db: Session = Depends(get_db)):
    """
    Endpoint súper optimizado que devuelve las rutas con sus trazados y paradas.
    Realiza pocas consultas y procesa los datos en memoria para máxima velocidad.
    """
    try:
        # 1. Obtener todos los datos necesarios en consultas masivas
        routes = db.query(Route).all()
        stops = db.query(Stop).all()
        
        # Optimización: Cargar solo las columnas necesarias
        trips = db.query(Trip.trip_id, Trip.route_id, Trip.shape_id).all()
        stop_times = db.query(StopTime.trip_id, StopTime.stop_id).distinct().all()
        shapes = db.query(Shape).order_by(Shape.shape_id, Shape.shape_pt_sequence).all()

        # 2. Procesar los datos en diccionarios para acceso rápido (O(1))
        stops_map = {s.stop_id: s for s in stops}
        
        shapes_map = defaultdict(list)
        for shape in shapes:
            shapes_map[shape.shape_id].append([shape.shape_pt_lat, shape.shape_pt_lon])

        # 3. Construir las relaciones en memoria (mucho más rápido que N+1 queries)
        route_to_trips = defaultdict(list)
        for trip in trips:
            route_to_trips[trip.route_id].append(trip)
            
        trip_to_stops = defaultdict(set)
        for st in stop_times:
            trip_to_stops[st.trip_id].add(st.stop_id)

        # 4. Ensamblar la respuesta final
        response_data = []
        for route in routes:
            route_shape_ids = set()
            route_stop_ids = set()

            # Obtener todos los shapes y stops de los viajes asociados a la ruta
            for trip in route_to_trips[route.route_id]:
                if trip.shape_id:
                    route_shape_ids.add(trip.shape_id)
                route_stop_ids.update(trip_to_stops[trip.trip_id])

            # Construir la lista de shapes y paradas para la ruta
            route_shapes = [shapes_map[shape_id] for shape_id in route_shape_ids if shape_id in shapes_map]
            route_stops = [stops_map[stop_id] for stop_id in route_stop_ids if stop_id in stops_map]
            
            response_data.append({
                "route_id": route.route_id,
                "route_short_name": route.route_short_name,
                "route_long_name": route.route_long_name,
                "route_color": route.route_color,
                "shapes": route_shapes,
                "stops": [
                    {
                        "stop_id": s.stop_id,
                        "stop_name": s.stop_name,
                        "stop_lat": s.stop_lat,
                        "stop_lon": s.stop_lon
                    } for s in route_stops
                ]
            })
            
        return response_data
    except Exception as e:
        # Captura cualquier error durante el proceso y devuelve un error claro
        raise HTTPException(status_code=500, detail=f"Error al procesar los datos del mapa: {str(e)}")