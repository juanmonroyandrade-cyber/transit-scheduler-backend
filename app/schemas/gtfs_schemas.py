from pydantic import BaseModel
from datetime import date, time
from typing import Optional, List

# Agency
class AgencyBase(BaseModel):
    agency_name: str
    agency_url: Optional[str]
    agency_timezone: Optional[str]
    agency_phone: Optional[str]

class AgencyCreate(AgencyBase):
    pass

class Agency(AgencyBase):
    agency_id: int

    class Config:
        orm_mode = True

# Route
class RouteBase(BaseModel):
    route_short_name: str
    route_long_name: Optional[str]
    route_desc: Optional[str]
    route_type: Optional[int] = 3

class RouteCreate(RouteBase):
    agency_id: int

class Route(RouteBase):
    route_id: int
    agency_id: int

    class Config:
        orm_mode = True

# Stop
class StopBase(BaseModel):
    stop_name: str
    stop_lat: float
    stop_lon: float

class StopCreate(StopBase):
    pass

class Stop(StopBase):
    stop_id: int

    class Config:
        orm_mode = True
