"""
File Processor Service
Procesa archivos CSV y XLSX con información de paradas (stops)
y los inserta o actualiza en la base de datos.
"""

import csv
import io
from typing import Dict, Union, Tuple, List
from sqlalchemy.orm import Session
from app.models.gtfs_models import Stop
import openpyxl


class FileProcessor:
    """Procesador de archivos CSV y XLSX para paradas (stops)"""

    def __init__(self, db: Session):
        self.db = db

    def detect_file_type(self, filename: str) -> str:
        """
        Detecta el tipo de archivo basándose en la extensión.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            'csv' o 'xlsx'
        """
        filename_lower = filename.lower()
        if filename_lower.endswith('.xlsx'):
            return 'xlsx'
        elif filename_lower.endswith('.csv'):
            return 'csv'
        else:
            raise ValueError(f"Extensión de archivo no soportada: {filename}")

    def read_csv_content(self, csv_content: bytes) -> Tuple[List[Dict], List[str]]:
        """
        Lee contenido CSV con soporte para UTF-8.
        
        Args:
            csv_content: Contenido del archivo CSV como bytes
            
        Returns:
            Tupla con (lista de diccionarios con las filas, lista de nombres de campos)
        """
        try:
            # Intentar decodificar con diferentes encodings
            csv_text = None
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    csv_text = csv_content.decode(encoding)
                    break
                except (UnicodeDecodeError, AttributeError):
                    continue
            
            if csv_text is None:
                raise ValueError("No se pudo decodificar el archivo CSV con ninguna codificación conocida")
            
            # Leer el CSV
            reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(reader)
            fieldnames = list(reader.fieldnames) if reader.fieldnames else []
            
            return rows, fieldnames
            
        except Exception as e:
            raise ValueError(f"Error al leer CSV: {str(e)}")

    def read_xlsx_content(self, xlsx_content: bytes) -> Tuple[List[Dict], List[str]]:
        """
        Lee contenido XLSX.
        
        Args:
            xlsx_content: Contenido del archivo XLSX como bytes
            
        Returns:
            Tupla con (lista de diccionarios con las filas, lista de nombres de campos)
        """
        workbook = None
        try:
            # Cargar el workbook desde bytes
            workbook = openpyxl.load_workbook(io.BytesIO(xlsx_content), read_only=True, data_only=True)
            sheet = workbook.active
            
            if sheet is None:
                raise ValueError("El archivo XLSX no contiene hojas válidas")
            
            # Convertir el generador a lista para poder iterar múltiples veces
            all_rows = list(sheet.iter_rows(values_only=True))
            
            if not all_rows:
                raise ValueError("El archivo XLSX está vacío")
            
            # Obtener encabezados (primera fila)
            header_row = all_rows[0]
            headers = []
            for cell_value in header_row:
                if cell_value is not None:
                    # Convertir a string y limpiar espacios
                    header = str(cell_value).strip()
                    headers.append(header)
                else:
                    headers.append("")
            
            # Filtrar encabezados vacíos al final
            while headers and not headers[-1]:
                headers.pop()
            
            if not headers:
                raise ValueError("El archivo XLSX no contiene encabezados válidos en la primera fila")
            
            print(f"DEBUG - Encabezados encontrados: {headers}")
            print(f"DEBUG - Número de columnas: {len(headers)}")
            
            # Leer todas las filas de datos (desde la segunda fila)
            rows = []
            for row_idx, row_values in enumerate(all_rows[1:], start=2):
                # Saltar filas completamente vacías
                if not row_values or all(cell is None or str(cell).strip() == "" for cell in row_values):
                    continue
                
                row_dict = {}
                for col_idx, value in enumerate(row_values):
                    if col_idx < len(headers) and headers[col_idx]:
                        # Convertir el valor a string y limpiar
                        if value is not None:
                            row_dict[headers[col_idx]] = str(value).strip()
                        else:
                            row_dict[headers[col_idx]] = ""
                
                if row_dict:  # Solo agregar si tiene datos
                    rows.append(row_dict)
                    
                    # DEBUG: Imprimir primera fila de datos
                    if row_idx == 2:
                        print(f"DEBUG - Primera fila de datos: {row_dict}")
            
            print(f"DEBUG - Total de filas leídas: {len(rows)}")
            
            return rows, headers
            
        except Exception as e:
            raise ValueError(f"Error al leer archivo XLSX: {str(e)}")
        finally:
            if workbook:
                workbook.close()

    def import_file_to_stops(
        self, 
        file_content: bytes, 
        filename: str,
        replace_existing: bool = True
    ) -> Dict:
        """
        Importa un archivo CSV o XLSX a la tabla de stops.

        Args:
            file_content: Contenido del archivo como bytes
            filename: Nombre del archivo para detectar el tipo
            replace_existing: Si True, reemplaza paradas existentes con el mismo stop_id

        Returns:
            Dict con estadísticas del proceso
        """
        try:
            if not filename:
                return {
                    "success": False,
                    "error": "No se proporcionó el nombre del archivo"
                }
            
            # Detectar tipo de archivo
            file_type = self.detect_file_type(filename)
            print(f"DEBUG - Tipo de archivo detectado: {file_type}")
            print(f"DEBUG - Nombre del archivo: {filename}")
            print(f"DEBUG - Tamaño del contenido: {len(file_content)} bytes")
            
            # Leer contenido según el tipo
            if file_type == 'xlsx':
                rows, fieldnames = self.read_xlsx_content(file_content)
            else:  # csv
                rows, fieldnames = self.read_csv_content(file_content)
            
            # Validar que se pudieron leer datos
            if not fieldnames:
                return {
                    "success": False,
                    "error": "No se pudieron leer los encabezados del archivo"
                }
            
            if not rows:
                return {
                    "success": False,
                    "error": "El archivo no contiene datos (solo encabezados)"
                }
            
            # Validar columnas requeridas
            required = {"stop_id", "stop_name", "stop_lat", "stop_lon", "wheelchair_boarding"}
            fieldnames_set = set(fieldnames)
            
            if not required.issubset(fieldnames_set):
                missing = required - fieldnames_set
                return {
                    "success": False,
                    "error": f"El archivo no contiene las columnas requeridas. Faltan: {', '.join(missing)}. "
                           f"Columnas encontradas: {', '.join(fieldnames)}"
                }

            inserted = 0
            updated = 0
            skipped = 0
            errors = []
            processed_ids = set()

            for row_num, row in enumerate(rows, start=2):
                try:
                    stop_id = str(row.get("stop_id", "")).strip()
                    stop_name = str(row.get("stop_name", "")).strip()
                    stop_lat = row.get("stop_lat", "").strip() if row.get("stop_lat") else ""
                    stop_lon = row.get("stop_lon", "").strip() if row.get("stop_lon") else ""
                    wheelchair_boarding = row.get("wheelchair_boarding", "").strip() if row.get("wheelchair_boarding") else ""

                    # Validar que stop_id no esté vacío
                    if not stop_id:
                        skipped += 1
                        continue
                    
                    # Evitar duplicados en el mismo archivo
                    if stop_id in processed_ids:
                        skipped += 1
                        continue

                    processed_ids.add(stop_id)

                    # Buscar si existe la parada
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
                        
                except Exception as row_error:
                    error_msg = f"Error en fila {row_num}: {str(row_error)}"
                    print(error_msg)
                    errors.append(error_msg)
                    skipped += 1
                    continue

            self.db.commit()

            result = {
                "success": True,
                "file_type": file_type,
                "stops_inserted": inserted,
                "stops_updated": updated,
                "stops_skipped": skipped,
                "total_processed": inserted + updated + skipped
            }
            
            if errors:
                result["warnings"] = errors[:10]  # Solo primeros 10 errores
            
            return result

        except ValueError as ve:
            self.db.rollback()
            return {
                "success": False,
                "error": str(ve)
            }
        except Exception as e:
            self.db.rollback()
            import traceback
            error_detail = traceback.format_exc()
            print(f"ERROR COMPLETO:\n{error_detail}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}"
            }

    # Mantener compatibilidad con código existente
    def import_csv_to_stops(self, csv_content: str, replace_existing: bool = True) -> Dict:
        """
        Método legacy para mantener compatibilidad.
        Se recomienda usar import_file_to_stops en su lugar.
        """
        if isinstance(csv_content, str):
            csv_content = csv_content.encode('utf-8')
        return self.import_file_to_stops(csv_content, "file.csv", replace_existing)


# Mantener compatibilidad con el nombre anterior de la clase
CSVProcessor = FileProcessor