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


import numpy as np
import pandas as pd

def format_dataframe_for_gtfs(df: pd.DataFrame, model) -> pd.DataFrame:
    """Aplica formato GTFS a un DataFrame antes de guardarlo en CSV, con ajuste dinámico de horas 24/25."""

    # --- Fechas ---
    date_columns = ['start_date', 'end_date', 'feed_start_date', 'feed_end_date', 'date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y%m%d').replace('NaT', '')

    # --- Booleanos ---
    bool_columns = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for col in bool_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: 1 if x is True or x == 1 else 0).astype(int)

    # --- bikes_allowed (sin decimales) ---
    for col in ['bike_allowed', 'bikes_allowed']:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip() != '' else ''
            )

    # --- Columnas GTFS ---
    all_model_columns = [c.name for c in model.__table__.columns]
    gtfs_columns = [col for col in all_model_columns if col not in NON_GTFS_ID_COLS]
    final_columns = [col for col in gtfs_columns if col in df.columns]
    df = df[final_columns]

    # --- Función para ajustar tiempos dinámicamente por trip ---
    def adjust_times_grouped(times, trip_ids=None):
        """Ajusta horas dinámicamente: suma 24h si cruza medianoche por trip_id."""
        adjusted = []
        last_seconds = None
        last_trip = None

        for idx, t in enumerate(times):
            current_trip = trip_ids[idx] if trip_ids is not None else None

            # Reinicia contador al cambiar de trip
            if current_trip != last_trip:
                last_seconds = None
                last_trip = current_trip

            if pd.isna(t) or t == '':
                adjusted.append('')
                continue

            # Convierte a h,m,s
            if hasattr(t, 'hour'):
                h, m, s = t.hour, t.minute, t.second
            elif isinstance(t, (pd.Timestamp, np.datetime64)):
                temp = pd.to_datetime(t).time()
                h, m, s = temp.hour, temp.minute, temp.second
            else:
                parts = str(t).split(':')
                h, m, s = map(int, (parts + ['0','0'])[:3])

            total_seconds = h*3600 + m*60 + s

            # Suma 24h si retrocede respecto al anterior
            if last_seconds is not None and total_seconds < last_seconds:
                total_seconds += 24*3600

            last_seconds = total_seconds

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            adjusted.append(f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")

        return adjusted

    # --- Tiempos dinámicos ---
    time_columns = ['arrival_time', 'departure_time']
    for col in time_columns:
        if col in df.columns:
            trip_ids = df['trip_id'].tolist() if 'trip_id' in df.columns else None
            # Ordena por trip y stop_sequence si existen
            if 'trip_id' in df.columns and 'stop_sequence' in df.columns:
                df = df.sort_values(['trip_id', 'stop_sequence'])
            df[col] = adjust_times_grouped(df[col].tolist(), trip_ids=trip_ids)

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