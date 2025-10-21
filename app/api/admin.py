# app/api/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, class_mapper
from sqlalchemy import inspect, func
from typing import Dict, Any
import math
import time
import traceback
from datetime import date, time as dt_time

from app.database import get_db
from app.models import gtfs_models

router = APIRouter(prefix="/admin", tags=["Admin"])

MODEL_MAP = {model.__tablename__: model for model in gtfs_models.Base.__subclasses__()}

# --- Función Auxiliar get_model_and_pk (Sin cambios) ---
def get_model_and_pk(table_name: str):
    print(f"[get_model_and_pk] Buscando modelo para tabla: {table_name}")
    if table_name not in MODEL_MAP:
        print(f"  -> Error: Tabla '{table_name}' no encontrada en MODEL_MAP.")
        raise HTTPException(status_code=404, detail=f"Tabla '{table_name}' no encontrada.")
    model = MODEL_MAP[table_name]
    print(f"  -> Modelo encontrado: {model.__name__}")
    try:
        inspector = inspect(model)
        pk_columns = [key.name for key in inspector.primary_key]
        print(f"  -> Llaves primarias encontradas: {pk_columns}")
    except Exception as e:
        print(f"  -> Error al inspeccionar modelo {model.__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al inspeccionar modelo para tabla '{table_name}': {e}")
    if not pk_columns:
        print(f"  -> Error: Modelo '{model.__name__}' no tiene llave primaria definida.")
        raise HTTPException(status_code=500, detail=f"Modelo para '{table_name}' no tiene llave primaria.")
    if len(pk_columns) > 1:
         print(f"  -> Error: Modelo '{model.__name__}' tiene llave primaria compuesta (no soportado).")
         raise HTTPException(status_code=501, detail="Edición de llaves primarias compuestas no soportada.")
    print(f"  -> Devolviendo modelo {model.__name__} y PK '{pk_columns[0]}'")
    return model, pk_columns[0]

# --- Endpoint /tables (Sin cambios) ---
@router.get("/tables")
async def get_tables():
    return sorted(list(MODEL_MAP.keys()))

# --- Endpoint /inspect/{table_name} (Sin cambios) ---
@router.get("/inspect/{table_name}")
async def inspect_table(table_name: str):
    print(f"[Inspect API] Solicitud para inspeccionar tabla: {table_name}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        mapper = class_mapper(model)
        columns = [{"name": c.name, "type": str(c.type), "primary_key": c.primary_key} for c in mapper.columns]
        print(f"  -> Inspección exitosa para {table_name}.")
        return {"columns": columns, "pk": pk_column_name}
    except HTTPException as http_exc:
        print(f"  -> Error HTTP durante inspección de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
         print(f"  -> Error inesperado durante inspección de {table_name}: {e}")
         traceback.print_exc()
         raise HTTPException(status_code=500, detail=f"Error interno al inspeccionar '{table_name}': {str(e)}")

# --- ✅ Endpoint /{table_name} MODIFICADO (sin paginación) ---
@router.get("/{table_name}")
async def get_table_data(
    table_name: str, 
    db: Session = Depends(get_db)
):
    """Obtiene TODOS los registros de una tabla."""
    print(f"[Data API] Solicitud para TODOS los registros de: {table_name}")
    data_start_time = time.time()
    try:
        model, pk_col = get_model_and_pk(table_name)
        
        # Obtiene TODOS los datos, ordenados por la PK para consistencia
        data = db.query(model).order_by(getattr(model, pk_col)).all()
        
        total_request_time = time.time() - data_start_time
        print(f"  -> Obtenidos {len(data)} registros ({table_name}). Total time: {total_request_time:.3f} s")
        
        # Devuelve la lista de datos directamente
        return data
        
    except HTTPException as http_exc:
        print(f"  -> Error HTTP al obtener datos de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"  -> Error inesperado al obtener datos de {table_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno al obtener '{table_name}': {str(e)}")


# --- Función auxiliar _convert_value (Sin cambios) ---
def _convert_value(value: Any, col: Any) -> Any:
    # ... (tu código de conversión de tipos va aquí) ...
    col_type_str = str(col.type).upper()
    target_value = None
    if value is None or value == '':
        if not col.nullable and not col.primary_key: print(f"Warning: Valor nulo/vacío para col no nula '{col.name}'. Usando None.")
        target_value = None
    else:
        try:
            if 'BOOL' in col_type_str: target_value = str(value).lower() in ['true', '1', 't', 'yes', 'y', 'on']
            elif 'INT' in col_type_str: target_value = int(value)
            elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str or 'NUMERIC' in col_type_str: target_value = float(value)
            elif 'DATE' in col_type_str: target_value = date.fromisoformat(str(value))
            elif 'TIME' in col_type_str: target_value = dt_time.fromisoformat(str(value))
            else: target_value = str(value)
        except (ValueError, TypeError) as conv_err:
            error_type_guess = "desconocido"
            if 'BOOL' in col_type_str: error_type_guess = "booleano (true/false)"
            elif 'INT' in col_type_str: error_type_guess = "entero"
            elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str: error_type_guess = "número decimal"
            elif 'DATE' in col_type_str: error_type_guess = "fecha (YYYY-MM-DD)"
            elif 'TIME' in col_type_str: error_type_guess = "hora (HH:MM:SS)"
            raise ValueError(f"Valor '{value}'. No se pudo convertir a {error_type_guess}. ({conv_err})")
    return target_value

# --- Endpoint POST /{table_name} (Sin cambios) ---
@router.post("/{table_name}")
async def create_table_item(table_name: str, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    # ... (código igual) ...
    print(f"[Admin POST API] Creando en {table_name}: {item_data}")
    try:
        model, pk_col = get_model_and_pk(table_name)
        mapper = class_mapper(model)
        cleaned_data = {}
        for col in mapper.columns:
            col_name = col.name
            if col_name in item_data:
                try: cleaned_data[col_name] = _convert_value(item_data[col_name], col)
                except ValueError as conversion_error: raise HTTPException(status_code=400, detail=f"Error conversión para '{col_name}': {conversion_error}")
        print(f"  -> Datos limpios: {cleaned_data}")
        new_item = model(**cleaned_data)
        db.add(new_item); db.commit(); db.refresh(new_item)
        print(f"  -> Éxito al crear en {table_name}.")
        return new_item
    except HTTPException as http_exc: db.rollback(); print(f"  -> Error HTTP: {http_exc.detail}"); raise http_exc
    except Exception as e: db.rollback(); print(f"  -> Error DB/inesperado: {e}"); traceback.print_exc(); raise HTTPException(status_code=400, detail=f"Error al crear en '{table_name}': {e}")

# --- Endpoint PUT /{table_name}/{item_id} (Sin cambios) ---
@router.put("/{table_name}/{item_id}")
async def update_table_item(table_name: str, item_id: Any, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    # ... (código igual) ...
    print(f"[Admin PUT API] Actualizando {item_id} en {table_name}: {item_data}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        pk_col_obj = inspect(model).columns[pk_column_name]
        try: typed_item_id = _convert_value(item_id, pk_col_obj)
        except ValueError: raise HTTPException(status_code=400, detail=f"ID '{item_id}' inválido.")

        item_to_update = db.query(model).filter(getattr(model, pk_column_name) == typed_item_id).first()
        if not item_to_update: raise HTTPException(status_code=404, detail="Registro no encontrado.")
        
        mapper = class_mapper(model); updated_fields = {}
        for key, value in item_data.items():
             col = mapper.columns.get(key)
             if col is not None and not col.primary_key:
                 try:
                     converted_value = _convert_value(value, col)
                     setattr(item_to_update, key, converted_value); updated_fields[key] = converted_value
                 except ValueError as conversion_error: raise HTTPException(status_code=400, detail=f"Error conversión para '{key}': {conversion_error}")
             elif col is None: print(f"Warning: Columna inexistente '{key}' ignorada.")
        print(f"  -> Campos actualizados: {updated_fields}")
        db.commit(); db.refresh(item_to_update)
        print(f"  -> Éxito al actualizar {typed_item_id} en {table_name}.")
        return item_to_update
    except HTTPException as http_exc: db.rollback(); print(f"  -> Error HTTP: {http_exc.detail}"); raise http_exc
    except Exception as e: db.rollback(); print(f"  -> Error DB/inesperado: {e}"); traceback.print_exc(); raise HTTPException(status_code=400, detail=f"Error al actualizar en '{table_name}': {e}")

# --- Endpoint DELETE /{table_name}/{item_id} (Sin cambios) ---
@router.delete("/{table_name}/{item_id}")
async def delete_table_item(table_name: str, item_id: Any, db: Session = Depends(get_db)):
    # ... (código igual) ...
    print(f"[Admin DELETE API] Eliminando {item_id} de {table_name}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        pk_col_obj = inspect(model).columns[pk_column_name]
        try: typed_item_id = _convert_value(item_id, pk_col_obj)
        except ValueError: raise HTTPException(status_code=400, detail=f"ID '{item_id}' inválido.")

        item_to_delete = db.query(model).filter(getattr(model, pk_column_name) == typed_item_id).first()
        if not item_to_delete: raise HTTPException(status_code=404, detail="Registro no encontrado.")
        
        db.delete(item_to_delete); db.commit()
        print(f"  -> Éxito al eliminar {typed_item_id} de {table_name}.")
        return {"status": "success", "message": "Registro eliminado."}
    except HTTPException as http_exc: db.rollback(); print(f"  -> Error HTTP: {http_exc.detail}"); raise http_exc
    except Exception as e:
        db.rollback(); print(f"  -> Error DB/inesperado: {e}"); traceback.print_exc()
        if "FOREIGN KEY constraint failed" in str(e): raise HTTPException(status_code=400, detail="No se puede eliminar: registro en uso.")
        raise HTTPException(status_code=400, detail=f"Error al eliminar de '{table_name}': {e}")