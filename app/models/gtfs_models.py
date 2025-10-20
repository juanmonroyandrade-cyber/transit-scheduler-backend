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
    agency_url = Column(String(500))
    agency_timezone = Column(String(50))
    agency_phone = Column(String(50))

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
    start_date = Column(Date)
    end_date = Column(Date)

    trips = relationship("Trip", back_populates="calendar")


# -------------------------------
# FareAttribute
# -------------------------------
class FareAttribute(Base):
    __tablename__ = "fare_attributes"
    fare_id = Column(String(50), primary_key=True, index=True)
    price = Column(DECIMAL(10, 2))
    currency_type = Column(String(3))
    payment_method = Column(Integer)
    transfers = Column(Integer)

    fare_rules = relationship("FareRule", back_populates="fare_attribute")


# -------------------------------
# FareRule
# -------------------------------
class FareRule(Base):
    __tablename__ = "fare_rules"
    id = Column(Integer, primary_key=True, index=True)
    fare_id = Column(String(50), ForeignKey("fare_attributes.fare_id"))
    route_id = Column(String(50), ForeignKey("routes.route_id"))

    fare_attribute = relationship("FareAttribute", back_populates="fare_rules")
    route = relationship("Route", back_populates="fare_rules")


# -------------------------------
# FeedInfo
# -------------------------------
class FeedInfo(Base):
    __tablename__ = "feed_info"
    feed_publisher_name = Column(String(255), primary_key=True)
    feed_publisher_url = Column(String(500))
    feed_lang = Column(String(2))
    feed_start_date = Column(Date)
    feed_end_date = Column(Date)
    feed_version = Column(String(50))
    default_lang = Column(String(2))
    feed_contact_url = Column(String(500))


# -------------------------------
# Route
# -------------------------------
class Route(Base):
    __tablename__ = "routes"
    route_id = Column(String(50), primary_key=True, index=True)
    route_short_name = Column(String(50))
    route_long_name = Column(String(255))
    route_type = Column(Integer)
    route_color = Column(String(6))
    route_text_color = Column(String(6))
    agency_id = Column(Integer, ForeignKey("agencies.agency_id"))

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
    shape_pt_sequence = Column(Integer)
    shape_pt_lat = Column(DECIMAL(10, 8))
    shape_pt_lon = Column(DECIMAL(11, 8))
    shape_dist_traveled = Column(Float)


# -------------------------------
# Stop
# -------------------------------
class Stop(Base):
    __tablename__ = "stops"
    stop_id = Column(Integer, primary_key=True, index=True)
    stop_name = Column(String(255), nullable=False)
    stop_lat = Column(DECIMAL(10, 8), nullable=False)
    stop_lon = Column(DECIMAL(11, 8), nullable=False)
    wheelchair_boarding = Column(Integer)

    stop_times = relationship("StopTime", back_populates="stop")


# -------------------------------
# Trip
# -------------------------------
class Trip(Base):
    __tablename__ = "trips"
    trip_id = Column(String(50), primary_key=True, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"))
    service_id = Column(String(50), ForeignKey("calendar.service_id"))
    trip_headsign = Column(String(255))
    direction_id = Column(Integer)
    block_id = Column(String(50))
    shape_id = Column(String(50))
    wheelchair_accessible = Column(Integer)
    bikes_allowed = Column(Integer)

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
    arrival_time = Column(Time)
    departure_time = Column(Time)
    timepoint = Column(Integer)
    stop_sequence = Column(Integer)
    shape_dist_traveled = Column(Float)

    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")
