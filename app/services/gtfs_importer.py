"""
GTFS Importer Service
Lee archivos GTFS (ZIP) y los importa a la base de datos
"""
import zipfile
import io
import csv
from typing import Dict, List, Optional, BinaryIO
from datetime import datetime, time, date
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd

from app.models.gtfs_models import (
    Agency, Route, Stop, Shape, ShapePoint, Calendar,
    Trip, StopTime, RouteStop
)


class GTFSImporter:
    """Importador de archivos GTFS"""
    
    # Archivos requeridos en GTFS
    REQUIRED_FILES = ['agency.txt', 'routes.txt', 'stops.txt', 'trips.txt', 'stop_times.txt']
    
    # Archivos opcionales
    OPTIONAL_FILES = ['calendar.txt', 'shapes.txt', 'calendar_dates.txt', 'frequencies.txt']
    
    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            'agencies': 0,
            'routes': 0,
            'stops': 0,
            'trips': 0,
            'stop_times': 0,
            'shapes': 0,
            'shape_points': 0,
            'calendar': 0,
            'errors': []
        }
        # Mapeos para referencias cruzadas
        self.route_mapping = {}  # route_id original -> route_id nuevo
        self.stop_mapping = {}   # stop_id original -> stop_id nuevo
        self.trip_mapping = {}   # trip_id original -> trip_id nuevo
        self.shape_mapping = {}  # shape_id original -> shape_id nuevo
        self.service_mapping = {} # service_id original -> service_id nuevo
    
    def import_gtfs(self, gtfs_zip: BinaryIO, agency_name: str = None) -> Dict:
        """
        Importa un archivo GTFS completo
        
        Args:
            gtfs_zip: Archivo ZIP binario del GTFS
            agency_name: Nombre opcional para la agencia (override del GTFS)
            
        Returns:
            Dict con estadísticas de importación
        """
        try:
            # Leer ZIP
            with zipfile.ZipFile(gtfs_zip, 'r') as zip_ref:
                # Validar archivos requeridos
                files_in_zip = zip_ref.namelist()
                missing_files = [f for f in self.REQUIRED_FILES if f not in files_in_zip]
                
                if missing_files:
                    raise ValueError(f"Archivos requeridos faltantes: {', '.join(missing_files)}")
                
                # Importar en orden (dependencias)
                print("📦 Importando agency.txt...")
                self._import_agency(zip_ref, agency_name)
                
                print("📦 Importando calendar.txt...")
                if 'calendar.txt' in files_in_zip:
                    self._import_calendar(zip_ref)
                else:
                    # Crear calendario por defecto
                    self._create_default_calendar()
                
                print("📦 Importando routes.txt...")
                self._import_routes(zip_ref)
                
                print("📦 Importando stops.txt...")
                self._import_stops(zip_ref)
                
                print("📦 Importando shapes.txt...")
                if 'shapes.txt' in files_in_zip:
                    self._import_shapes(zip_ref)
                
                print("📦 Importando trips.txt...")
                self._import_trips(zip_ref)
                
                print("📦 Importando stop_times.txt...")
                self._import_stop_times(zip_ref)
                
                # Commit final
                self.db.commit()
                
                print("✅ Importación completada")
                return {
                    'success': True,
                    'stats': self.stats
                }
                
        except Exception as e:
            self.db.rollback()
            self.stats['errors'].append(str(e))
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    def _import_agency(self, zip_ref: zipfile.ZipFile, override_name: str = None):
        """Importa agency.txt"""
        with zip_ref.open('agency.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                agency = Agency(
                    agency_name=override_name or row.get('agency_name', 'Unknown Agency'),
                    agency_url=row.get('agency_url'),
                    agency_timezone=row.get('agency_timezone', 'America/Merida'),
                    agency_phone=row.get('agency_phone'),
                    agency_lang=row.get('agency_lang')
                )
                self.db.add(agency)
                self.db.flush()
                self.stats['agencies'] += 1
    
    def _import_calendar(self, zip_ref: zipfile.ZipFile):
        """Importa calendar.txt"""
        with zip_ref.open('calendar.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                original_service_id = row['service_id']
                
                calendar = Calendar(
                    service_name=original_service_id,
                    monday=bool(int(row.get('monday', 1))),
                    tuesday=bool(int(row.get('tuesday', 1))),
                    wednesday=bool(int(row.get('wednesday', 1))),
                    thursday=bool(int(row.get('thursday', 1))),
                    friday=bool(int(row.get('friday', 1))),
                    saturday=bool(int(row.get('saturday', 1))),
                    sunday=bool(int(row.get('sunday', 1))),
                    start_date=self._parse_date(row['start_date']),
                    end_date=self._parse_date(row['end_date'])
                )
                self.db.add(calendar)
                self.db.flush()
                
                # Mapear IDs
                self.service_mapping[original_service_id] = calendar.service_id
                self.stats['calendar'] += 1
    
    def _create_default_calendar(self):
        """Crea un calendario por defecto si no existe en GTFS"""
        calendar = Calendar(
            service_name='default',
            monday=True, tuesday=True, wednesday=True,
            thursday=True, friday=True, saturday=True, sunday=True,
            start_date=date.today(),
            end_date=date(date.today().year + 1, 12, 31)
        )
        self.db.add(calendar)
        self.db.flush()
        self.service_mapping['default'] = calendar.service_id
        self.stats['calendar'] += 1
    
    def _import_routes(self, zip_ref: zipfile.ZipFile):
        """Importa routes.txt"""
        with zip_ref.open('routes.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                original_route_id = row['route_id']
                
                route = Route(
                    agency_id=1,  # Asume primera agencia
                    route_short_name=row.get('route_short_name', ''),
                    route_long_name=row.get('route_long_name', ''),
                    route_desc=row.get('route_desc'),
                    route_type=int(row.get('route_type', 3)),
                    route_url=row.get('route_url'),
                    route_color=row.get('route_color', 'FFFFFF'),
                    route_text_color=row.get('route_text_color', '000000')
                )
                self.db.add(route)
                self.db.flush()
                
                # Mapear IDs
                self.route_mapping[original_route_id] = route.route_id
                self.stats['routes'] += 1
    
    def _import_stops(self, zip_ref: zipfile.ZipFile):
        """Importa stops.txt"""
        with zip_ref.open('stops.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                original_stop_id = row['stop_id']
                
                stop = Stop(
                    stop_code=row.get('stop_code', original_stop_id),
                    stop_name=row.get('stop_name', 'Unknown Stop'),
                    stop_desc=row.get('stop_desc'),
                    stop_lat=float(row['stop_lat']),
                    stop_lon=float(row['stop_lon']),
                    zone_id=row.get('zone_id'),
                    stop_url=row.get('stop_url'),
                    location_type=int(row.get('location_type', 0)),
                    parent_station=row.get('parent_station'),
                    wheelchair_boarding=int(row.get('wheelchair_boarding', 0))
                )
                self.db.add(stop)
                self.db.flush()
                
                # Actualizar geometría con trigger de base de datos
                # (el trigger update_stop_geom se encarga de esto)
                
                # Mapear IDs
                self.stop_mapping[original_stop_id] = stop.stop_id
                self.stats['stops'] += 1
    
    def _import_shapes(self, zip_ref: zipfile.ZipFile):
        """Importa shapes.txt"""
        with zip_ref.open('shapes.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            # Agrupar por shape_id
            grouped = df.groupby('shape_id')
            
            for original_shape_id, group in grouped:
                # Ordenar por secuencia
                group = group.sort_values('shape_pt_sequence')
                
                # Crear LineString geometry
                coords = [(float(row['shape_pt_lon']), float(row['shape_pt_lat'])) 
                         for _, row in group.iterrows()]
                
                # Crear shape
                shape = Shape(
                    shape_geom=f"SRID=4326;LINESTRING({','.join([f'{lon} {lat}' for lon, lat in coords])})"
                )
                self.db.add(shape)
                self.db.flush()
                
                # Insertar puntos individuales
                for _, row in group.iterrows():
                    point = ShapePoint(
                        shape_id=shape.shape_id,
                        shape_pt_lat=float(row['shape_pt_lat']),
                        shape_pt_lon=float(row['shape_pt_lon']),
                        shape_pt_sequence=int(row['shape_pt_sequence']),
                        shape_dist_traveled=float(row.get('shape_dist_traveled', 0))
                    )
                    self.db.add(point)
                    self.stats['shape_points'] += 1
                
                # Mapear IDs
                self.shape_mapping[original_shape_id] = shape.shape_id
                self.stats['shapes'] += 1
    
    def _import_trips(self, zip_ref: zipfile.ZipFile):
        """Importa trips.txt"""
        with zip_ref.open('trips.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                original_trip_id = row['trip_id']
                original_route_id = row['route_id']
                original_service_id = row.get('service_id', 'default')
                original_shape_id = row.get('shape_id')
                
                trip = Trip(
                    route_id=self.route_mapping.get(original_route_id),
                    service_id=self.service_mapping.get(original_service_id, 1),
                    trip_headsign=row.get('trip_headsign'),
                    trip_short_name=row.get('trip_short_name'),
                    direction_id=int(row.get('direction_id', 0)),
                    block_id=int(row['block_id']) if row.get('block_id') else None,
                    shape_id=self.shape_mapping.get(original_shape_id) if original_shape_id else None,
                    wheelchair_accessible=int(row.get('wheelchair_accessible', 0)),
                    bikes_allowed=int(row.get('bikes_allowed', 0))
                )
                self.db.add(trip)
                self.db.flush()
                
                # Mapear IDs
                self.trip_mapping[original_trip_id] = trip.trip_id
                self.stats['trips'] += 1
    
    def _import_stop_times(self, zip_ref: zipfile.ZipFile):
        """Importa stop_times.txt"""
        with zip_ref.open('stop_times.txt') as f:
            df = pd.read_csv(f, dtype=str)
            
            for _, row in df.iterrows():
                original_trip_id = row['trip_id']
                original_stop_id = row['stop_id']
                
                stop_time = StopTime(
                    trip_id=self.trip_mapping.get(original_trip_id),
                    stop_id=self.stop_mapping.get(original_stop_id),
                    stop_sequence=int(row['stop_sequence']),
                    arrival_time=self._parse_time(row['arrival_time']),
                    departure_time=self._parse_time(row['departure_time']),
                    stop_headsign=row.get('stop_headsign'),
                    pickup_type=int(row.get('pickup_type', 0)),
                    drop_off_type=int(row.get('drop_off_type', 0)),
                    timepoint=int(row.get('timepoint', 1)),
                    shape_dist_traveled=float(row['shape_dist_traveled']) if row.get('shape_dist_traveled') else None
                )
                self.db.add(stop_time)
                self.stats['stop_times'] += 1
    
    def _parse_time(self, time_str: str) -> time:
        """Convierte string GTFS time a Python time (maneja >24:00:00)"""
        if not time_str or pd.isna(time_str):
            return time(0, 0, 0)
        
        parts = time_str.strip().split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        
        # GTFS permite horas > 24 (ej: 25:30:00 = 01:30:00 del día siguiente)
        # Para simplificar, normalizamos a 24h
        hours = hours % 24
        
        return time(hours, minutes, seconds)
    
    def _parse_date(self, date_str: str) -> date:
        """Convierte string GTFS date (YYYYMMDD) a Python date"""
        if not date_str or pd.isna(date_str):
            return date.today()
        
        date_str = str(date_str).strip()
        return datetime.strptime(date_str, '%Y%m%d').date()


# ============================================
# Funciones auxiliares
# ============================================

def validate_gtfs_file(gtfs_zip: BinaryIO) -> Dict:
    """
    Valida estructura básica del GTFS sin importarlo
    
    Returns:
        Dict con resultado de validación
    """
    try:
        with zipfile.ZipFile(gtfs_zip, 'r') as zip_ref:
            files_in_zip = zip_ref.namelist()
            
            # Verificar archivos requeridos
            missing = [f for f in GTFSImporter.REQUIRED_FILES if f not in files_in_zip]
            extra = [f for f in files_in_zip if f.endswith('.txt') and 
                    f not in GTFSImporter.REQUIRED_FILES + GTFSImporter.OPTIONAL_FILES]
            
            return {
                'valid': len(missing) == 0,
                'files_found': files_in_zip,
                'missing_required': missing,
                'extra_files': extra,
                'error': None
            }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }