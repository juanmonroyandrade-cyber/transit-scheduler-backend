# app/api/timetables.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select, text # Asegúrate de importar text si usas SQL directo
from app import models, database # Importa tus modelos y config de BD
from datetime import time, timedelta
from collections import defaultdict
import re
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/api", # Prefijo común para las rutas de este módulo
    tags=["timetables"], # Etiqueta para la documentación de Swagger/OpenAPI
)

# --- Dependencia para obtener la sesión de BD ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Funciones de Utilidad ---
def parse_time_to_seconds(time_str: Optional[str]) -> Optional[int]:
    """Parsea HH:MM:SS a segundos desde medianoche, maneja None y horas > 24."""
    if time_str is None:
        return None
    try:
        # Permite horas mayores a 23 y maneja potencial error si split falla
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2: # Si solo viene HH:MM
             return parts[0] * 3600 + parts[1] * 60
        return None # Formato inesperado
    except (ValueError, IndexError, AttributeError):
        # AttributeError añadido por si time_str no es string
        return None

def format_time_from_seconds(total_seconds: Optional[int]) -> Optional[str]:
    """Convierte segundos desde medianoche a HH:MM."""
    if total_seconds is None:
        return None
    try:
        # Asegurarse que es un entero
        total_seconds = int(total_seconds)
        # Manejar segundos negativos si fuera posible (aunque no debería en tiempos GTFS)
        if total_seconds < 0:
            return None # O manejar como prefieras
        # Calcular horas y minutos, permitiendo horas > 23
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return None

def get_bus_number_from_block(block_id: Optional[str]) -> Optional[int]:
    """Extrae el número de bus del block_id (asume formato XXX.Y)."""
    if not block_id or '.' not in block_id:
        return None
    try:
        # Busca un punto seguido de dígitos al final de la cadena
        match = re.search(r'\.(\d+)$', block_id)
        return int(match.group(1)) if match else None
    except (ValueError, AttributeError):
        return None

