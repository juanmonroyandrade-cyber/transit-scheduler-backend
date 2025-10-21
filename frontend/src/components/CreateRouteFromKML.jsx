import React, { useState, useEffect } from 'react';

export default function CreateRouteFromKML() {
  const [routeData, setRouteData] = useState({
    route_id: '',
    route_short_name: '',
    route_long_name: '',
    route_type: 3, // Default: Bus
    route_color: 'FFFFFF', // Default: White
    route_text_color: '000000', // Default: Black
    agency_id: null, // Se asignará del primer agency disponible
  });
  const [kmlFileDir0, setKmlFileDir0] = useState(null);
  const [shapeIdDir0, setShapeIdDir0] = useState('');
  const [kmlFileDir1, setKmlFileDir1] = useState(null);
  const [shapeIdDir1, setShapeIdDir1] = useState('');
  const [agencies, setAgencies] = useState([]); // Para seleccionar agency_id
  
  const [status, setStatus] = useState({ message: '', type: '' }); // success, error, loading
  const [loading, setLoading] = useState(false);

  // Cargar agencias disponibles al montar
  useEffect(() => {
    const fetchAgencies = async () => {
        try {
            const res = await fetch('http://localhost:8000/admin/agencies'); // Asume que tienes este endpoint
            if (!res.ok) throw new Error('No se pudieron cargar las agencias.');
            const data = await res.json();
            setAgencies(data);
            // Asigna automáticamente el ID de la primera agencia si existe
            if (data.length > 0 && !routeData.agency_id) {
                setRouteData(prev => ({ ...prev, agency_id: data[0].agency_id }));
            }
        } catch (err) {
            console.error(err);
             setStatus({ message: 'Error al cargar agencias: ' + err.message, type: 'error' });
        }
    };
    fetchAgencies();
  }, []); // Carga una sola vez

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setRouteData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e, direction) => {
    const file = e.target.files[0];
    if (direction === 0) {
      setKmlFileDir0(file);
    } else {
      setKmlFileDir1(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus({ message: 'Procesando...', type: 'loading' });

    // Validaciones básicas
    if (!routeData.route_id || !routeData.route_short_name || !routeData.agency_id) {
        setStatus({ message: 'ID de Ruta, Nombre Corto y Agencia son requeridos.', type: 'error' });
        setLoading(false);
        return;
    }
     if ((!kmlFileDir0 || !shapeIdDir0) && (!kmlFileDir1 || !shapeIdDir1)) {
        setStatus({ message: 'Debes proporcionar al menos un archivo KML con su Shape ID.', type: 'error' });
        setLoading(false);
        return;
    }
    if ((kmlFileDir0 && !shapeIdDir0) || (!kmlFileDir0 && shapeIdDir0)) {
         setStatus({ message: 'Debes proporcionar KML y Shape ID para Sentido 1.', type: 'error' });
         setLoading(false);
         return;
    }
     if ((kmlFileDir1 && !shapeIdDir1) || (!kmlFileDir1 && shapeIdDir1)) {
         setStatus({ message: 'Debes proporcionar KML y Shape ID para Sentido 2.', type: 'error' });
         setLoading(false);
         return;
    }


    const formData = new FormData();

    // Añadir datos de la ruta como JSON stringificado
    formData.append('route_data', JSON.stringify(routeData));
    
    // Añadir archivos KML y shape IDs si existen
    if (kmlFileDir0 && shapeIdDir0) {
        formData.append('kml_file_0', kmlFileDir0);
        formData.append('shape_id_0', shapeIdDir0);
    }
     if (kmlFileDir1 && shapeIdDir1) {
        formData.append('kml_file_1', kmlFileDir1);
        formData.append('shape_id_1', shapeIdDir1);
    }

    try {
      // Usaremos un nuevo endpoint, por ejemplo /routes/create-with-kml
      const res = await fetch('http://localhost:8000/routes/create-with-kml', {
        method: 'POST',
        body: formData, // No necesita 'Content-Type' header, el navegador lo pone con FormData
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.detail || `Error ${res.status} del servidor.`);
      }

      setStatus({ message: `¡Ruta '${result.route_short_name}' creada exitosamente! Shapes agregados: ${result.shapes_added.join(', ')}`, type: 'success' });
      // Limpiar formulario (opcional)
       // setRouteData({ route_id: '', route_short_name: '', ... });
       // setKmlFileDir0(null); setShapeIdDir0(''); ... etc.

    } catch (err) {
      console.error("Error al crear ruta:", err);
      setStatus({ message: `Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };
  
  // Opciones para route_type GTFS
  const routeTypeOptions = [
    { value: 0, label: 'Tranvía, Tren ligero' },
    { value: 1, label: 'Subterráneo, Metro' },
    { value: 2, label: 'Tren' },
    { value: 3, label: 'Autobús' },
    { value: 4, label: 'Ferry' },
    { value: 5, label: 'Teleférico' },
    { value: 6, label: 'Góndola' },
    { value: 7, label: 'Funicular' },
    // Añadir más si es necesario
  ];

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Crear Ruta desde KML</h1>

      {/* Mensaje de Estado */}
      {status.message && (
        <div className={`p-3 mb-4 rounded-md text-sm ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' : 
            status.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' : 
            'bg-blue-100 text-blue-800 border border-blue-200'
        }`}>
          {status.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-6">
        
        {/* Sección Datos de la Ruta */}
        <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Datos de la Ruta</legend>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                <div>
                    <label htmlFor="agency_id" className="block text-sm font-medium text-gray-700">Agencia <span className="text-red-500">*</span></label>
                    <select id="agency_id" name="agency_id" value={routeData.agency_id || ''} onChange={handleInputChange} required 
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-100"
                            disabled={agencies.length === 0}>
                        <option value="" disabled>Selecciona una agencia...</option>
                        {agencies.map(agency => (
                            <option key={agency.agency_id} value={agency.agency_id}>{agency.agency_name} (ID: {agency.agency_id})</option>
                        ))}
                    </select>
                     {agencies.length === 0 && <p className="text-xs text-red-500 mt-1">No hay agencias disponibles. Importa un GTFS primero.</p>}
                </div>
                <div>
                    <label htmlFor="route_id" className="block text-sm font-medium text-gray-700">ID de Ruta <span className="text-red-500">*</span></label>
                    <input type="text" id="route_id" name="route_id" value={routeData.route_id} onChange={handleInputChange} required 
                           className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                </div>
                 <div>
                    <label htmlFor="route_short_name" className="block text-sm font-medium text-gray-700">Nombre Corto <span className="text-red-500">*</span></label>
                    <input type="text" id="route_short_name" name="route_short_name" value={routeData.route_short_name} onChange={handleInputChange} required 
                           className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                </div>
                <div>
                    <label htmlFor="route_long_name" className="block text-sm font-medium text-gray-700">Nombre Largo</label>
                    <input type="text" id="route_long_name" name="route_long_name" value={routeData.route_long_name} onChange={handleInputChange} 
                           className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                </div>
                 <div>
                    <label htmlFor="route_type" className="block text-sm font-medium text-gray-700">Tipo de Ruta</label>
                     <select id="route_type" name="route_type" value={routeData.route_type} onChange={handleInputChange}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                        {routeTypeOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                    </select>
                </div>
                 <div className="flex space-x-4">
                    <div className="flex-1">
                        <label htmlFor="route_color" className="block text-sm font-medium text-gray-700">Color (Hex)</label>
                        <div className="flex items-center">
                            <span className="inline-block h-8 w-8 rounded border border-gray-300 mr-2" style={{ backgroundColor: `#${routeData.route_color}` }}></span>
                            <input type="text" id="route_color" name="route_color" value={routeData.route_color} onChange={handleInputChange} maxLength="6" placeholder="Ej: FF0000"
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                        </div>
                    </div>
                     <div className="flex-1">
                        <label htmlFor="route_text_color" className="block text-sm font-medium text-gray-700">Color Texto (Hex)</label>
                         <div className="flex items-center">
                             <span className="inline-block h-8 w-8 rounded border border-gray-300 mr-2 flex items-center justify-center font-bold" style={{ backgroundColor: `#${routeData.route_text_color}`, color: `#${routeData.route_color}`}}>Aa</span>
                             <input type="text" id="route_text_color" name="route_text_color" value={routeData.route_text_color} onChange={handleInputChange} maxLength="6" placeholder="Ej: 000000"
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                         </div>
                    </div>
                </div>
            </div>
        </fieldset>

        {/* Sección Sentido 1 (Ida) */}
        <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Sentido 1 (Ida)</legend>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                 <div>
                    <label htmlFor="shape_id_0" className="block text-sm font-medium text-gray-700">Shape ID (Sentido 1) <span className="text-red-500">*</span></label>
                    <input type="text" id="shape_id_0" value={shapeIdDir0} onChange={(e) => setShapeIdDir0(e.target.value)} 
                           placeholder="Identificador único para este trazado"
                           className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                </div>
                <div>
                    <label htmlFor="kml_file_0" className="block text-sm font-medium text-gray-700">Archivo KML (Sentido 1) <span className="text-red-500">*</span></label>
                    <input type="file" id="kml_file_0" accept=".kml" onChange={(e) => handleFileChange(e, 0)} 
                           className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                </div>
            </div>
        </fieldset>

        {/* Sección Sentido 2 (Vuelta) */}
         <fieldset className="border p-4 rounded-md">
            <legend className="text-lg font-semibold px-2 text-gray-700">Sentido 2 (Vuelta)</legend>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                 <div>
                    <label htmlFor="shape_id_1" className="block text-sm font-medium text-gray-700">Shape ID (Sentido 2) <span className="text-red-500">*</span></label>
                    <input type="text" id="shape_id_1" value={shapeIdDir1} onChange={(e) => setShapeIdDir1(e.target.value)} 
                           placeholder="Identificador único para este trazado"
                           className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/>
                </div>
                <div>
                    <label htmlFor="kml_file_1" className="block text-sm font-medium text-gray-700">Archivo KML (Sentido 2) <span className="text-red-500">*</span></label>
                    <input type="file" id="kml_file_1" accept=".kml" onChange={(e) => handleFileChange(e, 1)} 
                           className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                </div>
            </div>
        </fieldset>
        
        {/* Botón de Envío */}
        <div className="flex justify-end pt-4">
             <button type="submit" disabled={loading || agencies.length === 0}
                    className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50">
                 {loading ? 'Creando Ruta...' : 'Crear Ruta y Shapes'}
             </button>
        </div>

      </form>
    </div>
  );
}