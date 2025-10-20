// frontend/src/components/MapView.jsx

import { useEffect, useState, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Arreglo para el ícono por defecto de Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
});

// --- Componente para una sola ruta en la barra lateral ---
function RouteItem({ route, visibility, onToggle }) {
  const [showStopsList, setShowStopsList] = useState(false);

  return (
    <div className="mb-4 p-3 bg-white rounded-lg shadow">
      <p className="font-bold text-gray-800">{route.route_short_name}</p>
      <p className="text-sm text-gray-600 mb-2">{route.route_long_name}</p>
      <div className="flex items-center space-x-4 text-sm">
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={visibility.showLine}
            onChange={() => onToggle(route.route_id, "showLine")}
            className="mr-2"
          />
          Línea
        </label>
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={visibility.showStops}
            onChange={() => onToggle(route.route_id, "showStops")}
            className="mr-2"
          />
          Paradas
        </label>
      </div>
      <button onClick={() => setShowStopsList(!showStopsList)} className="text-blue-600 hover:underline text-sm mt-2">
        {showStopsList ? "Ocultar" : "Mostrar"} lista de paradas ({route.stops.length})
      </button>
      {showStopsList && (
        <ul className="mt-2 pl-4 max-h-40 overflow-y-auto text-xs list-decimal">
          {route.stops.map(stop => (
            <li key={stop.stop_id} className="text-gray-700">{stop.stop_name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// --- Componente Principal del Mapa ---
export default function MapView() {
  const [routesData, setRoutesData] = useState([]);
  const [visibility, setVisibility] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // ✅ 1. AHORA SOLO HAY UNA LLAMADA A LA API
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch("http://localhost:8000/gtfs/routes-with-details");
        if (!res.ok) {
          throw new Error(`Error ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        setRoutesData(data);

        // Inicializa la visibilidad
        const initialVisibility = {};
        data.forEach(route => {
          initialVisibility[route.route_id] = { showLine: false, showStops: false };
        });
        setVisibility(initialVisibility);
      } catch (err) {
        console.error("Error al obtener datos GTFS:", err);
        setError("No se pudieron cargar los datos de las rutas. Asegúrate que el backend funciona y que hay datos GTFS cargados.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleVisibilityToggle = (routeId, type) => {
    setVisibility(prev => ({
      ...prev,
      [routeId]: { ...prev[routeId], [type]: !prev[routeId][type] },
    }));
  };

  // ✅ 2. LA LÓGICA DE RENDERIZADO ES MÁS SENCILLA
  const visibleLayers = useMemo(() => {
    return routesData.flatMap(route => {
      const layers = [];
      const isVisible = visibility[route.route_id];

      if (isVisible?.showLine) {
        route.shapes.forEach((shapePoints, index) => {
          layers.push(<Polyline key={`${route.route_id}-line-${index}`} positions={shapePoints} color={route.route_color ? `#${route.route_color}` : 'blue'} />);
        });
      }

      if (isVisible?.showStops) {
        route.stops.forEach(stop => {
          layers.push(
            <Marker key={`${route.route_id}-stop-${stop.stop_id}`} position={[stop.stop_lat, stop.stop_lon]}>
              <Popup>{stop.stop_name}</Popup>
            </Marker>
          );
        });
      }
      return layers;
    });
  }, [routesData, visibility]);

  if (error) return <div className="p-4 text-red-500 bg-red-50">{error}</div>;
  
  return (
    <div className="flex" style={{ height: 'calc(100vh - 64px)' }}>
      <div className="w-1/3 md:w-1/4 p-4 overflow-y-auto bg-gray-50 border-r">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Rutas Disponibles</h2>
        {loading ? (
          <p>Cargando rutas...</p>
        ) : (
          routesData.map(route => (
            <RouteItem 
              key={route.route_id}
              route={route}
              visibility={visibility[route.route_id] || {}}
              onToggle={handleVisibilityToggle}
            />
          ))
        )}
      </div>

      <div className="w-2/3 md:w-3/4">
        <MapContainer center={[20.9674, -89.5926]} zoom={12} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          {visibleLayers}
        </MapContainer>
      </div>
    </div>
  );
}