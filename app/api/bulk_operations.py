# app/api/bulk_operations.py

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import Optional
import io

from app.database import get_db
from app.models.gtfs_models import Trip, StopTime
from app.services.excel_importer import ExcelImporter

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


@router.delete("/delete-trips-and-stoptimes")
async def delete_trips_and_stoptimes(
    route_id: str = Query(..., description="ID de la ruta"),
    service_id: Optional[str] = Query(None, description="ID del servicio/periodicidad (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Elimina trips y sus stop_times asociados por ruta y opcionalmente por servicio.
    
    **Parámetros:**
    - route_id: ID de la ruta (requerido)
    - service_id: ID del servicio/periodicidad (opcional, si no se proporciona borra TODOS los trips de la ruta)
    
    **Retorna:**
    - trips_deleted: Número de trips eliminados
    - stop_times_deleted: Número de stop_times eliminados
    """
    
    print(f"\n{'='*70}")
    print(f"🗑️  BORRADO MASIVO DE TRIPS Y STOP_TIMES")
    print(f"{'='*70}")
    print(f"📍 Ruta: {route_id}")
    print(f"📅 Servicio: {service_id if service_id else 'TODOS'}")
    
    try:
        # 1. Buscar trips que coincidan con los criterios
        trip_query = db.query(Trip).filter(Trip.route_id == route_id)
        
        if service_id:
            trip_query = trip_query.filter(Trip.service_id == service_id)
        
        trips_to_delete = trip_query.all()
        
        if not trips_to_delete:
            print(f"⚠️  No se encontraron trips para eliminar")
            return {
                "success": True,
                "message": "No se encontraron trips que coincidan con los criterios",
                "trips_deleted": 0,
                "stop_times_deleted": 0
            }
        
        trip_ids = [trip.trip_id for trip in trips_to_delete]
        print(f"✅ Encontrados {len(trip_ids)} trips para eliminar")
        
        # 2. Eliminar stop_times asociados
        stop_times_stmt = delete(StopTime).where(StopTime.trip_id.in_(trip_ids))
        stop_times_result = db.execute(stop_times_stmt)
        stop_times_deleted = stop_times_result.rowcount
        
        print(f"✅ Eliminados {stop_times_deleted} stop_times")
        
        # 3. Eliminar trips
        trips_stmt = delete(Trip).where(Trip.trip_id.in_(trip_ids))
        trips_result = db.execute(trips_stmt)
        trips_deleted = trips_result.rowcount
        
        print(f"✅ Eliminados {trips_deleted} trips")
        
        # 4. Commit
        db.commit()
        
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "message": f"Eliminados {trips_deleted} trips y {stop_times_deleted} stop_times",
            "trips_deleted": trips_deleted,
            "stop_times_deleted": stop_times_deleted,
            "route_id": route_id,
            "service_id": service_id
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el borrado: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error al eliminar trips y stop_times: {str(e)}"
        )


@router.get("/count-trips")
async def count_trips(
    route_id: str = Query(..., description="ID de la ruta"),
    service_id: Optional[str] = Query(None, description="ID del servicio (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Cuenta cuántos trips y stop_times serían eliminados (sin borrarlos).
    Útil para confirmar antes de borrar.
    """
    try:
        trip_query = db.query(Trip).filter(Trip.route_id == route_id)
        
        if service_id:
            trip_query = trip_query.filter(Trip.service_id == service_id)
        
        trips = trip_query.all()
        trip_count = len(trips)
        
        if trip_count == 0:
            return {
                "route_id": route_id,
                "service_id": service_id,
                "trips_count": 0,
                "stop_times_count": 0
            }
        
        trip_ids = [trip.trip_id for trip in trips]
        stop_times_count = db.query(StopTime).filter(
            StopTime.trip_id.in_(trip_ids)
        ).count()
        
        return {
            "route_id": route_id,
            "service_id": service_id,
            "trips_count": trip_count,
            "stop_times_count": stop_times_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al contar registros: {str(e)}"
        )


@router.post("/upload-trips-stoptimes")
async def upload_trips_stoptimes(
    trips_file: UploadFile = File(..., description="Archivo Excel de trips"),
    stoptimes_file: UploadFile = File(..., description="Archivo Excel de stop_times"),
    interpolate_times: bool = Form(True),
    calculate_distances: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Carga trips y stop_times desde DOS archivos Excel separados.
    
    **Archivo TRIPS (orden de columnas):**
    route_id, service_id, trip_id, trip_headsign, direction_id, 
    block_id, shape_id, wheelchair_accessible, bikes_allowed
    
    **Archivo STOP_TIMES (orden de columnas):**
    trip_id, arrival_time, departure_time, stop_id, stop_sequence, 
    stop_headsign, pickup_type, drop_off_type, continuous_pickup, 
    continuous_drop_off, shape_dist_traveled, timepoint
    
    **Opciones:**
    - interpolate_times: Si True, interpola tiempos entre primera y última parada
    - calculate_distances: Si True, calcula shape_dist_traveled automáticamente desde shapes
    """
    
    # Validar extensiones
    if not trips_file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="El archivo de trips debe ser Excel (.xlsx, .xls)"
        )
    
    if not stoptimes_file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="El archivo de stop_times debe ser Excel (.xlsx, .xls)"
        )
    
    try:
        # Leer contenido de ambos archivos
        trips_content = await trips_file.read()
        stoptimes_content = await stoptimes_file.read()
        
        print(f"📁 Archivo trips: {trips_file.filename} ({len(trips_content)} bytes)")
        print(f"📁 Archivo stop_times: {stoptimes_file.filename} ({len(stoptimes_content)} bytes)")
        
        # Importar
        importer = ExcelImporter(db)
        result = importer.import_trips_and_stoptimes(
            trips_content=trips_content,
            stoptimes_content=stoptimes_content,
            interpolate_times=interpolate_times,
            calculate_distances=calculate_distances
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar archivos Excel: {str(e)}"
        )