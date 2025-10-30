# app/api/scheduling_updated.py

"""
API actualizada para programación de rutas con:
- Guardar/cargar escenarios con nombre
- Cálculo de intervalos
- Integración con routes y shapes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
import re

from app.database import get_db
from app.models.scheduling_models import SchedulingParameters
from app.services.interval_processor import process_intervals

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ==================== VALIDADORES ====================

def validate_time_format(time_str: str) -> str:
    """Valida que el formato sea HH:MM"""
    if not time_str:
        raise ValueError("El campo no puede estar vacío")
    
    pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    if not re.match(pattern, time_str):
        raise ValueError(f"Formato inválido: '{time_str}' (use HH:MM)")
    
    return time_str


# ==================== SCHEMAS ====================

class Tabla1Model(BaseModel):
    numeroRuta: str
    nombreRuta: str
    periodicidad: str
    horaInicioCentro: str
    horaInicioBarrio: str
    horaFinCentro: str
    horaFinBarrio: str
    dwellCentro: int
    dwellBarrio: int
    distanciaCB: float
    distanciaBC: float
    
    @field_validator('horaInicioCentro', 'horaInicioBarrio', 'horaFinCentro', 'horaFinBarrio')
    @classmethod
    def validate_time(cls, v: str) -> str:
        return validate_time_format(v)


class Tabla2ItemModel(BaseModel):
    desde: str
    buses: int
    
    @field_validator('desde')
    @classmethod
    def validate_desde(cls, v: str) -> str:
        return validate_time_format(v)


class Tabla3ItemModel(BaseModel):
    desde: str
    tiempoCB: str
    tiempoBC: str
    tiempoCiclo: str
    
    @field_validator('desde', 'tiempoCB', 'tiempoBC')
    @classmethod
    def validate_times(cls, v: str) -> str:
        return validate_time_format(v)


class SaveParametersRequest(BaseModel):
    """Request para guardar parámetros con nombre"""
    name: str  # Nombre del escenario (ej: "Programación Ruta 1 L-V")
    tabla1: Tabla1Model
    tabla2: List[Tabla2ItemModel]
    tabla3: List[Tabla3ItemModel]


class CalculateIntervalsRequest(BaseModel):
    tabla1: Tabla1Model
    tabla2: List[Tabla2ItemModel]
    tabla3: List[Tabla3ItemModel]


# ==================== ENDPOINTS DE CÁLCULO ====================

@router.post("/calculate-intervals")
async def calculate_intervals(request: CalculateIntervalsRequest):
    """
    Calcula intervalos de paso basados en los parámetros de entrada
    
    Retorna:
        - tabla4: Intervalos Centro
        - tabla5: Intervalos Barrio
        - tabla6: Tiempos Centro→Barrio agrupados
        - tabla7: Tiempos Barrio→Centro agrupados
    """
    print("\n🔢 Endpoint /calculate-intervals llamado")
    
    try:
        if not request.tabla2:
            raise HTTPException(
                status_code=400,
                detail="Tabla 2 (Flota Variable) no puede estar vacía"
            )
        
        if not request.tabla3:
            raise HTTPException(
                status_code=400,
                detail="Tabla 3 (Tiempos de Recorrido) no puede estar vacía"
            )
        
        # Convertir a diccionario para el procesador
        parameters = {
            "tabla1": request.tabla1.model_dump(),
            "tabla2": [item.model_dump() for item in request.tabla2],
            "tabla3": [item.model_dump() for item in request.tabla3]
        }
        
        # Procesar intervalos
        result = process_intervals(parameters)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Error en el cálculo: {result.get('error', 'Error desconocido')}"
            )
        
        return {
            "success": True,
            "tabla4": result["tabla4"],
            "tabla5": result["tabla5"],
            "tabla6": result["tabla6"],
            "tabla7": result["tabla7"],
            "tiempo_procesamiento": result["tiempo_procesamiento"]
        }
        
    except ValueError as e:
        print(f"❌ Error de validación: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE PARÁMETROS CON NOMBRE ====================

@router.post("/parameters")
async def save_parameters(request: SaveParametersRequest, db: Session = Depends(get_db)):
    """
    Guarda o actualiza parámetros con nombre específico
    
    Si ya existe un escenario con el mismo nombre para la misma ruta, lo sobrescribe.
    """
    print(f"\n💾 Guardando parámetros: '{request.name}'")
    
    try:
        route_id = request.tabla1.numeroRuta
        
        # Buscar si existe un escenario con el mismo nombre y ruta
        existing = db.query(SchedulingParameters)\
            .filter(
                SchedulingParameters.name == request.name,
                SchedulingParameters.route_id == route_id
            )\
            .first()
        
        if existing:
            # ACTUALIZAR existente
            print(f"  → Actualizando escenario existente (ID: {existing.id})")
            existing.tabla1 = request.tabla1.model_dump()
            existing.tabla2 = [item.model_dump() for item in request.tabla2]
            existing.tabla3 = [item.model_dump() for item in request.tabla3]
            existing.updated_at = datetime.now()
            
            db.commit()
            db.refresh(existing)
            
            return {
                "success": True,
                "message": f"Escenario '{request.name}' actualizado",
                "id": existing.id,
                "action": "updated"
            }
        else:
            # CREAR nuevo
            print(f"  → Creando nuevo escenario")
            new_params = SchedulingParameters(
                name=request.name,
                route_id=route_id,
                tabla1=request.tabla1.model_dump(),
                tabla2=[item.model_dump() for item in request.tabla2],
                tabla3=[item.model_dump() for item in request.tabla3],
                is_active=0  # No activar automáticamente
            )
            
            db.add(new_params)
            db.commit()
            db.refresh(new_params)
            
            print(f"✅ Escenario guardado con ID: {new_params.id}")
            
            return {
                "success": True,
                "message": f"Escenario '{request.name}' creado",
                "id": new_params.id,
                "action": "created"
            }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")


@router.get("/parameters")
async def list_parameters(
    route_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos los escenarios guardados
    
    Args:
        route_id: Filtrar por ruta específica (opcional)
    """
    print(f"\n📋 Listando escenarios (route_id: {route_id})")
    
    try:
        query = db.query(SchedulingParameters)
        
        if route_id:
            query = query.filter(SchedulingParameters.route_id == route_id)
        
        params_list = query\
            .order_by(SchedulingParameters.updated_at.desc())\
            .all()
        
        result = []
        for params in params_list:
            result.append({
                "id": params.id,
                "name": params.name,
                "route_id": params.route_id,
                "route_name": params.tabla1.get("nombreRuta", "") if params.tabla1 else "",
                "periodicidad": params.tabla1.get("periodicidad", "") if params.tabla1 else "",
                "is_active": params.is_active,
                "created_at": params.created_at.isoformat() if params.created_at else None,
                "updated_at": params.updated_at.isoformat() if params.updated_at else None
            })
        
        print(f"✅ {len(result)} escenarios encontrados")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{param_id}")
