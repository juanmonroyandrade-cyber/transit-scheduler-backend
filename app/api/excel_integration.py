# app/api/excel_integration.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
import shutil
from datetime import datetime
import json

from app.database import get_db
from app.services.excel_processor import process_scheduling_parameters

router = APIRouter(prefix="/excel", tags=["Excel Integration"])

# Directorio para almacenar archivos Excel
EXCEL_UPLOADS_DIR = r"C:\Users\ATY.IMDUT-CALLE60-D\Documents\Proyectos_GitHub\transit-scheduler-backend\uploads\excel"
EXCEL_OUTPUTS_DIR = r"C:\Users\ATY.IMDUT-CALLE60-D\Documents\Proyectos_GitHub\transit-scheduler-backend\outputs\excel"


# Crear directorios si no existen
os.makedirs(EXCEL_UPLOADS_DIR, exist_ok=True)
os.makedirs(EXCEL_OUTPUTS_DIR, exist_ok=True)


@router.post("/upload-base-excel")
async def upload_base_excel(file: UploadFile = File(...)):
    """
    Sube el archivo Excel base que se usará para los cálculos
    """
    try:
        if not file.filename.endswith(('.xlsx', '.xlsm')):
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos .xlsx o .xlsm"
            )
        
        # Guardar el archivo
        file_path = os.path.join(EXCEL_UPLOADS_DIR, "base_template.xlsx")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": "Archivo Excel base cargado correctamente",
            "filename": file.filename,
            "path": file_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-parameters")
async def process_parameters(parameters: Dict[str, Any]):
    """
    Procesa los parámetros de programación:
    1. Escribe en el Excel
    2. Recalcula fórmulas
    3. Extrae resultados
    
    Body esperado:
    {
      "tabla1": {...},
      "tabla2": [...],
      "tabla3": [...],
      ...
    }
    """
    try:
        print("\n🚀 Endpoint /process-parameters llamado")
        print(f"📦 Parámetros recibidos: {json.dumps(parameters, indent=2, default=str)}")
        
        # Verificar que existe el archivo base
        base_excel_path = os.path.join(EXCEL_UPLOADS_DIR, "base_template.xlsx")
        
        if not os.path.exists(base_excel_path):
            raise HTTPException(
                status_code=404,
                detail="No se encontró el archivo Excel base. Por favor, súbelo primero usando /upload-base-excel"
            )
        
        # Procesar el Excel
        results = process_scheduling_parameters(base_excel_path, parameters)
        
        if not results['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Error procesando Excel: {results.get('error', 'Error desconocido')}"
            )
        
        return {
            "success": True,
            "message": "Parámetros procesados correctamente",
            "results": {
                "tabla4": results['tabla4'],
                "tabla5": results['tabla5'],
                "tabla6": results['tabla6'],
                "tabla7": results['tabla7']
            },
            "timestamp": results['timestamp']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.get("/check-base-excel")
async def check_base_excel():
    """
    Verifica si existe un archivo Excel base cargado
    """
    base_excel_path = os.path.join(EXCEL_UPLOADS_DIR, "base_template.xlsx")
    
    exists = os.path.exists(base_excel_path)
    
    if exists:
        file_size = os.path.getsize(base_excel_path)
        modified_time = datetime.fromtimestamp(os.path.getmtime(base_excel_path))
        
        return {
            "exists": True,
            "path": base_excel_path,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "last_modified": modified_time.isoformat()
        }
    else:
        return {
            "exists": False,
            "message": "No hay archivo Excel base cargado"
        }