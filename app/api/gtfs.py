# app/api/gtfs.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session, joinedload, aliased # Importar aliased
from sqlalchemy import distinct, asc # Importar asc para ordenar
from typing import Optional
from collections import defaultdict
import time

from app.database import get_db
from app.services.gtfs_importer import GTFSImporter
# Asegúrate de importar todos los modelos necesarios
from app.models.gtfs_models import Route, Stop, Shape, Trip, StopTime 

router = APIRouter(prefix="/gtfs", tags=["GTFS"])

# --- Endpoint de importación (sin cambios) ---
@router.post("/import")
async def import_gtfs( file: UploadFile = File(...), agency_name: Optional[str] = Form(None), db: Session = Depends(get_db)):
    # ... (código se mantiene igual)
    try:
        importer = GTFSImporter(db)
        result = importer.import_gtfs(file.file, agency_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- ENDPOINT DEL MAPA: OPTIMIZADO CON ORDEN Y DIRECCIÓN DE PARADAS ---
@router.get("/routes-with-details")
async def get_routes_with_details(db: Session = Depends(get_db)):
    """
    Endpoint optimizado que devuelve rutas con trazados y paradas
    ordenadas por secuencia y agrupadas por dirección (sentido).
    """
    start_time = time.time()
    print("🚀 Iniciando consulta optimizada V3 (con orden y dirección)...")
    try:
        # 1. Carga masiva de datos base
        print("   - Cargando rutas...")
        routes = db.query(Route).all()
        print(f"     -> {len(routes)} rutas cargadas.")

        print("   - Cargando paradas...")
        stops = db.query(Stop.stop_id, Stop.stop_name, Stop.stop_lat, Stop.stop_lon).all()
        stops_map = {s.stop_id: {"stop_id": s.stop_id, "stop_name": s.stop_name, "stop_lat": s.stop_lat, "stop_lon": s.stop_lon} for s in stops}
        print(f"     -> {len(stops_map)} paradas mapeadas.")
        
        print("   - Cargando shapes...")
        shapes_tuples = db.query(Shape.shape_id, Shape.shape_pt_lat, Shape.shape_pt_lon, Shape.shape_pt_sequence).order_by(Shape.shape_id, Shape.shape_pt_sequence).all()
        shapes_map = defaultdict(list)
        for shape_id, lat, lon, _ in shapes_tuples:
            shapes_map[shape_id].append([lat, lon])
        print(f"     -> {len(shapes_map)} shapes procesados.")

        # 2. Consulta optimizada para Trips y StopTimes CON ORDEN Y DIRECCIÓN
        print("   - Cargando y procesando viajes y tiempos de parada (ordenados)...")
        trips_stoptimes_start = time.time()
        
        # Obtenemos Trip (con route_id, shape_id, direction_id) y StopTime (con stop_id, stop_sequence)
        # Ordenamos por route_id, direction_id, trip_id (para agrupar), y stop_sequence
        query = db.query(
                Trip.route_id, 
                Trip.trip_id, 
                Trip.direction_id, 
                Trip.shape_id, 
                StopTime.stop_id, 
                StopTime.stop_sequence
            )\
            .join(StopTime, Trip.trip_id == StopTime.trip_id)\
            .order_by(
                Trip.route_id, 
                Trip.direction_id, 
                # Podríamos agrupar por un trip representativo si hay muchos, pero por ahora tomamos todos
                # Trip.trip_id, 
                StopTime.stop_sequence.asc() # Orden ascendente por secuencia
            )
            
        results = query.all()
        print(f"     -> {len(results)} registros de stop_times con info de trip cargados. ({(time.time() - trips_stoptimes_start):.2f}s)")

        # 3. Procesar resultados para agrupar paradas por ruta y dirección
        print("   - Agrupando paradas por ruta y dirección...")
        processing_start = time.time()
        route_stops_by_direction = defaultdict(lambda: defaultdict(list))
        # También guardamos los shapes por ruta/dirección para asociarlos
        route_shapes_by_direction = defaultdict(lambda: defaultdict(set)) 
        
        # Usamos un set para evitar duplicados de paradas *dentro* de una misma secuencia/dirección/ruta
        # Mantenemos el orden gracias a la consulta ordenada
        processed_stops = defaultdict(lambda: defaultdict(set)) 

        for route_id, trip_id, direction_id, shape_id, stop_id, stop_sequence in results:
            # Asegura que direction_id sea 0 o 1, default a 0 si es None o inválido
            dir_key = direction_id if direction_id in [0, 1] else 0 
            
            # Añade shape_id al set de la dirección correspondiente
            if shape_id:
                route_shapes_by_direction[route_id][dir_key].add(shape_id)
                
            # Añade parada si no está ya en el set para esta secuencia
            stop_tuple = (stop_sequence, stop_id) # Usamos tupla para el set
            if stop_tuple not in processed_stops[route_id][dir_key]:
                 stop_info = stops_map.get(stop_id)
                 if stop_info:
                     # Guardamos la info completa de la parada junto con su secuencia
                     route_stops_by_direction[route_id][dir_key].append({
                         **stop_info, 
                         "stop_sequence": stop_sequence 
                     })
                     processed_stops[route_id][dir_key].add(stop_tuple)
        
        print(f"     -> Agrupación completada. ({(time.time() - processing_start):.2f}s)")

        # 4. Ensamblar la respuesta final
        print("   - Ensamblando respuesta final...")
        assembly_start = time.time()
        response_data = []
        for route in routes:
            stops_dir_0 = route_stops_by_direction[route.route_id].get(0, [])
            stops_dir_1 = route_stops_by_direction[route.route_id].get(1, [])
            
            shapes_dir_0_ids = route_shapes_by_direction[route.route_id].get(0, set())
            shapes_dir_1_ids = route_shapes_by_direction[route.route_id].get(1, set())

            # Obtiene las coordenadas de los shapes para cada dirección
            shapes_dir_0 = [shapes_map[s_id] for s_id in shapes_dir_0_ids if s_id in shapes_map]
            shapes_dir_1 = [shapes_map[s_id] for s_id in shapes_dir_1_ids if s_id in shapes_map]
            
            response_data.append({
                "route_id": route.route_id,
                "route_short_name": route.route_short_name,
                "route_long_name": route.route_long_name,
                "route_color": route.route_color,
                # Devolvemos shapes y stops separados por dirección
                "direction_0": {
                    "stops": stops_dir_0,
                    "shapes": shapes_dir_0
                },
                "direction_1": {
                    "stops": stops_dir_1,
                    "shapes": shapes_dir_1
                }
            })
            
        total_time = time.time() - start_time
        print(f"   - Ensamblaje completado. ({time.time() - assembly_start:.2f}s)")
        print(f"✅ Consulta V3 completada en {total_time:.2f} segundos.")
        return response_data
        
    except Exception as e:
        import traceback
        print(f"❌ Error durante la consulta V3: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar datos del mapa V3: {str(e)}")