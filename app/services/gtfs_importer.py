import zipfile
import io
import pandas as pd
from typing import Dict, BinaryIO
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement

from app.models.gtfs_models import (
    Agency, Route, Stop, Shape, ShapePoint, Calendar,
    Trip, StopTime
)

class GTFSImporter:
    REQUIRED_FILES = ['agency.txt', 'routes.txt', 'stops.txt', 'trips.txt', 'stop_times.txt']
    OPTIONAL_FILES = ['calendar.txt', 'shapes.txt', 'calendar_dates.txt', 'frequencies.txt']

    def __init__(self, db: Session):
        self.db = db
        self.stats = {'agencies':0,'routes':0,'stops':0,'trips':0,'stop_times':0,'shapes':0,'shape_points':0,'calendar':0,'errors':[]}
        self.route_mapping = {}
        self.stop_mapping = {}
        self.trip_mapping = {}
        self.shape_mapping = {}
        self.service_mapping = {}

    def import_gtfs(self, gtfs_zip: BinaryIO, agency_name: str = None) -> Dict:
        try:
            with zipfile.ZipFile(gtfs_zip, 'r') as zip_ref:
                files_in_zip = zip_ref.namelist()
                missing = [f for f in self.REQUIRED_FILES if f not in files_in_zip]
                if missing:
                    raise ValueError(f"Faltan archivos requeridos: {', '.join(missing)}")

                # Importar en orden
                self._import_agency(zip_ref, agency_name)
                if 'calendar.txt' in files_in_zip:
                    self._import_calendar(zip_ref)
                else:
                    self._create_default_calendar()
                self._import_routes(zip_ref)
                self._import_stops(zip_ref)
                if 'shapes.txt' in files_in_zip:
                    self._import_shapes(zip_ref)
                self._import_trips(zip_ref)
                self._import_stop_times(zip_ref)

                self.db.commit()
                return {'success': True, 'stats': self.stats}

        except Exception as e:
            self.db.rollback()
            self.stats['errors'].append(str(e))
            return {'success': False, 'error': str(e), 'stats': self.stats}

    def _import_agency(self, zip_ref, override_name=None):
        with zip_ref.open('agency.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                agency = Agency(
                    agency_name=override_name or row.get('agency_name', 'Unknown'),
                    agency_url=row.get('agency_url'),
                    agency_timezone=row.get('agency_timezone', 'America/Merida'),
                    agency_phone=row.get('agency_phone'),
                    agency_lang=row.get('agency_lang')
                )
                self.db.add(agency)
                self.db.flush()
                self.stats['agencies'] += 1

    def _import_calendar(self, zip_ref):
        with zip_ref.open('calendar.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                original_id = row['service_id']
                calendar = Calendar(
                    service_name=original_id,
                    monday=bool(int(row.get('monday',1))),
                    tuesday=bool(int(row.get('tuesday',1))),
                    wednesday=bool(int(row.get('wednesday',1))),
                    thursday=bool(int(row.get('thursday',1))),
                    friday=bool(int(row.get('friday',1))),
                    saturday=bool(int(row.get('saturday',1))),
                    sunday=bool(int(row.get('sunday',1))),
                    start_date=self._parse_date(row['start_date']),
                    end_date=self._parse_date(row['end_date'])
                )
                self.db.add(calendar)
                self.db.flush()
                self.service_mapping[original_id] = calendar.service_id
                self.stats['calendar'] += 1

    def _create_default_calendar(self):
        cal = Calendar(
            service_name='default',
            monday=True, tuesday=True, wednesday=True,
            thursday=True, friday=True, saturday=True, sunday=True,
            start_date=date.today(),
            end_date=date(date.today().year + 1,12,31)
        )
        self.db.add(cal)
        self.db.flush()
        self.service_mapping['default'] = cal.service_id
        self.stats['calendar'] += 1

    def _import_routes(self, zip_ref):
        with zip_ref.open('routes.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                original_id = row['route_id']
                route = Route(
                    agency_id=1,
                    route_short_name=row.get('route_short_name',''),
                    route_long_name=row.get('route_long_name',''),
                    route_desc=row.get('route_desc'),
                    route_type=int(row.get('route_type',3)),
                    route_color=row.get('route_color','FFFFFF'),
                    route_text_color=row.get('route_text_color','000000')
                )
                self.db.add(route)
                self.db.flush()
                self.route_mapping[original_id] = route.route_id
                self.stats['routes'] += 1

    def _import_stops(self, zip_ref):
        with zip_ref.open('stops.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                original_id = row['stop_id']
                stop = Stop(
                    stop_code=row.get('stop_code',original_id),
                    stop_name=row.get('stop_name','Unknown Stop'),
                    stop_desc=row.get('stop_desc'),
                    stop_lat=float(row['stop_lat']),
                    stop_lon=float(row['stop_lon']),
                    zone_id=row.get('zone_id'),
                    stop_url=row.get('stop_url'),
                    location_type=int(row.get('location_type',0)),
                    parent_station=row.get('parent_station'),
                    wheelchair_boarding=int(row.get('wheelchair_boarding',0)),
                    geom=WKTElement(f"POINT({row['stop_lon']} {row['stop_lat']})", srid=4326)
                )
                self.db.add(stop)
                self.db.flush()
                self.stop_mapping[original_id] = stop.stop_id
                self.stats['stops'] += 1

    def _import_shapes(self, zip_ref):
        with zip_ref.open('shapes.txt') as f:
            df = pd.read_csv(f, dtype=str)
            grouped = df.groupby('shape_id')
            for shape_id, group in grouped:
                group = group.sort_values('shape_pt_sequence')
                coords = [(float(r['shape_pt_lon']), float(r['shape_pt_lat'])) for _,r in group.iterrows()]
                shape = Shape(
                    shape_geom=WKTElement(f"LINESTRING({','.join([f'{lon} {lat}' for lon, lat in coords])})", srid=4326)
                )
                self.db.add(shape)
                self.db.flush()
                for _, row in group.iterrows():
                    point = ShapePoint(
                        shape_id=shape.shape_id,
                        shape_pt_lat=float(row['shape_pt_lat']),
                        shape_pt_lon=float(row['shape_pt_lon']),
                        shape_pt_sequence=int(row['shape_pt_sequence']),
                        shape_dist_traveled=float(row.get('shape_dist_traveled',0))
                    )
                    self.db.add(point)
                    self.stats['shape_points'] += 1
                self.shape_mapping[shape_id] = shape.shape_id
                self.stats['shapes'] += 1

    def _import_trips(self, zip_ref):
        with zip_ref.open('trips.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                original_trip_id = row['trip_id']
                trip = Trip(
                    route_id=self.route_mapping.get(row['route_id']),
                    service_id=self.service_mapping.get(row.get('service_id','default')),
                    trip_headsign=row.get('trip_headsign'),
                    trip_short_name=row.get('trip_short_name'),
                    direction_id=int(row.get('direction_id',0)),
                    block_id=int(row['block_id']) if row.get('block_id') else None,
                    shape_id=self.shape_mapping.get(row.get('shape_id')) if row.get('shape_id') else None,
                    wheelchair_accessible=int(row.get('wheelchair_accessible',0)),
                    bikes_allowed=int(row.get('bikes_allowed',0))
                )
                self.db.add(trip)
                self.db.flush()
                self.trip_mapping[original_trip_id] = trip.trip_id
                self.stats['trips'] += 1

    def _import_stop_times(self, zip_ref):
        with zip_ref.open('stop_times.txt') as f:
            df = pd.read_csv(f, dtype=str)
            for _, row in df.iterrows():
                st = StopTime(
                    trip_id=self.trip_mapping.get(row['trip_id']),
                    stop_id=self.stop_mapping.get(row['stop_id']),
                    stop_sequence=int(row['stop_sequence']),
                    arrival_time=self._parse_time(row['arrival_time']),
                    departure_time=self._parse_time(row['departure_time']),
                    stop_headsign=row.get('stop_headsign'),
                    pickup_type=int(row.get('pickup_type',0)),
                    drop_off_type=int(row.get('drop_off_type',0)),
                    timepoint=int(row.get('timepoint',1)),
                    shape_dist_traveled=float(row['shape_dist_traveled']) if row.get('shape_dist_traveled') else None
                )
                self.db.add(st)
                self.stats['stop_times'] += 1

    def _parse_time(self, s: str) -> time:
        if not s or pd.isna(s): return time(0,0,0)
        h,m,sec = [int(p) for p in s.split(':')]
        return time(h%24,m,sec)

    def _parse_date(self, s: str) -> date:
        if not s or pd.isna(s): return date.today()
        return datetime.strptime(str(s),'%Y%m%d').date()


def validate_gtfs_file(gtfs_zip: BinaryIO) -> Dict:
    try:
        with zipfile.ZipFile(gtfs_zip,'r') as zip_ref:
            files_in_zip = zip_ref.namelist()
            missing = [f for f in GTFSImporter.REQUIRED_FILES if f not in files_in_zip]
            extra = [f for f in files_in_zip if f.endswith('.txt') and f not in GTFSImporter.REQUIRED_FILES + GTFSImporter.OPTIONAL_FILES]
            return {'valid':len(missing)==0,'files_found':files_in_zip,'missing_required':missing,'extra_files':extra,'error':None}
    except Exception as e:
        return {'valid':False,'error':str(e)}
