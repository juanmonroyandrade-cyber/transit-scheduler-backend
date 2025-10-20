"""
GTFS Importer Service - CORREGIDO
"""
import pandas as pd
from zipfile import ZipFile
from io import BytesIO
from typing import Dict, BinaryIO
from datetime import datetime, time
from sqlalchemy.orm import Session
import traceback

# Importa todos los modelos para poder limpiarlos
from app.models.gtfs_models import (
    Agency,
    Calendar,
    FareAttribute,
    FareRule,
    FeedInfo,
    Route,
    Shape,
    Stop,
    StopTime,
    Trip,
)

class GTFSImporter:
    """Importador de archivos GTFS"""
    
    def __init__(self, db: Session):
        self.db = db
        self.agency_id = None

    # --- INICIO DE LA SECCIÓN CORREGIDA ---

    def _clear_existing_data(self):
        """
        Elimina todos los registros de las tablas GTFS.
        El orden es crucial para no violar las restricciones de llaves foráneas.
        """
        try:
            print("🗑️ Limpiando datos GTFS existentes...")
            
            # Se eliminan primero las tablas con dependencias (llaves foráneas)
            self.db.query(StopTime).delete(synchronize_session=False)
            self.db.query(Trip).delete(synchronize_session=False)
            self.db.query(FareRule).delete(synchronize_session=False)
            self.db.query(Route).delete(synchronize_session=False)
            
            # Ahora se pueden eliminar las tablas de las que dependían las anteriores
            self.db.query(Stop).delete(synchronize_session=False)
            self.db.query(Calendar).delete(synchronize_session=False)
            self.db.query(FareAttribute).delete(synchronize_session=False)
            self.db.query(Agency).delete(synchronize_session=False)
            
            # Finalmente, las tablas sin dependencias
            self.db.query(Shape).delete(synchronize_session=False)
            self.db.query(FeedInfo).delete(synchronize_session=False)
            
            self.db.commit()
            print("✅ Limpieza completada.")
        except Exception as e:
            print(f"❌ Error durante la limpieza de datos: {e}")
            self.db.rollback()
            raise  # Vuelve a lanzar la excepción para que sea manejada por el endpoint

    def import_gtfs(self, gtfs_zip: BinaryIO, agency_name: str = None) -> Dict:
        """
        Importa un archivo GTFS completo, limpiando los datos anteriores primero.
        """
        try:
            # 1. Limpiar todos los datos GTFS existentes
            self._clear_existing_data()

            # 2. Continuar con la importación como antes
            content = gtfs_zip.read() if hasattr(gtfs_zip, 'read') else gtfs_zip
            
            with ZipFile(BytesIO(content)) as zip_ref:
                results = {
                    "agency": 0, "calendar": 0, "fare_attributes": 0,
                    "fare_rules": 0, "feed_info": 0, "routes": 0,
                    "shapes": 0, "stops": 0, "stop_times": 0, "trips": 0
                }
                
                filenames = zip_ref.namelist()
                print(f"📦 Archivos encontrados en GTFS: {filenames}")
                
                # Importar en orden de dependencias
                if "agency.txt" in filenames:
                    print("📥 Importando agency...")
                    self._import_agency(zip_ref, agency_name)
                    results["agency"] = 1

                if "calendar.txt" in filenames:
                    print("📥 Importando calendar...")
                    calendars = self._import_calendar(zip_ref)
                    results["calendar"] = len(calendars) if calendars else 0

                if "fare_attributes.txt" in filenames:
                    print("📥 Importando fare_attributes...")
                    fares = self._import_fare_attributes(zip_ref)
                    results["fare_attributes"] = len(fares) if fares else 0

                if "routes.txt" in filenames:
                    print("📥 Importando routes...")
                    routes = self._import_routes(zip_ref)
                    results["routes"] = len(routes) if routes else 0

                if "fare_rules.txt" in filenames:
                    print("📥 Importando fare_rules...")
                    rules = self._import_fare_rules(zip_ref)
                    results["fare_rules"] = len(rules) if rules else 0

                if "shapes.txt" in filenames:
                    print("📥 Importando shapes...")
                    shapes = self._import_shapes(zip_ref)
                    results["shapes"] = len(shapes) if shapes else 0

                if "stops.txt" in filenames:
                    print("📥 Importando stops...")
                    stops = self._import_stops(zip_ref)
                    results["stops"] = len(stops) if stops else 0

                if "trips.txt" in filenames:
                    print("📥 Importando trips...")
                    trips = self._import_trips(zip_ref)
                    results["trips"] = len(trips) if trips else 0

                if "stop_times.txt" in filenames:
                    print("📥 Importando stop_times...")
                    stop_times = self._import_stop_times(zip_ref)
                    results["stop_times"] = len(stop_times) if stop_times else 0

                if "feed_info.txt" in filenames:
                    print("📥 Importando feed_info...")
                    feed = self._import_feed_info(zip_ref)
                    results["feed_info"] = 1 if feed else 0

                return {"status": "success", "imported": results}
                
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error en importación: {e}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    # --- FIN DE LA SECCIÓN CORREGIDA ---
    
    def _safe_int(self, value, default=None):
        """Convierte valor a int de forma segura"""
        try:
            if pd.isna(value):
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_str(self, value, default=""):
        """Convierte valor a string de forma segura"""
        try:
            if pd.isna(value):
                return default
            return str(value).strip()
        except (ValueError, TypeError):
            return default
    
    def _parse_time_safe(self, value):
        """Convierte string GTFS time a Python time (maneja >24:00:00)"""
        if pd.isna(value):
            return None
        
        s = str(value).strip()
        try:
            parts = s.split(":")
            h = int(parts[0]) if len(parts) > 0 else 0
            m = int(parts[1]) if len(parts) > 1 else 0
            sec = int(parts[2]) if len(parts) > 2 else 0
            
            # Normalizar horas > 24
            h_norm = h % 24
            return time(h_norm, m, sec)
        except Exception as e:
            print(f"Error parsing time '{value}': {e}")
            return None
    
    def _parse_date_safe(self, value):
        """Convierte string GTFS date (YYYYMMDD) a Python date"""
        if pd.isna(value):
            return None
        
        try:
            s = str(value).strip()
            return datetime.strptime(s, "%Y%m%d").date()
        except Exception as e:
            print(f"Error parsing date '{value}': {e}")
            return None

    def _import_agency(self, zip_ref, override_name=None):
        """Importa agency.txt"""
        df = pd.read_csv(zip_ref.open("agency.txt"), dtype=str)
        
        agency = Agency(
            agency_name=override_name or self._safe_str(df.iloc[0].get("agency_name"), "Unknown"),
            agency_url=self._safe_str(df.iloc[0].get("agency_url")),
            agency_timezone=self._safe_str(df.iloc[0].get("agency_timezone"), "America/Mexico_City"),
            agency_phone=self._safe_str(df.iloc[0].get("agency_phone"))
        )
        self.db.add(agency)
        self.db.commit()
        self.agency_id = agency.agency_id
        print(f"✅ Agency importada: {agency.agency_name} (ID: {agency.agency_id})")
        return agency

    def _import_calendar(self, zip_ref):
        """Importa calendar.txt"""
        df = pd.read_csv(zip_ref.open("calendar.txt"), dtype=str)
        calendars = []
        
        for _, row in df.iterrows():
            try:
                calendar = Calendar(
                    service_id=self._safe_str(row["service_id"]),
                    monday=bool(int(row.get("monday", 0))),
                    tuesday=bool(int(row.get("tuesday", 0))),
                    wednesday=bool(int(row.get("wednesday", 0))),
                    thursday=bool(int(row.get("thursday", 0))),
                    friday=bool(int(row.get("friday", 0))),
                    saturday=bool(int(row.get("saturday", 0))),
                    sunday=bool(int(row.get("sunday", 0))),
                    start_date=self._parse_date_safe(row["start_date"]),
                    end_date=self._parse_date_safe(row["end_date"])
                )
                self.db.add(calendar)
                calendars.append(calendar)
            except Exception as e:
                print(f"⚠️ Error importando calendar: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(calendars)} calendars importados")
        return calendars

    def _import_fare_attributes(self, zip_ref):
        """Importa fare_attributes.txt"""
        df = pd.read_csv(zip_ref.open("fare_attributes.txt"), dtype=str)
        fares = []
        
        for _, row in df.iterrows():
            try:
                fare = FareAttribute(
                    fare_id=self._safe_str(row["fare_id"]),
                    price=float(row["price"]),
                    currency_type=self._safe_str(row["currency_type"]),
                    payment_method=int(row["payment_method"]),
                    transfers=self._safe_int(row.get("transfers"))
                )
                self.db.add(fare)
                fares.append(fare)
            except Exception as e:
                print(f"⚠️ Error importando fare: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(fares)} fare_attributes importados")
        return fares

    def _import_fare_rules(self, zip_ref):
        """Importa fare_rules.txt"""
        df = pd.read_csv(zip_ref.open("fare_rules.txt"), dtype=str)
        rules = []
        
        for _, row in df.iterrows():
            try:
                rule = FareRule(
                    fare_id=self._safe_str(row["fare_id"]),
                    route_id=self._safe_str(row["route_id"])
                )
                self.db.add(rule)
                rules.append(rule)
            except Exception as e:
                print(f"⚠️ Error importando fare_rule: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(rules)} fare_rules importados")
        return rules

    def _import_feed_info(self, zip_ref):
        """Importa feed_info.txt"""
        df = pd.read_csv(zip_ref.open("feed_info.txt"), dtype=str)
        
        try:
            info = FeedInfo(
                feed_publisher_name=self._safe_str(df.iloc[0]["feed_publisher_name"]),
                feed_publisher_url=self._safe_str(df.iloc[0].get("feed_publisher_url")),
                feed_lang=self._safe_str(df.iloc[0].get("feed_lang")),
                feed_start_date=self._parse_date_safe(df.iloc[0].get("feed_start_date")),
                feed_end_date=self._parse_date_safe(df.iloc[0].get("feed_end_date")),
                feed_version=self._safe_str(df.iloc[0].get("feed_version")),
                default_lang=self._safe_str(df.iloc[0].get("default_lang")),
                feed_contact_url=self._safe_str(df.iloc[0].get("feed_contact_url")),
                # ✅ LÍNEA AÑADIDA para el campo que faltaba
                feed_contact_email=self._safe_str(df.iloc[0].get("feed_contact_email"))
            )
            self.db.add(info)
            self.db.commit()
            print(f"✅ Feed info importado")
            return info
        except Exception as e:
            print(f"⚠️ Error importando feed_info: {e}")
            return None

    def _import_routes(self, zip_ref):
        """Importa routes.txt"""
        df = pd.read_csv(zip_ref.open("routes.txt"), dtype=str)
        routes = []
        
        for _, row in df.iterrows():
            try:
                route = Route(
                    route_id=self._safe_str(row["route_id"]),
                    route_short_name=self._safe_str(row.get("route_short_name")),
                    route_long_name=self._safe_str(row.get("route_long_name")),
                    route_type=int(row["route_type"]),
                    route_color=self._safe_str(row.get("route_color")),
                    route_text_color=self._safe_str(row.get("route_text_color")),
                    agency_id=self.agency_id
                )
                self.db.add(route)
                routes.append(route)
            except Exception as e:
                print(f"⚠️ Error importando route: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(routes)} routes importados")
        return routes

    def _import_shapes(self, zip_ref):
        """Importa shapes.txt"""
        df = pd.read_csv(zip_ref.open("shapes.txt"), dtype=str)
        shapes = []
        
        for _, row in df.iterrows():
            try:
                shape = Shape(
                    shape_id=self._safe_str(row["shape_id"]),
                    shape_pt_lat=float(row["shape_pt_lat"]),
                    shape_pt_lon=float(row["shape_pt_lon"]),
                    shape_pt_sequence=int(row["shape_pt_sequence"]),
                    shape_dist_traveled=float(row["shape_dist_traveled"]) if pd.notna(row.get("shape_dist_traveled")) else None
                )
                self.db.add(shape)
                shapes.append(shape)
            except Exception as e:
                print(f"⚠️ Error importando shape: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(shapes)} shapes importados")
        return shapes

    def _import_stops(self, zip_ref):
        """Importa stops.txt"""
        df = pd.read_csv(zip_ref.open("stops.txt"), dtype=str)
        stops = []
        
        for _, row in df.iterrows():
            try:
                stop = Stop(
                    stop_id=self._safe_int(row["stop_id"]),
                    stop_name=self._safe_str(row["stop_name"]),
                    stop_lat=float(row["stop_lat"]),
                    stop_lon=float(row["stop_lon"]),
                    wheelchair_boarding=self._safe_int(row.get("wheelchair_boarding"))
                )
                self.db.add(stop)
                stops.append(stop)
            except Exception as e:
                print(f"⚠️ Error importando stop: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(stops)} stops importados")
        return stops

    def _import_trips(self, zip_ref):
        """Importa trips.txt"""
        df = pd.read_csv(zip_ref.open("trips.txt"), dtype=str)
        trips = []
        
        for _, row in df.iterrows():
            try:
                trip = Trip(
                    route_id=self._safe_str(row["route_id"]),
                    trip_id=self._safe_str(row["trip_id"]),
                    service_id=self._safe_str(row["service_id"]),
                    trip_headsign=self._safe_str(row.get("trip_headsign")),
                    direction_id=self._safe_int(row.get("direction_id")),
                    block_id=self._safe_str(row.get("block_id")),
                    shape_id=self._safe_str(row.get("shape_id")),
                    wheelchair_accessible=self._safe_int(row.get("wheelchair_accessible")),
                    bikes_allowed=self._safe_int(row.get("bikes_allowed"))
                )
                self.db.add(trip)
                trips.append(trip)
            except Exception as e:
                print(f"⚠️ Error importando trip: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(trips)} trips importados")
        return trips

    def _import_stop_times(self, zip_ref):
        """Importa stop_times.txt"""
        df = pd.read_csv(zip_ref.open("stop_times.txt"), dtype=str)
        stop_times = []
        
        for _, row in df.iterrows():
            try:
                st = StopTime(
                    trip_id=self._safe_str(row["trip_id"]),
                    stop_id=self._safe_int(row["stop_id"]),
                    arrival_time=self._parse_time_safe(row["arrival_time"]),
                    departure_time=self._parse_time_safe(row["departure_time"]),
                    timepoint=self._safe_int(row.get("timepoint")),
                    stop_sequence=int(row["stop_sequence"]),
                    shape_dist_traveled=float(row["shape_dist_traveled"]) if pd.notna(row.get("shape_dist_traveled")) else None
                )
                self.db.add(st)
                stop_times.append(st)
            except Exception as e:
                print(f"⚠️ Error importando stop_time: {e}")
                continue
        
        self.db.commit()
        print(f"✅ {len(stop_times)} stop_times importados")
        return stop_times


def validate_gtfs_file(gtfs_zip: BinaryIO) -> Dict:
    """
    Valida estructura básica del GTFS sin importarlo
    """
    try:
        content = gtfs_zip.read() if hasattr(gtfs_zip, 'read') else gtfs_zip
        
        with ZipFile(BytesIO(content)) as zip_ref:
            files_in_zip = zip_ref.namelist()
            
            required_files = ['agency.txt', 'routes.txt', 'stops.txt', 'trips.txt', 'stop_times.txt']
            missing = [f for f in required_files if f not in files_in_zip]
            
            return {
                'valid': len(missing) == 0,
                'files_found': files_in_zip,
                'missing_required': missing,
                'error': None
            }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }