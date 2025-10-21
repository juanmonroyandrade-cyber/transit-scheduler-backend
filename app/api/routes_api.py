# app/api/routes_api.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
import json
from typing import Optional
import traceback
from datetime import date, time as dt_time

from app.database import get_db
from app.models.gtfs_models import Route, Shape
from app.services.kml_processor import KMLProcessor

router = APIRouter(prefix="/routes", tags=["Routes Custom"])

async def process_and_save_kml(db: Session, kml_file: UploadFile, shape_id: str, replace_existing: bool = True):
    """
    Procesa KML, calcula distancia, y guarda/reemplaza shapes.
    """
    if not kml_file or not shape_id:
        return 0, 0.0 # Puntos, distancia

    print(f"  -> [process_kml] Iniciando para shape_id '{shape_id}' (replace={replace_existing})...")
    coordinates = []
    try:
        kml_content_bytes = await kml_file.read()
        try: kml_content_str = kml_content_bytes.decode('utf-8')
        except UnicodeDecodeError: kml_content_str = kml_content_bytes.decode('latin-1', errors='ignore')
        print(f"     -> [process_kml] KML leído.")

        processor = KMLProcessor(db)
        print(f"     -> [process_kml] KMLProcessor instanciado.")

        # ✅ *** VERIFICA Y USA EL NOMBRE CORRECTO DEL MÉTODO ***
        if not hasattr(processor, 'parse_kml_content'):
             # Si este error persiste, el nombre del método en kml_processor.py ES OTRO
             raise AttributeError("Método 'parse_kml_content' NO existe en KMLProcessor.")

        # Llama al método correcto que SÍ existe en tu clase
        coordinates = processor.parse_kml_content(kml_content_str)
        print(f"     -> [process_kml] Coordenadas extraídas (vía parse_kml_content): {len(coordinates)}")

        if not coordinates: raise ValueError("No se encontraron coordenadas válidas en KML.")

        # --- Lógica de Reemplazo ---
        existing_shape_count = db.query(Shape).filter(Shape.shape_id == shape_id).count()
        if existing_shape_count > 0:
            if replace_existing:
                print(f"     -> [process_kml] Eliminando {existing_shape_count} puntos para shape '{shape_id}'...")
                stmt = delete(Shape).where(Shape.shape_id == shape_id)
                db.execute(stmt); db.flush()
                print(f"     -> [process_kml] Puntos anteriores eliminados.")
            else:
                raise ValueError(f"Shape ID '{shape_id}' ya existe y no se permite reemplazar.")
        # --- Fin Reemplazo ---

        shape_points_to_add = []; valid_points_count = 0; cumulative_distance_meters = 0.0; last_coord = None
        # Asegúrate que KMLProcessor tenga calculate_distance
        if not hasattr(processor, 'calculate_distance'):
             raise AttributeError("Método 'calculate_distance' NO existe en KMLProcessor.")

        # Asume que coordinates es [(lon, lat)] o [(lat, lon)], ajusta si es necesario
        # TU CÓDIGO de kml_processor devuelve (lat, lon)
        for i, (lat, lon) in enumerate(coordinates):
            try:
                lat_float = float(lat); lon_float = float(lon)
                if not (-90 <= lat_float <= 90 and -180 <= lon_float <= 180): raise ValueError("Coords fuera de rango")

                if i > 0 and last_coord:
                    # calculate_distance espera (lat1, lon1, lat2, lon2)
                    segment_distance = processor.calculate_distance(last_coord[1], last_coord[0], lat_float, lon_float)
                    cumulative_distance_meters += segment_distance

                shape_point = Shape(
                    shape_id=shape_id, shape_pt_lat=round(lat_float, 8), shape_pt_lon=round(lon_float, 8),
                    shape_pt_sequence=i + 1, shape_dist_traveled=round(cumulative_distance_meters, 3) )
                shape_points_to_add.append(shape_point)
                valid_points_count += 1
                # Guarda (lon, lat) para la siguiente iteración
                last_coord = (lon_float, lat_float)

            except (ValueError, TypeError) as coord_err:
                 print(f"     -> Warning: Coordenada inválida ({lat}, {lon}) ignorada. Error: {coord_err}")
                 continue

        if not shape_points_to_add: raise ValueError("No se pudieron extraer puntos válidos del KML.")

        db.add_all(shape_points_to_add)
        print(f"   -> [process_kml] {valid_points_count} puntos válidos preparados. Dist: {cumulative_distance_meters:.2f} m.")
        return valid_points_count, cumulative_distance_meters

    except (ValueError, AttributeError) as ve:
         print(f"Error procesando KML '{shape_id}': {ve}")
         raise ve # Relanza para 400
    except Exception as e:
        print(f"Error inesperado procesando KML '{shape_id}': {e}")
        traceback.print_exc()
        raise ValueError(f"Error inesperado procesando KML '{shape_id}': {e}") from e


