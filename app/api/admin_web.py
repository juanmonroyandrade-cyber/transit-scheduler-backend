from fastapi import APIRouter, Request, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.gtfs_models import Agency, Calendar, FareAttribute, FareRule, FeedInfo, Route, Shape, StopTime, Stop, Trip
from app.services.gtfs_importer import GTFSImporter  # ruta corregida

router = APIRouter(prefix="/admin-web", tags=["Admin Web"])

TABLES = {
    "agency": Agency,
    "calendar": Calendar,
    "fare_attributes": FareAttribute,
    "fare_rules": FareRule,
    "feed_info": FeedInfo,
    "routes": Route,
    "shapes": Shape,
    "stop_times": StopTime,
    "stops": Stop,
    "trips": Trip
}

HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Admin GTFS Avanzado</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        h1 {{ margin-bottom: 20px; }}
        .tab {{ cursor: pointer; padding: 10px; display: inline-block; background: #ddd; margin-right: 5px; border-radius: 4px; }}
        .tab.active {{ background: #007acc; color: white; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; background: white; }}
        th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
        th {{ background: #eee; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        input {{ width: 100%; border: none; background: transparent; }}
        button {{ margin: 2px; padding: 5px 8px; cursor: pointer; }}
        #pagination {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Admin GTFS Avanzado</h1>

    <h2>Cargar archivo GTFS (.zip)</h2>
    <input type="file" id="gtfsFile" accept=".zip"/>
    <button onclick="uploadGTFS()">Subir</button>
    <pre id="gtfsResult" style="background:#eee;padding:10px;"></pre>

    <div id="tabs">
        {''.join([f'<span class="tab {"active" if i==0 else ""}" data-table="{t}">{t.replace("_"," ").title()}</span>' for i,t in enumerate(TABLES)])}
    </div>
    <div id="pagination">
        <button id="prevPage">⬅️ Anterior</button>
        <span id="pageInfo">Página 1</span>
        <button id="nextPage">➡️ Siguiente</button>
    </div>
    <div id="table-container"></div>

<script>
let currentTable = "{list(TABLES.keys())[0]}";
let currentPage = 1;
const pageSize = 100;

// Función para subir GTFS
async function uploadGTFS() {{
    const fileInput = document.getElementById('gtfsFile');
    if (!fileInput.files.length) return alert('Selecciona un archivo .zip');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    document.getElementById('gtfsResult').innerText = "Cargando...";

    try {{
        const res = await fetch('/admin-web/upload-gtfs', {{ method: 'POST', body: formData }});
        const data = await res.json();
        if (res.ok) {{
            document.getElementById('gtfsResult').innerText = JSON.stringify(data, null, 2);
        }} else {{
            document.getElementById('gtfsResult').innerText = "Error: " + (data.detail || JSON.stringify(data));
        }}
    }} catch (err) {{
        document.getElementById('gtfsResult').innerText = "Error de conexión con el servidor";
        console.error(err);
    }}
}}

// Función para cargar tablas
async function loadTable(table, page=1) {{
    currentTable = table;
    currentPage = page;
    const res = await fetch(`/admin/${{table}}?skip=${{(page-1)*pageSize}}&limit=${{pageSize}}`);
    const data = await res.json();
    if (!data.length) {{
        document.getElementById('table-container').innerHTML = '<p>No hay datos.</p>';
        return;
    }}
    const columns = Object.keys(data[0]);
    let html = '<table><thead><tr>';
    columns.forEach(col => html += `<th>${{col}}</th>`);
    html += '<th>Acciones</th></tr></thead><tbody>';
    data.forEach(row => {{
        html += '<tr>';
        columns.forEach(col => html += `<td><input value="${{row[col] ?? ''}}" data-col="${{col}}" data-type="${{typeof row[col]}}"></td>`);
        html += `<td>
            <button onclick="saveRow(this)">💾</button>
            <button onclick="deleteRow(this)">🗑️</button>
        </td>`;
        html += '</tr>';
    }});
    html += '<tr>';
    columns.forEach(col => html += `<td><input data-col="${{col}}" placeholder="Nuevo" data-type="string"></td>`);
    html += `<td><button onclick="addRow(this)">➕</button></td>`;
    html += '</tr>';
    html += '</tbody></table>';
    document.getElementById('table-container').innerHTML = html;
    document.getElementById('pageInfo').innerText = `Página ${{page}}`;
}}

function parseValue(input) {{
    const type = input.dataset.type;
    let val = input.value;
    if (type === 'number') return Number(val);
    if (type === 'boolean') return val === 'true' ? 1 : 0;
    return val;
}}

async function saveRow(btn) {{
    const tr = btn.closest('tr');
    const inputs = tr.querySelectorAll('input');
    const payload = {{}};
    let pk = null;
    inputs.forEach(input => {{
        const col = input.dataset.col;
        payload[col] = parseValue(input);
        if (col.endsWith('_id')) pk = input.value;
    }});
    if (!pk) {{ alert('No se encontró PK'); return; }}
    if (!confirm('Guardar cambios?')) return;
    const res = await fetch(`/admin/${{currentTable}}/${{pk}}`, {{
        method: 'PUT',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify(payload)
    }});
    if (res.ok) loadTable(currentTable, currentPage);
    else alert('Error al guardar');
}}

async function deleteRow(btn) {{
    const tr = btn.closest('tr');
    const inputs = tr.querySelectorAll('input');
    let pk = null;
    inputs.forEach(input => {{ if (input.dataset.col.endsWith('_id')) pk = input.value; }});
    if (!pk) {{ alert('No se encontró PK'); return; }}
    if (!confirm('Eliminar registro?')) return;
    const res = await fetch(`/admin/${{currentTable}}/${{pk}}`, {{method:'DELETE'}});
    if (res.ok) loadTable(currentTable, currentPage);
}}

async function addRow(btn) {{
    const tr = btn.closest('tr');
    const inputs = tr.querySelectorAll('input');
    const payload = {{}};
    inputs.forEach(input => {{ if (input.value) payload[input.dataset.col] = parseValue(input); }});
    const res = await fetch(`/admin/${{currentTable}}`, {{
        method:'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify(payload)
    }});
    if (res.ok) loadTable(currentTable, currentPage);
    else alert('Error al agregar');
}}

document.querySelectorAll('.tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        loadTable(tab.dataset.table, 1);
    }});
}});

document.getElementById('prevPage').addEventListener('click', () => {{
    if (currentPage > 1) loadTable(currentTable, currentPage-1);
}});
document.getElementById('nextPage').addEventListener('click', () => {{
    loadTable(currentTable, currentPage+1);
}});

loadTable(currentTable, currentPage);
</script>
</body>
</html>
"""

# Dashboard principal
@router.get("/", response_class=HTMLResponse)
async def admin_web_dashboard():
    return HTMLResponse(content=HTML_TEMPLATE)

# Endpoint para subir GTFS
@router.post("/upload-gtfs")
async def upload_gtfs(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .zip GTFS")
    try:
        content = await file.read()
        importer = GTFSImporter(db)
        result = importer.import_gtfs(content)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
