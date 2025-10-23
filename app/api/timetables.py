# app/api/timetables.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import time, datetime
from collections import defaultdict

from app.database import get_db
from app.models.gtfs_models import Route, Trip, StopTime, Stop, Calendar, Shape

router = APIRouter(prefix="/timetables", tags=["Timetables"])


# ===== SCHEMAS =====

class TimetableRequest(BaseModel):
    """Request para generar timetable"""
    route_id: str
    service_id: str
    stop_ids: List[int]
    time_range: Optional[Dict[str, str]] = {"start": "00:00", "end": "23:59"}


class StopInfo(BaseModel):
    """Información de una parada"""
    stop_id: int
    stop_name: str
    stop_sequence: int
    direction_id: int


# ===== FUNCIONES AUXILIARES =====

def extract_bus_number(block_id: str) -> str:
    """
    Extrae el número de bus del block_id.
    Ejemplo: "580.1" → "1", "580.2" → "2"
    """
    if not block_id or '.' not in block_id:
        return "N/A"
    
    try:
        # Tomar el número después del punto
        bus_num = block_id.split('.')[-1]
        return bus_num
    except:
        return "N/A"


def time_to_str(t: Optional[time]) -> Optional[str]:
    """Convierte objeto time a string HH:MM"""
    if t is None:
        return None
    return t.strftime("%H:%M")


def parse_time_filter(time_str: str) -> time:
    """Parsea string HH:MM a objeto time"""
    try:
        h, m = map(int, time_str.split(':'))
        return time(hour=h, minute=m)
    except:
        return time(0, 0)


def get_service_days_description(calendar: Calendar) -> str:
    """Genera descripción de días del servicio"""
    days = []
    if calendar.monday: days.append("Lunes")
    if calendar.tuesday: days.append("Martes")
    if calendar.wednesday: days.append("Miércoles")
    if calendar.thursday: days.append("Jueves")
    if calendar.friday: days.append("Viernes")
    if calendar.saturday: days.append("Sábado")
    if calendar.sunday: days.append("Domingo")
    
    if not days:
        return "Sin días definidos"
    
    # Simplificar si es L-V o S-D
    if len(days) == 5 and "Lunes" in days and "Viernes" in days:
        return "Lunes a Viernes"
    elif len(days) == 2 and "Sábado" in days and "Domingo" in days:
        return "Sábados y Domingos"
    elif len(days) == 7:
        return "Diario"
    else:
        return ", ".join(days)


# ===== ENDPOINTS =====

