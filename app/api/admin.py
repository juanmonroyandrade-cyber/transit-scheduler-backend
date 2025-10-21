# app/api/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, class_mapper
from sqlalchemy import inspect, func
from typing import Dict, Any
import math
import time
import traceback # Para logs detallados

from app.database import get_db
from app.models import gtfs_models

router = APIRouter(prefix="/admin", tags=["Admin"])

MODEL_MAP = {model.__tablename__: model for model in gtfs_models.Base.__subclasses__()}

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

@router.get("/tables")
async def get_tables():
    return sorted(list(MODEL_MAP.keys()))

@router.get("/inspect/{table_name}")
async def inspect_table(table_name: str):
    print(f"[Inspect API] Solicitud para inspeccionar tabla: {table_name}")
    try:
        model, pk_column_name = get_model_and_pk(table_name)
        mapper = class_mapper(model)
        columns = [{"name": c.name, "type": str(c.type), "primary_key": c.primary_key} for c in mapper.columns]
        print(f"  -> Inspección exitosa para {table_name}. Columnas: {len(columns)}, PK: {pk_column_name}")
        return {"columns": columns, "pk": pk_column_name}
    except HTTPException as http_exc:
        # Re-lanza las excepciones HTTP generadas por get_model_and_pk
        print(f"  -> Error HTTP durante inspección de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
         # Captura cualquier otro error durante la inspección/mapeo
         print(f"  -> Error inesperado durante inspección de {table_name}: {e}")
         traceback.print_exc() # Imprime el stack trace completo en el log del backend
         raise HTTPException(status_code=500, detail=f"Error interno al inspeccionar tabla '{table_name}': {str(e)}")


@router.get("/{table_name}")
async def get_table_data(
    table_name: str, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=500)
):
    print(f"[Data API] Solicitud para tabla: {table_name}, página: {page}, por_página: {per_page}")
    data_start_time = time.time()
    try:
        model, pk_col = get_model_and_pk(table_name) # Puede lanzar HTTPException
        
        # Contar registros
        count_start = time.time()
        total_records = db.query(func.count(getattr(model, pk_col))).scalar()
        count_duration = time.time() - count_start
        print(f"  > Contando registros ({table_name}): {total_records} ({(count_duration)*1000:.2f} ms)")

        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1
        # Asegurarse que la página solicitada no sea mayor al total de páginas
        if page > total_pages and total_records > 0:
             page = total_pages # Opcional: ir a la última página si se pide una inexistente
             # O podrías lanzar un error 404:
             # raise HTTPException(status_code=404, detail=f"Página {page} no existe. Total de páginas: {total_pages}")
        
        offset = (page - 1) * per_page
        
        # Obtener datos para la página
        data_query_start = time.time()
        data = db.query(model).order_by(getattr(model, pk_col)).offset(offset).limit(per_page).all() # Añadir order_by para consistencia
        data_query_duration = time.time() - data_query_start
        print(f"  > Obteniendo {len(data)} registros ({table_name}) ({(data_query_duration)*1000:.2f} ms)")
        
        response = {
            "data": data, "page": page, "per_page": per_page,
            "total_pages": total_pages, "total_records": total_records, }
        total_request_time = time.time() - data_start_time
        print(f"  -> Enviando respuesta para {table_name} p.{page}. Total time: {total_request_time:.3f} s")
        return response
        
    except HTTPException as http_exc:
        # Re-lanza excepciones HTTP (ej. 404 de get_model_and_pk)
        print(f"  -> Error HTTP al obtener datos de {table_name}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Captura cualquier otro error (ej. error de consulta SQLAlchemy)
        print(f"  -> Error inesperado al obtener datos de {table_name}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno al obtener datos de '{table_name}': {str(e)}")

# --- Endpoints POST, PUT, DELETE (Se mantienen igual que en la versión anterior, con conversión de tipos) ---
@router.post("/{table_name}")
async def create_table_item(table_name: str, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    # ... (código igual) ...
    model, _ = get_model_and_pk(table_name)
    mapper = class_mapper(model)
    cleaned_data = {}
    for col in mapper.columns:
        col_name = col.name
        value = item_data.get(col_name) # Usar get para evitar KeyError
        col_type_str = str(col.type).upper()

        if value == '' or value is None:
             if not col.nullable and not col.primary_key: # ¿Qué hacer con no nulos vacíos? Por ahora, omitir.
                  print(f"Warning: Campo no nulo {col_name} vacío/nulo omitido al crear.")
                  continue
             else:
                  cleaned_data[col_name] = None # Permitir nulos
        else:
            try:
                if 'INT' in col_type_str: cleaned_data[col_name] = int(value)
                elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str: cleaned_data[col_name] = float(value)
                elif 'BOOLEAN' in col_type_str: cleaned_data[col_name] = str(value).lower() in ['true', '1', 't', 'yes', 'y']
                # Añadir DATE/TIME si es necesario
                # elif 'DATE' in col_type_str: cleaned_data[col_name] = # parse date
                # elif 'TIME' in col_type_str: cleaned_data[col_name] = # parse time
                else: cleaned_data[col_name] = str(value) # Default a string
            except (ValueError, TypeError) as conv_err:
                 raise HTTPException(status_code=400, detail=f"Valor inválido para {col_name}: '{value}'. {conv_err}")

    try:
        new_item = model(**cleaned_data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    except Exception as e:
        db.rollback()
        print(f"Error DB al crear en {table_name}: {e}")
        raise HTTPException(status_code=400, detail=f"Error al crear en {table_name}: {e}")


@router.put("/{table_name}/{item_id}")
async def update_table_item(table_name: str, item_id: Any, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    # ... (código igual, con conversión de tipos) ...
    model, pk_column_name = get_model_and_pk(table_name)
    item_to_update = db.query(model).filter(getattr(model, pk_column_name) == item_id).first()
    if not item_to_update: raise HTTPException(status_code=404, detail="Registro no encontrado.")
    
    mapper = class_mapper(model)
    for key, value in item_data.items():
         col = mapper.columns.get(key)
         if col is not None:
             # Omitir actualización de llave primaria
             if col.primary_key: continue

             col_type_str = str(col.type).upper()
             try:
                 if value == '' or value is None:
                     if not col.nullable:
                          print(f"Warning: Intento de vaciar campo no nulo {key} en {table_name}. Ignorando.")
                          continue # Ignora el intento de vaciar un campo no nulo
                     else: value = None
                 elif 'INT' in col_type_str: value = int(value)
                 elif 'FLOAT' in col_type_str or 'DECIMAL' in col_type_str: value = float(value)
                 elif 'BOOLEAN' in col_type_str: value = str(value).lower() in ['true', '1', 't', 'yes', 'y']
                 # Añadir DATE/TIME si es necesario
                 else: value = str(value) # Default a string
                 
                 setattr(item_to_update, key, value)
             except (ValueError, TypeError) as conv_err:
                  raise HTTPException(status_code=400, detail=f"Valor inválido para {key}: '{value}'. {conv_err}")
         else:
             print(f"Warning: Se intentó actualizar columna inexistente '{key}' en tabla '{table_name}'.")


    try:
        db.commit()
        db.refresh(item_to_update)
        return item_to_update
    except Exception as e:
        db.rollback()
        print(f"Error DB al actualizar {table_name}: {e}")
        raise HTTPException(status_code=400, detail=f"Error al actualizar en {table_name}: {e}")

@router.delete("/{table_name}/{item_id}")
async def delete_table_item(table_name: str, item_id: Any, db: Session = Depends(get_db)):
    # ... (código igual) ...
    model, pk_column_name = get_model_and_pk(table_name)
    item_to_delete = db.query(model).filter(getattr(model, pk_column_name) == item_id).first()
    if not item_to_delete: raise HTTPException(status_code=404, detail="Registro no encontrado.")
    try:
        db.delete(item_to_delete)
        db.commit()
        return {"status": "success", "message": "Registro eliminado."}
    except Exception as e:
        db.rollback()
        print(f"Error DB al eliminar de {table_name}: {e}")
        if "FOREIGN KEY constraint failed" in str(e): raise HTTPException(status_code=400, detail=f"No se puede eliminar: el registro está siendo usado por otra tabla.")
        raise HTTPException(status_code=400, detail=f"Error al eliminar de {table_name}: {e}")