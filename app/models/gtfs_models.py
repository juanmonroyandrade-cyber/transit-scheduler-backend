# app/models/gtfs_models.py

from sqlalchemy import Column, Integer, String, Boolean, Date, Time, Float, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.database import Base

# -------------------------------
# Agency
# -------------------------------
class Agency(Base):
    __tablename__ = "agencies"
    agency_id = Column(Integer, primary_key=True, index=True)
    agency_name = Column(String(255), nullable=False)
    agency_url = Column(String(500), nullable=True)
    agency_timezone = Column(String(50), nullable=True)
    agency_phone = Column(String(50), nullable=True)

    routes = relationship("Route", back_populates="agency")

# -------------------------------
# Calendar
# -------------------------------
class Calendar(Base):
    __tablename__ = "calendar"
    service_id = Column(String(50), primary_key=True, index=True)
    monday = Column(Boolean, default=False)
    tuesday = Column(Boolean, default=False)
    wednesday = Column(Boolean, default=False)
    thursday = Column(Boolean, default=False)
    friday = Column(Boolean, default=False)
    saturday = Column(Boolean, default=False)
    sunday = Column(Boolean, default=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    trips = relationship("Trip", back_populates="calendar")
class CalendarDate(Base):
    __tablename__ = "calendar_dates"
    # Usar un 'id' autoincremental como PK es más fácil para editar
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_id = Column(String(50), ForeignKey("calendar.service_id"), index=True, nullable=False)
    date = Column(Date, nullable=False)
    # 1 = Servicio añadido, 2 = Servicio removido
    exception_type = Column(Integer, nullable=False, default=1)


# -------------------------------
# FeedInfo
# -------------------------------
class FeedInfo(Base):
    __tablename__ = "feed_info"
    # ✅ Se cambia la llave primaria a un id autoincremental para facilitar la edición
    feed_info_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feed_publisher_name = Column(String(255), nullable=False)
    feed_publisher_url = Column(String(500), nullable=True)
    feed_lang = Column(String(10), nullable=True)
    feed_start_date = Column(Date, nullable=True)
    feed_end_date = Column(Date, nullable=True)
    feed_version = Column(String(50), nullable=True)
    default_lang = Column(String(10), nullable=True)
    feed_contact_url = Column(String(500), nullable=True)
    # ✅ Se añade la columna que faltaba
    feed_contact_email = Column(String(255), nullable=True)

# (El resto de los modelos: FareAttribute, FareRule, Route, Shape, Stop, Trip, StopTime se mantienen igual)
# ...
# -------------------------------
# FareAttribute
# -------------------------------
class FareAttribute(Base):
    __tablename__ = "fare_attributes"
    fare_id = Column(String(50), primary_key=True, index=True)
    price = Column(DECIMAL(10, 2), nullable=True)
    currency_type = Column(String(3), nullable=True)
    payment_method = Column(Integer, nullable=True)
    transfers = Column(Integer, nullable=True)

    fare_rules = relationship("FareRule", back_populates="fare_attribute")


# -------------------------------
# FareRule
# -------------------------------
class FareRule(Base):
    __tablename__ = "fare_rules"
    id = Column(Integer, primary_key=True, index=True)
    fare_id = Column(String(50), ForeignKey("fare_attributes.fare_id"))
    route_id = Column(String(50), ForeignKey("routes.route_id"), nullable=True)

    fare_attribute = relationship("FareAttribute", back_populates="fare_rules")
    route = relationship("Route", back_populates="fare_rules")

# -------------------------------
# Route
# -------------------------------
class Route(Base):
    __tablename__ = "routes"
    route_id = Column(String(50), primary_key=True, index=True)
    route_short_name = Column(String(50), nullable=True)
    route_long_name = Column(String(255), nullable=True)
    route_type = Column(Integer, nullable=True)
    route_color = Column(String(6), nullable=True)
    route_text_color = Column(String(6), nullable=True)
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"), nullable=True)

    agency = relationship("Agency", back_populates="routes")
    trips = relationship("Trip", back_populates="route")
    fare_rules = relationship("FareRule", back_populates="route")


# -------------------------------
# Shape
# -------------------------------
class Shape(Base):
    __tablename__ = "shapes"
    id = Column(Integer, primary_key=True, index=True)
    shape_id = Column(String(50), index=True)
    shape_pt_sequence = Column(Integer, nullable=True)
    shape_pt_lat = Column(DECIMAL(10, 8), nullable=True)
    shape_pt_lon = Column(DECIMAL(11, 8), nullable=True)
    shape_dist_traveled = Column(Float, nullable=True)


# -------------------------------
# Stop
# -------------------------------
class Stop(Base):
    __tablename__ = "stops"
    stop_id = Column(Integer, primary_key=True, index=True)
    stop_name = Column(String(255), nullable=False)
    stop_lat = Column(DECIMAL(10, 8), nullable=False)
    stop_lon = Column(DECIMAL(11, 8), nullable=False)
    wheelchair_boarding = Column(Integer, nullable=True)

    stop_times = relationship("StopTime", back_populates="stop")


# -------------------------------
# Trip
# -------------------------------
class Trip(Base):
    __tablename__ = "trips"
    trip_id = Column(String(50), primary_key=True, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"))
    service_id = Column(String(50), ForeignKey("calendar.service_id"))
    trip_headsign = Column(String(255), nullable=True)
    direction_id = Column(Integer, nullable=True)
    block_id = Column(String(50), nullable=True)
    shape_id = Column(String(50), nullable=True)
    wheelchair_accessible = Column(Integer, nullable=True)
    bikes_allowed = Column(Integer, nullable=True)

    route = relationship("Route", back_populates="trips")
    calendar = relationship("Calendar", back_populates="trips")
    stop_times = relationship("StopTime", back_populates="trip")


# -------------------------------
# StopTime
# -------------------------------
class StopTime(Base):
    __tablename__ = "stop_times"
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String(50), ForeignKey("trips.trip_id"))
    stop_id = Column(Integer, ForeignKey("stops.stop_id"))
    arrival_time = Column(Time, nullable=True)
    departure_time = Column(Time, nullable=True)
    timepoint = Column(Integer, nullable=True)
    stop_sequence = Column(Integer, nullable=True)
    shape_dist_traveled = Column(Float, nullable=True)

    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")