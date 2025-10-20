"""
CSV Processor Service
Procesa archivos CSV con información de paradas (stops)
y los inserta o actualiza en la base de datos.
"""

import csv
import io
from typing import Dict
from sqlalchemy.orm import Session
from app.models.gtfs_models import Stop


class CSVProcessor:
    """Procesador de archivos CSV para paradas (stops)"""

    def __init__(self, db: Session):
        self.db = db

    def import_csv_to_stops(self, csv_content: str, replace_existing: bool = True) -> Dict:
        """
        Importa un archivo CSV a la tabla de stops.

        Args:
            csv_content: Contenido del archivo CSV como string
            replace_existing: Si True, reemplaza paradas existentes con el mismo stop_id

        Returns:
            Dict con estadísticas del proceso
        """
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            required = {"stop_id", "stop_name", "stop_lat", "stop_lon", "wheelchair_boarding"}

            if not required.issubset(reader.fieldnames):
                return {
                    "success": False,
                    "error": f"El CSV no contiene las columnas requeridas: {', '.join(required)}"
                }

            inserted = 0
            updated = 0
            skipped = 0
            processed_ids = set()

            for row in reader:
                stop_id = row.get("stop_id")
                stop_name = row.get("stop_name")
                stop_lat = row.get("stop_lat")
                stop_lon = row.get("stop_lon")
                wheelchair_boarding = row.get("wheelchair_boarding")

                if not stop_id or stop_id in processed_ids:
                    skipped += 1
                    continue

                processed_ids.add(stop_id)

                existing_stop = self.db.query(Stop).filter(Stop.stop_id == stop_id).first()

                if existing_stop:
                    if replace_existing:
                        existing_stop.stop_name = stop_name
                        existing_stop.stop_lat = stop_lat
                        existing_stop.stop_lon = stop_lon
                        existing_stop.wheelchair_boarding = wheelchair_boarding
                        updated += 1
                    else:
                        skipped += 1
                else:
                    new_stop = Stop(
                        stop_id=stop_id,
                        stop_name=stop_name,
                        stop_lat=stop_lat,
                        stop_lon=stop_lon,
                        wheelchair_boarding=wheelchair_boarding
                    )
                    self.db.add(new_stop)
                    inserted += 1

            self.db.commit()

            return {
                "success": True,
                "stops_inserted": inserted,
                "stops_updated": updated,
                "stops_skipped": skipped,
                "total_processed": inserted + updated + skipped
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
