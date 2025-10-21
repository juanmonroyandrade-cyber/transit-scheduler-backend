# app/api/routes_api.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
from typing import Optional
import traceback
from datetime import date, time as dt_time

from app.database import get_db
from app.models.gtfs_models import Route, Shape
from app.services.kml_processor import KMLProcessor

router = APIRouter(prefix="/routes", tags=["Routes Custom"])

async def process_and_save_kml(db: Session, kml_file: UploadFile, shape_id: str):
    """
    Procesa un archivo KML y guarda los puntos en la tabla shapes.
    Devuelve el número de puntos guardados o lanza una excepción.
    """
    if not kml_file or not shape_id:
        return 0

    print(f"  -> [process_kml] Iniciando para shape_id '{shape_id}'...")
    try:
        # KML content might be bytes, decode it if KMLProcessor expects string
        kml_content_bytes = await kml_file.read()
        try:
            # Try decoding with UTF-8 first, fallback to latin-1 if needed
            kml_content_str = kml_content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            print("     -> [process_kml] Warning: KML no es UTF-8, intentando latin-1.")
            kml_content_str = kml_content_bytes.decode('latin-1', errors='ignore')

        print(f"     -> [process_kml] KML leído y decodificado ({len(kml_content_str)} chars).")

        processor = KMLProcessor(db)
        print(f"     -> [process_kml] KMLProcessor instanciado.")

        # ✅ *** CORRECCIÓN AQUÍ: Usa el nombre correcto del método ***
        coordinates = processor.parse_kml_content(kml_content_str) # Cambiado de extract_coordinates_from_kml
        print(f"     -> [process_kml] Coordenadas extraídas (método parse_kml_content): {len(coordinates) if coordinates else 'Ninguna'}")

        if not coordinates:
            raise ValueError(f"No se encontraron coordenadas válidas en KML para shape_id '{shape_id}'.")

        shape_points = []
        valid_points_count = 0
        # KMLProcessor devuelve (lat, lon) según tu código anterior
        for i, (lat, lon) in enumerate(coordinates):
            try:
                lat_float = float(lat)
                lon_float = float(lon)
                if not (-90 <= lat_float <= 90 and -180 <= lon_float <= 180): raise ValueError(f"Coords fuera de rango ({lat_float}, {lon_float})")
                shape_point = Shape( shape_id=shape_id, shape_pt_lat=lat_float, shape_pt_lon=lon_float, shape_pt_sequence=i + 1 )
                shape_points.append(shape_point)
                valid_points_count += 1
            except (ValueError, TypeError) as coord_err:
                 print(f"     -> Warning: Coordenada inválida ({lat}, {lon}) ignorada para shape '{shape_id}' seq {i+1}. Error: {coord_err}")
                 continue

        if not shape_points: raise ValueError(f"No se pudieron extraer puntos válidos del KML para shape '{shape_id}'.")

        db.add_all(shape_points)
        print(f"   -> [process_kml] {valid_points_count} puntos válidos preparados para shape '{shape_id}'.")
        return valid_points_count

    # Errores específicos primero
    except ValueError as ve:
         print(f"Error (ValueError) procesando KML para '{shape_id}': {ve}")
         raise ve # Relanza para que create_route_with_kml lo maneje como 400
    except AttributeError as ae: # Por si acaso hay otro error de atributo
        print(f"Error (AttributeError) procesando KML para '{shape_id}': {ae}")
        traceback.print_exc()
        raise ValueError(f"Error interno del procesador KML: {ae}") from ae
    # Error genérico al final
    except Exception as e:
        print(f"Error (Exception) inesperado procesando KML para '{shape_id}': {e}")
        traceback.print_exc()
        raise ValueError(f"Error inesperado procesando KML para '{shape_id}': {e}") from e

