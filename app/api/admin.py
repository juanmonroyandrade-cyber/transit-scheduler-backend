# app/api/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, class_mapper
from sqlalchemy import inspect, func
from typing import Dict, Any
import math
import time
import traceback
from datetime import date, time as dt_time, datetime # Importar para posible parsing

from app.database import get_db
from app.models import gtfs_models

router = APIRouter(prefix="/admin", tags=["Admin"])

MODEL_MAP = {model.__tablename__: model for model in gtfs_models.Base.__subclasses__()}

def get_model_and_pk(table_name: str):
    # ... (sin cambios respecto a la versión anterior) ...
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

@router.get("/tables")
async def get_tables():
    return sorted(list(MODEL_MAP.keys()))

@router.get("/inspect/{table_name}")
async def inspect_table(table_name: str):
    # ... (sin cambios respecto a la versión anterior) ...
    print(f"[Inspect API] Solicitud para inspeccionar tabla: {table_name}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        mapper = class_mapper(model)
        columns = [{"name": c.name, "type": str(c.type), "primary_key": c.primary_key} for c in mapper.columns]
        print(f"  -> Inspección exitosa para {table_name}. Columnas: {len(columns)}, PK: {pk_column_name}")
        return {"columns": columns, "pk": pk_column_name}
    except HTTPException as http_exc:
        print(f"  -> Error HTTP durante inspección de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
         print(f"  -> Error inesperado durante inspección de {table_name}: {e}")
         traceback.print_exc()
         raise HTTPException(status_code=500, detail=f"Error interno al inspeccionar tabla '{table_name}': {str(e)}")

@router.get("/{table_name}")
async def get_table_data(
    table_name: str, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=500)
):
    # ... (sin cambios respecto a la versión anterior) ...
    print(f"[Data API] Solicitud para tabla: {table_name}, página: {page}, por_página: {per_page}")
    data_start_time = time.time()
    try:
        model, pk_col = get_model_and_pk(table_name)
        count_start = time.time()
        total_records = db.query(func.count(getattr(model, pk_col))).scalar()
        count_duration = time.time() - count_start
        print(f"  > Contando registros ({table_name}): {total_records} ({(count_duration)*1000:.2f} ms)")
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1
        if page > total_pages and total_records > 0: page = total_pages
        offset = (page - 1) * per_page
        data_query_start = time.time()
        # Ordenar por PK ayuda a la consistencia de la paginación
        data = db.query(model).order_by(getattr(model, pk_col)).offset(offset).limit(per_page).all()
        data_query_duration = time.time() - data_query_start
        print(f"  > Obteniendo {len(data)} registros ({table_name}) ({(data_query_duration)*1000:.2f} ms)")
        response = { "data": data, "page": page, "per_page": per_page, "total_pages": total_pages, "total_records": total_records, }
        total_request_time = time.time() - data_start_time
        print(f"  -> Enviando respuesta para {table_name} p.{page}. Total time: {total_request_time:.3f} s")
        return response
    except HTTPException as http_exc:
        print(f"  -> Error HTTP al obtener datos de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"  -> Error inesperado al obtener datos de {table_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno al obtener datos de '{table_name}': {str(e)}")


# --- ✅ FUNCIÓN AUXILIAR PARA CONVERSIÓN DE TIPOS ---
def _convert_value(value: Any, col: Any) -> Any:
    """Intenta convertir el valor al tipo esperado por la columna SQLAlchemy."""
    col_type_str = str(col.type).upper()
    target_value = None

    if value is None or value == '':
        if not col.nullable and not col.primary_key:
             # Para POST, podría ser un error si no hay default en DB.
             # Para PUT, si no es nulo, no deberíamos setearlo a None.
             print(f"Warning: Valor nulo/vacío para columna no nula '{col.name}'. Se usará None.")
             # Podríamos decidir lanzar error aquí si quisiéramos ser más estrictos en PUT.
             # raise ValueError(f"'{col.name}' no puede ser nulo.")
        target_value = None # Permitir nulos o confiar en default de DB
    else:
        try:
            # Orden de chequeo importante
            if 'BOOL' in col_type_str:
                if isinstance(value, bool): target_value = value
                else: target_value = str(value).lower() in ['true', '1', 't', 'yes', 'y', 'on'] # Añadido 'on' por si acaso
            elif 'INT' in col_type_str: target_value = int(value)
            elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str or 'NUMERIC' in col_type_str: target_value = float(value)
            elif 'DATE' in col_type_str: target_value = date.fromisoformat(str(value)) # Intentar parsear fecha
            elif 'TIME' in col_type_str: target_value = dt_time.fromisoformat(str(value)) # Intentar parsear hora
            # Podríamos añadir DATETIME
            else: target_value = str(value)
        except (ValueError, TypeError) as conv_err:
            # Determinar tipo para mensaje de error
            error_type_guess = "desconocido"
            if 'BOOL' in col_type_str: error_type_guess = "booleano (true/false)"
            elif 'INT' in col_type_str: error_type_guess = "entero"
            elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str: error_type_guess = "número decimal"
            elif 'DATE' in col_type_str: error_type_guess = "fecha (YYYY-MM-DD)"
            elif 'TIME' in col_type_str: error_type_guess = "hora (HH:MM:SS)"
            raise ValueError(f"Valor inválido '{value}'. No se pudo convertir a {error_type_guess}. ({conv_err})")
            
    return target_value


@router.post("/{table_name}")
async def create_table_item(table_name: str, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    print(f"[Admin POST API] Creando registro en {table_name} con datos: {item_data}")
    try:
        model, pk_col = get_model_and_pk(table_name)
        mapper = class_mapper(model)
        cleaned_data = {}
        
        for col in mapper.columns:
            col_name = col.name
            if col_name in item_data: # Procesa solo si el dato viene del frontend
                try:
                    cleaned_data[col_name] = _convert_value(item_data[col_name], col)
                except ValueError as conversion_error:
                    raise HTTPException(status_code=400, detail=f"Error de conversión para '{col_name}': {conversion_error}")
        
        print(f"  -> Datos limpios para crear: {cleaned_data}")
        new_item = model(**cleaned_data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        print(f"  -> Registro creado exitosamente en {table_name}.")
        return new_item
        
    except HTTPException as http_exc:
        db.rollback()
        print(f"  -> Error HTTP al crear en {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        db.rollback()
        print(f"  -> Error DB/inesperado al crear en {table_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error al crear registro en '{table_name}': {e}")


@router.put("/{table_name}/{item_id}")
async def update_table_item(table_name: str, item_id: Any, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    print(f"[Admin PUT API] Actualizando registro {item_id} en {table_name} con datos: {item_data}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        
        # Intentar convertir item_id al tipo correcto de la PK antes de buscar
        pk_col_obj = inspect(model).columns[pk_column_name]
        try:
             typed_item_id = _convert_value(item_id, pk_col_obj)
        except ValueError:
             raise HTTPException(status_code=400, detail=f"ID '{item_id}' tiene un formato inválido para la llave primaria.")

        item_to_update = db.query(model).filter(getattr(model, pk_column_name) == typed_item_id).first()
        if not item_to_update:
            print(f"  -> Error: Registro con ID '{typed_item_id}' no encontrado en {table_name}.")
            raise HTTPException(status_code=404, detail="Registro no encontrado.")
        
        mapper = class_mapper(model)
        updated_fields = {}
        for key, value in item_data.items():
             col = mapper.columns.get(key)
             if col is not None and not col.primary_key: # Solo actualiza columnas existentes y no la PK
                 try:
                     converted_value = _convert_value(value, col)
                     setattr(item_to_update, key, converted_value)
                     updated_fields[key] = converted_value
                 except ValueError as conversion_error:
                      raise HTTPException(status_code=400, detail=f"Error de conversión para '{key}': {conversion_error}")
             elif col is None:
                  print(f"Warning: Se intentó actualizar columna inexistente '{key}' en tabla '{table_name}'.")

        print(f"  -> Campos actualizados: {updated_fields}")
        db.commit()
        db.refresh(item_to_update)
        print(f"  -> Registro {typed_item_id} actualizado exitosamente en {table_name}.")
        return item_to_update

    except HTTPException as http_exc:
        db.rollback()
        print(f"  -> Error HTTP al actualizar {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        db.rollback()
        print(f"  -> Error DB/inesperado al actualizar {table_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error al actualizar registro en '{table_name}': {e}")


@router.delete("/{table_name}/{item_id}")
async def delete_table_item(table_name: str, item_id: Any, db: Session = Depends(get_db)):
    # ... (sin cambios significativos, solo añadir conversión de ID) ...
    print(f"[Admin DELETE API] Solicitud para eliminar registro {item_id} de {table_name}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        pk_col_obj = inspect(model).columns[pk_column_name]
        try:
            typed_item_id = _convert_value(item_id, pk_col_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"ID '{item_id}' tiene un formato inválido.")

        item_to_delete = db.query(model).filter(getattr(model, pk_column_name) == typed_item_id).first()
        if not item_to_delete:
            print(f"  -> Error: Registro con ID '{typed_item_id}' no encontrado para eliminar.")
            raise HTTPException(status_code=404, detail="Registro no encontrado.")
        
        db.delete(item_to_delete)
        db.commit()
        print(f"  -> Registro {typed_item_id} eliminado exitosamente de {table_name}.")
        return {"status": "success", "message": "Registro eliminado."}
        
    except HTTPException as http_exc:
        db.rollback()
        print(f"  -> Error HTTP al eliminar de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        db.rollback()
        print(f"  -> Error DB/inesperado al eliminar de {table_name}: {e}")
        traceback.print_exc()
        # Verificar si es error de FK
        if "FOREIGN KEY constraint failed" in str(e):
             raise HTTPException(status_code=400, detail=f"No se puede eliminar: el registro está siendo usado por otra tabla.")
        raise HTTPException(status_code=400, detail=f"Error al eliminar de '{table_name}': {e}")