@router.get("/route-stops/{route_id}")
async def get_route_stops(route_id: str, db: Session = Depends(get_db)):
    """
    Obtiene todas las paradas de una ruta (ambos sentidos),
    ordenadas por dirección y secuencia.
    """
    print(f"[Timetables API] ✅ Endpoint llamado: /route-stops/{route_id}")
    
    try:
        # Verificar que la ruta existe
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            print(f"[Timetables API] ❌ Ruta no encontrada: {route_id}")
            raise HTTPException(status_code=404, detail=f"Ruta '{route_id}' no encontrada")
        
        print(f"[Timetables API] ✅ Ruta encontrada: {route.route_short_name}")
        
        # Obtener trips de la ruta
        trips = db.query(Trip).filter(Trip.route_id == route_id).all()
        
        if not trips:
            print(f"[Timetables API] ⚠️ No hay trips para ruta {route_id}")
            return {"stops": []}
        
        print(f"[Timetables API] ✅ {len(trips)} trips encontrados")
        
        trip_ids = [t.trip_id for t in trips]
        
        # Obtener stop_times de esos trips
        stop_times = db.query(StopTime, Stop, Trip)\
            .join(Stop, StopTime.stop_id == Stop.stop_id)\
            .join(Trip, StopTime.trip_id == Trip.trip_id)\
            .filter(StopTime.trip_id.in_(trip_ids))\
            .order_by(Trip.direction_id, StopTime.stop_sequence)\
            .all()
        
        print(f"[Timetables API] ✅ {len(stop_times)} stop_times encontrados")
        
        # Agrupar paradas únicas (evitar duplicados)
        stops_dict = {}
        for st, stop, trip in stop_times:
            key = (stop.stop_id, trip.direction_id)
            if key not in stops_dict:
                stops_dict[key] = {
                    "stop_id": stop.stop_id,
                    "stop_name": stop.stop_name,
                    "stop_sequence": st.stop_sequence,
                    "direction_id": trip.direction_id or 0
                }
        
        stops_list = list(stops_dict.values())
        
        # Ordenar por dirección y secuencia
        stops_list.sort(key=lambda x: (x['direction_id'], x['stop_sequence']))
        
        print(f"[Timetables API] ✅ {len(stops_list)} paradas únicas devueltas")
        
        return {"stops": stops_list}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Timetables API] ❌ Error obteniendo paradas: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_timetable(request: TimetableRequest, db: Session = Depends(get_db)):
    """
    Genera un timetable consolidado mostrando ciclos completos por bus:
    S1 → S2 → S1 agrupados en una fila por ciclo.
    """
    print(f"[Timetables API] Generando timetable para ruta {request.route_id}, servicio {request.service_id}")
    
    try:
        # Obtener información de la ruta
        route = db.query(Route).filter(Route.route_id == request.route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        
        # Obtener shape para calcular distancia
        shapes = db.query(Shape).filter(Shape.shape_id.like(f"{request.route_id}%")).all()
        route_distance = 0
        if shapes:
            max_dist = max([s.shape_dist_traveled or 0 for s in shapes], default=0)
            route_distance = round(max_dist / 1000, 2)  # Convertir a km
        
        # Obtener información del servicio
        calendar = db.query(Calendar).filter(Calendar.service_id == request.service_id).first()
        if not calendar:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        
        # Obtener trips de la ruta con el servicio especificado
        trips = db.query(Trip).filter(
            and_(
                Trip.route_id == request.route_id,
                Trip.service_id == request.service_id
            )
        ).all()
        
        if not trips:
            raise HTTPException(
                status_code=404, 
                detail="No se encontraron viajes para esta combinación de ruta y servicio"
            )
        
        print(f"  → {len(trips)} trips encontrados")
        
        # Parsear rango de tiempo
        time_start = parse_time_filter(request.time_range['start'])
        time_end = parse_time_filter(request.time_range['end'])
        
        # Agrupar trips por bus (block_id) y dirección
        trips_by_bus = defaultdict(lambda: {"dir_0": [], "dir_1": []})
        for trip in trips:
            bus_number = extract_bus_number(trip.block_id or "")
            direction = trip.direction_id or 0
            trip_data = {
                "trip": trip,
                "start_time": get_trip_start_time(db, trip.trip_id)
            }
            if direction == 0:
                trips_by_bus[bus_number]["dir_0"].append(trip_data)
            else:
                trips_by_bus[bus_number]["dir_1"].append(trip_data)
        
        # Ordenar trips de cada dirección por hora de salida
        for bus_number in trips_by_bus:
            trips_by_bus[bus_number]["dir_0"].sort(key=lambda x: x["start_time"] or time(0, 0))
            trips_by_bus[bus_number]["dir_1"].sort(key=lambda x: x["start_time"] or time(0, 0))
        
        # Construir ciclos completos (S1 → S2 → S1)
        consolidated_cycles = []
        cycle_counter = 1
        
        for bus_number in sorted(trips_by_bus.keys()):
            dir_0_trips = trips_by_bus[bus_number]["dir_0"]
            dir_1_trips = trips_by_bus[bus_number]["dir_1"]
            
            # Emparejar viajes dir_0 con dir_1 siguientes
            idx_1 = 0
            for trip_0_data in dir_0_trips:
                trip_0 = trip_0_data["trip"]
                
                # Buscar el siguiente viaje en dir_1
                trip_1 = None
                trip_1_data = None
                while idx_1 < len(dir_1_trips):
                    if dir_1_trips[idx_1]["start_time"] and trip_0_data["start_time"]:
                        if dir_1_trips[idx_1]["start_time"] >= trip_0_data["start_time"]:
                            trip_1_data = dir_1_trips[idx_1]
                            trip_1 = trip_1_data["trip"]
                            idx_1 += 1
                            break
                    idx_1 += 1
                
                # Obtener horarios para dir_0
                stop_times_dir_0 = get_stop_times_for_trip(
                    db, trip_0.trip_id, request.stop_ids, time_start, time_end
                )
                
                # Obtener horarios para dir_1 si existe
                stop_times_dir_1 = []
                if trip_1:
                    stop_times_dir_1 = get_stop_times_for_trip(
                        db, trip_1.trip_id, request.stop_ids, time_start, time_end
                    )
                
                # Calcular intervalos y duraciones
                first_stop_dir_0 = next((st for st in stop_times_dir_0 if st["arrival_time"]), None)
                last_stop_dir_0 = next((st for st in reversed(stop_times_dir_0) if st["arrival_time"]), None)
                first_stop_dir_1 = next((st for st in stop_times_dir_1 if st["arrival_time"]), None) if stop_times_dir_1 else None
                last_stop_dir_1 = next((st for st in reversed(stop_times_dir_1) if st["arrival_time"]), None) if stop_times_dir_1 else None
                
                cycle_data = {
                    "recorrido": cycle_counter,
                    "bus_number": bus_number,
                    "dir_0": {
                        "first_stop_time": first_stop_dir_0["arrival_time"] if first_stop_dir_0 else None,
                        "last_stop_time": last_stop_dir_0["arrival_time"] if last_stop_dir_0 else None,
                        "stop_times": stop_times_dir_0
                    },
                    "dir_1": {
                        "first_stop_time": first_stop_dir_1["arrival_time"] if first_stop_dir_1 else None,
                        "last_stop_time": last_stop_dir_1["arrival_time"] if last_stop_dir_1 else None,
                        "stop_times": stop_times_dir_1
                    },
                    "distance_km": route_distance
                }
                
                consolidated_cycles.append(cycle_data)
                cycle_counter += 1
        
        # Obtener información de las paradas seleccionadas con dirección
        stops_by_direction = {"dir_0": [], "dir_1": []}
        for stop_id in request.stop_ids:
            stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
            if stop:
                # Determinar dirección de la parada
                stop_time_sample = db.query(StopTime, Trip).join(Trip).filter(
                    and_(
                        StopTime.stop_id == stop_id,
                        Trip.route_id == request.route_id
                    )
                ).first()
                
                if stop_time_sample:
                    direction = stop_time_sample[1].direction_id or 0
                    stop_info = {
                        "stop_id": stop.stop_id,
                        "stop_name": stop.stop_name
                    }
                    if direction == 0:
                        stops_by_direction["dir_0"].append(stop_info)
                    else:
                        stops_by_direction["dir_1"].append(stop_info)
        
        # Preparar respuesta
        result = {
            "route_id": request.route_id,
            "route_name": f"{route.route_short_name} - {route.route_long_name}",
            "service_id": request.service_id,
            "service_days": get_service_days_description(calendar),
            "stops_by_direction": stops_by_direction,
            "cycles": consolidated_cycles,
            "total_cycles": len(consolidated_cycles),
            "route_distance_km": route_distance
        }
        
        print(f"✅ Timetable generado: {len(consolidated_cycles)} ciclos")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generando timetable: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando timetable: {str(e)}")


def get_stop_times_for_trip(
    db: Session, 
    trip_id: str, 
    stop_ids: List[int], 
    time_start: time, 
    time_end: time
) -> List[Dict]:
    """Obtiene los horarios de un trip para las paradas especificadas"""
    stop_times_data = []
    
    for stop_id in stop_ids:
        st = db.query(StopTime).filter(
            and_(
                StopTime.trip_id == trip_id,
                StopTime.stop_id == stop_id
            )
        ).first()
        
        if st and st.arrival_time:
            # Verificar si está en el rango de tiempo
            if st.arrival_time >= time_start and st.arrival_time <= time_end:
                stop_times_data.append({
                    "stop_id": stop_id,
                    "arrival_time": time_to_str(st.arrival_time),
                    "departure_time": time_to_str(st.departure_time)
                })
            else:
                stop_times_data.append({
                    "stop_id": stop_id,
                    "arrival_time": None,
                    "departure_time": None
                })
        else:
            stop_times_data.append({
                "stop_id": stop_id,
                "arrival_time": None,
                "departure_time": None
            })
    
    return stop_times_data


def get_trip_start_time(db: Session, trip_id: str) -> Optional[time]:
    """Obtiene la hora de inicio de un trip (primera parada)"""
    first_stop = db.query(StopTime).filter(
        StopTime.trip_id == trip_id
    ).order_by(StopTime.stop_sequence).first()
    
    return first_stop.departure_time if first_stop else None