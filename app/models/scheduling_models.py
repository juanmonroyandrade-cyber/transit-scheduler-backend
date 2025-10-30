# app/models/scheduling_models.py

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from datetime import datetime
from app.database import Base

class SchedulingParameters(Base):
    """
    Almacena los parámetros de programación completos
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
    #   "dwellCentro": 0,
    #   "dwellBarrio": 0,
    #   "distanciaCB": 15.5,
    #   "distanciaBC": 15.5
    # }
    
    # ===== TABLA 2: Flota Variable (JSON Array) =====
    tabla2 = Column(JSON, nullable=True)
    # Estructura: [{"desde": "05:00", "buses": 6}, ...]
    
    # ===== TABLA 3: Tiempos de Recorrido (JSON Array) =====
    tabla3 = Column(JSON, nullable=True)
    # Estructura: [{"desde": "00:00", "tiempoCB": "00:36", "tiempoBC": "00:36", "tiempoCiclo": "01:12"}, ...]
    
    # ===== METADATOS =====
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)