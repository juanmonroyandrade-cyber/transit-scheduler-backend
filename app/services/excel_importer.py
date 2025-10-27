# app/services/excel_importer.py

import pandas as pd
import openpyxl
import io
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import time, timedelta
import traceback

from app.models.gtfs_models import Trip, StopTime, Stop, Shape
from app.services.kml_processor import KMLProcessor


class ExcelImporter:
    """Importador de trips y stop_times desde archivos Excel separados con interpolación"""

    def __init__(self, db: Session):
        self.db = db
        self.kml_processor = KMLProcessor(db)

    def import_trips_and_stoptimes(
        self,
        trips_content: bytes,
        stoptimes_content: bytes,
        interpolate_times: bool = True,
        calculate_distances: bool = True
    ) -> Dict:
        """
        Importa trips y stop_times desde DOS archivos Excel separados.
        """

        try:
            print(f"\n{'='*70}")
            print(f"📥 IMPORTACIÓN DE TRIPS Y STOP_TIMES DESDE EXCEL")
            print(f"{'='*70}")

            # Leer archivo de trips
            trips_df = pd.read_excel(io.BytesIO(trips_content), dtype=str)
            print(f"✅ Trips leídos: {len(trips_df)} registros")
            print(f"   Columnas encontradas: {list(trips_df.columns)}")

            # Validar que TODAS las columnas requeridas estén presentes (sin importar el orden)
            required_trips_cols = [
                'route_id', 'service_id', 'trip_id', 'trip_headsign', 'direction_id',
                'block_id', 'shape_id', 'wheelchair_accessible', 'bikes_allowed'
            ]

            missing_trips_cols = set(required_trips_cols) - set(trips_df.columns)
            if missing_trips_cols:
                raise ValueError(f"Faltan columnas REQUERIDAS en archivo de trips: {missing_trips_cols}")

            # Reordenar automáticamente al orden esperado por GTFS
            trips_df = trips_df[required_trips_cols]
            print(f"✅ Columnas de trips reordenadas al formato GTFS estándar")

            # Leer archivo de stop_times
            stoptimes_df = pd.read_excel(io.BytesIO(stoptimes_content), dtype=str)
            print(f"✅ Stop_times leídos: {len(stoptimes_df)} registros")
            print(f"   Columnas encontradas: {list(stoptimes_df.columns)}")

            # Validar columnas stop_times
            required_stoptimes_cols = [
                'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence',
                'stop_headsign', 'pickup_type', 'drop_off_type', 'continuous_pickup',
                'continuous_drop_off', 'shape_dist_traveled', 'timepoint'
            ]

            missing_stoptimes_cols = set(required_stoptimes_cols) - set(stoptimes_df.columns)
            if missing_stoptimes_cols:
                raise ValueError(f"Faltan columnas REQUERIDAS en archivo de stop_times: {missing_stoptimes_cols}")

            # Reordenar stop_times
            stoptimes_df = stoptimes_df[required_stoptimes_cols]
            print(f"✅ Columnas de stop_times reordenadas al formato GTFS estándar")

            # 1. Importar trips primero
            trips_imported = self._import_trips(trips_df)
            print(f"✅ Importados {trips_imported} trips")

            # 2. Hacer flush para que los trips estén disponibles
            self.db.flush()

            # 3. Calcular distancias si se solicita (ANTES de interpolar)
            if calculate_distances:
                print("📏 Calculando distancias desde shapes...")
                stoptimes_df = self._calculate_shape_distances(stoptimes_df)
                print("✅ Distancias calculadas")
            else:
                stoptimes_df['shape_dist_traveled'] = pd.to_numeric(
                    stoptimes_df['shape_dist_traveled'],
                    errors='coerce'
                ).fillna(0).astype(float)
                print("⚠️  Usando distancias del archivo (sin calcular)")

            # 4. Interpolar tiempos si se solicita (DESPUÉS de calcular distancias)
            if interpolate_times:
                print("⏱️  Interpolando tiempos...")
                print(f"   Paradas antes de interpolar: {len(stoptimes_df[stoptimes_df['arrival_time'].notna() & (stoptimes_df['arrival_time'] != '')])}")
                stoptimes_df = self._interpolate_times(stoptimes_df)
                print(f"   Paradas después de interpolar: {len(stoptimes_df[stoptimes_df['arrival_time'].notna() & (stoptimes_df['arrival_time'] != '')])}")
                print("✅ Tiempos interpolados")

            # 5. Importar stop_times
            stop_times_imported = self._import_stop_times(stoptimes_df)
            print(f"✅ Importados {stop_times_imported} stop_times")

            # Commit
            self.db.commit()

            print(f"{'='*70}\n")

            return {
                "success": True,
                "trips_imported": trips_imported,
                "stop_times_imported": stop_times_imported,
                "interpolated": interpolate_times,
                "distances_calculated": calculate_distances
            }

        except Exception as e:
            self.db.rollback()
            print(f"❌ Error durante importación: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _import_trips(self, df: pd.DataFrame) -> int:
        """Importa trips desde DataFrame"""
        count = 0

        for _, row in df.iterrows():
            try:
                trip = Trip(
                    trip_id=str(row.get('trip_id', '')).strip(),
                    route_id=str(row.get('route_id', '')).strip(),
                    service_id=str(row.get('service_id', '')).strip(),
                    trip_headsign=str(row.get('trip_headsign', '')).strip() or None,
                    direction_id=self._safe_int(row.get('direction_id')),
                    block_id=str(row.get('block_id', '')).strip() or None,
                    shape_id=str(row.get('shape_id', '')).strip() or None,
                    wheelchair_accessible=self._safe_int(row.get('wheelchair_accessible')),
                    bikes_allowed=self._safe_int(row.get('bikes_allowed'))
                )

                self.db.add(trip)
                count += 1

            except Exception as e:
                print(f"⚠️  Error en trip {row.get('trip_id')}: {e}")
                continue

        self.db.flush()
        return count

    def _calculate_shape_distances(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula shape_dist_traveled para cada stop_time usando el shape más cercano
        y respetando la monotonicidad por trip (evita repeticiones iguales).
        """
        # Normalizar columnas
        df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
        df['stop_id'] = df['stop_id'].astype(str).str.strip()
        df['trip_id'] = df['trip_id'].astype(str).str.strip()

        # Cargar stops con coordenadas
        stops = self.db.query(Stop).all()
        stops_dict = {}
        for stop in stops:
            sid = str(stop.stop_id).strip()
            try:
                stops_dict[sid] = (float(stop.stop_lat), float(stop.stop_lon))
            except:
                continue

        # Cargar shapes (ordenados por shape_id y sequence)
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

        # Asegurar orden por distancia
        for sid, pts in shapes_dict.items():
            pts.sort(key=lambda x: x['dist'])

        # Procesar por trip (similar a MatchStopsAndShapesForTrip)
        df = df.sort_values(['trip_id', 'stop_sequence']).reset_index(drop=True)
        result_shape_dist = [0.0] * len(df)
        trip_groups = df.groupby('trip_id', sort=False)

        eps = 1.0  # incremento mínimo en metros para evitar empates

        print("🔍 Procesando trips para asignar shape_dist_traveled (monotonía estricta)...")
        for trip_id, group in trip_groups:
            indices = group.index.tolist()
            if len(indices) == 0:
                continue

            trip = self.db.query(Trip).filter(Trip.trip_id == trip_id).first()
            if not trip or not trip.shape_id:
                for idx in indices:
                    result_shape_dist[idx] = 0.0
                print(f" - Trip {trip_id}: sin shape_id -> asignando 0 a {len(indices)} paradas")
                continue

            shape_id = str(trip.shape_id)
            if shape_id not in shapes_dict or len(shapes_dict[shape_id]) == 0:
                for idx in indices:
                    result_shape_dist[idx] = 0.0
                print(f" - Trip {trip_id}: shape_id {shape_id} no encontrado en shapes -> 0")
                continue

            shape_points = shapes_dict[shape_id]
            last_matched_idx = 0
            last_matched_dist = float(shape_points[0]['dist']) if len(shape_points) > 0 else 0.0

            for local_pos, idx in enumerate(indices):
                row = df.loc[idx]
                stop_id = str(row['stop_id']).strip()

                if local_pos == 0:
                    # Primera parada = 0
                    result_shape_dist[idx] = 0.0
                    last_matched_idx = 0
                    last_matched_dist = 0.0
                    continue

                if stop_id not in stops_dict:
                    # sin coords -> usar last_matched_dist (se ajustará si es necesario más adelante)
                    result_shape_dist[idx] = last_matched_dist
                    print(f"   ⚠️ Trip {trip_id} Seq {row['stop_sequence']}: stop_id {stop_id} sin coords -> provisional {last_matched_dist:.1f}")
                    continue

                stop_lat, stop_lon = stops_dict[stop_id]

                # 1) punto globalmente más cercano
                min_dist = float('inf')
                min_idx = None
                for i_p, pt in enumerate(shape_points):
                    d = self.kml_processor.calculate_distance(stop_lat, stop_lon, pt['lat'], pt['lon'])
                    if d < min_dist:
                        min_dist = d
                        min_idx = i_p

                # 2) evitar retroceder: si min_idx < last_matched_idx, buscar mejor desde last_matched_idx hacia adelante
                chosen_idx = min_idx
                if min_idx is None:
                    chosen_idx = last_matched_idx
                elif min_idx < last_matched_idx:
                    min_dist_forward = float('inf')
                    min_idx_forward = None
                    for i_p in range(last_matched_idx, len(shape_points)):
                        pt = shape_points[i_p]
                        d = self.kml_processor.calculate_distance(stop_lat, stop_lon, pt['lat'], pt['lon'])
                        if d < min_dist_forward:
                            min_dist_forward = d
                            min_idx_forward = i_p
                    if min_idx_forward is not None:
                        chosen_idx = min_idx_forward
                    else:
                        chosen_idx = min_idx

                chosen_point = shape_points[chosen_idx]
                chosen_dist = float(chosen_point['dist'])

                # Si chosen_dist no avanza respecto al anterior, intentar buscar primer punto adelante con dist > last_matched_dist
                if chosen_dist <= last_matched_dist:
                    forward_found = False
                    for i_p in range(last_matched_idx + 1, len(shape_points)):
                        if shape_points[i_p]['dist'] > last_matched_dist:
                            chosen_idx = i_p
                            chosen_point = shape_points[chosen_idx]
                            chosen_dist = float(chosen_point['dist'])
                            forward_found = True
                            break

                    if not forward_found:
                        # fallback: dar un pequeño incremento para mantener estrictez
                        chosen_dist = last_matched_dist + eps
                        print(f"   ⚠️ Trip {trip_id} Seq {row['stop_sequence']}: no se encontró punto adelante -> usar last+{eps} = {chosen_dist:.1f}")

                # Finalmente asegurarnos chosen_dist >= last_matched_dist + eps
                if chosen_dist <= last_matched_dist:
                    chosen_dist = last_matched_dist + eps

                result_shape_dist[idx] = chosen_dist
                last_matched_idx = chosen_idx
                last_matched_dist = chosen_dist

            print(f" - Trip {trip_id}: asignadas {len(indices)} paradas (shape {shape_id})")

        # Asignar valores al df y asegurar float
        df['shape_dist_traveled'] = pd.to_numeric(pd.Series(result_shape_dist), errors='coerce').fillna(0.0).astype(float)

        # Forzar primera parada de cada trip a 0 y aplicar monotonía estricta por trip (última salvaguarda)
        for trip_id, group in df.groupby('trip_id'):
            indices = group.index.tolist()
            if not indices:
                continue
            df.at[indices[0], 'shape_dist_traveled'] = 0.0
            for i in range(1, len(indices)):
                prev_idx = indices[i - 1]
                cur_idx = indices[i]
                prev_dist = float(df.at[prev_idx, 'shape_dist_traveled'])
                cur_dist = float(df.at[cur_idx, 'shape_dist_traveled'])
                if cur_dist <= prev_dist:
                    df.at[cur_idx, 'shape_dist_traveled'] = prev_dist + eps
                    print(f"   🔧 Ajuste monotonicidad Trip {trip_id} Seq {df.at[cur_idx, 'stop_sequence']}: {cur_dist:.1f} -> {prev_dist + eps:.1f}")

        return df

    def _interpolate_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Interpola tiempos entre la primera y última parada de cada trip.
        """
        print("\n" + "="*70)
        print("INICIO DE INTERPOLACIÓN")
        print("="*70)

        df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
        df['shape_dist_traveled'] = pd.to_numeric(df['shape_dist_traveled'], errors='coerce').fillna(0).astype(float)

        df = df.sort_values(['trip_id', 'stop_sequence'])

        trips_interpolated = 0
        stops_interpolated = 0

        for trip_id, group in df.groupby('trip_id'):
            group_indices = group.index.tolist()

            has_time_mask = (
                group['arrival_time'].notna() &
                (group['arrival_time'] != '') &
                (group['arrival_time'].astype(str).str.strip() != '') &
                (group['arrival_time'].astype(str).str.strip() != 'nan')
            )
            has_time = group[has_time_mask]

            if len(has_time) < 2:
                print(f"⚠️  Trip {trip_id}: Solo {len(has_time)} paradas con tiempo (necesita ≥2). Omitiendo.")
                continue

            print(f"\n🔄 Interpolando trip: {trip_id}")
            print(f"   Total paradas: {len(group)}")
            print(f"   Con tiempo inicial: {len(has_time)}")

            trip_interpolated = False

            for idx in group_indices:
                current_time = df.at[idx, 'arrival_time']
                if pd.notna(current_time) and \
                   str(current_time).strip() != '' and \
                   str(current_time).strip() != 'nan':
                    continue

                current_seq = int(df.at[idx, 'stop_sequence'])
                current_dist = float(df.at[idx, 'shape_dist_traveled'])

                prev_stops = group[
                    (group['stop_sequence'] < current_seq) &
                    has_time_mask
                ]

                if len(prev_stops) == 0:
                    continue

                last_time_stop = prev_stops.iloc[-1]
                last_time = self._parse_time(last_time_stop['arrival_time'])
                last_dist = float(last_time_stop['shape_dist_traveled'])
                last_seq = int(last_time_stop['stop_sequence'])

                next_stops = group[
                    (group['stop_sequence'] > current_seq) &
                    has_time_mask
                ]

                if len(next_stops) == 0:
                    continue

                next_time_stop = next_stops.iloc[0]
                next_time = self._parse_time(next_time_stop['arrival_time'])
                next_dist = float(next_time_stop['shape_dist_traveled'])
                next_seq = int(next_time_stop['stop_sequence'])

                if not last_time or not next_time:
                    continue

                if next_dist <= last_dist:
                    print(f"   ⚠️  Seq {current_seq}: Distancias inválidas (last={last_dist:.1f}m, next={next_dist:.1f}m)")
                    continue

                delta_dist = next_dist - last_dist
                proportion = (current_dist - last_dist) / delta_dist

                last_seconds = last_time.hour * 3600 + last_time.minute * 60 + last_time.second
                next_seconds = next_time.hour * 3600 + next_time.minute * 60 + next_time.second

                if next_seconds < last_seconds:
                    next_seconds += 24 * 3600

                time_diff = next_seconds - last_seconds
                interpolated_seconds = int(last_seconds + (time_diff * proportion))

                interpolated_time = self._seconds_to_time(interpolated_seconds)
                time_str = self._format_time(interpolated_time, interpolated_seconds)

                df.at[idx, 'arrival_time'] = time_str
                df.at[idx, 'departure_time'] = time_str
                df.at[idx, 'timepoint'] = 0

                stops_interpolated += 1
                trip_interpolated = True

                print(f"   ✅ Seq {current_seq}: {time_str} (entre seq {last_seq} y {next_seq}, dist={current_dist:.1f}m, prop={proportion:.2%})")

            if trip_interpolated:
                trips_interpolated += 1

        print(f"\n{'='*70}")
        print(f"RESUMEN DE INTERPOLACIÓN:")
        print(f"  Trips procesados con interpolación: {trips_interpolated}")
        print(f"  Paradas interpoladas: {stops_interpolated}")
        print(f"{'='*70}\n")

        return df

    def _import_stop_times(self, df: pd.DataFrame) -> int:
        """Importa stop_times desde DataFrame"""
        count = 0

        for _, row in df.iterrows():
            try:
                arrival_time_str = str(row.get('arrival_time', '')).strip()
                departure_time_str = str(row.get('departure_time', '')).strip()

                arrival_time = self._parse_time(arrival_time_str) if arrival_time_str and arrival_time_str != 'nan' else None
                departure_time = self._parse_time(departure_time_str) if departure_time_str and departure_time_str != 'nan' else None

                stop_id_value = self._safe_int(row.get('stop_id'))
                if stop_id_value is None:
                    print(f"⚠️  Omitiendo stop_time: stop_id inválido para trip {row.get('trip_id')}")
                    continue

                stop_sequence_value = self._safe_int(row.get('stop_sequence'))
                if stop_sequence_value is None:
                    print(f"⚠️  Omitiendo stop_time: stop_sequence inválido para trip {row.get('trip_id')}")
                    continue

                stop_time = StopTime(
                    trip_id=str(row.get('trip_id', '')).strip(),
                    stop_id=stop_id_value,
                    stop_sequence=stop_sequence_value,
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                    timepoint=self._safe_int(row.get('timepoint'), 1),
                    shape_dist_traveled=self._safe_float(row.get('shape_dist_traveled'))
                )

                self.db.add(stop_time)
                count += 1

            except Exception as e:
                print(f"⚠️  Error en stop_time {row.get('trip_id')}-{row.get('stop_id')}: {e}")
                traceback.print_exc()
                continue

        self.db.flush()
        return count

    # === FUNCIONES AUXILIARES ===

    def _parse_time(self, time_str) -> Optional[time]:
        """Convierte string de tiempo a objeto time (maneja >24h)"""
        if not time_str or pd.isna(time_str) or str(time_str).strip() == '':
            return None

        s = str(time_str).strip()
        s = s.replace('_', ':')
        parts = s.split(':')

        if len(parts) < 2:
            return None

        try:
            h = int(parts[0])
            m = int(parts[1])
            sec = int(parts[2]) if len(parts) > 2 else 0

            h = h % 24
            return time(h, m, sec)
        except:
            return None

    def _format_time(self, t: time, total_seconds: Optional[int] = None) -> str:
        """Convierte time a string formato HH:MM:SS (maneja >24h si se pasa total_seconds)"""
        if t is None:
            return None

        if total_seconds is not None and total_seconds >= 24 * 3600:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"

    def _seconds_to_time(self, total_seconds: int) -> time:
        """Convierte segundos totales a objeto time (normaliza a <24h para el objeto)"""
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hours, minutes, seconds)

    def _safe_int(self, value, default=None):
        """Convierte valor a int de forma segura"""
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return default
        try:
            return int(float(value))
        except:
            return default

    def _safe_float(self, value, default=None):
        """Convierte valor a float de forma segura"""
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return default
        try:
            return float(value)
        except:
            return default
