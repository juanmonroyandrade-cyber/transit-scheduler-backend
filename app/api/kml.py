"""
API Endpoints para importación de KML y gestión de shapes
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.kml_processor import KMLProcessor, validate_kml_content
from app.models.gtfs_models import Route, Shape

router = APIRouter(prefix="/kml", tags=["KML & Shapes"])


@router.get("/form", response_class=HTMLResponse)
async def kml_import_form():
    """
    Formulario HTML para importar KML y crear/editar rutas
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Importar KML - Transit Scheduler</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 28px;
                margin-bottom: 10px;
            }
            .header p {
                opacity: 0.9;
                font-size: 14px;
            }
            .content {
                padding: 40px;
            }
            .section {
                margin-bottom: 30px;
            }
            .section-title {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                font-weight: 500;
                color: #555;
                margin-bottom: 8px;
                font-size: 14px;
            }
            input[type="text"], textarea, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus, textarea:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            input[type="file"] {
                width: 100%;
                padding: 10px;
                border: 2px dashed #e0e0e0;
                border-radius: 8px;
                background: #f9f9f9;
                cursor: pointer;
            }
            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            input[type="checkbox"] {
                width: 20px;
                height: 20px;
                cursor: pointer;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 14px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .btn:active {
                transform: translateY(0);
            }
            .result {
                margin-top: 20px;
                padding: 20px;
                border-radius: 8px;
                display: none;
            }
            .result.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .result.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .help-text {
                font-size: 12px;
                color: #888;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🗺️ Importar KML</h1>
                <p>Convierte archivos KML en shapes GTFS</p>
            </div>
            
            <div class="content">
                <form id="kmlForm" enctype="multipart/form-data">
                    
                    <!-- Sección 1: Información de la Ruta -->
                    <div class="section">
                        <div class="section-title">📋 Información de la Ruta</div>
                        
                        <div class="form-group">
                            <label for="route_id">Route ID*</label>
                            <input type="text" id="route_id" name="route_id" required 
                                   placeholder="ej: R001">
                            <div class="help-text">ID único de la ruta</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="route_short_name">Nombre Corto*</label>
                            <input type="text" id="route_short_name" name="route_short_name" required 
                                   placeholder="ej: 1, 79A, Express">
                            <div class="help-text">Nombre que verán los usuarios</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="route_long_name">Nombre Largo</label>
                            <input type="text" id="route_long_name" name="route_long_name" 
                                   placeholder="ej: Centro - Barrio Norte">
                        </div>
                        
                        <div class="form-group">
                            <label for="route_type">Tipo de Ruta*</label>
                            <select id="route_type" name="route_type" required>
                                <option value="3">Bus (3)</option>
                                <option value="0">Tren ligero (0)</option>
                                <option value="1">Metro (1)</option>
                                <option value="2">Tren (2)</option>
                                <option value="4">Ferry (4)</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="route_color">Color de la Ruta</label>
                            <input type="text" id="route_color" name="route_color" 
                                   placeholder="FFFFFF" maxlength="6">
                            <div class="help-text">Código hexadecimal sin #</div>
                        </div>
                    </div>
                    
                    <!-- Sección 2: Shape (KML) -->
                    <div class="section">
                        <div class="section-title">🗺️ Shape (Trazado de la Ruta)</div>
                        
                        <div class="form-group">
                            <label for="shape_id">Shape ID*</label>
                            <input type="text" id="shape_id" name="shape_id" required 
                                   placeholder="ej: shape_R001">
                            <div class="help-text">ID único del trazado geográfico</div>
                        </div>
                        
                        <div class="form-group">
                            <label for="kml_file">Archivo KML*</label>
                            <input type="file" id="kml_file" name="kml_file" accept=".kml" required>
                            <div class="help-text">Archivo KML con el LineString de la ruta</div>
                        </div>
                        
                        <div class="form-group checkbox-group">
                            <input type="checkbox" id="replace_existing" name="replace_existing" checked>
                            <label for="replace_existing" style="margin: 0;">
                                Reemplazar shape si ya existe
                            </label>
                        </div>
                    </div>
                    
                    <!-- Botón Submit -->
                    <button type="submit" class="btn">
                        🚀 Importar Ruta y KML
                    </button>
                    
                    <!-- Resultado -->
                    <div id="result" class="result"></div>
                </form>
            </div>
        </div>
        
        <script>
            document.getElementById('kmlForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const resultDiv = document.getElementById('result');
                
                // Mostrar loading
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = '⏳ Procesando...';
                
                try {
                    const response = await fetch('/kml/import', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.success) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            <strong>✅ Éxito!</strong><br>
                            Ruta creada: ${data.route.route_short_name}<br>
                            Shape importado: ${data.shape.shape_id}<br>
                            Puntos: ${data.shape.points_imported}<br>
                            Distancia total: ${data.shape.total_distance_km} km
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `
                            <strong>❌ Error</strong><br>
                            ${data.error || 'Error desconocido'}
                        `;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `
                        <strong>❌ Error</strong><br>
                        ${error.message}
                    `;
                }
            });
            
            // Auto-generar shape_id desde route_id
            document.getElementById('route_id').addEventListener('input', (e) => {
                const routeId = e.target.value;
                const shapeIdField = document.getElementById('shape_id');
                if (routeId && !shapeIdField.value) {
                    shapeIdField.value = `shape_${routeId}`;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/import")
async def import_kml_and_route(
    route_id: str = Form(...),
    route_short_name: str = Form(...),
    route_long_name: str = Form(""),
    route_type: int = Form(3),
    route_color: str = Form("FFFFFF"),
    shape_id: str = Form(...),
    kml_file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Importa un archivo KML y crea/actualiza una ruta
    
    **Proceso:**
    1. Valida el archivo KML
    2. Crea o actualiza la ruta en routes.txt
    3. Importa el shape desde el KML
    4. Calcula distancias entre puntos
    5. Actualiza la ruta con el shape_id
    """
    try:
        # Leer contenido del KML
        kml_content = await kml_file.read()
        kml_text = kml_content.decode('utf-8')
        
        # Validar KML
        print("📥 Validando KML...")
        validation = validate_kml_content(kml_text)
        
        if not validation['valid']:
            raise HTTPException(status_code=400, detail=validation['error'])
        
        print(f"✅ KML válido: {validation['points_found']} puntos, ~{validation['estimated_distance_km']} km")
        
        # Verificar si la ruta ya existe
        existing_route = db.query(Route).filter(Route.route_id == route_id).first()
        
        if existing_route:
            # Actualizar ruta existente
            print(f"🔄 Actualizando ruta existente: {route_id}")
            existing_route.route_short_name = route_short_name
            existing_route.route_long_name = route_long_name
            existing_route.route_type = route_type
            existing_route.route_color = route_color
            route = existing_route
        else:
            # Crear nueva ruta
            print(f"➕ Creando nueva ruta: {route_id}")
            route = Route(
                route_id=route_id,
                route_short_name=route_short_name,
                route_long_name=route_long_name,
                route_type=route_type,
                route_color=route_color,
                route_text_color="000000",
                agency_id=1  # Asume primera agencia
            )
            db.add(route)
        
        db.commit()
        
        # Importar KML como shapes
        print(f"📍 Importando shapes desde KML...")
        processor = KMLProcessor(db)
        shape_result = processor.import_kml_to_shapes(
            kml_text,
            shape_id,
            replace_existing=replace_existing
        )
        
        if not shape_result['success']:
            raise HTTPException(status_code=500, detail=shape_result['error'])
        
        return {
            'success': True,
            'route': {
                'route_id': route.route_id,
                'route_short_name': route.route_short_name,
                'route_long_name': route.route_long_name,
                'route_type': route.route_type
            },
            'shape': shape_result,
            'validation': validation
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-shape-only")
async def import_kml_shape_only(
    shape_id: str = Form(...),
    kml_file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Importa solo el shape desde un KML (sin crear ruta)
    """
    try:
        kml_content = await kml_file.read()
        kml_text = kml_content.decode('utf-8')
        
        processor = KMLProcessor(db)
        result = processor.import_kml_to_shapes(
            kml_text,
            shape_id,
            replace_existing=replace_existing
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return result
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shapes/{shape_id}")
async def get_shape_info(
    shape_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene información de un shape existente
    """
    processor = KMLProcessor(db)
    info = processor.get_shape_info(shape_id)
    
    if not info:
        raise HTTPException(status_code=404, detail="Shape no encontrado")
    
    return info


@router.get("/shapes")
async def list_shapes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todos los shapes únicos
    """
    from sqlalchemy import distinct, func
    
    # Obtener shape_ids únicos
    shapes = db.query(
        Shape.shape_id,
        func.count(Shape.id).label('point_count'),
        func.max(Shape.shape_dist_traveled).label('total_distance')
    ).group_by(Shape.shape_id).offset(skip).limit(limit).all()
    
    return {
        'shapes': [
            {
                'shape_id': s.shape_id,
                'point_count': s.point_count,
                'total_distance_km': float(s.total_distance) if s.total_distance else 0
            }
            for s in shapes
        ]
    }