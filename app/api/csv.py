"""
API Endpoints para importación de CSV/XLSX de paradas (stops)
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.csv_processor import FileProcessor
from fastapi.responses import StreamingResponse
import io
import csv

router = APIRouter(prefix="/csv", tags=["CSV & Stops"])


@router.get("/template")
async def download_csv_template():
    """
    Devuelve una plantilla CSV vacía con los encabezados correctos
    """
    headers = ["stop_id", "stop_name", "stop_lat", "stop_lon", "wheelchair_boarding"]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stops_template.csv"}
    )


@router.get("/form", response_class=HTMLResponse)
async def csv_import_form():
    """
    Formulario HTML para importar un archivo CSV o XLSX de paradas
    """
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Importar Paradas</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: #fff;
                padding: 40px;
                border-radius: 16px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                text-align: center;
                margin-bottom: 20px;
                color: #185a9d;
            }
            .file-input-wrapper {
                position: relative;
                width: 100%;
                margin-bottom: 15px;
            }
            input[type="file"] {
                width: 100%;
                padding: 15px;
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: #f9f9f9;
                cursor: pointer;
            }
            input[type="file"]:hover {
                border-color: #43cea2;
                background: #f0f9f5;
            }
            label {
                font-weight: 500;
                display: block;
                margin-bottom: 10px;
            }
            .file-types {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .btn {
                background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);
                color: white;
                padding: 14px;
                width: 100%;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.2s;
            }
            .btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 8px 15px rgba(24,90,157,0.4);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 8px;
                display: none;
            }
            .success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .info {
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 15px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📍 Importar Paradas</h1>
            
            <div class="info">
                ℹ️ Soporta archivos CSV (UTF-8) y Excel (XLSX)
            </div>
            
            <form id="csvForm" enctype="multipart/form-data">
                <label for="file">Selecciona un archivo:</label>
                <div class="file-input-wrapper">
                    <input type="file" id="file" name="file" accept=".csv,.xlsx" required>
                    <div class="file-types">Formatos soportados: .csv, .xlsx</div>
                </div>
                
                <div style="margin-bottom:10px;">
                    <label>
                        <input type="checkbox" name="replace_existing" id="replaceCheck" checked> 
                        Reemplazar paradas existentes
                    </label>
                </div>
                
                <button type="submit" class="btn" id="submitBtn">🚀 Importar Archivo</button>
            </form>

            <div id="result" class="result"></div>
        </div>

        <script>
            document.getElementById("csvForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                
                const fileInput = document.getElementById("file");
                const resultDiv = document.getElementById("result");
                const submitBtn = document.getElementById("submitBtn");
                const replaceCheck = document.getElementById("replaceCheck");
                
                // Validar que se haya seleccionado un archivo
                if (!fileInput.files || fileInput.files.length === 0) {
                    resultDiv.style.display = "block";
                    resultDiv.className = "result error";
                    resultDiv.innerHTML = "❌ Por favor selecciona un archivo";
                    return;
                }
                
                const file = fileInput.files[0];
                const fileName = file.name;
                
                console.log("Procesando archivo:", fileName, "Tamaño:", file.size, "bytes");
                
                // Crear FormData manualmente para tener control total
                const formData = new FormData();
                formData.append("file", file, fileName);
                formData.append("replace_existing", replaceCheck.checked ? "true" : "false");
                
                // Deshabilitar botón durante la carga
                submitBtn.disabled = true;
                submitBtn.textContent = "⏳ Procesando...";
                
                resultDiv.style.display = "block";
                resultDiv.className = "result";
                resultDiv.innerHTML = "⏳ Cargando archivo al servidor...";

                try {
                    console.log("Enviando petición a /csv/import");
                    
                    const response = await fetch("/csv/import", {
                        method: "POST",
                        body: formData
                    });
                    
                    console.log("Respuesta recibida, status:", response.status);
                    
                    const data = await response.json();
                    console.log("Datos recibidos:", data);
                    
                    if (response.ok && data.success) {
                        resultDiv.className = "result success";
                        const fileType = data.file_type ? data.file_type.toUpperCase() : 'ARCHIVO';
                        resultDiv.innerHTML = `
                            ✅ <strong>Importación completada (${fileType})</strong><br>
                            📥 Insertadas: <strong>${data.stops_inserted}</strong><br>
                            🔄 Actualizadas: <strong>${data.stops_updated}</strong><br>
                            ⏭️ Omitidas: <strong>${data.stops_skipped}</strong><br>
                            📊 Total procesadas: <strong>${data.total_processed}</strong>
                        `;
                        // Limpiar el formulario después de éxito
                        fileInput.value = "";
                        replaceCheck.checked = true;
                    } else {
                        resultDiv.className = "result error";
                        const errorMsg = data.error || data.detail || "Error desconocido";
                        resultDiv.innerHTML = "❌ <strong>Error:</strong> " + errorMsg;
                    }
                } catch (err) {
                    console.error("Error en la petición:", err);
                    resultDiv.className = "result error";
                    resultDiv.innerHTML = "❌ <strong>Error de conexión:</strong> " + err.message;
                } finally {
                    // Rehabilitar botón
                    submitBtn.disabled = false;
                    submitBtn.textContent = "🚀 Importar Archivo";
                }
            });
            
            // Mostrar información del archivo seleccionado
            document.getElementById("file").addEventListener("change", (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    const file = e.target.files[0];
                    console.log("Archivo seleccionado:", file.name, "Tipo:", file.type, "Tamaño:", file.size, "bytes");
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    replace_existing: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Importa un archivo CSV o XLSX de paradas (stops) a la base de datos.
    Soporta:
    - Archivos CSV con codificación UTF-8 (con o sin BOM)
    - Archivos Excel (.xlsx)
    
    Si una parada ya existe, se actualiza según el parámetro replace_existing.
    """
    try:
        print(f"\n{'='*60}")
        print(f"INICIO DE IMPORTACIÓN")
        print(f"{'='*60}")
        
        # Validar que hay un archivo
        if not file or not file.filename:
            print("ERROR: No se proporcionó archivo")
            raise HTTPException(
                status_code=400,
                detail="No se proporcionó ningún archivo"
            )
        
        print(f"Archivo recibido: {file.filename}")
        print(f"Content-Type: {file.content_type}")
        
        # Validar extensión del archivo
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith('.csv') or filename_lower.endswith('.xlsx')):
            print(f"ERROR: Extensión no válida: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Solo se permiten archivos .csv o .xlsx. Archivo recibido: {file.filename}"
            )
        
        # Leer el contenido del archivo como bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            print("ERROR: Archivo vacío")
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío"
            )
        
        print(f"Tamaño del archivo: {len(file_bytes)} bytes")
        print(f"Replace existing: {replace_existing}")
        
        # Procesar el archivo
        processor = FileProcessor(db)
        result = processor.import_file_to_stops(
            file_content=file_bytes,
            filename=file.filename,
            replace_existing=replace_existing
        )

        print(f"\nResultado del procesamiento:")
        print(f"  - Success: {result.get('success')}")
        print(f"  - File type: {result.get('file_type')}")
        print(f"  - Insertadas: {result.get('stops_inserted', 0)}")
        print(f"  - Actualizadas: {result.get('stops_updated', 0)}")
        print(f"  - Omitidas: {result.get('stops_skipped', 0)}")
        print(f"{'='*60}\n")

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"ERROR COMPLETO EN ENDPOINT:")
        print(error_detail)
        print(f"{'='*60}\n")
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")