# Endpoint renombrado a create_or_update para reflejar la lógica de upsert
@router.post("/create-with-kml", status_code=200) # Cambiado a 200 OK porque puede crear o actualizar
async def create_or_update_route_with_kml(
    db: Session = Depends(get_db),
    route_data: str = Form(...),
    kml_file_0: Optional[UploadFile] = File(None),
    shape_id_0: Optional[str] = Form(None),
    kml_file_1: Optional[UploadFile] = File(None),
    shape_id_1: Optional[str] = Form(None)
):
    print(f"[create-update-route] Recibida solicitud. Route data: {route_data}")
    # Validaciones KML/Shape ID
    if not route_data: raise HTTPException(status_code=400, detail="Faltan datos de ruta (route_data).")
    if (kml_file_0 and not shape_id_0) or (not kml_file_0 and shape_id_0): raise HTTPException(status_code=400, detail="Proporciona KML y Shape ID juntos para Sentido 1.")
    if (kml_file_1 and not shape_id_1) or (not kml_file_1 and shape_id_1): raise HTTPException(status_code=400, detail="Proporciona KML y Shape ID juntos para Sentido 2.")
    if not kml_file_0 and not kml_file_1: raise HTTPException(status_code=400, detail="Proporciona al menos un KML.")

    clean_shape_id_0 = shape_id_0.strip() if shape_id_0 else None
    clean_shape_id_1 = shape_id_1.strip() if shape_id_1 else None
    if clean_shape_id_0 and clean_shape_id_1 and clean_shape_id_0 == clean_shape_id_1: raise HTTPException(status_code=400, detail="Shape IDs deben ser diferentes.")

    # Parseo y Validación route_data
    try:
        route_dict = json.loads(route_data)
        required_fields = ['route_id', 'route_short_name', 'agency_id']
        for field in required_fields:
            if field not in route_dict or not route_dict[field]: raise HTTPException(status_code=400, detail=f"Falta '{field}' en route_data.")
        print(f"  -> Route data parseado: {route_dict}")
    except json.JSONDecodeError: raise HTTPException(status_code=400, detail="JSON inválido para route_data.")
    except Exception as parse_err: raise HTTPException(status_code=400, detail=f"Error en datos de ruta: {parse_err}")

    route_id = route_dict['route_id']
    shapes_processed_info = [] # Para la respuesta detallada
    total_points_added = 0
    action_performed = "creada"

    # --- Transacción ---
    try:
        # Upsert Route
        existing_route = db.query(Route).filter(Route.route_id == route_id).with_for_update().first() # Lock for update
        if existing_route:
            print(f"  -> Actualizando ruta ID '{route_id}'...")
            for key, value in route_dict.items():
                if hasattr(existing_route, key): setattr(existing_route, key, value)
            route_to_process = existing_route
            action_performed = "actualizada"
        else:
            print(f"  -> Creando ruta ID '{route_id}'...")
            route_to_process = Route(**route_dict)
            db.add(route_to_process)
            # Flush después de procesar KMLs para asegurar que todo esté en la sesión antes del commit

        # Procesa KMLs (con reemplazo=True)
        if kml_file_0 and clean_shape_id_0:
            print(f"  -> Procesando KML 0 ({clean_shape_id_0})...")
            # No es necesario verificar existencia aquí si replace=True
            points, dist = await process_and_save_kml(db, kml_file_0, clean_shape_id_0, replace_existing=True)
            if points > 0: shapes_processed_info.append({"shape_id": clean_shape_id_0, "points": points, "distance_m": round(dist, 2)})
            total_points_added += points

        if kml_file_1 and clean_shape_id_1:
            print(f"  -> Procesando KML 1 ({clean_shape_id_1})...")
            points, dist = await process_and_save_kml(db, kml_file_1, clean_shape_id_1, replace_existing=True)
            if points > 0: shapes_processed_info.append({"shape_id": clean_shape_id_1, "points": points, "distance_m": round(dist, 2)})
            total_points_added += points

        # Commit final
        db.commit()
        db.refresh(route_to_process) # Carga datos actualizados/creados
        print(f"✅ Transacción completa. Ruta '{route_to_process.route_short_name}' {action_performed}. Shapes procesados: {len(shapes_processed_info)}")
        
        # ✅ Asegura que la respuesta incluya 'shapes_added' o similar como espera el frontend
        #    Usaremos 'shapes_processed' que contiene más detalles.
        return {
            "message": f"Ruta {action_performed} y shapes procesados",
            "route_id": route_to_process.route_id,
            "route_short_name": route_to_process.route_short_name,
            "action": action_performed,
            "shapes_processed": shapes_processed_info, # Frontend usará esto
            "total_points_added": total_points_added,
             # Incluye 'shapes_added' como array de IDs para compatibilidad con el frontend actual
             "shapes_added": [s["shape_id"] for s in shapes_processed_info]
        }

    # Manejo de errores
    except IntegrityError as e:
        db.rollback(); print(f"Error Integridad: {e}")
        detail = f"Error DB: {e}"
        # Ya no debería fallar UNIQUE route_id por el upsert
        if "FOREIGN KEY constraint failed" in str(e) and ".agency_id" in str(e): detail = f"Agency ID '{route_dict.get('agency_id')}' no existe."
        # Podría fallar UNIQUE shape_id si se intenta añadir el mismo ID dos veces en la *misma* request
        # O si hay otro constraint
        raise HTTPException(status_code=400, detail=detail)
    except ValueError as e: # Captura errores de process_kml
         db.rollback(); print(f"Error Valor (KML/ShapeID): {e}")
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
         db.rollback(); print(f"Error Inesperado: {e}")
         traceback.print_exc()
         raise HTTPException(status_code=500, detail=f"Error interno: {e}")