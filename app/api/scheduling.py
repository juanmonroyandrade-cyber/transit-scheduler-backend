# app/api/scheduling.py
"""
API de Programación de Rutas - Versión Actualizada
Integra el procesador de intervalos en Python (sin dependencia de Excel)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.scheduling_models import SchedulingParameters
from app.services.interval_processor import IntervalProcessor

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ===== SCHEMAS (Pydantic Models) =====

class Tabla1(BaseModel):
    """Parámetros generales"""
    horaInicio: str      # Formato HH:MM
    horaFin: str         # Formato HH:MM
    dwellCentro: str     # Formato HH:MM (tiempo de parada en Centro)
    dwellBarrio: str     # Formato HH:MM (tiempo de parada en Barrio)

class Tabla2Item(BaseModel):
    """Flota variable"""
    desde: str   # Formato HH:MM
    buses: int

class Tabla3Item(BaseModel):
    """Tiempos de recorrido variables"""
    horaCambio: str       # Formato HH:MM
    tCentroBarrio: str    # Formato HH:MM (Tiempo Centro→Barrio)
    tBarrioCentro: str    # Formato HH:MM (Tiempo Barrio→Centro)
    # El tiempo de ciclo se calcula automáticamente: tCentroBarrio + tBarrioCentro + dwells

class Tabla4Item(BaseModel):
    """Intervalos de paso en Centro (resultado)"""
    desde: str
    hasta: str
    headway: int

class Tabla5Item(BaseModel):
    """Intervalos de paso en Barrio (resultado)"""
    desde: str
    hasta: str
    headway: int

class Tabla6Item(BaseModel):
    """Tiempos de recorrido Centro→Barrio (resultado)"""
    desde: str
    hasta: str
    recorridoCentroBarrio: str

class Tabla7Item(BaseModel):
    """Tiempos de recorrido Barrio→Centro (resultado)"""
    desde: str
    hasta: str
    recorridoBarrioCentro: str

class ParametersInput(BaseModel):
    """Datos de entrada (tablas 1-3)"""
    tabla1: Tabla1
    tabla2: List[Tabla2Item]
    tabla3: List[Tabla3Item]

class ParametersOutput(BaseModel):
    """Datos completos (tablas 1-7)"""
    tabla1: Tabla1
    tabla2: List[Tabla2Item]
    tabla3: List[Tabla3Item]
    tabla4: List[Tabla4Item]
    tabla5: List[Tabla5Item]
    tabla6: List[Tabla6Item]
    tabla7: List[Tabla7Item]


# ===== ENDPOINTS =====

@router.post("/calculate", response_model=Dict[str, Any])
async def calculate_intervals(data: ParametersInput, db: Session = Depends(get_db)):
    """
    Calcula los intervalos de paso (TABLAS 4-7) a partir de los parámetros (TABLAS 1-3)
    
    Este endpoint:
    1. Recibe las tablas 1-3 con los parámetros de entrada
    2. Procesa los datos usando el algoritmo de intervalos
    3. Calcula las tablas 4-7 con los resultados
    4. Guarda todo en la base de datos
    5. Retorna los resultados completos
    """
    print("\n" + "="*70)
    print("🚀 ENDPOINT /calculate llamado")
    print("="*70)
    
    try:
        # 1. Preparar datos de entrada
        tabla1_dict = data.tabla1.dict()
        tabla2_list = [item.dict() for item in data.tabla2]
        tabla3_list = [item.dict() for item in data.tabla3]
        
        print(f"\n📥 Datos recibidos:")
        print(f"   Tabla 1: {tabla1_dict}")
        print(f"   Tabla 2: {len(tabla2_list)} filas")
        print(f"   Tabla 3: {len(tabla3_list)} filas")
        
        # 2. Procesar con el algoritmo
        processor = IntervalProcessor()
        resultados = processor.process_parameters(tabla1_dict, tabla2_list, tabla3_list)
        
        print(f"\n✅ Resultados generados:")
        print(f"   Tabla 4 (Intervalos Centro): {len(resultados['tabla4'])} períodos")
        print(f"   Tabla 5 (Intervalos Barrio): {len(resultados['tabla5'])} períodos")
        print(f"   Tabla 6 (Recorridos C→B): {len(resultados['tabla6'])} períodos")
        print(f"   Tabla 7 (Recorridos B→C): {len(resultados['tabla7'])} períodos")
        
        # 3. Guardar en base de datos
        # Desactivar parámetros anteriores
        db.query(SchedulingParameters).filter(
            SchedulingParameters.is_active == 1
        ).update({"is_active": 0})
        
        # Crear nuevo registro
        new_params = SchedulingParameters(
            name=f"Cálculo {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            tabla1=tabla1_dict,
            tabla2=tabla2_list,
            tabla3=tabla3_list,
            tabla4=resultados["tabla4"],
            tabla5=resultados["tabla5"],
            tabla6=resultados["tabla6"],
            tabla7=resultados["tabla7"],
            is_active=1
        )
        
        db.add(new_params)
        db.commit()
        db.refresh(new_params)
        
        print(f"\n💾 Guardado en BD con ID: {new_params.id}")
        
        # 4. Retornar resultados completos
        response = {
            "success": True,
            "message": "Cálculo completado exitosamente",
            "id": new_params.id,
            "tabla1": tabla1_dict,
            "tabla2": tabla2_list,
            "tabla3": tabla3_list,
            "tabla4": resultados["tabla4"],
            "tabla5": resultados["tabla5"],
            "tabla6": resultados["tabla6"],
            "tabla7": resultados["tabla7"]
        }
        
        print("\n" + "="*70)
        print("✅ ENDPOINT /calculate completado")
        print("="*70 + "\n")
        
        return response
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR en /calculate: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error al calcular intervalos: {str(e)}"
        )


@router.get("/parameters/active", response_model=Optional[Dict[str, Any]])
async def get_active_parameters(db: Session = Depends(get_db)):
    """
    Obtiene los parámetros activos más recientes (todas las 7 tablas)
    """
    print("\n📖 GET /parameters/active")
    
    try:
        params = db.query(SchedulingParameters)\
            .filter(SchedulingParameters.is_active == 1)\
            .order_by(SchedulingParameters.created_at.desc())\
            .first()
        
        if not params:
            print("  ℹ️  No hay parámetros activos")
            return None
        
        response = {
            "id": params.id,
            "name": params.name,
            "tabla1": params.tabla1 or {},
            "tabla2": params.tabla2 or [],
            "tabla3": params.tabla3 or [],
            "tabla4": params.tabla4 or [],
            "tabla5": params.tabla5 or [],
            "tabla6": params.tabla6 or [],
            "tabla7": params.tabla7 or [],
            "created_at": params.created_at.isoformat(),
            "updated_at": params.updated_at.isoformat()
        }
        
        print(f"  ✅ Parámetros ID {params.id} obtenidos")
        return response
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters", response_model=List[Dict[str, Any]])
async def list_parameters(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Lista todos los conjuntos de parámetros guardados
    """
    print(f"\n📋 GET /parameters (limit={limit}, offset={offset})")
    
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
                "is_active": params.is_active,
                "created_at": params.created_at.isoformat(),
                "updated_at": params.updated_at.isoformat()
            })
        
        print(f"  ✅ {len(result)} conjuntos obtenidos")
        return result
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{param_id}", response_model=Dict[str, Any])
async def get_parameters_by_id(param_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un conjunto específico de parámetros por ID
    """
    print(f"\n📖 GET /parameters/{param_id}")
    
    try:
        params = db.query(SchedulingParameters).filter(
            SchedulingParameters.id == param_id
        ).first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Parámetros no encontrados")
        
        response = {
            "id": params.id,
            "name": params.name,
            "tabla1": params.tabla1 or {},
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
        
        print(f"  ✅ Parámetros obtenidos")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/parameters/{param_id}")
async def delete_parameters(param_id: int, db: Session = Depends(get_db)):
    """
    Elimina un conjunto de parámetros
    """
    print(f"\n🗑️  DELETE /parameters/{param_id}")
    
    try:
        params = db.query(SchedulingParameters).filter(
            SchedulingParameters.id == param_id
        ).first()
        
        if not params:
            raise HTTPException(status_code=404, detail="Parámetros no encontrados")
        
        db.delete(params)
        db.commit()
        
        print(f"  ✅ Eliminado")
        return {"success": True, "message": "Parámetros eliminados"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"  ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))