async def get_parameters_by_id(param_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un escenario específico por ID
    """
    print(f"\n📄 Obteniendo escenario ID: {param_id}")
    
    try:
        params = db.query(SchedulingParameters)\
            .filter(SchedulingParameters.id == param_id)\
            .first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Escenario no encontrado")
        
        return {
            "id": params.id,
            "name": params.name,
            "route_id": params.route_id,
            "tabla1": params.tabla1,
            "tabla2": params.tabla2 or [],
            "tabla3": params.tabla3 or [],
            "created_at": params.created_at.isoformat() if params.created_at else None,
            "updated_at": params.updated_at.isoformat() if params.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/by-name/{name}")
async def get_parameters_by_name(
    name: str,
    route_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene un escenario por nombre
    
    Args:
        name: Nombre del escenario
        route_id: ID de ruta (opcional, para desambiguar)
    """
    print(f"\n📄 Buscando escenario: '{name}' (route: {route_id})")
    
    try:
        query = db.query(SchedulingParameters)\
            .filter(SchedulingParameters.name == name)
        
        if route_id:
            query = query.filter(SchedulingParameters.route_id == route_id)
        
        params = query.first()
        
        if not params:
            raise HTTPException(status_code=404, detail=f"Escenario '{name}' no encontrado")
        
        return {
            "id": params.id,
            "name": params.name,
            "route_id": params.route_id,
            "tabla1": params.tabla1,
            "tabla2": params.tabla2 or [],
            "tabla3": params.tabla3 or [],
            "created_at": params.created_at.isoformat() if params.created_at else None,
            "updated_at": params.updated_at.isoformat() if params.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/parameters/{param_id}")
async def delete_parameters(param_id: int, db: Session = Depends(get_db)):
    """
    Elimina un escenario guardado
    """
    print(f"\n🗑️ Eliminando escenario ID: {param_id}")
    
    try:
        params = db.query(SchedulingParameters)\
            .filter(SchedulingParameters.id == param_id)\
            .first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Escenario no encontrado")
        
        name = params.name
        db.delete(params)
        db.commit()
        
        print(f"✅ Escenario '{name}' eliminado")
        
        return {
            "success": True,
            "message": f"Escenario '{name}' eliminado correctamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINT AUXILIAR: SHAPES ====================

@router.get("/shapes-distances/{route_id}")
async def get_shapes_distances(route_id: str, db: Session = Depends(get_db)):
    """
    Obtiene las distancias máximas de los shapes de una ruta
    
    Retorna:
        {
            "route_id": "1",
            "centro_barrio": 15.5,  // shape {route_id}.1
            "barrio_centro": 15.3   // shape {route_id}.2
        }
    """
    print(f"\n📏 Obteniendo distancias de shapes para ruta: {route_id}")
    
    try:
        from app.models.gtfs_models import Shape
        
        # Shape Centro→Barrio (dirección .1)
        shape_cb = db.query(Shape)\
            .filter(Shape.shape_id == f"{route_id}.1")\
            .order_by(Shape.shape_dist_traveled.desc())\
            .first()
        
        # Shape Barrio→Centro (dirección .2)
        shape_bc = db.query(Shape)\
            .filter(Shape.shape_id == f"{route_id}.2")\
            .order_by(Shape.shape_dist_traveled.desc())\
            .first()
        
        distance_cb = float(shape_cb.shape_dist_traveled)/1000 if shape_cb and shape_cb.shape_dist_traveled else 0.0
        distance_bc = float(shape_bc.shape_dist_traveled)/1000 if shape_bc and shape_bc.shape_dist_traveled else 0.0
        
        print(f"  → C→B: {distance_cb:.2f} km")
        print(f"  → B→C: {distance_bc:.2f} km")
        
        return {
            "route_id": route_id,
            "centro_barrio": round(distance_cb, 2),
            "barrio_centro": round(distance_bc, 2)
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def health_check():
    """Verifica que el servicio esté funcionando"""
    return {
        "status": "ok",
        "service": "Interval Calculator & Parameters Manager",
        "version": "2.1"
    }