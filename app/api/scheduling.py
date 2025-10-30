# app/api/scheduling.py
# (Este es tu archivo 'scheduling_updated.py', con las nuevas integraciones)

"""
API actualizada para programación de rutas con:
- Guardar/cargar escenarios con nombre
- Cálculo de intervalos
- Integración con routes y shapes
- (NUEVO) Generación de Sábanas (estilo VBA) y GTFS
"""

# --- Imports existentes ---
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
import re
import traceback

# --- NUEVOS IMPORTS para la integración ---
from fastapi import File, UploadFile, Form
import json
import io
import pandas as pd

from app.database import get_db
from app.models.scheduling_models import SchedulingParameters
from app.services.interval_processor import process_intervals

# --- NUEVOS IMPORTS DE SERVICIOS ---
# (Estos archivos deben existir en 'app/services/')
from app.services.sheet_generator import generate_sheet_from_tables, consolidate_sheet
from app.services.gtfs_generator import create_gtfs_from_sheet


router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# ==================== VALIDADORES ====================

def validate_time_format(time_str: str) -> str:
    """Valida que el formato sea HH:MM"""
    if not time_str:
        # Permite strings vacíos
        return time_str
    
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
    
    # --- CAMPOS AÑADIDOS (con valores por defecto) ---
    idle_threshold_min: int = 30
    max_wait_minutes_pairing: int = 15
    num_buses_pool: int = 20
    
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


# ==================== ENDPOINTS DE CÁLCULO (Existente) ====================

@router.post("/calculate-intervals")
async def calculate_intervals(request: CalculateIntervalsRequest):
    """
    Calcula intervalos de paso basados en los parámetros de entrada
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE PARÁMETROS (Existentes) ====================

@router.post("/parameters")
async def save_parameters(request: SaveParametersRequest, db: Session = Depends(get_db)):
    """
    Guarda o actualiza parámetros con nombre específico
    """
    print(f"\n💾 Guardando parámetros: '{request.name}'")
    
    try:
        route_id = request.tabla1.numeroRuta
        
        existing = db.query(SchedulingParameters)\
            .filter(
                SchedulingParameters.name == request.name,
                SchedulingParameters.route_id == route_id
            )\
            .first()
        
        if existing:
            print(f"  → Actualizando escenario existente (ID: {existing.id})")
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
            print(f"  → Creando nuevo escenario")
            new_params = SchedulingParameters(
                name=request.name,
                route_id=route_id,
                tabla1=request.tabla1.model_dump(),
                tabla2=[item.model_dump() for item in request.tabla2],
                tabla3=[item.model_dump() for item in request.tabla3],
                is_active=0
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
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")


@router.get("/parameters")
async def list_parameters(
    route_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todos los escenarios guardados
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


# ==================== ENDPOINT AUXILIAR: SHAPES (Existente) ====================

@router.get("/shapes-distances/{route_id}")
async def get_shapes_distances(route_id: str, db: Session = Depends(get_db)):
    """
    Obtiene las distancias máximas de los shapes de una ruta
    """
    print(f"\n📏 Obteniendo distancias de shapes para ruta: {route_id}")
    
    try:
        from app.models.gtfs_models import Shape
        
        shape_cb = db.query(Shape)\
            .filter(Shape.shape_id == f"{route_id}.1")\
            .order_by(Shape.shape_dist_traveled.desc())\
            .first()
        
        shape_bc = db.query(Shape)\
            .filter(Shape.shape_id == f"{route_id}.2")\
            .order_by(Shape.shape_dist_traveled.desc())\
            .first()
        
        distance_cb = float(shape_cb.shape_dist_traveled)/1000 if shape_cb and shape_cb.shape_dist_traveled else 0.0
        distance_bc = float(shape_bc.shape_dist_traveled)/1000 if shape_bc and shape_bc.shape_dist_traveled else 0.0
        
        print(f"  → C→B: {distance_cb:.2f} km")
        print(f"  → B→C: {distance_bc:.2f} km")
        
        return {
            "route_id": route_id,
            "centro_barrio": round(distance_cb, 2),
            "barrio_centro": round(distance_bc, 2)
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================================================================
# --- NUEVOS ENDPOINTS PARA GENERACIÓN DE SÁBANA (LÓGICA VBA) ---
# =================================================================

@router.post("/generate-sheet-from-intervals")
async def api_generate_sheet_from_intervals(
    parameters: str = Form(...),
    route_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Genera la sábana de programación final (estilo VBA)
    usando los intervalos calculados (Tablas 4-7) como input.
    """
    print("\n📄 Endpoint /generate-sheet-from-intervals llamado")
    try:
        params_data = json.loads(parameters)
        
        # Extraer los datos que el frontend preparó
        tabla1_data = params_data.get("general")
        headways_centro = params_data.get("headways_centro") # Tabla 4
        headways_barrio = params_data.get("headways_barrio") # Tabla 5
        travel_times_cb = params_data.get("travel_times_cb") # Tabla 6
        travel_times_bc = params_data.get("travel_times_bc") # Tabla 7

        # --- Validación de Inputs ---
        if not all([tabla1_data, headways_centro, headways_barrio, travel_times_cb, travel_times_bc]):
            raise HTTPException(status_code=400, detail="Faltan datos de intervalos. Asegúrate de 'Calcular Intervalos' primero.")

        # --- Carga de Archivo Excel (para GTFS futuro) ---
        route_data_df = None
        if route_file:
            print(f"  → Leyendo archivo de arcos: {route_file.filename}")
            contents = await route_file.read()
            route_data_df = pd.read_excel(io.BytesIO(contents))
            # (Aquí podrías usar route_data_df para recalcular tiempos)
        
        # 1. Generar viajes crudos (como Timetables_Variable)
        # 
        raw_trips = generate_sheet_from_tables(
            tabla1_data,
            headways_centro,
            headways_barrio,
            travel_times_cb,
            travel_times_bc
        )
        
        if not raw_trips:
            raise HTTPException(status_code=400, detail="No se generaron viajes. Revisa los parámetros de tiempo y headway.")

        # 2. Consolidar los viajes (como TimetableFinal)
        # 
        max_wait = int(tabla1_data.get('max_wait_minutes_pairing', 15))
        final_sheet = consolidate_sheet(raw_trips, max_wait_minutes=max_wait)
        
        print(f"✅ Sábana generada con {len(final_sheet)} viajes consolidados.")

        return final_sheet

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Error al decodificar parámetros JSON.")
    except Exception as e:
        traceback.print_exc() # Imprime el error completo en la consola del backend
        raise HTTPException(status_code=500, detail=f"Error al generar la sábana: {str(e)}")


