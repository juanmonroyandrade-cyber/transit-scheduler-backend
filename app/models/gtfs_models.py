"""
Modelos SQLAlchemy para GTFS
Mapean las tablas de la base de datos
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, Time, Float, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base
from datetime import datetime

class Agency(Base):
    __tablename__ = "agencies"
    
    agency_id = Column(Integer, primary_key=True, index=True)
    agency_name = Column(String(255), nullable=False)
    agency_url = Column(String(500))
    agency_timezone = Column(String(100), default='America/Merida')
    agency_phone = Column(String(50))
    agency_lang = Column(String(10))
    agency_fare_url = Column(String(500))
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    routes = relationship("Route", back_populates="agency")


class Route(Base):
    __tablename__ = "routes"
    
    route_id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey('agencies.agency_id'))
    route_short_name = Column(String(50), nullable=False, index=True)
    route_long_name = Column(String(255))
    route_desc = Column(Text)
    route_type = Column(Integer, default=3)  # 3 = Bus
    route_url = Column(String(500))
    route_color = Column(String(6), default='FFFFFF')
    route_text_color = Column(String(6), default='000000')
    is_electric = Column(Boolean, default=False)
    km_total = Column(DECIMAL(10, 2))
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    agency = relationship("Agency", back_populates="routes")
    trips = relationship("Trip", back_populates="route", cascade="all, delete-orphan")
    shapes = relationship("Shape", back_populates="route", cascade="all, delete-orphan")
    route_stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")


class Stop(Base):
    __tablename__ = "stops"
    
    stop_id = Column(Integer, primary_key=True, index=True)
    stop_code = Column(String(50), unique=True, index=True)
    stop_name = Column(String(255), nullable=False, index=True)
    stop_desc = Column(Text)
    stop_lat = Column(DECIMAL(10, 8), nullable=False)
    stop_lon = Column(DECIMAL(11, 8), nullable=False)
    zone_id = Column(String(50))
    stop_url = Column(String(500))
    location_type = Column(Integer, default=0)
    parent_station = Column(String(50))
    wheelchair_boarding = Column(Integer, default=0)
    geom = Column(Geometry('POINT', srid=4326))
    created_at = Column(Date, default=datetime.utcnow)
    updated_at = Column(Date, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    stop_times = relationship("StopTime", back_populates="stop")


class Shape(Base):
    __tablename__ = "shapes"
    
    shape_id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id', ondelete='CASCADE'))
    shape_geom = Column(Geometry('LINESTRING', srid=4326))
    shape_dist_traveled = Column(DECIMAL(10, 3))
    kml_filename = Column(String(255))
    created_at = Column(Date, default=datetime.utcnow)
    
    # Relaciones
    route = relationship("Route", back_populates="shapes")
    shape_points = relationship("ShapePoint", back_populates="shape", cascade="all, delete-orphan")


class ShapePoint(Base):
    __tablename__ = "shape_points"
    
    id = Column(Integer, primary_key=True, index=True)
    shape_id = Column(Integer, ForeignKey('shapes.shape_id', ondelete='CASCADE'), index=True)
    shape_pt_lat = Column(DECIMAL(10, 8), nullable=False)
    shape_pt_lon = Column(DECIMAL(11, 8), nullable=False)
    shape_pt_sequence = Column(Integer, nullable=False)
    shape_dist_traveled = Column(DECIMAL(10, 3))
    
    # Relaciones
    shape = relationship("Shape", back_populates="shape_points")


class Calendar(Base):
    __tablename__ = "calendar"
    
    service_id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, unique=True)
    monday = Column(Boolean, default=True)
    tuesday = Column(Boolean, default=True)
    wednesday = Column(Boolean, default=True)
    thursday = Column(Boolean, default=True)
    friday = Column(Boolean, default=True)
    saturday = Column(Boolean, default=True)
    sunday = Column(Boolean, default=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Relaciones
    trips = relationship("Trip", back_populates="service")


class Trip(Base):
    __tablename__ = "trips"
    
    trip_id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id', ondelete='CASCADE'), index=True)
    service_id = Column(Integer, ForeignKey('calendar.service_id'), index=True)
    trip_headsign = Column(String(255))
    trip_short_name = Column(String(50))
    direction_id = Column(Integer, nullable=False)  # 0 o 1
    block_id = Column(Integer)
    shape_id = Column(Integer, ForeignKey('shapes.shape_id'))
    wheelchair_accessible = Column(Integer, default=0)
    bikes_allowed = Column(Integer, default=0)
    created_at = Column(Date, default=datetime.utcnow)
    
    # Relaciones
    route = relationship("Route", back_populates="trips")
    service = relationship("Calendar", back_populates="trips")
    stop_times = relationship("StopTime", back_populates="trip", cascade="all, delete-orphan")


class StopTime(Base):
    __tablename__ = "stop_times"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey('trips.trip_id', ondelete='CASCADE'), index=True)
    stop_id = Column(Integer, ForeignKey('stops.stop_id'), index=True)
    stop_sequence = Column(Integer, nullable=False)
    arrival_time = Column(Time, nullable=False)
    departure_time = Column(Time, nullable=False)
    stop_headsign = Column(String(255))
    pickup_type = Column(Integer, default=0)
    drop_off_type = Column(Integer, default=0)
    timepoint = Column(Integer, default=1)
    shape_dist_traveled = Column(DECIMAL(10, 3))
    
    # Relaciones
    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")


class RouteStop(Base):
    __tablename__ = "route_stops"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id', ondelete='CASCADE'), index=True)
    stop_id = Column(Integer, ForeignKey('stops.stop_id', ondelete='CASCADE'), index=True)
    direction_id = Column(Integer, nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    distance_from_start = Column(DECIMAL(10, 3))
    dwell_time = Column(Integer, default=0)
    is_timepoint = Column(Boolean, default=False)
    
    # Relaciones
    route = relationship("Route", back_populates="route_stops")


class Headway(Base):
    __tablename__ = "headways"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id', ondelete='CASCADE'), index=True)
    service_id = Column(Integer, ForeignKey('calendar.service_id'), index=True)
    direction_id = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    headway_minutes = Column(Integer, nullable=False)


class TravelTime(Base):
    __tablename__ = "travel_times"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id', ondelete='CASCADE'), index=True)
    direction_id = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    travel_time_minutes = Column(Integer, nullable=False)
    return_time_minutes = Column(Integer)


class Timetable(Base):
    __tablename__ = "timetables"
    
    timetable_id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey('routes.route_id'), index=True)
    service_id = Column(Integer, ForeignKey('calendar.service_id'), index=True)
    bus_id = Column(Integer, nullable=False)
    departure_a = Column(Time)
    arrival_b = Column(Time)
    departure_b = Column(Time)
    arrival_a = Column(Time)
    round_trip_minutes = Column(Integer)
    created_at = Column(Date, default=datetime.utcnow)