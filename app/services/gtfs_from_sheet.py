import logging
import traceback
from typing import List, Dict, Any, Optional # Asegúrate de importar Optional
from datetime import time #
from sqlalchemy.orm import Session
import pandas as pd

from app.models.gtfs_models import Trip, StopTime, Stop, Shape
from app.services.kml_processor import KMLProcessor

# NOTA: Tu código de logger está bien, lo mantengo
# Si 'app.services.kml_processor' no existe, ajusta la importación


class GTFSFromSheetGenerator:
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.kml_processor = KMLProcessor(db)

        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger = logger

    def generate(
        self,
        sheet_data: List[Dict],
        route_id: str,
        route_name: str,
        service_id: str,
        periodicity: str,
        shape_id_s1: str, # Este puede venir del formulario (manual)
        shape_id_s2: str, # Este puede venir del formulario (manual)
        stops_data: List[Dict], # Esto viene del Excel o DB
        bikes_allowed: int = 0
    ) -> Dict:

        warnings = []
        errors = []

        self.logger.debug("INICIO generate(): route_id=%s service_id=%s", route_id, service_id)
        self.logger.debug("Recibido shape_id_s1 (manual): %s", shape_id_s1)
        self.logger.debug("Recibido shape_id_s2 (manual): %s", shape_id_s2)
        self.logger.debug("Número de filas en sheet_data: %d", len(sheet_data) if sheet_data is not None else 0)
        self.logger.debug("Número de paradas en stops_data: %d", len(stops_data) if stops_data is not None else 0)

        # Keys esperadas del Excel (basado en tu nota del frontend)
        expected_stop_keys = {"direction_id", "stop_sequence", "stop_id", "shape_id"}
        
        # --- LÓGICA DE SHAPE ID (NUEVO) ---
        
        # Separar paradas
        stops_s1 = sorted([s for s in stops_data if s.get('direction_id') == 0], key=lambda x: int(x.get('stop_sequence', 0)))
        stops_s2 = sorted([s for s in stops_data if s.get('direction_id') == 1], key=lambda x: int(x.get('stop_sequence', 0)))

        # Determinar Shape IDs efectivos
        effective_shape_id_s1 = shape_id_s1
        effective_shape_id_s2 = shape_id_s2

        # Si no se proveyó un shape_id_s1 manualmente, intentar leerlo del stops_data
        if not effective_shape_id_s1 and stops_s1:
            first_stop_s1 = stops_s1[0]
            if first_stop_s1.get('shape_id'):
                effective_shape_id_s1 = str(first_stop_s1['shape_id'])
                self.logger.info("shape_id_s1 no proveído, extraído de stops_data: %s", effective_shape_id_s1)

        # Si no se proveyó un shape_id_s2 manualmente, intentar leerlo del stops_data
        if not effective_shape_id_s2 and stops_s2:
            first_stop_s2 = stops_s2[0]
            if first_stop_s2.get('shape_id'):
                effective_shape_id_s2 = str(first_stop_s2['shape_id'])
                self.logger.info("shape_id_s2 no proveído, extraído de stops_data: %s", effective_shape_id_s2)
        
        # Validación final de Shape IDs
        if not effective_shape_id_s1:
            msg = "Error Crítico: No se pudo determinar el Shape ID para Sentido 1 (ni manual ni desde el Excel)."
            self.logger.error(msg)
            errors.append(msg)
        if not effective_shape_id_s2:
            msg = "Error Crítico: No se pudo determinar el Shape ID para Sentido 2 (ni manual ni desde el Excel)."
            self.logger.error(msg)
            errors.append(msg)

        if errors:
            return {'success': False, 'errors': errors, 'warnings': warnings, 'trips_created': 0, 'stop_times_created': 0}
        
        # --- FIN LÓGICA DE SHAPE ID ---


        if not stops_s1:
            msg = "No se encontraron paradas para direction_id == 0 (S1)."
            self.logger.warning(msg)
            warnings.append(msg)
        if not stops_s2:
            msg = "No se encontraron paradas para direction_id == 1 (S2)."
            self.logger.warning(msg)
            warnings.append(msg)

        trips_list = []
        stop_times_list = []
        trip_counter_s1 = 0
        trip_counter_s2 = 0
        period_map = {
            'Lunes-Viernes': 'L-V', 'Lunes a Viernes': 'L-V',
            'Sábado': 'S', 'Sabado': 'S',
            'Domingo': 'D'
        }
        period_code = period_map.get(periodicity, periodicity)
        malformed_rows = []

        for ridx, row in enumerate(sheet_data or []):
            try:
                bus_id = row.get("BusID")
                sal_centro = row.get("Salida en Centro")
                lleg_barrio = row.get("Llegada en Barrio")
                sal_barrio = row.get("Salida en Barrio")
                lleg_centro = row.get("Llegada en Centro")

                if bus_id is None:
                    msg = f"Fila {ridx}: falta BusID"
                    self.logger.warning(msg)
                    warnings.append(msg)

                # SENTIDO 1: Centro-Barrio
                if sal_centro and sal_centro != '---':
                    trip_counter_s1 += 1
                    # USAR SHAPE ID EFECTIVO
                    trip_id = f"R{route_id}_{period_code}_S1_{effective_shape_id_s1}_T{trip_counter_s1:02d}"
                    block_id = f"R{route_id}_{bus_id}"

                    trip_dict = {
                        'route_id': route_id,
                        'service_id': service_id,
                        'trip_id': trip_id,
                        'trip_headsign': route_name,
                        'direction_id': 0,
                        'block_id': block_id,
                        'shape_id': effective_shape_id_s1, # USAR SHAPE ID EFECTIVO
                        'wheelchair_accessible': 1,
                        'bikes_allowed': bikes_allowed
                    }
                    trips_list.append(trip_dict)

                    for i, stop in enumerate(stops_s1):
                        is_first = i == 0
                        is_last = i == len(stops_s1) - 1
                        arr_time = ''
                        if is_first:
                            arr_time = sal_centro
                        elif is_last and lleg_barrio and lleg_barrio != '---':
                            arr_time = lleg_barrio

                        stop_times_list.append({
                            'trip_id': trip_id,
                            'arrival_time': arr_time,
                            'departure_time': arr_time,
                            'stop_id': stop.get('stop_id'),
                            'stop_sequence': stop.get('stop_sequence'),
                            'timepoint': 1,
                            'shape_dist_traveled': ''
                        })

                # SENTIDO 2: Barrio-Centro
                if sal_barrio and sal_barrio != '---':
                    trip_counter_s2 += 1
                    # USAR SHAPE ID EFECTIVO
                    trip_id = f"R{route_id}_{period_code}_S2_{effective_shape_id_s2}_T{trip_counter_s2:02d}"
                    block_id = f"R{route_id}_{bus_id}"

                    trip_dict = {
                        'route_id': route_id,
                        'service_id': service_id,
                        'trip_id': trip_id,
                        'trip_headsign': route_name,
                        'direction_id': 1,
                        'block_id': block_id,
                        'shape_id': effective_shape_id_s2, # USAR SHAPE ID EFECTIVO
                        'wheelchair_accessible': 1,
                        'bikes_allowed': bikes_allowed
                    }
                    trips_list.append(trip_dict)

                    for i, stop in enumerate(stops_s2):
                        is_first = i == 0
                        is_last = i == len(stops_s2) - 1
                        arr_time = ''
                        if is_first:
                            arr_time = sal_barrio
                        elif is_last and lleg_centro and lleg_centro != '---':
                            arr_time = lleg_centro
                            
                        stop_times_list.append({
                            'trip_id': trip_id,
                            'arrival_time': arr_time,
                            'departure_time': arr_time,
                            'stop_id': stop.get('stop_id'),
                            'stop_sequence': stop.get('stop_sequence'),
                            'timepoint': 1,
                            'shape_dist_traveled': ''
                        })
            except Exception as e:
                tb = traceback.format_exc()
                msg = f"Error procesando row index {ridx}: {e}\n{tb}"
                self.logger.error(msg)
                errors.append(msg)
                malformed_rows.append({'index': ridx, 'row': row, 'error': str(e)})
        
        if not trips_list:
            msg = "No se generó ningún trip. Revisa la sábana de datos."
            self.logger.warning(msg)
            warnings.append(msg)

        trips_df = pd.DataFrame(trips_list)
        stop_times_df = pd.DataFrame(stop_times_list)
        self.logger.debug("trips creados (count): %d, stop_times creados (count): %d", len(trips_df), len(stop_times_df))

        if stop_times_df.empty:
            self.logger.warning("stop_times_df está vacío, no se puede interpolar ni insertar.")
            return {
                'success': len(errors) == 0,
                'trips_created': len(trips_df),
                'stop_times_created': 0,
                'warnings': warnings,
                'errors': errors
            }

        try:
            stop_times_df = self._calculate_and_interpolate(trips_df, stop_times_df, warnings)
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"Error en calculate_and_interpolate: {e}\n{tb}"
            self.logger.error(msg)
            errors.append(msg)

        try:
            insert_errors = self._insert_to_db(trips_df, stop_times_df)
            if insert_errors:
                errors.extend(insert_errors)
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"Error general en insert_to_db: {e}\n{tb}"
            self.logger.error(msg)
            errors.append(msg)

        result = {
            'success': len(errors) == 0,
            'trips_created': len(trips_df),
            'stop_times_created': len(stop_times_df),
            'warnings': warnings,
            'errors': errors,
            'malformed_rows_sample': malformed_rows[:5]
        }
        return result

    def _calculate_and_interpolate(self, trips_df, stop_times_df, warnings=None):
        if warnings is None:
            warnings = []

        stop_times_df['stop_sequence'] = pd.to_numeric(stop_times_df.get('stop_sequence', 0), errors='coerce').fillna(0).astype(int)
        stop_times_df['stop_id'] = stop_times_df.get('stop_id', '').astype(str).str.strip()
        stop_times_df['trip_id'] = stop_times_df.get('trip_id', '').astype(str).str.strip()

        stop_times_df = self._calculate_shape_distances(stop_times_df, trips_df, warnings)
        stop_times_df = self._interpolate_times(stop_times_df)

        return stop_times_df

    def _calculate_shape_distances(self, df, trips_df, warnings=None):
        if warnings is None:
            warnings = []

        stops = self.db.query(Stop).all()
        stops_dict = {str(s.stop_id).strip(): (float(s.stop_lat), float(s.stop_lon)) for s in stops}
        self.logger.debug("Stops cargadas desde DB: %d", len(stops_dict))

        shapes = self.db.query(Shape).order_by(Shape.shape_id, Shape.shape_pt_sequence).all()
        shapes_dict = {}
        for shp in shapes:
            sid = str(shp.shape_id)
            if sid not in shapes_dict:
                shapes_dict[sid] = []
            shapes_dict[sid].append({
                'lat': float(shp.shape_pt_lat),
                'lon': float(shp.shape_pt_lon),
                'dist': float(shp.shape_dist_traveled or 0.0)
            })

        for sid, pts in shapes_dict.items():
            pts.sort(key=lambda x: x['dist'])

        df = df.sort_values(['trip_id', 'stop_sequence']).reset_index(drop=True)
        result_shape_dist = [0.0] * len(df)
        eps = 1.0

        existing_shape_ids = set(shapes_dict.keys())
        self.logger.debug("Shape IDs existentes en DB: %d", len(existing_shape_ids))

        # trips_df (que generamos en generate()) no está en la DB aún.
        # Debemos consultar los trips que *ya* están en la DB (para rutas existentes)
        # O, mejor, usar el 'shape_id' que ya asignamos al 'trip_dict'
        
        # Mapear trip_id a shape_id desde trips_df
        trip_to_shape_map = pd.Series(trips_df.shape_id.values, index=trips_df.trip_id).to_dict()

        for trip_id, group in df.groupby('trip_id'):
            indices = group.index.tolist()
            if not indices:
                continue

            shape_id = str(trip_to_shape_map.get(trip_id, ''))
            
            if not shape_id:
                msg = f"Trip {trip_id} sin shape_id en trips_df; asignando shape_dist_traveled=0"
                self.logger.warning(msg)
                warnings.append(msg)
                continue
            
            if shape_id not in shapes_dict:
                msg = f"Shape {shape_id} del trip {trip_id} no encontrado en DB/shapes_dict"
                self.logger.warning(msg)
                warnings.append(msg)
                continue

            shape_points = shapes_dict[shape_id]
            last_matched_idx = 0
            last_matched_dist = 0.0

            for local_pos, idx in enumerate(indices):
                row = df.loc[idx]
                stop_id = str(row['stop_id']).strip()

                if local_pos == 0:
                    result_shape_dist[idx] = 0.0
                    continue

                if stop_id not in stops_dict:
                    msg = f"stop_id {stop_id} no encontrado en stops DB; usando last_matched_dist ({last_matched_dist})"
                    self.logger.warning(msg)
                    warnings.append(msg)
                    result_shape_dist[idx] = last_matched_dist
                    continue

                stop_lat, stop_lon = stops_dict[stop_id]
                min_dist = float('inf')
                min_idx = None
                
                # Buscar desde el último punto encontrado hacia adelante
                for i_p in range(last_matched_idx, len(shape_points)):
                    pt = shape_points[i_p]
                    d = self.kml_processor.calculate_distance(stop_lat, stop_lon, pt['lat'], pt['lon'])
                    if d < min_dist:
                        min_dist = d
                        min_idx = i_p
                
                chosen_idx = min_idx if min_idx is not None else last_matched_idx
                chosen_dist = float(shape_points[chosen_idx]['dist']) if chosen_idx is not None else last_matched_dist

                if chosen_dist <= last_matched_dist:
                     chosen_dist = last_matched_dist + eps

                result_shape_dist[idx] = chosen_dist
                last_matched_idx = chosen_idx
                last_matched_dist = chosen_dist

        df['shape_dist_traveled'] = pd.Series(result_shape_dist).astype(float)
        
        # ... (Resto de la lógica de monotonicidad)
        return df

    def _interpolate_times(self, df):
        df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
        df['shape_dist_traveled'] = pd.to_numeric(df['shape_dist_traveled'], errors='coerce').fillna(0).astype(float)
        df = df.sort_values(['trip_id', 'stop_sequence'])

        for trip_id, group in df.groupby('trip_id'):
            group_indices = group.index.tolist()
            has_time_mask = (
                group['arrival_time'].notna() &
                (group['arrival_time'] != '') &
                (group['arrival_time'].astype(str).str.strip() != '')
            )
            has_time = group[has_time_mask]

            if len(has_time) < 2:
                self.logger.debug("Trip %s: menos de 2 stops con tiempo; no se interpola.", trip_id)
                continue

            for idx in group_indices:
                current_time = df.at[idx, 'arrival_time']
                if pd.notna(current_time) and str(current_time).strip() != '':
                    continue

                current_seq = int(df.at[idx, 'stop_sequence'])
                current_dist = float(df.at[idx, 'shape_dist_traveled'])

                prev_stops = group[(group['stop_sequence'] < current_seq) & has_time_mask]
                if len(prev_stops) == 0: continue

                last_time_stop = prev_stops.iloc[-1]
                # CORRECCIÓN: Usar _parse_time_to_seconds
                last_sec = self._parse_time_to_seconds(last_time_stop['arrival_time'])
                last_dist = float(last_time_stop['shape_dist_traveled'])

                next_stops = group[(group['stop_sequence'] > current_seq) & has_time_mask]
                if len(next_stops) == 0: continue

                next_time_stop = next_stops.iloc[0]
                # CORRECCIÓN: Usar _parse_time_to_seconds
                next_sec = self._parse_time_to_seconds(next_time_stop['arrival_time'])
                next_dist = float(next_time_stop['shape_dist_traveled'])

                # CORRECCIÓN: Checar Nones
                if last_sec is None or next_sec is None or next_dist <= last_dist:
                    continue
                
                # Evitar división por cero
                dist_diff = next_dist - last_dist
                if dist_diff == 0:
                    continue

                proportion = (current_dist - last_dist) / dist_diff

                if next_sec < last_sec:
                    next_sec += 24 * 3600

                interp_sec = int(last_sec + ((next_sec - last_sec) * proportion))

                hours = interp_sec // 3600
                minutes = (interp_sec % 3600) // 60
                seconds = interp_sec % 60
                # CORRECCIÓN: Generar string HH:MM:SS (puede ser > 23)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                df.at[idx, 'arrival_time'] = time_str
                df.at[idx, 'departure_time'] = time_str
                df.at[idx, 'timepoint'] = 0

        return df

    def _parse_time_to_seconds(self, time_str: str) -> Optional[int]:
        """
        CORRECCIÓN CRÍTICA: Parsea HH:MM:SS a segundos totales. Maneja horas > 23.
        """
        if not time_str or pd.isna(time_str):
            return None
        s = str(time_str).strip().replace('_', ':')
        parts = s.split(':')
        if len(parts) < 2:
            return None
        try:
            # NO usar % 24
            h = int(parts[0]) 
            m = int(parts[1])
            sec = int(parts[2]) if len(parts) > 2 else 0
            return (h * 3600) + (m * 60) + sec
        except Exception:
            return None
# CÓDIGO A AÑADIR (dentro de la clase)

    def _parse_gtfs_time_to_time_obj(self, time_str: str) -> Optional[time]:
        """
        Convierte un string HH:MM:SS a un objeto time de Python.
        Maneja 'None' y advierte sobre horas >= 24 (que SQLite no soporta).
        """
        if not time_str or pd.isna(time_str):
            return None
        try:
            s = str(time_str).strip().replace('_', ':')
            parts = s.split(':')
            h = int(parts[0])
            m = int(parts[1])
            sec = int(parts[2]) if len(parts) > 2 else 0

            # ADVERTENCIA: Python/SQLite 'time' no soporta horas > 23.
            # Haremos un módulo (modulo 24) para evitar el crash.
            if h >= 24:
                self.logger.warning(f"Hora GTFS '{time_str}' (>=24h) se guardará como {h % 24}h.")
                h = h % 24
                
            return time(h, m, sec)
        except Exception as e:
            self.logger.error(f"Error al parsear '{time_str}' a objeto time: {e}")
            return None


    def _insert_to_db(self, trips_df, stop_times_df):
        """
        CORRECCIÓN CRÍTICA: 
        1. stop_id se guarda como string.
        2. arrival_time y departure_time se guardan como string (los que generamos).
        """
        insert_errors = []
        for i, (_, row) in enumerate(trips_df.iterrows()):
            try:
                trip_kwargs = row.to_dict()
                self.logger.debug("Insertando Trip %d: %s", i, trip_kwargs.get('trip_id'))
                trip = Trip(**trip_kwargs)
                self.db.add(trip)
            except Exception as e:
                tb = traceback.format_exc()
                msg = f"Error insertando Trip row {i} ({row.to_dict()}): {e}\n{tb}"
                self.logger.error(msg)
                insert_errors.append(msg)

        for i, (_, row) in enumerate(stop_times_df.iterrows()):
            try:
                # Obtenemos los strings de tiempo
                arr_time_str = row['arrival_time']
                dep_time_str = row['departure_time']
                
                # --- CORRECCIÓN ---
                # Convertimos los strings a objetos 'time' de Python
                arr_time_obj = self._parse_gtfs_time_to_time_obj(arr_time_str)
                dep_time_obj = self._parse_gtfs_time_to_time_obj(dep_time_str)
                # --- FIN CORRECCIÓN ---

                stop_id_str = str(row['stop_id']) if row.get('stop_id') not in (None, '', 'nan') else None

                st_kwargs = dict(
                    trip_id=row['trip_id'],
                    stop_id=stop_id_str,
                    stop_sequence=int(row['stop_sequence']) if row.get('stop_sequence') not in (None, '', 'nan') else 0,
                    
                    # --- CORRECCIÓN ---
                    arrival_time=arr_time_obj,   # <-- Usar el objeto time
                    departure_time=dep_time_obj, # <-- Usar el objeto time
                    # --- FIN CORRECCIÓN ---

                    timepoint=int(row.get('timepoint', 1)),
                    shape_dist_traveled=float(row.get('shape_dist_traveled') or 0.0)
                )

                if st_kwargs['stop_id'] is None:
                    msg = f"stop_time row {i} tiene stop_id inválido: {row.get('stop_id')}"
                    self.logger.warning(msg)
                    insert_errors.append(msg)
                    continue # No insertar esta fila

                st = StopTime(**st_kwargs)
                self.db.add(st)
            except Exception as e:
                tb = traceback.format_exc()
                msg = f"Error insertando StopTime row {i} ({row.to_dict()}): {e}\n{tb}"
                self.logger.error(msg)
                insert_errors.append(msg)

        if insert_errors:
            self.logger.warning("Errores detectados; haciendo rollback.")
            try:
                self.db.rollback()
            except Exception:
                self.logger.exception("Error al hacer rollback")
            return insert_errors

        try:
            self.db.commit()
            self.logger.info("Commit exitoso: %d trips, %d stop_times", len(trips_df), len(stop_times_df))
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"Error en commit: {e}\n{tb}"
            self.logger.error(msg)
            try:
                self.db.rollback()
            except Exception:
                self.logger.exception("Error al hacer rollback después de fallo de commit")
            return [msg]

        return []