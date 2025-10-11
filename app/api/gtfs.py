"""
API Endpoints para importación/exportación GTFS
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import io

from app.database import get_db
from app.services.gtfs_importer import GTFSImporter, validate_gtfs_file

router = APIRouter(prefix="/gtfs", tags=["GTFS"])


@router.post("/import")
async def import_gtfs(
    file: UploadFile = File(..., description="Archivo GTFS en formato ZIP"),
    agency_name: Optional[str] = Form(None, description="Nombre de la agencia (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Importa un archivo GTFS completo a la base de datos
    
    **Proceso:**
    1. Valida estructura del ZIP
    2. Lee todos los archivos .txt
    3. Importa en orden: agency → calendar → routes → stops → shapes → trips → stop_times
    4. Genera IDs nuevos y mapea referencias
    5. Actualiza geometrías PostGIS automáticamente
    
    **Retorna:**
    - Estadísticas de importación
    - Lista de errores si los hay
    """
    
    # Validar que sea un ZIP
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un ZIP")
    
    # Leer contenido
    contents = await file.read()
    file_obj = io.BytesIO(contents)
    
    # Validar estructura primero
    validation = validate_gtfs_file(file_obj)
    if not validation['valid']:
        raise HTTPException(
            status_code=400,
            detail={
                'message': 'GTFS inválido',
                'missing_files': validation.get('missing_required', []),
                'error': validation.get('error')
            }
        )
    
    # Resetear puntero del archivo
    file_obj.seek(0)
    
    # Importar
    try:
        importer = GTFSImporter(db)
        result = importer.import_gtfs(file_obj, agency_name)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result)
        
        return {
            'message': 'GTFS importado exitosamente',
            'stats': result['stats'],
            'validation': validation
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_gtfs(
    file: UploadFile = File(..., description="Archivo GTFS en formato ZIP")
):
    """
    Valida la estructura de un archivo GTFS sin importarlo
    
    **Retorna:**
    - valid: bool
    - files_found: lista de archivos en el ZIP
    - missing_required: archivos requeridos faltantes
    - extra_files: archivos adicionales encontrados
    """
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un ZIP")
    
    contents = await file.read()
    file_obj = io.BytesIO(contents)
    
    validation = validate_gtfs_file(file_obj)
    
    return validation


@router.get("/stats")
async def get_gtfs_stats(db: Session = Depends(get_db)):
    """
    Retorna estadísticas de los datos GTFS cargados
    
    **Retorna:**
    - Total de rutas, paradas, viajes, etc.
    - Información de agencias
    - Rango de fechas de servicio
    """
    from app.models.gtfs_models import Agency, Route, Stop, Trip, StopTime, Calendar
    from sqlalchemy import func
    
    try:
        stats = {
            'agencies': db.query(Agency).count(),
            'routes': db.query(Route).count(),
            'stops': db.query(Stop).count(),
            'trips': db.query(Trip).count(),
            'stop_times': db.query(StopTime).count(),
            'calendar_services': db.query(Calendar).count()
        }
        
        # Info de agencias
        agencies = db.query(Agency).all()
        stats['agencies_list'] = [
            {
                'id': a.agency_id,
                'name': a.agency_name,
                'timezone': a.agency_timezone
            } for a in agencies
        ]
        
        # Rango de fechas
        calendar_info = db.query(
            func.min(Calendar.start_date).label('earliest_start'),
            func.max(Calendar.end_date).label('latest_end')
        ).first()
        
        if calendar_info:
            stats['service_period'] = {
                'start': str(calendar_info.earliest_start),
                'end': str(calendar_info.latest_end)
            }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes")
async def get_routes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todas las rutas importadas
    
    **Parámetros:**
    - skip: número de registros a saltar (paginación)
    - limit: máximo de registros a retornar
    """
    from app.models.gtfs_models import Route
    
    routes = db.query(Route).offset(skip).limit(limit).all()
    
    return {
        'total': db.query(Route).count(),
        'routes': [
            {
                'route_id': r.route_id,
                'short_name': r.route_short_name,
                'long_name': r.route_long_name,
                'type': r.route_type,
                'color': r.route_color,
                'is_electric': r.is_electric
            } for r in routes
        ]
    }


@router.get("/routes/{route_id}")
async def get_route_detail(
    route_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene detalle completo de una ruta específica
    
    **Incluye:**
    - Información básica de la ruta
    - Total de viajes
    - Paradas asociadas
    - Shapes si existen
    """
    from app.models.gtfs_models import Route, Trip, Stop, StopTime
    from sqlalchemy import func, distinct
    
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    
    # Contar viajes
    trips_count = db.query(Trip).filter(Trip.route_id == route_id).count()
    
    # Obtener paradas únicas de esta ruta
    stops_query = db.query(Stop).join(StopTime).join(Trip).filter(
        Trip.route_id == route_id
    ).distinct()
    
    stops = stops_query.all()
    
    return {
        'route': {
            'route_id': route.route_id,
            'short_name': route.route_short_name,
            'long_name': route.route_long_name,
            'description': route.route_desc,
            'type': route.route_type,
            'color': route.route_color,
            'text_color': route.route_text_color,
            'is_electric': route.is_electric,
            'km_total': float(route.km_total) if route.km_total else None
        },
        'stats': {
            'total_trips': trips_count,
            'total_stops': len(stops)
        },
        'stops': [
            {
                'stop_id': s.stop_id,
                'stop_name': s.stop_name,
                'lat': float(s.stop_lat),
                'lon': float(s.stop_lon)
            } for s in stops
        ]
    }


@router.get("/stops")
async def get_stops(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todas las paradas importadas
    
    **Parámetros:**
    - skip: paginación
    - limit: máximo de resultados
    - search: filtrar por nombre de parada
    """
    from app.models.gtfs_models import Stop
    
    query = db.query(Stop)
    
    if search:
        query = query.filter(Stop.stop_name.ilike(f'%{search}%'))
    
    total = query.count()
    stops = query.offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'stops': [
            {
                'stop_id': s.stop_id,
                'stop_code': s.stop_code,
                'stop_name': s.stop_name,
                'lat': float(s.stop_lat),
                'lon': float(s.stop_lon),
                'wheelchair_boarding': s.wheelchair_boarding
            } for s in stops
        ]
    }


@router.delete("/clear")
async def clear_gtfs_data(
    confirm: bool = Form(..., description="Confirmación para borrar todos los datos"),
    db: Session = Depends(get_db)
):
    """
    **PELIGRO**: Borra TODOS los datos GTFS de la base de datos
    
    **Requiere:**
    - confirm: true
    
    Útil para re-importar un GTFS limpio
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Debe confirmar la eliminación con confirm=true"
        )
    
    try:
        from app.models.gtfs_models import (
            StopTime, Trip, Shape, ShapePoint, Stop, Route, Calendar, Agency
        )
        
        # Borrar en orden (dependencias)
        db.query(StopTime).delete()
        db.query(Trip).delete()
        db.query(ShapePoint).delete()
        db.query(Shape).delete()
        db.query(Stop).delete()
        db.query(Route).delete()
        db.query(Calendar).delete()
        db.query(Agency).delete()
        
        db.commit()
        
        return {
            'message': 'Todos los datos GTFS han sido eliminados',
            'success': True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_gtfs(
    route_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Exporta los datos actuales a formato GTFS ZIP
    
    **Parámetros:**
    - route_id: Opcional, exportar solo una ruta específica
    
    **TODO**: Implementar generación de ZIP
    """
    # Esta funcionalidad la implementaremos después
    raise HTTPException(
        status_code=501,
        detail="Funcionalidad de exportación pendiente de implementar"
    )