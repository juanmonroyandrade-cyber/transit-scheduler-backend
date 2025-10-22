# app/api/timetables.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import time, datetime
from collections import defaultdict

from app.database import get_db
from app.models.gtfs_models import Route, Trip, StopTime, Stop, Calendar

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
    print(f"[Timetables API] Obteniendo paradas para ruta {route_id}")
    
    try:
        # Obtener trips de la ruta
        trips = db.query(Trip).filter(Trip.route_id == route_id).all()
        
        if not trips:
            return {"stops": []}
        
        trip_ids = [t.trip_id for t in trips]
        
        # Obtener stop_times de esos trips
        stop_times = db.query(StopTime, Stop, Trip)\
            .join(Stop, StopTime.stop_id == Stop.stop_id)\
            .join(Trip, StopTime.trip_id == Trip.trip_id)\
            .filter(StopTime.trip_id.in_(trip_ids))\
            .order_by(Trip.direction_id, StopTime.stop_sequence)\
            .all()
        
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
        
        print(f"✅ {len(stops_list)} paradas encontradas para ruta {route_id}")
        
        return {"stops": stops_list}
        
    except Exception as e:
        print(f"❌ Error obteniendo paradas: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_timetable(request: TimetableRequest, db: Session = Depends(get_db)):
    """
    Genera un timetable consolidado mostrando viajes consecutivos:
    S1 → S2 → S1 con sus horarios completos y número de bus.
    """
    print(f"[Timetables API] Generando timetable para ruta {request.route_id}, servicio {request.service_id}")
    
    try:
        # Obtener información de la ruta
        route = db.query(Route).filter(Route.route_id == request.route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        
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
        
        # Agrupar trips por bus (block_id)
        trips_by_bus = defaultdict(list)
        for trip in trips:
            bus_number = extract_bus_number(trip.block_id or "")
            trips_by_bus[bus_number].append(trip)
        
        # Ordenar trips de cada bus por hora de salida
        for bus_number in trips_by_bus:
            trips_by_bus[bus_number].sort(
                key=lambda t: get_trip_start_time(db, t.trip_id) or time(0, 0)
            )
        
        # Construir tabla de horarios consolidada
        consolidated_trips = []
        
        for bus_number, bus_trips in sorted(trips_by_bus.items()):
            # Procesar trips consecutivos de este bus
            for trip_idx, trip in enumerate(bus_trips, start=1):
                # Obtener stop_times para las paradas seleccionadas
                stop_times_data = []
                
                for stop_id in request.stop_ids:
                    st = db.query(StopTime).filter(
                        and_(
                            StopTime.trip_id == trip.trip_id,
                            StopTime.stop_id == stop_id
                        )
                    ).first()
                    
                    if st:
                        # Filtrar por rango de tiempo
                        if st.arrival_time:
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
                    else:
                        stop_times_data.append({
                            "stop_id": stop_id,
                            "arrival_time": None,
                            "departure_time": None
                        })
                
                # Determinar secuencia del viaje (ej: "S1→S2", "S2→S1")
                direction = trip.direction_id or 0
                trip_sequence = f"S{direction+1}→S{2 - direction}"
                
                consolidated_trips.append({
                    "trip_id": trip.trip_id,
                    "bus_number": bus_number,
                    "trip_sequence": trip_sequence,
                    "direction_id": direction,
                    "stop_times": stop_times_data
                })
        
        # Obtener información de las paradas seleccionadas
        selected_stops_info = []
        for stop_id in request.stop_ids:
            stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
            if stop:
                selected_stops_info.append({
                    "stop_id": stop.stop_id,
                    "stop_name": stop.stop_name
                })
        
        # Preparar respuesta
        result = {
            "route_id": request.route_id,
            "route_name": f"{route.route_short_name} - {route.route_long_name}",
            "service_id": request.service_id,
            "service_days": get_service_days_description(calendar),
            "selected_stops": selected_stops_info,
            "trips": consolidated_trips,
            "total_trips": len(consolidated_trips),
            "total_buses": len(trips_by_bus)
        }
        
        print(f"✅ Timetable generado: {len(consolidated_trips)} viajes, {len(trips_by_bus)} buses")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generando timetable: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando timetable: {str(e)}")


def get_trip_start_time(db: Session, trip_id: str) -> Optional[time]:
    """Obtiene la hora de inicio de un trip (primera parada)"""
    first_stop = db.query(StopTime).filter(
        StopTime.trip_id == trip_id
    ).order_by(StopTime.stop_sequence).first()
    
    return first_stop.departure_time if first_stop else None