# --- Endpoint ---
@router.get("/generate_chained_timetable/", response_model=Dict[str, Any])
async def generate_chained_timetable(
    route_id: str = Query(..., description="ID de la ruta GTFS"),
    service_id: str = Query(..., description="ID del servicio/calendario GTFS"),
    selected_stop_ids: List[str] = Query(..., description="Lista ordenada de IDs de parada (Centro, ..., Barrio, ..., Centro)"),
    db: Session = Depends(get_db)
):
    """
    Genera un horario encadenado por bus (block_id) para una ruta y servicio,
    mostrando solo las paradas seleccionadas en el orden especificado.
    """
    if len(selected_stop_ids) < 2:
        raise HTTPException(status_code=400, detail="Se requieren al menos 2 paradas seleccionadas (origen y destino).")

    # 1. Validar y Obtener Nombres de Parada (Stops) en el orden solicitado
    try:
        stops_query = db.query(models.Stop).filter(models.Stop.stop_id.in_(selected_stop_ids)).all()
        stops_dict = {stop.stop_id: stop.stop_name for stop in stops_query}
    except Exception as e:
        # Captura errores generales de BD al consultar paradas
        raise HTTPException(status_code=500, detail=f"Error al consultar paradas: {e}")

    ordered_stop_names = []
    missing_stops = []
    for stop_id in selected_stop_ids:
        name = stops_dict.get(stop_id)
        if name:
            ordered_stop_names.append(name)
        else:
            missing_stops.append(stop_id)

    if missing_stops:
        raise HTTPException(status_code=404, detail=f"No se encontraron las siguientes paradas en la BD: {', '.join(missing_stops)}")

    # Construir encabezados finales
    headers = ["Corridas", "Bus"] + ordered_stop_names

    # 2. Obtener Viajes (Trips)
    try:
        trips = db.query(models.Trip)\
            .filter(models.Trip.route_id == route_id, models.Trip.service_id == service_id)\
            .order_by(models.Trip.block_id)\
            .all()
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error al consultar viajes: {e}")

    if not trips:
         # Devolver estructura vacía si no hay viajes, no es un error 404
        return {"headers": headers, "corridas": [], "stop_ids_ordered": selected_stop_ids}

    trip_ids = [trip.trip_id for trip in trips]

    # 3. Obtener Tiempos de Parada (StopTimes) SOLO para paradas seleccionadas y viajes filtrados
    try:
        stop_times = db.query(models.StopTime)\
            .filter(models.StopTime.trip_id.in_(trip_ids), models.StopTime.stop_id.in_(selected_stop_ids))\
            .order_by(models.StopTime.trip_id, models.StopTime.stop_sequence)\
            .all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar tiempos de parada: {e}")


    # 4. Agrupar StopTimes por Trip ID y calcular tiempo de inicio del trip
    stop_times_by_trip = defaultdict(lambda: {stop_id: None for stop_id in selected_stop_ids})
    trip_start_times = {} # trip_id -> start_time_seconds

    # Para calcular el start_time, necesitamos la primera parada REAL del viaje, no solo las seleccionadas
    try:
        first_stop_times_query = db.query(
                models.StopTime.trip_id,
                func.min(models.StopTime.stop_sequence).label('min_sequence')
            )\
            .filter(models.StopTime.trip_id.in_(trip_ids))\
            .group_by(models.StopTime.trip_id)\
            .subquery()

        first_stop_times = db.query(models.StopTime)\
            .join(first_stop_times_query,
                  (models.StopTime.trip_id == first_stop_times_query.c.trip_id) &
                  (models.StopTime.stop_sequence == first_stop_times_query.c.min_sequence)
            ).all()

        for st in first_stop_times:
            start_time_str = st.departure_time or st.arrival_time
            start_seconds = parse_time_to_seconds(start_time_str)
            if start_seconds is not None:
                trip_start_times[st.trip_id] = start_seconds

    except Exception as e:
        # Podríamos continuar sin ordenar perfectamente o lanzar error
         raise HTTPException(status_code=500, detail=f"Error al obtener tiempos de inicio de viaje: {e}")

    # Ahora sí, agrupar los tiempos de las paradas SELECCIONADAS
    for st in stop_times:
        time_in_seconds = parse_time_to_seconds(st.departure_time or st.arrival_time)
        # Solo almacenar si el tiempo es válido
        if time_in_seconds is not None:
            stop_times_by_trip[st.trip_id][st.stop_id] = time_in_seconds

    # 5. Agrupar Trips por Block ID
    trips_by_block = defaultdict(list)
    for trip in trips:
        # Solo incluir trips que tengan tiempo de inicio calculado y al menos un stop_time en las paradas seleccionadas
        if trip.trip_id in trip_start_times and trip.trip_id in stop_times_by_trip:
            # Asignar el tiempo de inicio calculado al objeto trip para ordenar
            trip.start_time_seconds = trip_start_times[trip.trip_id]
            trips_by_block[trip.block_id].append(trip)

    # Ordenar viajes dentro de cada bloque por hora de inicio
    for block_id in trips_by_block:
        trips_by_block[block_id].sort(key=lambda t: t.start_time_seconds)

    # 6. Procesar Corridas Empalmadas
    processed_corridas = []
    processed_trip_ids = set() # Evitar duplicados

    sorted_block_ids = sorted(trips_by_block.keys(), key=lambda x: (get_bus_number_from_block(x) or float('inf'), x or ""))

    for block_id in sorted_block_ids:
        bus_number = get_bus_number_from_block(block_id)
        block_trips = trips_by_block[block_id]

        for i, trip1 in enumerate(block_trips):
            if trip1.trip_id in processed_trip_ids:
                continue

            # Iniciar nueva corrida
            corrida_data = {
                "id": f"{block_id}_{trip1.trip_id}",
                "bus": bus_number,
                "times": {stop_id: None for stop_id in selected_stop_ids},
                "first_time_seconds": trip1.start_time_seconds # Para ordenar
            }
            trip1_times_dict = stop_times_by_trip.get(trip1.trip_id, {})

            # Lógica Asumiendo: direction_id=0 es IDA, direction_id=1 es VUELTA
            # Y selected_stop_ids = [CentroIda, ..., Barrio, ..., CentroVuelta]
            # Podría necesitar ajustes si el orden o los IDs de dirección son diferentes

            if trip1.direction_id == 0: # IDA
                # Copiar tiempos de IDA
                for stop_id in selected_stop_ids:
                    if trip1_times_dict.get(stop_id) is not None:
                         corrida_data["times"][stop_id] = format_time_from_seconds(trip1_times_dict[stop_id])
                processed_trip_ids.add(trip1.trip_id)

                # Buscar siguiente trip de VUELTA (direction_id=1)
                if i + 1 < len(block_trips):
                    trip2 = block_trips[i+1]
                    if trip2.direction_id == 1 and trip2.trip_id not in processed_trip_ids:
                        trip2_times_dict = stop_times_by_trip.get(trip2.trip_id, {})
                        # Copiar tiempos de VUELTA (solo si no existen o son paradas posteriores)
                        # Esta lógica asume que las paradas de selected_stop_ids están ordenadas lógicamente
                        last_stop_index_trip1 = -1
                        for idx, stop_id in enumerate(selected_stop_ids):
                             if corrida_data["times"][stop_id] is not None:
                                 last_stop_index_trip1 = idx

                        for idx, stop_id in enumerate(selected_stop_ids):
                            # Añadir tiempo de trip2 si:
                            # 1. No había tiempo de trip1 O
                            # 2. La parada está DESPUÉS de la última parada con tiempo de trip1
                            if trip2_times_dict.get(stop_id) is not None and \
                               (corrida_data["times"][stop_id] is None or idx > last_stop_index_trip1):
                                 corrida_data["times"][stop_id] = format_time_from_seconds(trip2_times_dict[stop_id])
                        processed_trip_ids.add(trip2.trip_id)

            elif trip1.direction_id == 1: # VUELTA (Corrida incompleta al inicio)
                 # Copiar tiempos de VUELTA
                 for stop_id in selected_stop_ids:
                     if trip1_times_dict.get(stop_id) is not None:
                         corrida_data["times"][stop_id] = format_time_from_seconds(trip1_times_dict[stop_id])
                 processed_trip_ids.add(trip1.trip_id)

            # Añadir la corrida solo si tiene al menos un tiempo registrado
            if any(corrida_data["times"].values()):
                 processed_corridas.append(corrida_data)

    # Ordenar corridas por la hora del primer trip
    processed_corridas.sort(key=lambda c: c["first_time_seconds"])

    # Añadir número de corrida y limpiar
    for idx, corrida in enumerate(processed_corridas):
        corrida["corrida_num"] = idx + 1
        del corrida["first_time_seconds"] # Ya no es necesario

    return {"headers": headers, "corridas": processed_corridas, "stop_ids_ordered": selected_stop_ids}