# app/api/routes_api.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
from typing import Optional

from app.database import get_db
from app.models.gtfs_models import Route, Shape # Importa los modelos
from app.services.kml_processor import KMLProcessor # Importa tu procesador KML

router = APIRouter(prefix="/routes", tags=["Routes Custom"])

async def process_and_save_kml(db: Session, kml_file: UploadFile, shape_id: str):
    """
    Procesa un archivo KML y guarda los puntos en la tabla shapes.
    Devuelve el número de puntos guardados o lanza una excepción.
    """
    if not kml_file or not shape_id:
        return 0

    try:
        # Lee el contenido del archivo KML
        kml_content = await kml_file.read()
        
        # Procesa el KML para obtener coordenadas
        processor = KMLProcessor()
        coordinates = processor.extract_coordinates_from_kml(kml_content)
        
        if not coordinates:
            raise ValueError(f"No se encontraron coordenadas válidas en el KML para shape_id '{shape_id}'.")

        # Inserta los puntos en la tabla shapes
        shape_points = []
        for i, (lon, lat) in enumerate(coordinates):
            shape_point = Shape(
                shape_id=shape_id,
                shape_pt_lat=lat,
                shape_pt_lon=lon,
                shape_pt_sequence=i + 1 # Secuencia empieza en 1
                # shape_dist_traveled se podría calcular si fuera necesario
            )
            shape_points.append(shape_point)
            
        # Añade todos los puntos en una transacción
        db.add_all(shape_points)
        # Nota: Hacemos commit en la función principal para asegurar atomicidad
        
        print(f"   -> Procesados {len(shape_points)} puntos para shape_id '{shape_id}'.")
        return len(shape_points)

    except Exception as e:
        # Relanza la excepción para que sea manejada por el endpoint principal
        print(f"Error procesando KML para shape_id '{shape_id}': {e}")
        raise ValueError(f"Error procesando KML para '{shape_id}': {e}") from e

@router.post("/create-with-kml")
async def create_route_with_kml(
    db: Session = Depends(get_db),
    route_data: str = Form(...), # Datos de la ruta como JSON string
    kml_file_0: Optional[UploadFile] = File(None),
    shape_id_0: Optional[str] = Form(None),
    kml_file_1: Optional[UploadFile] = File(None),
    shape_id_1: Optional[str] = Form(None)
):
    """
    Crea una nueva ruta en la tabla 'routes' y procesa hasta dos KML 
    para añadir sus trazados a la tabla 'shapes'.
    """
    print(f"Recibida solicitud para crear ruta con KML. Route data: {route_data}")
    
    # Validaciones básicas
    if not route_data:
        raise HTTPException(status_code=400, detail="Faltan los datos de la ruta (route_data).")
    if (kml_file_0 and not shape_id_0) or (not kml_file_0 and shape_id_0):
         raise HTTPException(status_code=400, detail="Debe proporcionar KML y Shape ID juntos para Sentido 1.")
    if (kml_file_1 and not shape_id_1) or (not kml_file_1 and shape_id_1):
         raise HTTPException(status_code=400, detail="Debe proporcionar KML y Shape ID juntos para Sentido 2.")
    if not kml_file_0 and not kml_file_1:
         raise HTTPException(status_code=400, detail="Debe proporcionar al menos un archivo KML.")
    if shape_id_0 and shape_id_1 and shape_id_0 == shape_id_1:
         raise HTTPException(status_code=400, detail="Los Shape ID para Sentido 1 y Sentido 2 deben ser diferentes.")

    try:
        # Parsea los datos de la ruta
        route_dict = json.loads(route_data)
        
        # Verifica campos requeridos para Route
        required_fields = ['route_id', 'route_short_name', 'agency_id']
        for field in required_fields:
            if field not in route_dict or not route_dict[field]:
                 raise HTTPException(status_code=400, detail=f"Falta el campo requerido '{field}' en route_data.")

        # Crea el objeto Route (sin añadirlo aún a la sesión)
        new_route = Route(**route_dict)
        
        shapes_added = []
        points_added_0 = 0
        points_added_1 = 0
        
        # Inicia transacción
        try:
            # Añade la ruta primero para verificar integridad (ej. route_id único)
            db.add(new_route)
            db.flush() # Fuerza la inserción o el error de integridad aquí
            print(f"  -> Ruta '{new_route.route_short_name}' (ID: {new_route.route_id}) pre-añadida.")

            # Procesa KML 0 si existe
            if kml_file_0 and shape_id_0:
                print(f"  -> Procesando KML para Sentido 0 (Shape ID: {shape_id_0})...")
                # Antes de procesar, verifica si el shape_id ya existe
                existing_shape = db.query(Shape).filter(Shape.shape_id == shape_id_0).first()
                if existing_shape:
                     raise ValueError(f"El Shape ID '{shape_id_0}' ya existe en la base de datos.")
                points_added_0 = await process_and_save_kml(db, kml_file_0, shape_id_0)
                if points_added_0 > 0:
                     shapes_added.append(shape_id_0)
            
            # Procesa KML 1 si existe
            if kml_file_1 and shape_id_1:
                print(f"  -> Procesando KML para Sentido 1 (Shape ID: {shape_id_1})...")
                 # Verifica si el shape_id ya existe
                existing_shape = db.query(Shape).filter(Shape.shape_id == shape_id_1).first()
                if existing_shape:
                     raise ValueError(f"El Shape ID '{shape_id_1}' ya existe en la base de datos.")
                points_added_1 = await process_and_save_kml(db, kml_file_1, shape_id_1)
                if points_added_1 > 0:
                     shapes_added.append(shape_id_1)

            # Si todo fue bien, confirma la transacción
            db.commit()
            db.refresh(new_route) # Carga datos completos de la ruta creada
            print(f"✅ Transacción completada. Ruta '{new_route.route_short_name}' creada. Shapes añadidos: {shapes_added}")
            
            return {
                "message": "Ruta y shapes creados exitosamente",
                "route_id": new_route.route_id,
                "route_short_name": new_route.route_short_name,
                "shapes_added": shapes_added,
                "points_added": points_added_0 + points_added_1
            }

        except IntegrityError as e:
            db.rollback()
            print(f"Error de Integridad: {e}")
            if "UNIQUE constraint failed: routes.route_id" in str(e):
                 raise HTTPException(status_code=400, detail=f"El ID de Ruta '{route_dict.get('route_id')}' ya existe.")
            elif "FOREIGN KEY constraint failed" in str(e):
                 raise HTTPException(status_code=400, detail=f"El Agency ID '{route_dict.get('agency_id')}' no existe.")
            else:
                 raise HTTPException(status_code=400, detail=f"Error de base de datos al crear la ruta: {e}")
        except ValueError as e: # Captura errores de process_and_save_kml o shape_id duplicado
             db.rollback()
             raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
             db.rollback() # Rollback general
             print(f"Error inesperado en transacción: {e}")
             traceback.print_exc()
             raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Formato inválido para route_data (debe ser JSON).")
    except Exception as e:
        print(f"Error general antes de la transacción: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")