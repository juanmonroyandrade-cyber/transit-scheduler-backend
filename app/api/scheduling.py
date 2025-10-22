# app/api/scheduling.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.scheduling_models import SchedulingParameters

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ===== SCHEMAS (Pydantic Models) =====

class Tabla1(BaseModel):
    """Parámetros generales"""
    numeroRuta: str
    nombreRuta: str
    periodicidad: str
    horaInicioCentro: str
    horaInicioBarrio: str
    horaFinCentro: str
    horaFinBarrio: str
    tiempoRecorridoCB: str
    tiempoRecorridoBC: str
    dwellCentro: int
    dwellBarrio: int
    distanciaCB: float
    distanciaBC: float

class Tabla2Item(BaseModel):
    """Buses variables por hora"""
    hora: int
    buses: int

class Tabla3Item(BaseModel):
    """Tiempos de ciclo variables"""
    hora: int
    tCicloAB: str
    tCicloBA: str

class Tabla4Item(BaseModel):
    """Headways Centro"""
    desde: str
    hasta: str
    headway: int

class Tabla5Item(BaseModel):
    """Headways Barrio"""
    desde: str
    hasta: str
    headway: int

class Tabla6Item(BaseModel):
    """Tiempos recorrido variables Centro"""
    desde: str
    hasta: str
    recorridoAB: str

class Tabla7Item(BaseModel):
    """Tiempos recorrido variables Barrio"""
    desde: str
    hasta: str
    recorridoBA: str

class ParametersCreate(BaseModel):
    """Datos completos para crear/actualizar parámetros"""
    tabla1: Tabla1
    tabla2: List[Tabla2Item]
    tabla3: List[Tabla3Item]
    tabla4: List[Tabla4Item]
    tabla5: List[Tabla5Item]
    tabla6: List[Tabla6Item]
    tabla7: List[Tabla7Item]


# ===== ENDPOINTS =====

@router.post("/parameters", response_model=Dict[str, Any])
async def save_parameters(data: ParametersCreate, db: Session = Depends(get_db)):
    """
    Guarda los parámetros de programación (7 tablas)
    """
    print(f"[Scheduling API] Guardando parámetros completos...")
    
    try:
        # Desactivar parámetros anteriores (opcional)
        db.query(SchedulingParameters).filter(
            SchedulingParameters.is_active == 1
        ).update({"is_active": 0})
        
        # Crear nuevo registro
        new_params = SchedulingParameters(
            route_id=data.tabla1.numeroRuta,
            name=f"Ruta {data.tabla1.numeroRuta} - {data.tabla1.nombreRuta}",
            tabla1=data.tabla1.dict(),
            tabla2=[item.dict() for item in data.tabla2],
            tabla3=[item.dict() for item in data.tabla3],
            tabla4=[item.dict() for item in data.tabla4],
            tabla5=[item.dict() for item in data.tabla5],
            tabla6=[item.dict() for item in data.tabla6],
            tabla7=[item.dict() for item in data.tabla7],
            is_active=1
        )
        
        db.add(new_params)
        db.commit()
        db.refresh(new_params)
        
        print(f"✅ Parámetros guardados con ID: {new_params.id}")
        
        return {
            "success": True,
            "message": "Parámetros guardados correctamente",
            "id": new_params.id
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar parámetros: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")


@router.get("/parameters/active", response_model=Optional[Dict[str, Any]])
async def get_active_parameters(db: Session = Depends(get_db)):
    """
    Obtiene los parámetros activos más recientes
    """
    print("[Scheduling API] Obteniendo parámetros activos...")
    
    try:
        params = db.query(SchedulingParameters)\
            .filter(SchedulingParameters.is_active == 1)\
            .order_by(SchedulingParameters.created_at.desc())\
            .first()
        
        if not params:
            print("  -> No hay parámetros activos")
            return None
        
        # Devolver en el formato esperado por el frontend
        response = {
            "id": params.id,
            "name": params.name,
            "route_id": params.route_id,
            "tabla1": params.tabla1,
            "tabla2": params.tabla2 or [],
            "tabla3": params.tabla3 or [],
            "tabla4": params.tabla4 or [],
            "tabla5": params.tabla5 or [],
            "tabla6": params.tabla6 or [],
            "tabla7": params.tabla7 or [],
            "created_at": params.created_at.isoformat(),
            "updated_at": params.updated_at.isoformat()
        }
        
        print(f"✅ Parámetros obtenidos: ID {params.id}")
        return response
        
    except Exception as e:
        print(f"❌ Error al obtener parámetros: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al obtener parámetros: {str(e)}")


@router.get("/parameters", response_model=List[Dict[str, Any]])
async def list_parameters(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Lista todos los conjuntos de parámetros guardados
    """
    print(f"[Scheduling API] Listando parámetros (limit={limit}, offset={offset})...")
    
    try:
        params_list = db.query(SchedulingParameters)\
            .order_by(SchedulingParameters.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()
        
        result = []
        for params in params_list:
            result.append({
                "id": params.id,
                "name": params.name,
                "route_id": params.route_id,
                "is_active": params.is_active,
                "created_at": params.created_at.isoformat(),
                "updated_at": params.updated_at.isoformat()
            })
        
        print(f"✅ {len(result)} conjuntos de parámetros obtenidos")
        return result
        
    except Exception as e:
        print(f"❌ Error al listar parámetros: {e}")
        raise HTTPException(status_code=500, detail=f"Error al listar: {str(e)}")


@router.get("/parameters/{param_id}", response_model=Dict[str, Any])
async def get_parameters_by_id(param_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un conjunto específico de parámetros por ID
    """
    print(f"[Scheduling API] Obteniendo parámetros ID: {param_id}")
    
    try:
        params = db.query(SchedulingParameters).filter(
            SchedulingParameters.id == param_id
        ).first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Parámetros no encontrados")
        
        response = {
            "id": params.id,
            "name": params.name,
            "route_id": params.route_id,
            "tabla1": params.tabla1,
            "tabla2": params.tabla2 or [],
            "tabla3": params.tabla3 or [],
            "tabla4": params.tabla4 or [],
            "tabla5": params.tabla5 or [],
            "tabla6": params.tabla6 or [],
            "tabla7": params.tabla7 or [],
            "created_at": params.created_at.isoformat(),
            "updated_at": params.updated_at.isoformat(),
            "is_active": params.is_active
        }
        
        print(f"✅ Parámetros {param_id} obtenidos")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error al obtener parámetros: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/parameters/{param_id}")
async def delete_parameters(param_id: int, db: Session = Depends(get_db)):
    """
    Elimina un conjunto de parámetros
    """
    print(f"[Scheduling API] Eliminando parámetros ID: {param_id}")
    
    try:
        params = db.query(SchedulingParameters).filter(
            SchedulingParameters.id == param_id
        ).first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Parámetros no encontrados")
        
        db.delete(params)
        db.commit()
        
        print(f"✅ Parámetros {param_id} eliminados")
        return {"success": True, "message": "Parámetros eliminados"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error al eliminar: {e}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")