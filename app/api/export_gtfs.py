# app/api/export_gtfs.py

import io
import zipfile
import pandas as pd
import csv
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.database import get_db
# Importa todos tus modelos GTFS
from app.models.gtfs_models import (
    Agency, Route, Trip, StopTime, Stop, Calendar, 
    CalendarDate, Shape, FareAttribute, FareRule, FeedInfo
)

router = APIRouter(prefix="/export-gtfs", tags=["Export GTFS"])

# Define los modelos y los nombres de archivo .txt correspondientes
MODELS_TO_EXPORT = [
    (Agency, "agency.txt"),
    (Route, "routes.txt"),
    (Trip, "trips.txt"),
    (StopTime, "stop_times.txt"),
    (Stop, "stops.txt"),
    (Calendar, "calendar.txt"),
    (CalendarDate, "calendar_dates.txt"),
    (Shape, "shapes.txt"),
    (FareAttribute, "fare_attributes.txt"),
    (FareRule, "fare_rules.txt"),
    (FeedInfo, "feed_info.txt"),
]

# ✅ --- INICIO DE LA MODIFICACIÓN ---
# Lista de columnas 'id' personalizadas que NO son parte del estándar GTFS
# y solo se usan para facilitar la edición en el admin.
NON_GTFS_ID_COLS = ['id', 'feed_info_id']
# --- FIN DE LA MODIFICACIÓN ---


def format_dataframe_for_gtfs(df: pd.DataFrame, model) -> pd.DataFrame:
    """Aplica formato específico de GTFS a un DataFrame antes de guardarlo en CSV."""
    
    # Maneja columnas de fechas (de objeto date/datetime a YYYYMMDD string)
    date_columns = ['start_date', 'end_date', 'feed_start_date', 'feed_end_date', 'date']
    for col in date_columns:
        if col in df.columns:
            # Convierte a datetime (si no lo es ya) y luego a string YYYYMMDD
            # Maneja NaT (Not a Time) que puede aparecer si hay nulos
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y%m%d').replace('NaT', '')

    # Maneja columnas de tiempo (de objeto time a HH:MM:SS string)
    time_columns = ['arrival_time', 'departure_time']
    for col in time_columns:
        if col in df.columns:
             # Convierte a string con formato HH:MM:SS
             df[col] = df[col].apply(lambda x: x.strftime('%H:%M:%S') if pd.notna(x) and x else None)

    # Maneja columnas booleanas (de True/False/None a 1/0)
    bool_columns = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for col in bool_columns:
        if col in df.columns:
            # Convierte True a 1, y cualquier otra cosa (False, None, 0) a 0
            df[col] = df[col].apply(lambda x: 1 if x is True or x == 1 else 0).astype(int)

    # ✅ --- INICIO DE LA MODIFICACIÓN ---
    # Obtiene todas las columnas definidas en el modelo
    all_model_columns = [c.name for c in model.__table__.columns]
    
    # Define las columnas GTFS (todas las del modelo MENOS las IDs personalizadas)
    gtfs_columns = [col for col in all_model_columns if col not in NON_GTFS_ID_COLS]
    
    # Filtra el DataFrame para que solo tenga las columnas GTFS que realmente existen en el df
    final_columns = [col for col in gtfs_columns if col in df.columns]
    
    # Reordena el DataFrame para que coincida con el orden de las columnas GTFS
    df = df[final_columns]
    # --- FIN DE LA MODIFICACIÓN ---

    return df

@router.get("/export-zip")
async def export_gtfs_zip(db: Session = Depends(get_db)):
    """
    Consulta todas las tablas GTFS, las convierte a CSV y las devuelve en un archivo .zip.
    """
    print("Iniciando exportación de GTFS a .zip...")
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        for model, filename in MODELS_TO_EXPORT:
            print(f"  -> Procesando {filename} (Modelo: {model.__name__})...")
            try:
                query = db.query(model)
                df = pd.read_sql(query.statement, db.bind)
                
                if df.empty:
                    print(f"     ... Tabla {filename} está vacía, omitiendo.")
                    continue
                    
                # Elimina columna interna de SQLAlchemy si existe
                if '_sa_instance_state' in df.columns:
                    df = df.drop(columns=['_sa_instance_state'])
                
                # ✅ Aplica formato GTFS (incluyendo la eliminación de columnas 'id')
                df_formatted = format_dataframe_for_gtfs(df, model)

                # Convierte el DataFrame a un string CSV
                # na_rep='' asegura que los nulos se guarden como campos vacíos
                # quoting=csv.QUOTE_NONNUMERIC puede dar problemas si una columna
                # numérica (como stop_id) se almacena como string.
                # Usar QUOTE_MINIMAL es a menudo más seguro para GTFS.
                csv_data = df_formatted.to_csv(index=False, na_rep="", quoting=csv.QUOTE_MINIMAL)
                
                zip_file.writestr(filename, csv_data)
                print(f"     ... {filename} añadido al zip ({len(df)} registros).")
                
            except Exception as e:
                print(f"     *** ERROR procesando {filename}: {e}")
                traceback.print_exc() # Imprime el error completo en el log del backend
                zip_file.writestr(f"ERROR__{filename}.txt", f"No se pudo exportar {filename}.\nError: {e}")

    zip_buffer.seek(0)
    print("Exportación completada. Enviando archivo .zip.")

    # Devuelve el buffer como una respuesta de streaming
    return StreamingResponse(
        content=zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gtfs_export_{pd.Timestamp.now().strftime('%Y-%m-%d')}.zip"
        }
    )