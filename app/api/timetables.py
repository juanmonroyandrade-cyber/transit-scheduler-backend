# VERSIÓN FINAL CORRECTA - S1 y S2 como sentidos INDEPENDIENTES
# app/api/timetables.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import gtfs_models
from collections import defaultdict
import re
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/api",
    tags=["timetables"],
)

def parse_time_to_seconds(time_str: Optional[str]) -> Optional[int]:
    if time_str is None:
        return None
    try:
        parts = list(map(int, str(time_str).split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 3600 + parts[1] * 60
        return None
    except:
        return None

def format_time_from_seconds(total_seconds: Optional[int]) -> Optional[str]:
    if total_seconds is None:
        return None
    try:
        total_seconds = int(total_seconds)
        if total_seconds < 0:
            return None
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    except:
        return None

def get_bus_number_from_block(block_id: Optional[str]) -> Optional[int]:
    if not block_id:
        return None
    try:
        block_str = str(block_id)
        
        # Buscar patrón: número después de punto (.) o guión bajo (_)
        # Ejemplos: "block_1.5" -> 5, "block_1_5" -> 5, "R1_05" -> 5
        
        # Primero intenta con punto
        match_dot = re.search(r'\.(\d+)$', block_str)
        if match_dot:
            return int(match_dot.group(1))
        
        # Si no hay punto, intenta con guión bajo
        match_underscore = re.search(r'_(\d+)$', block_str)
        if match_underscore:
            return int(match_underscore.group(1))
        
        # Si no encuentra ninguno, devolver None
        return None
    except:
        return None

@router.get("/available_services/")
async def get_available_services(
    route_id: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        trips = db.query(gtfs_models.Trip.service_id).filter(
            gtfs_models.Trip.route_id == route_id
        ).distinct().all()

        service_ids = [trip.service_id for trip in trips]
        if not service_ids:
            return []

        calendars = db.query(gtfs_models.Calendar).filter(
            gtfs_models.Calendar.service_id.in_(service_ids)
        ).all()

        result = []
        for calendar in calendars:
            days = []
            if calendar.monday: days.append("Lun")
            if calendar.tuesday: days.append("Mar")
            if calendar.wednesday: days.append("Mié")
            if calendar.thursday: days.append("Jue")
            if calendar.friday: days.append("Vie")
            if calendar.saturday: days.append("Sáb")
            if calendar.sunday: days.append("Dom")

            result.append({
                "service_id": calendar.service_id,
                "days": ", ".join(days) if days else "Sin días",
                "start_date": str(calendar.start_date) if calendar.start_date else None,
                "end_date": str(calendar.end_date) if calendar.end_date else None
            })

        if not result:
            for service_id in service_ids:
                result.append({
                    "service_id": service_id,
                    "days": "Sin calendario",
                    "start_date": None,
                    "end_date": None
                })

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route_stops/")
async def get_route_stops(
    route_id: str = Query(...),
    direction_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        trip_query = db.query(gtfs_models.Trip).filter(
            gtfs_models.Trip.route_id == route_id
        )
        
        if direction_id is not None:
            trip_query = trip_query.filter(gtfs_models.Trip.direction_id == direction_id)
        
        trips = trip_query.all()
        if not trips:
            return []

        trip_ids = [trip.trip_id for trip in trips]
        
        stop_counts = db.query(
            gtfs_models.StopTime.trip_id,
            func.count(gtfs_models.StopTime.stop_id).label('count')
        ).filter(
            gtfs_models.StopTime.trip_id.in_(trip_ids)
        ).group_by(gtfs_models.StopTime.trip_id).order_by(
            func.count(gtfs_models.StopTime.stop_id).desc()
        ).first()

        if not stop_counts:
            return []

        longest_trip_id = stop_counts.trip_id
        stop_times = db.query(gtfs_models.StopTime).filter(
            gtfs_models.StopTime.trip_id == longest_trip_id
        ).order_by(gtfs_models.StopTime.stop_sequence).all()

        stop_ids = [st.stop_id for st in stop_times]
        stops = db.query(gtfs_models.Stop).filter(
            gtfs_models.Stop.stop_id.in_(stop_ids)
        ).all()

        stops_dict = {stop.stop_id: stop for stop in stops}

        result = []
        for st in stop_times:
            stop = stops_dict.get(st.stop_id)
            if stop:
                result.append({
                    "stop_id": str(stop.stop_id),
                    "stop_name": stop.stop_name,
                    "stop_sequence": st.stop_sequence,
                    "stop_lat": float(stop.stop_lat) if stop.stop_lat else None,
                    "stop_lon": float(stop.stop_lon) if stop.stop_lon else None
                })

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate_chained_timetable/")
async def generate_chained_timetable(
    route_id: str = Query(...),
    service_id: str = Query(...),
    selected_stop_ids: List[str] = Query(...),
    db: Session = Depends(get_db)
):
    """
    VERSIÓN FINAL CORRECTA:
    - S1 y S2 son INDEPENDIENTES (diferentes directions)
    - Cada sentido tiene sus propias paradas y secuencias
    - Solo se muestran las seleccionadas de cada sentido
    """
    
    print(f"\n{'='*70}")
    print(f"🚀 GENERANDO HORARIO - S1 Y S2 INDEPENDIENTES")
    print(f"{'='*70}")
    print(f"📍 Ruta: {route_id}")
    print(f"📅 Servicio: {service_id}")
    print(f"🚏 Paradas seleccionadas: {len(selected_stop_ids)}")
    
    if len(selected_stop_ids) < 2:
        raise HTTPException(status_code=400, detail="Mínimo 2 paradas")

    try:
        # 1. Obtener trip de SENTIDO 1 (direction_id=0)
        trip_s1 = db.query(gtfs_models.Trip).filter(
            gtfs_models.Trip.route_id == route_id,
            gtfs_models.Trip.service_id == service_id,
            gtfs_models.Trip.direction_id == 0
        ).first()
        
        # 2. Obtener trip de SENTIDO 2 (direction_id=1)
        trip_s2 = db.query(gtfs_models.Trip).filter(
            gtfs_models.Trip.route_id == route_id,
            gtfs_models.Trip.service_id == service_id,
            gtfs_models.Trip.direction_id == 1
        ).first()
        
        if not trip_s1 or not trip_s2:
            raise HTTPException(status_code=404, detail="No hay trips para ambos sentidos")
        
        # 3. Obtener TODAS las paradas de S1 ordenadas
        stop_times_s1 = db.query(gtfs_models.StopTime).filter(
            gtfs_models.StopTime.trip_id == trip_s1.trip_id
        ).order_by(gtfs_models.StopTime.stop_sequence).all()
        
        all_stops_s1 = [str(st.stop_id) for st in stop_times_s1]
        
        # 4. Obtener TODAS las paradas de S2 ordenadas
        stop_times_s2 = db.query(gtfs_models.StopTime).filter(
            gtfs_models.StopTime.trip_id == trip_s2.trip_id
        ).order_by(gtfs_models.StopTime.stop_sequence).all()
        
        all_stops_s2 = [str(st.stop_id) for st in stop_times_s2]
        
        print(f"✅ Paradas totales S1: {len(all_stops_s1)}")
        print(f"✅ Paradas totales S2: {len(all_stops_s2)}")
        
        # 5. Obtener nombres de todas las paradas
        all_stop_ids_combined = list(set(all_stops_s1 + all_stops_s2))
        stops_query = db.query(gtfs_models.Stop).filter(
            gtfs_models.Stop.stop_id.in_(all_stop_ids_combined)
        ).all()
        stops_dict = {str(stop.stop_id): stop.stop_name for stop in stops_query}
        
        # Validar paradas seleccionadas
        for stop_id in selected_stop_ids:
            if stop_id not in stops_dict:
                raise HTTPException(status_code=404, detail=f"Parada {stop_id} no existe")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 6. CREAR HEADERS - Filtrar solo seleccionadas
    headers = ["Corridas", "Bus"]
    column_keys = []
    
    print(f"\n📋 Columnas S1 (solo seleccionadas):")
    # S1: Solo paradas seleccionadas que existen en S1
    for stop_id in all_stops_s1:
        if stop_id in selected_stop_ids:
            name = stops_dict[stop_id]
            headers.append(f"{name} (S1)")
            column_keys.append(f"s1_{stop_id}")
            print(f"  s1_{stop_id}: {name}")
    
    print(f"\n📋 Columnas S2 (solo seleccionadas):")
    # S2: Solo paradas seleccionadas que existen en S2
    for stop_id in all_stops_s2:
        if stop_id in selected_stop_ids:
            name = stops_dict[stop_id]
            headers.append(f"{name} (S2)")
            column_keys.append(f"s2_{stop_id}")
            print(f"  s2_{stop_id}: {name}")
    
    print(f"\n✅ Total columnas: {len(headers)}")

    # 7. Obtener TODOS los trips
    try:
        trips = db.query(gtfs_models.Trip).filter(
            gtfs_models.Trip.route_id == route_id,
            gtfs_models.Trip.service_id == service_id
        ).all()
        
        print(f"✅ Total trips: {len(trips)}")
        
        if not trips:
            return {
                "headers": headers,
                "corridas": [],
                "stop_ids_ordered": column_keys,
                "total_corridas": 0,
                "route_id": route_id,
                "service_id": service_id
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error trips: {e}")

    trip_ids = [trip.trip_id for trip in trips]

    # 8. Obtener stop_times de paradas seleccionadas
    try:
        stop_times = db.query(gtfs_models.StopTime).filter(
            gtfs_models.StopTime.trip_id.in_(trip_ids),
            gtfs_models.StopTime.stop_id.in_(selected_stop_ids)
        ).all()
        
        print(f"✅ Stop times: {len(stop_times)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stop_times: {e}")

    # 9. Organizar por trip
    stop_times_by_trip = defaultdict(lambda: {})
    trip_first_time = {}

    for st in stop_times:
        time_str = st.departure_time or st.arrival_time
        if time_str:
            time_seconds = parse_time_to_seconds(str(time_str))
            if time_seconds is not None:
                stop_times_by_trip[st.trip_id][str(st.stop_id)] = time_seconds
                
                if st.trip_id not in trip_first_time:
                    trip_first_time[st.trip_id] = time_seconds

    # 10. Separar por dirección
    trips_ida = []
    trips_vuelta = []

    for trip in trips:
        if trip.trip_id in trip_first_time:
            trip.start_time = trip_first_time[trip.trip_id]
            if trip.direction_id == 0:
                trips_ida.append(trip)
            else:
                trips_vuelta.append(trip)

    trips_ida.sort(key=lambda t: t.start_time)
    trips_vuelta.sort(key=lambda t: t.start_time)

    print(f"✅ IDA: {len(trips_ida)}, VUELTA: {len(trips_vuelta)}")

    # 11. EMPALMADO
    all_corridas = []
    used_vuelta = set()
    
    for ida_trip in trips_ida:
        bus_number = get_bus_number_from_block(ida_trip.block_id)
        block_id = ida_trip.block_id
        
        corrida = {
            "id": f"ida_{ida_trip.trip_id}",
            "bus": bus_number,
            "times": {key: None for key in column_keys},
            "sort_time": ida_trip.start_time,
        }
        
        # Llenar S1 según orden de all_stops_s1
        ida_times = stop_times_by_trip[ida_trip.trip_id]
        for stop_id in all_stops_s1:
            if stop_id in selected_stop_ids and stop_id in ida_times:
                corrida["times"][f"s1_{stop_id}"] = format_time_from_seconds(ida_times[stop_id])
        
        # Buscar VUELTA del mismo block
        vuelta_trip = None
        for vtrip in trips_vuelta:
            if (vtrip.block_id == block_id and 
                vtrip.trip_id not in used_vuelta and
                vtrip.start_time > ida_trip.start_time):
                vuelta_trip = vtrip
                break
        
        if vuelta_trip:
            # Llenar S2 según orden de all_stops_s2
            vuelta_times = stop_times_by_trip[vuelta_trip.trip_id]
            for stop_id in all_stops_s2:
                if stop_id in selected_stop_ids and stop_id in vuelta_times:
                    corrida["times"][f"s2_{stop_id}"] = format_time_from_seconds(vuelta_times[stop_id])
            
            used_vuelta.add(vuelta_trip.trip_id)
        
        all_corridas.append(corrida)
    
    # VUELTA sin IDA
    for vuelta_trip in trips_vuelta:
        if vuelta_trip.trip_id in used_vuelta:
            continue
        
        bus_number = get_bus_number_from_block(vuelta_trip.block_id)
        
        corrida = {
            "id": f"vuelta_{vuelta_trip.trip_id}",
            "bus": bus_number,
            "times": {key: None for key in column_keys},
            "sort_time": vuelta_trip.start_time,
        }
        
        vuelta_times = stop_times_by_trip[vuelta_trip.trip_id]
        for stop_id in all_stops_s2:
            if stop_id in selected_stop_ids and stop_id in vuelta_times:
                corrida["times"][f"s2_{stop_id}"] = format_time_from_seconds(vuelta_times[stop_id])
        
        all_corridas.append(corrida)

    print(f"✅ Corridas: {len(all_corridas)}")

    # 12. Ordenar
    all_corridas.sort(key=lambda c: c["sort_time"])
    
    for idx, corrida in enumerate(all_corridas):
        corrida["corrida_num"] = idx + 1
        del corrida["sort_time"]

    print(f"{'='*70}\n")

    return {
        "headers": headers,
        "corridas": all_corridas,
        "stop_ids_ordered": column_keys,
        "total_corridas": len(all_corridas),
        "route_id": route_id,
        "service_id": service_id
    }