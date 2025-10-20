"""
API Endpoints para importación de CSV de paradas (stops)
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.csv_processor import CSVProcessor
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
    Formulario HTML para importar un archivo CSV de paradas
    """



    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Importar CSV de Paradas</title>
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
            input[type="file"] {
                width: 100%;
                padding: 15px;
                border: 2px dashed #ccc;
                border-radius: 8px;
                margin-bottom: 15px;
                background: #f9f9f9;
            }
            label {
                font-weight: 500;
                display: block;
                margin-bottom: 10px;
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
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 15px rgba(24,90,157,0.4);
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📍 Importar CSV de Paradas</h1>
            <form id="csvForm" enctype="multipart/form-data">
                <label for="file">Selecciona un archivo CSV:</label>
                <input type="file" id="file" name="file" accept=".csv" required>
                
                <div style="margin-bottom:10px;">
                    <label><input type="checkbox" name="replace_existing" checked> Reemplazar paradas existentes</label>
                </div>
                
                <button type="submit" class="btn">🚀 Importar CSV</button>
            </form>

            <div id="result" class="result"></div>
        </div>

        <script>
            document.getElementById("csvForm").addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const resultDiv = document.getElementById("result");
                resultDiv.style.display = "block";
                resultDiv.className = "result";
                resultDiv.innerHTML = "⏳ Procesando...";

                try {
                    const response = await fetch("/csv/import", {
                        method: "POST",
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        resultDiv.className = "result success";
                        resultDiv.innerHTML = `
                            ✅ <strong>Importación completada</strong><br>
                            Insertadas: ${data.stops_inserted}<br>
                            Actualizadas: ${data.stops_updated}<br>
                            Omitidas: ${data.stops_skipped}<br>
                            Total procesadas: ${data.total_processed}
                        `;
                    } else {
                        resultDiv.className = "result error";
                        resultDiv.innerHTML = "❌ Error: " + (data.error || "Error desconocido");
                    }
                } catch (err) {
                    resultDiv.className = "result error";
                    resultDiv.innerHTML = "❌ Error: " + err.message;
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
    Importa un archivo CSV de paradas (stops) a la base de datos.
    Si una parada ya existe, se actualiza.
    """
    try:
        csv_bytes = await file.read()
        csv_text = csv_bytes.decode("utf-8", errors="ignore")


        processor = CSVProcessor(db)
        result = processor.import_csv_to_stops(csv_text, replace_existing=replace_existing)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
