import { useEffect, useState, useMemo } from "react";
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

// --- Componente RouteItem (sin cambios) ---
function RouteItem({ route, visibility, onToggle }) {
  const [showStopsList, setShowStopsList] = useState(false);
  return (
    <div className="mb-4 p-3 bg-white rounded-lg shadow">
      <p className="font-bold text-gray-800">{route.route_short_name}</p>
      <p className="text-sm text-gray-600 mb-2">{route.route_long_name}</p>
      <div className="flex items-center space-x-4 text-sm">
        <label className="flex items-center cursor-pointer"> <input type="checkbox" checked={visibility.showLine} onChange={() => onToggle(route.route_id, "showLine")} className="mr-2"/> Línea </label>
        <label className="flex items-center cursor-pointer"> <input type="checkbox" checked={visibility.showStops} onChange={() => onToggle(route.route_id, "showStops")} className="mr-2"/> Paradas </label>
      </div>
      <button onClick={() => setShowStopsList(!showStopsList)} className="text-blue-600 hover:underline text-sm mt-2"> {showStopsList ? "Ocultar" : "Mostrar"} paradas ({route.stops.length}) </button>
      {showStopsList && ( <ul className="mt-2 pl-4 max-h-40 overflow-y-auto text-xs list-decimal"> {route.stops.map(stop => ( <li key={stop.stop_id} className="text-gray-700">{stop.stop_name}</li> ))} </ul> )}
    </div>
  );
}

// --- Componente MapView (con filtro añadido) ---
export default function MapView() {
  const [routesData, setRoutesData] = useState([]);
  const [visibility, setVisibility] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState(""); // ✅ Estado para el término de búsqueda

  // Carga inicial de datos
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch("http://localhost:8000/gtfs/routes-with-details");
        if (!res.ok) throw new Error(`Error ${res.status}: ${await res.text()}`);
        const data = await res.json();
        setRoutesData(data);
        const initialVisibility = {};
        data.forEach(route => { initialVisibility[route.route_id] = { showLine: false, showStops: false }; });
        setVisibility(initialVisibility);
      } catch (err) { setError("No se pudieron cargar los datos del mapa: " + err.message);
      } finally { setLoading(false); }
    };
    fetchData();
  }, []);

  const handleVisibilityToggle = (routeId, type) => {
    setVisibility(prev => ({ ...prev, [routeId]: { ...prev[routeId], [type]: !prev[routeId][type] }, }));
  };

  // ✅ Filtra las rutas basándose en searchTerm
  const filteredRoutes = useMemo(() => {
    if (!searchTerm) return routesData;
    const lowerSearchTerm = searchTerm.toLowerCase();
    return routesData.filter(route => 
        (route.route_short_name && route.route_short_name.toLowerCase().includes(lowerSearchTerm)) ||
        (route.route_long_name && route.route_long_name.toLowerCase().includes(lowerSearchTerm))
    );
  }, [routesData, searchTerm]);

  // Renderiza las capas visibles (líneas y marcadores)
  const visibleLayers = useMemo(() => {
    // Solo renderiza capas de rutas filtradas
    return filteredRoutes.flatMap(route => {
      const layers = [];
      const isVisible = visibility[route.route_id];
      if (isVisible?.showLine) {
        route.shapes.forEach((shapePoints, index) => { layers.push(<Polyline key={`${route.route_id}-line-${index}`} positions={shapePoints} color={route.route_color ? `#${route.route_color}` : 'blue'} weight={3}/>); });
      }
      if (isVisible?.showStops) {
        route.stops.forEach(stop => { layers.push( <Marker key={`${route.route_id}-stop-${stop.stop_id}`} position={[stop.stop_lat, stop.stop_lon]}> <Popup>{stop.stop_name}</Popup> </Marker> ); });
      }
      return layers;
    });
  }, [filteredRoutes, visibility]); // Depende de las rutas filtradas

  if (error) return <div className="p-4 text-red-500 bg-red-50">{error}</div>;
  if (loading) return <div className="p-4 text-center animate-pulse">Cargando datos del mapa...</div>;
  
  return (
    <div className="flex" style={{ height: 'calc(100vh - 64px)' }}> {/* Ajusta altura si tienes header */}
      {/* Barra Lateral */}
      <div className="w-1/3 md:w-1/4 p-4 overflow-y-auto bg-gray-50 border-r border-gray-200 flex flex-col">
        <h2 className="text-xl font-bold mb-4 text-gray-800 flex-shrink-0">Rutas Disponibles</h2>
        
        {/* ✅ Campo de Búsqueda/Filtro */}
        <div className="mb-4 flex-shrink-0">
          <input
            type="text"
            placeholder="Buscar ruta (ej: R101)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>

        {/* Lista de Rutas (Scrollable) */}
        <div className="flex-grow overflow-y-auto">
          {filteredRoutes.length > 0 ? (
            filteredRoutes.map((route) => (
              <RouteItem 
                key={route.route_id}
                route={route}
                visibility={visibility[route.route_id] || {}}
                onToggle={handleVisibilityToggle}
              />
            ))
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">
              {searchTerm ? 'No se encontraron rutas.' : 'Cargando rutas...'}
            </p>
          )}
        </div>
      </div>

      {/* Mapa */}
      <div className="w-2/3 md:w-3/4">
        <MapContainer center={[20.9674, -89.5926]} zoom={12} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
          {visibleLayers}
        </MapContainer>
      </div>
    </div>
  );
}