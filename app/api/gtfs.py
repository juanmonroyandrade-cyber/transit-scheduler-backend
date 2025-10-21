# app/api/gtfs.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional
from collections import defaultdict
import time 

from app.database import get_db
from app.services.gtfs_importer import GTFSImporter
from app.models.gtfs_models import Route, Stop, Shape, Trip, StopTime

router = APIRouter(prefix="/gtfs", tags=["GTFS"])

# --- Endpoint de importación (se mantiene igual) ---
@router.post("/import")
async def import_gtfs( file: UploadFile = File(...), agency_name: Optional[str] = Form(None), db: Session = Depends(get_db)):
    try:
        importer = GTFSImporter(db)
        result = importer.import_gtfs(file.file, agency_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ENDPOINT DEL MAPA: SÚPER OPTIMIZADO V2 ---
@router.get("/routes-with-details")
async def get_routes_with_details(db: Session = Depends(get_db)):
    start_time = time.time()
    print("🚀 Iniciando consulta optimizada V2...")
    try:
        # 1. Consultas masivas
        print("   - Cargando rutas...")
        routes = db.query(Route).all()
        print(f"   - Rutas cargadas: {len(routes)} ({time.time() - start_time:.2f}s)")

        print("   - Cargando paradas...")
        stops_query_start = time.time()
        stops = db.query(Stop.stop_id, Stop.stop_name, Stop.stop_lat, Stop.stop_lon).all()
        stops_map = {s.stop_id: {"stop_id": s.stop_id, "stop_name": s.stop_name, "stop_lat": s.stop_lat, "stop_lon": s.stop_lon} for s in stops}
        print(f"   - Paradas cargadas y mapeadas: {len(stops_map)} ({time.time() - stops_query_start:.2f}s)")
        
        print("   - Cargando viajes...")
        trips_query_start = time.time()
        trips = db.query(Trip.trip_id, Trip.route_id, Trip.shape_id).all()
        print(f"   - Viajes cargados: {len(trips)} ({time.time() - trips_query_start:.2f}s)")
        
        print("   - Cargando stop_times...")
        stop_times_query_start = time.time()
        # Optimización: Cargar como tuplas es más rápido
        stop_times_tuples = db.query(StopTime.trip_id, StopTime.stop_id).distinct().all()
        print(f"   - StopTimes cargados: {len(stop_times_tuples)} ({time.time() - stop_times_query_start:.2f}s)")
        
        print("   - Cargando shapes...")
        shapes_query_start = time.time()
        # Optimización: Cargar como tuplas
        shapes_tuples = db.query(Shape.shape_id, Shape.shape_pt_lat, Shape.shape_pt_lon, Shape.shape_pt_sequence).order_by(Shape.shape_id, Shape.shape_pt_sequence).all()
        print(f"   - Shapes cargados: {len(shapes_tuples)} ({time.time() - shapes_query_start:.2f}s)")

        # 2. Procesar shapes en diccionario
        print("   - Procesando shapes...")
        shapes_process_start = time.time()
        shapes_map = defaultdict(list)
        for shape_id, lat, lon, _ in shapes_tuples:
            shapes_map[shape_id].append([lat, lon])
        print(f"   - Shapes procesados. ({time.time() - shapes_process_start:.2f}s)")

        # 3. Construir relaciones
        print("   - Construyendo relaciones...")
        relations_start = time.time()
        route_to_trips = defaultdict(list)
        trip_ids_in_routes = set() 
        for trip in trips:
            route_to_trips[trip.route_id].append(trip)
            trip_ids_in_routes.add(trip.trip_id)
            
        trip_to_stop_ids = defaultdict(set)
        for trip_id, stop_id in stop_times_tuples:
            if trip_id in trip_ids_in_routes:
                trip_to_stop_ids[trip_id].add(stop_id)
        print(f"   - Relaciones construidas. ({time.time() - relations_start:.2f}s)")

        # 4. Ensamblar respuesta
        print("   - Ensamblando respuesta...")
        assembly_start = time.time()
        response_data = []
        for route in routes:
            route_shape_ids = set()
            route_stop_ids = set()
            for trip in route_to_trips.get(route.route_id, []):
                if trip.shape_id: route_shape_ids.add(trip.shape_id)
                route_stop_ids.update(trip_to_stop_ids.get(trip.trip_id, set()))
            
            route_shapes_coords = [shapes_map[shape_id] for shape_id in route_shape_ids if shape_id in shapes_map]
            route_stops_data = [stops_map[stop_id] for stop_id in route_stop_ids if stop_id in stops_map]
            
            response_data.append({
                "route_id": route.route_id, "route_short_name": route.route_short_name,
                "route_long_name": route.route_long_name, "route_color": route.route_color,
                "shapes": route_shapes_coords, "stops": route_stops_data })
            
        total_time = time.time() - start_time
        print(f"   - Ensamblaje completado. ({time.time() - assembly_start:.2f}s)")
        print(f"✅ Consulta optimizada V2 completada en {total_time:.2f} segundos.")
        return response_data
        
    except Exception as e:
        import traceback
        print(f"❌ Error durante la consulta optimizada V2: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar datos del mapa: {str(e)}")