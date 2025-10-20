# app/api/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, class_mapper
from sqlalchemy import inspect
from typing import Dict, Any
import math

from app.database import get_db
from app.models import gtfs_models

router = APIRouter(prefix="/admin", tags=["Admin"])

MODEL_MAP = {model.__tablename__: model for model in gtfs_models.Base.__subclasses__()}

def get_model_and_pk(table_name: str):
    if table_name not in MODEL_MAP:
        raise HTTPException(status_code=404, detail=f"Tabla '{table_name}' no encontrada.")
    model = MODEL_MAP[table_name]
    pk_columns = [key.name for key in inspect(model).primary_key]
    if not pk_columns:
        raise HTTPException(status_code=500, detail=f"El modelo '{table_name}' no tiene llave primaria.")
    if len(pk_columns) > 1:
        raise HTTPException(status_code=501, detail="La edición de llaves primarias compuestas no está soportada.")
    return model, pk_columns[0]

@router.get("/tables")
async def get_tables():
    return sorted(list(MODEL_MAP.keys()))

@router.get("/inspect/{table_name}")
async def inspect_table(table_name: str):
    model, pk_column_name = get_model_and_pk(table_name)
    mapper = class_mapper(model)
    columns = [{"name": c.name, "type": str(c.type), "primary_key": c.primary_key} for c in mapper.columns]
    return {"columns": columns, "pk": pk_column_name}

# ✅ ENDPOINT MODIFICADO PARA PAGINACIÓN
@router.get("/{table_name}")
async def get_table_data(
    table_name: str, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000)
):
    """Obtiene los registros de una tabla de forma paginada."""
    model, _ = get_model_and_pk(table_name)
    
    total_records = db.query(model).count()
    total_pages = math.ceil(total_records / per_page)
    
    offset = (page - 1) * per_page
    data = db.query(model).offset(offset).limit(per_page).all()
    
    return {
        "data": data,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "total_records": total_records,
    }

# --- (El resto de los endpoints POST, PUT, DELETE se mantienen igual) ---

@router.post("/{table_name}")
async def create_table_item(table_name: str, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    model, _ = get_model_and_pk(table_name)
    new_item = model(**item_data)
    try:
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear el registro: {e}")

@router.put("/{table_name}/{item_id}")
async def update_table_item(table_name: str, item_id: Any, item_data: Dict[str, Any], db: Session = Depends(get_db)):
    model, pk_column_name = get_model_and_pk(table_name)
    item_to_update = db.query(model).filter(getattr(model, pk_column_name) == item_id).first()
    if not item_to_update:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    for key, value in item_data.items():
        setattr(item_to_update, key, value)
    try:
        db.commit()
        db.refresh(item_to_update)
        return item_to_update
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al actualizar: {e}")

@router.delete("/{table_name}/{item_id}")
async def delete_table_item(table_name: str, item_id: Any, db: Session = Depends(get_db)):
    model, pk_column_name = get_model_and_pk(table_name)
    item_to_delete = db.query(model).filter(getattr(model, pk_column_name) == item_id).first()
    if not item_to_delete:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    try:
        db.delete(item_to_delete)
        db.commit()
        return {"status": "success", "message": "Registro eliminado."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar: {e}")