# app/models/scheduling_models.py

from sqlalchemy import Column, Integer, String, Float, Time, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SchedulingParameters(Base):
    """
    Almacena los parámetros de programación completos (7 tablas)
    """
    __tablename__ = "scheduling_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), index=True, nullable=True)
    name = Column(String(255), nullable=False, default="Configuración Principal")
    
    # ===== TABLA 1: Parámetros Generales (JSON) =====
    tabla1 = Column(JSON, nullable=False)
    # Estructura esperada:
    # {
    #   "numeroRuta": "1",
    #   "nombreRuta": "Ruta Centro-Barrio",
    #   "periodicidad": "Diario",
    #   "horaInicioCentro": "03:54",
    #   "horaInicioBarrio": "04:30",
    #   "horaFinCentro": "22:58",
    #   "horaFinBarrio": "22:46",
    #   "tiempoRecorridoCB": "00:36",
    #   "tiempoRecorridoBC": "00:36",
    #   "dwellCentro": 0,
    #   "dwellBarrio": 0,
    #   "distanciaCB": 15.5,
    #   "distanciaBC": 15.5
    # }
    
    # ===== TABLA 2: Buses Variables por Hora (JSON Array) =====
    tabla2 = Column(JSON, nullable=True)
    # Estructura: [{"hora": 4, "buses":