@router.post("/generate-gtfs-from-sheet")
async def api_generate_gtfs_from_sheet(
    sheet_data_json: str = Form(...),  # La sábana final como string JSON
    route_file: UploadFile = File(...), # El Excel de arcos de línea
    db: Session = Depends(get_db)
):
    """
    (FUTURO) Genera los archivos trips.txt y stop_times.txt a partir de una sábana
    de programación y un archivo Excel de arcos de línea.
    """
    print("\n🚌 Endpoint /generate-gtfs-from-sheet llamado")
    try:
        # 1. Cargar datos
        sheet_data = json.loads(sheet_data_json)
        
        print(f"  → Leyendo archivo de arcos: {route_file.filename}")
        contents = await route_file.read()
        route_data_df = pd.read_excel(io.BytesIO(contents))
        
        # Validar que el excel de arcos tenga las columnas necesarias
        required_cols = ['stop_id', 'stop_sequence', 'direction_id', 'time_from_start_min']
        if not all(col in route_data_df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in route_data_df.columns]
            raise ValueError(f"Faltan columnas en el Excel de arcos de línea: {', '.join(missing)}")

        # 2. Llamar al servicio
        trips_df, stop_times_df = create_gtfs_from_sheet(sheet_data, route_data_df)

        print(f"✅ GTFS generado. Trips: {len(trips_df)}, StopTimes: {len(stop_times_df)}")
        
        # Devolvemos un resumen (en un futuro, devolvería un .zip)
        return {
            "message": "Archivos GTFS generados.",
            "trips_count": len(trips_df),
            "stop_times_count": len(stop_times_df)
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar GTFS: {str(e)}")


# ==================== HEALTH CHECK (Existente) ====================

@router.get("/health")
async def health_check():
    """Verifica que el servicio esté funcionando"""
    return {
        "status": "ok",
        "service": "Interval Calculator & Parameters Manager",
        "version": "2.1" # Versión actualizada
    }