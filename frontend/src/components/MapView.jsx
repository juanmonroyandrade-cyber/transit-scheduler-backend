import React, { useEffect, useState, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Arreglo ícono Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
});

// --- Componente para mostrar lista de paradas de UN sentido ---
function DirectionStopsList({ directionId, stops, title }) {
    if (!stops || stops.length === 0) {
        return <p className="text-xs text-gray-500 italic px-4 py-1">No hay paradas definidas para este sentido.</p>;
    }
    return (
        <div>
            <h4 className="text-sm font-semibold text-gray-700 mt-2 mb-1 px-4">{title} ({stops.length})</h4>
            <ul className="pl-8 max-h-40 overflow-y-auto text-xs list-decimal space-y-1 text-gray-600">
                {/* Asume que las paradas ya vienen ordenadas por secuencia desde el backend */}
                {stops.map((stop, index) => (
                    <li key={stop.stop_id + '-' + index}> 
                        {stop.stop_name || 'Parada sin nombre'} 
                        {/* Opcional: mostrar secuencia */}
                        {/* <span className="text-gray-400 ml-1">({stop.stop_sequence})</span> */}
                    </li>
                ))}
            </ul>
        </div>
    );
}


// --- Componente RouteItem (Modificado para mostrar paradas por dirección) ---
function RouteItem({ route, visibility, onToggle }) {
  const [showStopsList, setShowStopsList] = useState(false); // Control general para ambas listas
  
  // Extrae paradas de cada dirección
  const stopsDir0 = route.direction_0?.stops || [];
  const stopsDir1 = route.direction_1?.stops || [];
  const totalStops = stopsDir0.length + stopsDir1.length;

  return (
    <div className="mb-4 p-3 bg-white rounded-lg shadow hover:shadow-md transition-shadow duration-150">
      <p className="font-bold text-gray-800">{route.route_short_name || 'Sin nombre corto'}</p>
      <p className="text-sm text-gray-600 mb-2">{route.route_long_name || 'Sin nombre largo'}</p>
      
      {/* Toggles de Visibilidad (Línea y Paradas generales) */}
      <div className="flex items-center space-x-4 text-sm mb-2">
        <label className="flex items-center cursor-pointer"> <input type="checkbox" checked={visibility?.showLine || false} onChange={() => onToggle(route.route_id, "showLine")} className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"/> Línea </label>
        <label className="flex items-center cursor-pointer"> <input type="checkbox" checked={visibility?.showStops || false} onChange={() => onToggle(route.route_id, "showStops")} className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"/> Paradas </label>
      </div>
      
      {/* Botón para mostrar/ocultar listas de paradas */}
      {totalStops > 0 && (
         <button onClick={() => setShowStopsList(!showStopsList)} className="text-blue-600 hover:text-blue-800 text-sm font-medium"> 
             {showStopsList ? "Ocultar" : "Mostrar"} Paradas por Sentido ({totalStops}) 
         </button>
      )}

      {/* Listas de paradas por dirección (condicional) */}
      {showStopsList && (
         <div className="mt-2 border-t pt-2">
             <DirectionStopsList directionId={0} stops={stopsDir0} title="Sentido 1 (Ida)" />
             <DirectionStopsList directionId={1} stops={stopsDir1} title="Sentido 2 (Vuelta)" />
         </div>
      )}
    </div>
  );
}

