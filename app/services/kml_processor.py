"""
KML Processor Service
Procesa archivos KML y los convierte en shapes GTFS
"""
import xml.etree.ElementTree as ET
import re
from typing import List, Tuple, Dict
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.orm import Session

from app.models.gtfs_models import Shape


class KMLProcessor:
    """Procesador de archivos KML para shapes de rutas"""
    
    NAMESPACES = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'gx': 'http://www.google.com/kml/ext/2.2'
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def parse_kml_content(self, kml_content: str) -> List[Tuple[float, float]]:
        """
        Extrae coordenadas de un archivo KML
        
        Args:
            kml_content: Contenido del archivo KML como string
            
        Returns:
            Lista de tuplas (lat, lon)
        """
        try:
            # Limpiar contenido
            kml_content = kml_content.strip()
            
            # Intentar parsear como XML
            root = ET.fromstring(kml_content)
            
            # Buscar LineString
            linestring = root.find('.//kml:LineString', self.NAMESPACES)
            if linestring is not None:
                coords_elem = linestring.find('kml:coordinates', self.NAMESPACES)
                if coords_elem is not None and coords_elem.text:
                    return self._parse_coordinates(coords_elem.text)
            
            # Si no se encontró con namespace, intentar sin él
            linestring = root.find('.//LineString')
            if linestring is not None:
                coords_elem = linestring.find('coordinates')
                if coords_elem is not None and coords_elem.text:
                    return self._parse_coordinates(coords_elem.text)
            
            # Buscar en Placemark
            for placemark in root.findall('.//Placemark'):
                linestring = placemark.find('.//LineString')
                if linestring is not None:
                    coords_elem = linestring.find('coordinates')
                    if coords_elem is not None and coords_elem.text:
                        return self._parse_coordinates(coords_elem.text)
            
            raise ValueError("No se encontró LineString en el KML")
            
        except ET.ParseError as e:
            # Si falla el parsing XML, intentar extraer coordenadas con regex
            return self._parse_coordinates_fallback(kml_content)
    
    def _parse_coordinates(self, coord_text: str) -> List[Tuple[float, float]]:
        """
        Parsea texto de coordenadas KML
        Formato: "lon,lat,elevation lon,lat,elevation ..."
        """
        coordinates = []
        
        # Limpiar texto
        coord_text = coord_text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
        coord_text = re.sub(r'\s+', ' ', coord_text).strip()
        
        # Dividir por espacios
        points = coord_text.split(' ')
        
        for point in points:
            point = point.strip()
            if not point:
                continue
            
            parts = point.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    
                    # Validar coordenadas razonables
                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                        coordinates.append((lat, lon))
                except (ValueError, IndexError):
                    continue
        
        return coordinates
    
    def _parse_coordinates_fallback(self, kml_content: str) -> List[Tuple[float, float]]:
        """
        Extrae coordenadas usando regex cuando falla el parsing XML
        """
        # Buscar bloque de coordenadas
        coord_match = re.search(r'<coordinates>(.*?)</coordinates>', kml_content, re.DOTALL | re.IGNORECASE)
        
        if coord_match:
            coord_text = coord_match.group(1)
            return self._parse_coordinates(coord_text)
        
        raise ValueError("No se pudieron extraer coordenadas del KML")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula distancia haversine entre dos puntos (en km)
        Equivalente a la función DistKM de VBA
        """
        # Radio de la Tierra en m
        R = 6371000.0
        
        # Convertir a radianes
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Diferencias
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Fórmula haversine
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def import_kml_to_shapes(
        self, 
        kml_content: str, 
        shape_id: str,
        replace_existing: bool = True
    ) -> Dict:
        """
        Importa un KML como shapes en la base de datos
        
        Args:
            kml_content: Contenido del archivo KML
            shape_id: ID del shape a crear/actualizar
            replace_existing: Si True, reemplaza shapes existentes con el mismo ID
            
        Returns:
            Dict con estadísticas de importación
        """
        try:
            # Parsear coordenadas
            print(f"📥 Parseando KML para shape_id: {shape_id}")
            coordinates = self.parse_kml_content(kml_content)
            
            if not coordinates:
                return {
                    'success': False,
                    'error': 'No se encontraron coordenadas válidas en el KML'
                }
            
            print(f"✅ Encontradas {len(coordinates)} coordenadas")
            
            # Verificar si el shape_id ya existe
            existing_shapes = self.db.query(Shape).filter(
                Shape.shape_id == shape_id
            ).all()
            
            if existing_shapes:
                if replace_existing:
                    print(f"🔄 Reemplazando {len(existing_shapes)} puntos existentes del shape {shape_id}")
                    # Eliminar shapes existentes
                    for shape in existing_shapes:
                        self.db.delete(shape)
                    self.db.commit()
                else:
                    return {
                        'success': False,
                        'error': f'El shape_id {shape_id} ya existe. Use replace_existing=True para reemplazar.'
                    }
            
            # Crear nuevos shapes con distancias calculadas
            cumulative_distance = 0.0
            shapes_created = []
            
            for idx, (lat, lon) in enumerate(coordinates):
                # Calcular distancia desde el punto anterior
                if idx > 0:
                    prev_lat, prev_lon = coordinates[idx - 1]
                    segment_distance = self.calculate_distance(prev_lat, prev_lon, lat, lon)
                    cumulative_distance += segment_distance
                
                # Crear shape point
                shape = Shape(
                    shape_id=shape_id,
                    shape_pt_lat=round(lat, 6),
                    shape_pt_lon=round(lon, 6),
                    shape_pt_sequence=idx + 1,
                    shape_dist_traveled=round(cumulative_distance, 3)
                )
                
                self.db.add(shape)
                shapes_created.append(shape)
            
            # Commit
            self.db.commit()
            
            print(f"✅ Importados {len(shapes_created)} puntos del shape")
            print(f"📏 Distancia total: {cumulative_distance:.3f} km")
            
            return {
                'success': True,
                'shape_id': shape_id,
                'points_imported': len(shapes_created),
                'total_distance_km': round(cumulative_distance, 3),
                'replaced': len(existing_shapes) > 0
            }
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error importando KML: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_shape_info(self, shape_id: str) -> Dict:
        """
        Obtiene información de un shape existente
        """
        shapes = self.db.query(Shape).filter(
            Shape.shape_id == shape_id
        ).order_by(Shape.shape_pt_sequence).all()
        
        if not shapes:
            return None
        
        return {
            'shape_id': shape_id,
            'total_points': len(shapes),
            'total_distance_km': float(shapes[-1].shape_dist_traveled) if shapes[-1].shape_dist_traveled else 0,
            'start_point': {
                'lat': float(shapes[0].shape_pt_lat),
                'lon': float(shapes[0].shape_pt_lon)
            },
            'end_point': {
                'lat': float(shapes[-1].shape_pt_lat),
                'lon': float(shapes[-1].shape_pt_lon)
            }
        }


def validate_kml_content(kml_content: str) -> Dict:
    """
    Valida contenido KML sin importarlo
    """
    try:
        processor = KMLProcessor(None)  # No necesita DB para validar
        coordinates = processor.parse_kml_content(kml_content)
        
        if not coordinates:
            return {
                'valid': False,
                'error': 'No se encontraron coordenadas en el KML'
            }
        
        # Calcular distancia total estimada
        total_distance = 0.0
        for i in range(1, len(coordinates)):
            lat1, lon1 = coordinates[i-1]
            lat2, lon2 = coordinates[i]
            total_distance += processor.calculate_distance(lat1, lon1, lat2, lon2)
        
        return {
            'valid': True,
            'points_found': len(coordinates),
            'estimated_distance_km': round(total_distance, 3),
            'start_point': {'lat': coordinates[0][0], 'lon': coordinates[0][1]},
            'end_point': {'lat': coordinates[-1][0], 'lon': coordinates[-1][1]}
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }