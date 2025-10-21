import React, { useState, useEffect } from 'react';

export default function CreateRouteFromKML() {
  const [routeData, setRouteData] = useState({
    route_id: '',
    route_short_name: '',
    route_long_name: '',
    route_type: 3, // Default: Bus
    route_color: 'FFFFFF',
    route_text_color: '000000',
    agency_id: null,
  });
  const [kmlFileDir0, setKmlFileDir0] = useState(null);
  const [shapeIdDir0, setShapeIdDir0] = useState('');
  const [kmlFileDir1, setKmlFileDir1] = useState(null);
  const [shapeIdDir1, setShapeIdDir1] = useState('');
  const [agencies, setAgencies] = useState([]);

  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);
  const [loadingAgencies, setLoadingAgencies] = useState(true);

  // Cargar agencias
  useEffect(() => {
    let isMounted = true;
    setLoadingAgencies(true);
    setStatus({ message: '', type: '' });

    const fetchAgencies = async () => {
        try {
            console.log("[CreateRouteKML] Fetching agencies...");
            const url = 'http://localhost:8000/admin/agencies?page=1&per_page=1000'; // Usa la URL con paginación
            console.log(`[CreateRouteKML] Fetching URL: ${url}`);
            const res = await fetch(url);
            if (!isMounted) return;

            if (!res.ok) {
                 let errorDetail = `HTTP ${res.status}`;
                 try {
                     const errorJson = await res.json();
                     if (errorJson.detail && Array.isArray(errorJson.detail)) {
                         errorDetail = errorJson.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('; ');
                     } else if (errorJson.detail) { errorDetail = errorJson.detail; }
                 } catch (e) { errorDetail = `${res.status}: ${res.statusText}`; }
                 console.error("[CreateRouteKML] Fetch agencies failed:", errorDetail);
                 throw new Error(`No se pudieron cargar agencias (${errorDetail}).`);
            }

            const data = await res.json();
            console.log("[CreateRouteKML] Agencies received:", data);

            const agenciesData = Array.isArray(data?.data) ? data.data : [];
            setAgencies(agenciesData);

            if (agenciesData.length > 0 && routeData.agency_id === null) {
                setRouteData(prev => ({ ...prev, agency_id: agenciesData[0].agency_id }));
            } else if (agenciesData.length === 0) {
                 setStatus({ message: 'No se encontraron agencias. Carga un GTFS.', type: 'warning' });
            }
        } catch (err) {
            console.error("[CreateRouteKML] Error in fetchAgencies:", err);
            const errorMessage = (err instanceof Error ? err.message : String(err)) || 'Error desconocido.';
            if(isMounted) setStatus({ message: `Error al cargar agencias: ${errorMessage}`, type: 'error' });
        } finally {
            if(isMounted) setLoadingAgencies(false);
        }
    };
    fetchAgencies();
    return () => { isMounted = false; };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    const val = (name === 'agency_id' || name === 'route_type') ? parseInt(value, 10) : value;
    setRouteData(prev => ({ ...prev, [name]: val }));
  };

  const handleFileChange = (e, direction) => {
    const file = e.target.files[0];
    if (direction === 0) setKmlFileDir0(file);
    else setKmlFileDir1(file);
  };

  const handleSubmit = async (e) => {
    // ... (sin cambios respecto a la versión anterior) ...
    e.preventDefault();
    setLoading(true);
    setStatus({ message: 'Procesando...', type: 'loading' });
    if (!routeData.route_id || !routeData.route_short_name || !routeData.agency_id) {setStatus({ message: 'ID Ruta, Nombre Corto y Agencia requeridos.', type: 'error' }); setLoading(false); return;}
    if ((!kmlFileDir0 || !shapeIdDir0) && (!kmlFileDir1 || !shapeIdDir1)) {setStatus({ message: 'Proporciona al menos un KML con su Shape ID.', type: 'error' }); setLoading(false); return;}
    if ((kmlFileDir0 && !shapeIdDir0) || (!kmlFileDir0 && shapeIdDir0)) {setStatus({ message: 'Proporciona KML y Shape ID para Sentido 1.', type: 'error' }); setLoading(false); return;}
    if ((kmlFileDir1 && !shapeIdDir1) || (!kmlFileDir1 && shapeIdDir1)) {setStatus({ message: 'Proporciona KML y Shape ID para Sentido 2.', type: 'error' }); setLoading(false); return;}
     if (shapeIdDir0 && shapeIdDir1 && shapeIdDir0.trim() === shapeIdDir1.trim()) { setStatus({ message: 'Los Shape IDs deben ser diferentes.', type: 'error'}); setLoading(false); return; }
    const formDataToSend = new FormData();
    formDataToSend.append('route_data', JSON.stringify(routeData));
    if (kmlFileDir0 && shapeIdDir0) { formDataToSend.append('kml_file_0', kmlFileDir0); formDataToSend.append('shape_id_0', shapeIdDir0.trim()); }
    if (kmlFileDir1 && shapeIdDir1) { formDataToSend.append('kml_file_1', kmlFileDir1); formDataToSend.append('shape_id_1', shapeIdDir1.trim()); }
    try {
      const res = await fetch('http://localhost:8000/routes/create-with-kml', { method: 'POST', body: formDataToSend });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || `Error ${res.status}`);
      setStatus({ message: `Ruta '${result.route_short_name}' creada! Shapes: ${result.shapes_added.join(', ')}`, type: 'success' });
    } catch (err) {
      console.error("Error al crear ruta:", err);
      setStatus({ message: `Error al crear: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const routeTypeOptions = [ { value: 0, label: 'Tranvía' }, { value: 1, label: 'Metro' }, { value: 2, label: 'Tren' }, { value: 3, label: 'Autobús' }, { value: 4, label: 'Ferry' }, /* ... */ ];

  // --- Clases Tailwind ---
  const inputBaseStyle = "mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed";
  const fileInputBaseStyle = "mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-1.5 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer";
  const labelBaseStyle = "block text-sm font-medium text-gray-700";
  const requiredMark = <span className="text-red-500">*</span>;

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Crear Ruta desde KML</h1>

      {status.message && ( <div className={`p-3 mb-4 rounded-md text-sm border ${ status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' : status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' : status.type === 'warning' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' : 'bg-blue-100 text-blue-800 border-blue-200' }`}> {status.message} </div> )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-6">
        {/* Datos Ruta */}
        <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Datos de la Ruta</legend>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                <div>
                    <label htmlFor="agency_id" className={labelBaseStyle}>Agencia {requiredMark}</label>
                    <select id="agency_id" name="agency_id" value={routeData.agency_id ?? ''} onChange={handleInputChange} required className={`${inputBaseStyle} ${loadingAgencies || agencies.length === 0 ? 'cursor-not-allowed bg-gray-100' : ''}`} disabled={loadingAgencies || agencies.length === 0}>
                        <option value="" disabled>{loadingAgencies ? 'Cargando...' : 'Selecciona...'}</option>
                        {agencies.map(agency => ( <option key={agency.agency_id} value={agency.agency_id}>{agency.agency_name || `ID ${agency.agency_id}`}</option> ))}
                    </select>
                     {!loadingAgencies && agencies.length === 0 && !status.message.includes('agencias') && <p className="text-xs text-orange-600 mt-1">No hay agencias.</p>}
                </div>
                 <div><label htmlFor="route_id" className={labelBaseStyle}>ID Ruta {requiredMark}</label><input type="text" id="route_id" name="route_id" value={routeData.route_id} onChange={handleInputChange} required className={inputBaseStyle}/></div>
                 <div><label htmlFor="route_short_name" className={labelBaseStyle}>Nombre Corto {requiredMark}</label><input type="text" id="route_short_name" name="route_short_name" value={routeData.route_short_name} onChange={handleInputChange} required className={inputBaseStyle}/></div>
                 <div><label htmlFor="route_long_name" className={labelBaseStyle}>Nombre Largo</label><input type="text" id="route_long_name" name="route_long_name" value={routeData.route_long_name} onChange={handleInputChange} className={inputBaseStyle}/></div>
                 <div><label htmlFor="route_type" className={labelBaseStyle}>Tipo Ruta</label><select id="route_type" name="route_type" value={routeData.route_type} onChange={handleInputChange} className={inputBaseStyle}>{routeTypeOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}</select></div>
                 <div className="flex space-x-4"><div className="flex-1"><label htmlFor="route_color" className={labelBaseStyle}>Color</label><div className="flex items-center mt-1"><span className="inline-block h-8 w-8 rounded border border-gray-300 mr-2" style={{ backgroundColor: `#${routeData.route_color}` }}></span><input type="text" id="route_color" name="route_color" value={routeData.route_color} onChange={handleInputChange} maxLength="6" placeholder="FFFFFF" className={inputBaseStyle}/></div></div><div className="flex-1"><label htmlFor="route_text_color" className={labelBaseStyle}>Color Texto</label><div className="flex items-center mt-1"><span className="inline-block h-8 w-8 rounded border border-gray-300 mr-2 flex items-center justify-center font-bold" style={{ backgroundColor: `#${routeData.route_text_color}`, color: `#${routeData.route_color}`}}>Aa</span><input type="text" id="route_text_color" name="route_text_color" value={routeData.route_text_color} onChange={handleInputChange} maxLength="6" placeholder="000000" className={inputBaseStyle}/></div></div></div>
            </div>
        </fieldset>

        {/* Sentido 1 */}
        <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Sentido 1 (Ida)</legend>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                 <div><label htmlFor="shape_id_0" className={labelBaseStyle}>Shape ID (Sentido 1)</label><input type="text" id="shape_id_0" value={shapeIdDir0} onChange={(e) => setShapeIdDir0(e.target.value)} placeholder="ID único trazado ida" className={inputBaseStyle}/></div>
                <div><label htmlFor="kml_file_0" className={labelBaseStyle}>Archivo KML (Sentido 1)</label><input type="file" id="kml_file_0" accept=".kml,application/vnd.google-earth.kml+xml" onChange={(e) => handleFileChange(e, 0)} className={fileInputBaseStyle}/></div>
            </div>
             <p className="text-xs text-gray-500 mt-2">Proporciona un Shape ID y un KML si se usa este sentido.</p>
        </fieldset>

        {/* Sentido 2 */}
        <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Sentido 2 (Vuelta)</legend>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                 <div><label htmlFor="shape_id_1" className={labelBaseStyle}>Shape ID (Sentido 2)</label><input type="text" id="shape_id_1" value={shapeIdDir1} onChange={(e) => setShapeIdDir1(e.target.value)} placeholder="ID único trazado vuelta" className={inputBaseStyle}/></div>
                <div><label htmlFor="kml_file_1" className={labelBaseStyle}>Archivo KML (Sentido 2)</label><input type="file" id="kml_file_1" accept=".kml,application/vnd.google-earth.kml+xml" onChange={(e) => handleFileChange(e, 1)} className={fileInputBaseStyle}/></div>
            </div>
             <p className="text-xs text-gray-500 mt-2">Proporciona un Shape ID y un KML si se usa este sentido.</p>
        </fieldset>

        {/* Botón Envío */}
        <div className="flex justify-end pt-4">
             <button type="submit" disabled={loading || loadingAgencies || agencies.length === 0}
                    className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed">
                 {loading ? 'Creando...' : 'Crear Ruta y Shapes'}
             </button>
        </div>
      </form>
    </div>
  );
}