@router.post("/create-with-kml")
async def create_route_with_kml(
    db: Session = Depends(get_db),
    route_data: str = Form(...),
    kml_file_0: Optional[UploadFile] = File(None),
    shape_id_0: Optional[str] = Form(None),
    kml_file_1: Optional[UploadFile] = File(None),
    shape_id_1: Optional[str] = Form(None)
):
    # ... (El resto de esta función se mantiene igual que la versión anterior) ...
    print(f"[create-route] Recibida solicitud. Route data: {route_data}")
    if not route_data: raise HTTPException(status_code=400, detail="Faltan datos de ruta (route_data).")
    if (kml_file_0 and not shape_id_0) or (not kml_file_0 and shape_id_0): raise HTTPException(status_code=400, detail="Proporciona KML y Shape ID juntos para Sentido 1.")
    if (kml_file_1 and not shape_id_1) or (not kml_file_1 and shape_id_1): raise HTTPException(status_code=400, detail="Proporciona KML y Shape ID juntos para Sentido 2.")
    if not kml_file_0 and not kml_file_1: raise HTTPException(status_code=400, detail="Proporciona al menos un archivo KML.")

    clean_shape_id_0 = shape_id_0.strip() if shape_id_0 else None
    clean_shape_id_1 = shape_id_1.strip() if shape_id_1 else None
    if clean_shape_id_0 and clean_shape_id_1 and clean_shape_id_0 == clean_shape_id_1: raise HTTPException(status_code=400, detail="Los Shape IDs deben ser diferentes.")

    try:
        route_dict = json.loads(route_data)
        required_fields = ['route_id', 'route_short_name', 'agency_id']
        for field in required_fields:
            if field not in route_dict or not route_dict[field]: raise HTTPException(status_code=400, detail=f"Falta '{field}' en route_data.")
        print(f"  -> [create-route] Route data parseado: {route_dict}")
        new_route = Route(**route_dict)
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="Formato JSON inválido para route_data.")
    except Exception as parse_err: raise HTTPException(status_code=400, detail=f"Error en datos de ruta: {parse_err}")

    shapes_added = []; points_added_0 = 0; points_added_1 = 0
    try:
        db.add(new_route); db.flush()
        print(f"  -> [create-route] Ruta '{new_route.route_short_name}' pre-añadida.")

        if kml_file_0 and clean_shape_id_0:
            print(f"  -> [create-route] Procesando KML 0 ({clean_shape_id_0})...")
            existing_shape = db.query(Shape.shape_id).filter(Shape.shape_id == clean_shape_id_0).first()
            if existing_shape: raise ValueError(f"Shape ID '{clean_shape_id_0}' ya existe.")
            points_added_0 = await process_and_save_kml(db, kml_file_0, clean_shape_id_0)
            if points_added_0 > 0: shapes_added.append(clean_shape_id_0)

        if kml_file_1 and clean_shape_id_1:
            print(f"  -> [create-route] Procesando KML 1 ({clean_shape_id_1})...")
            existing_shape = db.query(Shape.shape_id).filter(Shape.shape_id == clean_shape_id_1).first()
            if existing_shape: raise ValueError(f"Shape ID '{clean_shape_id_1}' ya existe.")
            points_added_1 = await process_and_save_kml(db, kml_file_1, clean_shape_id_1)
            if points_added_1 > 0: shapes_added.append(clean_shape_id_1)

        db.commit(); db.refresh(new_route)
        print(f"✅ [create-route] Transacción completa. Ruta '{new_route.route_short_name}' creada. Shapes: {shapes_added}")
        return { "message": "Ruta y shapes creados", "route_id": new_route.route_id, "route_short_name": new_route.route_short_name, "shapes_added": shapes_added, "points_added": points_added_0 + points_added_1 }

    except IntegrityError as e:
        db.rollback(); print(f"Error Integridad: {e}")
        detail = f"Error DB: {e}"
        if "UNIQUE constraint failed: routes.route_id" in str(e): detail = f"ID Ruta '{route_dict.get('route_id')}' ya existe."
        elif "FOREIGN KEY constraint failed" in str(e) and ".agency_id" in str(e): detail = f"Agency ID '{route_dict.get('agency_id')}' no existe."
        elif "UNIQUE constraint failed: shapes.shape_id" in str(e): detail = "Uno de los Shape IDs ya existe."
        raise HTTPException(status_code=400, detail=detail)
    except ValueError as e:
         db.rollback(); print(f"Error Valor (KML/ShapeID): {e}")
         # Devuelve 400 Bad Request con el mensaje del ValueError
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
         db.rollback(); print(f"Error Inesperado: {e}")
         traceback.print_exc()
         raise HTTPException(status_code=500, detail=f"Error interno: {e}")