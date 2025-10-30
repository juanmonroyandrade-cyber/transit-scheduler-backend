# app/api/scheduling_updated.py

"""
API actualizada para cálculo de intervalos con validación de formato HH:MM
Compatible con Pydantic V2
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any
import re

# Importar el procesador de intervalos
from app.services.interval_processor import process_intervals

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ==================== VALIDADORES ====================

def validate_time_format(time_str: str) -> str:
    """
    Valida que el formato sea HH:MM
    """
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


class CalculateIntervalsRequest(BaseModel):
    tabla1: Tabla1Model
    tabla2: List[Tabla2ItemModel]
    tabla3: List[Tabla3ItemModel]


# ==================== ENDPOINT ====================

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
        # Validaciones adicionales
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


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def health_check():
    """Verifica que el servicio esté funcionando"""
    return {
        "status": "ok",
        "service": "Interval Calculator",
        "version": "2.0"
    }