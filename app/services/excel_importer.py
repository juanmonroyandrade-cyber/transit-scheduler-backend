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
        
        **Archivo TRIPS (orden de columnas):**
        route_id, service_id, trip_id, trip_headsign, direction_id, 
        block_id, shape_id, wheelchair_accessible, bikes_allowed
        
        **Archivo STOP_TIMES (orden de columnas):**
        trip_id, arrival_time, departure_time, stop_id, stop_sequence, 
        stop_headsign, pickup_type, drop_off_type, continuous_pickup, 
        continuous_drop_off, shape_dist_traveled, timepoint
        
        **Parámetros:**
        - trips_content: Contenido del archivo Excel de trips
        - stoptimes_content: Contenido del archivo Excel de stop_times
        - interpolate_times: Si True, interpola tiempos entre paradas
        - calculate_distances: Si True, calcula shape_dist_traveled automáticamente
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
            
            # ✅ Reordenar automáticamente al orden esperado por GTFS
            trips_df = trips_df[required_trips_cols]
            print(f"✅ Columnas de trips reordenadas al formato GTFS estándar")
            
            # Leer archivo de stop_times
            stoptimes_df = pd.read_excel(io.BytesIO(stoptimes_content), dtype=str)
            print(f"✅ Stop_times leídos: {len(stoptimes_df)} registros")
            print(f"   Columnas encontradas: {list(stoptimes_df.columns)}")
            
            # Validar que TODAS las columnas requeridas estén presentes (sin importar el orden)
            required_stoptimes_cols = [
                'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence',
                'stop_headsign', 'pickup_type', 'drop_off_type', 'continuous_pickup',
                'continuous_drop_off', 'shape_dist_traveled', 'timepoint'
            ]
            
            missing_stoptimes_cols = set(required_stoptimes_cols) - set(stoptimes_df.columns)
            if missing_stoptimes_cols:
                raise ValueError(f"Faltan columnas REQUERIDAS en archivo de stop_times: {missing_stoptimes_cols}")
            
            # ✅ Reordenar automáticamente al orden esperado por GTFS
            stoptimes_df = stoptimes_df[required_stoptimes_cols]
            print(f"✅ Columnas de stop_times reordenadas al formato GTFS estándar")
            
            # 1. Importar trips primero
            trips_imported = self._import_trips(trips_df)
            print(f"✅ Importados {trips_imported} trips")
            
            # ✅ 2. CRÍTICO: Hacer flush para que los trips estén disponibles
            self.db.flush()
            
            # 3. Calcular distancias si se solicita (ANTES de interpolar)
            if calculate_distances:
                print("📏 Calculando distancias desde shapes...")
                stoptimes_df = self._calculate_shape_distances(stoptimes_df)
                print("✅ Distancias calculadas")
            else:
                # Si no se calculan, asegurar que las columnas sean numéricas
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
        Calcula shape_dist_traveled para cada stop_time usando el shape más cercano.
        Similar al script de R que enviaste.
        """
        
        # ✅ Convertir columnas a tipos correctos ANTES de procesar
        df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
        df['stop_id'] = df['stop_id'].astype(str).str.strip()
        df['trip_id'] = df['trip_id'].astype(str).str.strip()
        
        # Obtener todos los stops con coordenadas
        stops = self.db.query(Stop).all()
        stops_dict = {
            str(stop.stop_id): (float(stop.stop_lat), float(stop.stop_lon))
            for stop in stops
        }
        
        # Obtener todos los shapes
        shapes = self.db.query(Shape).order_by(
            Shape.shape_id, 
            Shape.shape_pt_sequence
        ).all()
        
        # Agrupar shapes por shape_id
        shapes_dict = {}
        for shape in shapes:
            if shape.shape_id not in shapes_dict:
                shapes_dict[shape.shape_id] = []
            shapes_dict[shape.shape_id].append({
                'lat': float(shape.shape_pt_lat),
                'lon': float(shape.shape_pt_lon),
                'dist': float(shape.shape_dist_traveled or 0)
            })
        
        # Calcular distancia para cada stop_time
        for idx, row in df.iterrows():
            trip_id = str(row['trip_id']).strip()
            stop_id = str(row['stop_id']).strip()
            
            # Obtener shape_id del trip
            trip = self.db.query(Trip).filter(Trip.trip_id == trip_id).first()
            if not trip or not trip.shape_id:
                df.at[idx, 'shape_dist_traveled'] = 0
                continue
            
            shape_id = trip.shape_id
            
            # Obtener coordenadas del stop
            if stop_id not in stops_dict:
                df.at[idx, 'shape_dist_traveled'] = 0
                continue
            
            stop_lat, stop_lon = stops_dict[stop_id]
            
            # Obtener puntos del shape
            if shape_id not in shapes_dict:
                df.at[idx, 'shape_dist_traveled'] = 0
                continue
            
            shape_points = shapes_dict[shape_id]
            
            # Buscar punto más cercano en el shape
            min_distance = float('inf')
            closest_dist = 0
            
            for point in shape_points:
                distance = self.kml_processor.calculate_distance(
                    stop_lat, stop_lon,
                    point['lat'], point['lon']
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_dist = point['dist']
            
            df.at[idx, 'shape_dist_traveled'] = closest_dist
        
        # Forzar primera parada de cada trip a 0
        df = df.sort_values(['trip_id', 'stop_sequence'])
        for trip_id in df['trip_id'].unique():
            trip_mask = df['trip_id'] == trip_id
            first_idx = df[trip_mask].index[0]
            df.at[first_idx, 'shape_dist_traveled'] = 0
        
        return df
    
    def _interpolate_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Interpola tiempos entre la primera y última parada de cada trip.
        Basado en el código VBA que enviaste.
        """
        
        print("\n" + "="*70)
        print("INICIO DE INTERPOLACIÓN")
        print("="*70)
        
        # ✅ CRÍTICO: Convertir stop_sequence a int antes de procesar
        df['stop_sequence'] = pd.to_numeric(df['stop_sequence'], errors='coerce').fillna(0).astype(int)
        
        # ✅ CRÍTICO: Convertir shape_dist_traveled a float
        df['shape_dist_traveled'] = pd.to_numeric(df['shape_dist_traveled'], errors='coerce').fillna(0).astype(float)
        
        df = df.sort_values(['trip_id', 'stop_sequence'])
        
        trips_interpolated = 0
        stops_interpolated = 0
        
        for trip_id, group in df.groupby('trip_id'):
            # Obtener índices del grupo
            group_indices = group.index.tolist()
            
            # Obtener paradas con tiempo definido
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
            
            # Iterar sobre cada parada del grupo
            for idx in group_indices:
                # Si ya tiene tiempo, saltar
                current_time = df.at[idx, 'arrival_time']
                if pd.notna(current_time) and \
                   str(current_time).strip() != '' and \
                   str(current_time).strip() != 'nan':
                    continue
                
                current_seq = int(df.at[idx, 'stop_sequence'])
                current_dist = float(df.at[idx, 'shape_dist_traveled'])
                
                # Buscar tiempo anterior más cercano
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
                
                # Buscar próximo tiempo
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
                
                # Validar que tenemos datos válidos
                if not last_time or not next_time:
                    continue
                
                if next_dist <= last_dist:
                    print(f"   ⚠️  Seq {current_seq}: Distancias inválidas (last={last_dist:.1f}m, next={next_dist:.1f}m)")
                    continue
                
                # Interpolar
                delta_dist = next_dist - last_dist
                proportion = (current_dist - last_dist) / delta_dist
                
                # Convertir tiempos a segundos
                last_seconds = last_time.hour * 3600 + last_time.minute * 60 + last_time.second
                next_seconds = next_time.hour * 3600 + next_time.minute * 60 + next_time.second
                
                # Si next_time es menor que last_time, asumimos que cruzó medianoche
                if next_seconds < last_seconds:
                    next_seconds += 24 * 3600
                
                time_diff = next_seconds - last_seconds
                interpolated_seconds = int(last_seconds + (time_diff * proportion))
                
                # Convertir de vuelta a time
                interpolated_time = self._seconds_to_time(interpolated_seconds)
                time_str = self._format_time(interpolated_time, interpolated_seconds)
                
                df.at[idx, 'arrival_time'] = time_str
                df.at[idx, 'departure_time'] = time_str
                df.at[idx, 'timepoint'] = 0  # Marcar como interpolado
                
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
                # Parsear tiempos (pueden ser >24h)
                arrival_time_str = str(row.get('arrival_time', '')).strip()
                departure_time_str = str(row.get('departure_time', '')).strip()
                
                arrival_time = self._parse_time(arrival_time_str) if arrival_time_str and arrival_time_str != 'nan' else None
                departure_time = self._parse_time(departure_time_str) if departure_time_str and departure_time_str != 'nan' else None
                
                # ✅ Asegurar conversiones de tipos
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
                import traceback
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
        
        # Manejar formato HH:MM:SS o HH_MM_SS
        s = s.replace('_', ':')
        parts = s.split(':')
        
        if len(parts) < 2:
            return None
        
        try:
            h = int(parts[0])
            m = int(parts[1])
            sec = int(parts[2]) if len(parts) > 2 else 0
            
            # Normalizar horas > 24 (para almacenar en DB)
            h = h % 24
            
            return time(h, m, sec)
        except:
            return None
    
    def _format_time(self, t: time, total_seconds: Optional[int] = None) -> str:
        """Convierte time a string formato HH:MM:SS (maneja >24h si se pasa total_seconds)"""
        if t is None:
            return None
        
        # Si tenemos los segundos totales y son >24h, usar esos
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