// --- Componente MapView (Modificado para renderizar shapes/stops por dirección) ---
export default function MapView() {
  const [routesData, setRoutesData] = useState([]);
  const [visibility, setVisibility] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // Carga inicial
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true); setError(null);
      try {
        const res = await fetch("http://localhost:8000/gtfs/routes-with-details");
        if (!res.ok) { const errorData = await res.text(); throw new Error(` ${res.status}: ${errorData || res.statusText}`); }
        const data = await res.json();
        setRoutesData(data);
        const initialVisibility = {};
        data.forEach(route => { initialVisibility[route.route_id] = { showLine: false, showStops: false }; });
        setVisibility(initialVisibility);
      } catch (err) { setError("No se pudo cargar mapa: " + err.message); } 
      finally { setLoading(false); }
    };
    fetchData();
  }, []);

  // Toggle visibilidad
  const handleVisibilityToggle = (routeId, type) => {
    setVisibility(prev => ({ ...prev, [routeId]: { ...prev[routeId], [type]: !prev[routeId]?.[type] }, }));
  };

  // Filtra rutas
  const filteredRoutes = useMemo(() => {
    // ... (sin cambios)
     if (!searchTerm) return routesData;
    const lowerSearchTerm = searchTerm.toLowerCase().trim();
    if (!lowerSearchTerm) return routesData;
    return routesData.filter(route => 
        (route.route_short_name && route.route_short_name.toLowerCase().includes(lowerSearchTerm)) ||
        (route.route_long_name && route.route_long_name.toLowerCase().includes(lowerSearchTerm))
    );
  }, [routesData, searchTerm]);

  // Renderiza capas visibles (líneas y marcadores)
  const visibleLayers = useMemo(() => {
    return filteredRoutes.flatMap(route => {
      const layers = [];
      const routeVisibility = visibility[route.route_id];
      if (!routeVisibility) return []; 

      // Función auxiliar para validar coordenadas
      const isValidCoord = (p) => Array.isArray(p) && p.length === 2 && typeof p[0] === 'number' && typeof p[1] === 'number';

      // Renderiza LÍNEAS si showLine está activo
      if (routeVisibility.showLine) {
          // Combina shapes de ambas direcciones o puedes diferenciarlas si quieres
          const allShapes = [
              ...(route.direction_0?.shapes || []), 
              ...(route.direction_1?.shapes || [])
          ];
          allShapes.forEach((shapePoints, index) => { 
            const validPositions = shapePoints.filter(isValidCoord);
            if (validPositions.length > 1) { 
               // Usar el color de la ruta si existe, si no, azul por defecto
               const routeColor = route.route_color ? `#${route.route_color}` : 'blue';
               layers.push(<Polyline key={`${route.route_id}-line-${index}`} positions={validPositions} color={routeColor} weight={4} opacity={0.7}/>); 
            }
          });
      }
      
      // Renderiza PARADAS si showStops está activo
      if (routeVisibility.showStops) {
           // Combina paradas de ambas direcciones
           const allStops = [
               ...(route.direction_0?.stops || []),
               ...(route.direction_1?.stops || [])
           ];
           // Usa un Set para evitar duplicar marcadores si una parada está en ambos sentidos
           const uniqueStopIds = new Set(); 
           allStops.forEach(stop => { 
             if (stop && !uniqueStopIds.has(stop.stop_id) && typeof stop.stop_lat === 'number' && typeof stop.stop_lon === 'number') {
               layers.push( <Marker key={`${route.route_id}-stop-${stop.stop_id}`} position={[stop.stop_lat, stop.stop_lon]}> <Popup>{stop.stop_name || 'Parada sin nombre'}</Popup> </Marker> ); 
               uniqueStopIds.add(stop.stop_id);
             }
           });
      }
      return layers;
    });
  }, [filteredRoutes, visibility]); // Depende de rutas filtradas y visibilidad

  // --- Renderizado del Componente ---
  if (loading) return <div className="p-4 text-center animate-pulse">Cargando mapa...</div>;
  if (error) return <div className="p-6 text-red-700 bg-red-100 border border-red-300 rounded shadow">{error}</div>;
  
  return (
    <div className="flex h-full"> 
      {/* Barra Lateral */}
      <div className="w-1/3 md:w-1/4 p-4 overflow-y-auto bg-gray-50 border-r border-gray-200 flex flex-col">
        <h2 className="text-xl font-bold mb-4 text-gray-800 flex-shrink-0">Rutas</h2>
        <div className="mb-4 flex-shrink-0 relative">
          <input type="search" placeholder="Buscar..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full px-3 py-2 pl-8 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm" />
           <svg className="w-4 h-4 absolute left-2.5 top-2.5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"> <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /> </svg>
        </div>
        <div className="flex-grow overflow-y-auto pr-2"> 
          {filteredRoutes.length > 0 ? (
            filteredRoutes.map((route) => ( <RouteItem key={route.route_id} route={route} visibility={visibility[route.route_id]} onToggle={handleVisibilityToggle} /> ))
          ) : ( <p className="text-sm text-gray-500 text-center py-6"> {searchTerm ? `No hay rutas para "${searchTerm}".` : (routesData.length === 0 ? 'No hay rutas.' : 'Cargando...')} </p> )}
        </div>
      </div>
      {/* Mapa */}
      <div className="flex-grow"> 
        <MapContainer center={[20.9674, -89.5926]} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom={true} >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
          {visibleLayers}
        </MapContainer>
      </div>
    </div>
  );
}