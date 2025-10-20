// src/components/MapView.jsx
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const defaultIcon = L.icon({
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function MapView() {
  const [routes, setRoutes] = useState([]);
  const [routeShapes, setRouteShapes] = useState({});
  const [routeStops, setRouteStops] = useState({});
  const [routeVisibility, setRouteVisibility] = useState({});
  const [stopVisibility, setStopVisibility] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedRoutes, setExpandedRoutes] = useState({});
  const API_URL = "http://localhost:8000/admin";

  useEffect(() => {
    loadMapData();
  }, []);

  const loadMapData = async () => {
    try {
      // 1️⃣ Cargar rutas
      const routesRes = await fetch(`${API_URL}/routes`);
      const routesData = await routesRes.json();
      setRoutes(routesData);

      // Inicializar visibilidad y expansión
      const initVisibility = {};
      const initStopVis = {};
      const initExpanded = {};
      routesData.forEach((r) => {
        initVisibility[r.route_id] = false;
        initStopVis[r.route_id] = false;
        initExpanded[r.route_id] = false;
      });
      setRouteVisibility(initVisibility);
      setStopVisibility(initStopVis);
      setExpandedRoutes(initExpanded);

      // 2️⃣ Cargar trips
      const tripsRes = await fetch(`${API_URL}/trips`);
      const tripsData = await tripsRes.json();

      // 3️⃣ Cargar shapes
      const shapesRes = await fetch(`${API_URL}/shapes`);
      const shapesData = await shapesRes.json();

      // Agrupar shapes por shape_id y ordenar por sequence
      const shapesGrouped = {};
      shapesData.forEach((pt) => {
        if (!shapesGrouped[pt.shape_id]) shapesGrouped[pt.shape_id] = [];
        shapesGrouped[pt.shape_id].push(pt);
      });
      Object.keys(shapesGrouped).forEach((sid) => {
        shapesGrouped[sid].sort((a, b) => a.shape_pt_sequence - b.shape_pt_sequence);
      });

      // 4️⃣ Asignar shapes a cada ruta (mediante trips)
      const routeShapesObj = {};
      routesData.forEach((route) => {
        const shapeIds = tripsData
          .filter((t) => t.route_id === route.route_id)
          .map((t) => t.shape_id);

        const allCoords = [];
        shapeIds.forEach((sid) => {
          if (shapesGrouped[sid]) {
            shapesGrouped[sid].forEach((pt) => {
              const lat = Number(pt.shape_pt_lat);
              const lon = Number(pt.shape_pt_lon);
              if (!isNaN(lat) && !isNaN(lon)) {
                allCoords.push([lat, lon]);
              }
            });
          }
        });

        routeShapesObj[route.route_id] = allCoords.length > 0 ? allCoords : null;
      });
      setRouteShapes(routeShapesObj);

      // 5️⃣ Cargar paradas
      const stopsPromises = routesData.map((route) =>
        fetch(`${API_URL}/routes/${route.route_id}/stops`)
          .then((r) => r.json())
          .then((data) => ({ route_id: route.route_id, stops: data.stops || [] }))
          .catch(() => ({ route_id: route.route_id, stops: [] }))
      );

      const stopsResults = await Promise.all(stopsPromises);
      const stopsObj = {};
      stopsResults.forEach(({ route_id, stops }) => {
        stopsObj[route_id] = stops;
      });
      setRouteStops(stopsObj);

      setLoading(false);
    } catch (error) {
      console.error("Error cargando datos del mapa:", error);
      setLoading(false);
    }
  };

  const toggleRoute = (route_id) => {
    setRouteVisibility((prev) => ({ ...prev, [route_id]: !prev[route_id] }));
  };

  const toggleRouteStops = (route_id) => {
    setStopVisibility((prev) => ({ ...prev, [route_id]: !prev[route_id] }));
  };

  const toggleExpanded = (route_id) => {
    setExpandedRoutes((prev) => ({ ...prev, [route_id]: !prev[route_id] }));
  };

  const formatColor = (color) => {
    if (!color) return "#0000FF";
    return color.startsWith("#") ? color : `#${color}`;
  };

  const getStopsForRoute = (route_id) => routeStops[route_id] || [];

  if (loading) {
    return (
      <div className="p-6 h-full w-full flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-lg">Cargando mapa...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      {/* 🧭 Panel lateral */}
      <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto shadow-lg">
        <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-purple-600">
          <h2 className="text-xl font-bold text-white">🗺️ Control de Rutas</h2>
          <p className="text-sm text-blue-100 mt-1">{routes.length} rutas disponibles</p>
        </div>

        <div className="p-3">
          {routes.map((route) => {
            const isExpanded = expandedRoutes[route.route_id];
            const isRouteVisible = routeVisibility[route.route_id];
            const areStopsVisible = stopVisibility[route.route_id];
            const stops = getStopsForRoute(route.route_id);
            const hasShape =
              routeShapes[route.route_id] && routeShapes[route.route_id]?.length > 0;

            return (
              <div key={route.route_id} className="mb-3 border rounded-lg overflow-hidden shadow-sm">
                <div className="bg-gray-50 p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: formatColor(route.route_color) }}
                      ></div>
                      <span className="font-semibold text-gray-800">
                        {route.route_short_name || route.route_id}
                      </span>
                      {!hasShape && <span className="text-xs text-orange-600">⚠️</span>}
                    </div>
                    <button
                      onClick={() => toggleExpanded(route.route_id)}
                      className="text-gray-500 hover:text-gray-700 p-1"
                    >
                      {isExpanded ? "▼" : "▶"}
                    </button>
                  </div>
                  {route.route_long_name && (
                    <p className="text-xs text-gray-600 mt-1 truncate">{route.route_long_name}</p>
                  )}
                </div>

                <div className="px-3 py-2 bg-white border-t border-gray-100">
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleRoute(route.route_id)}
                      className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
                        isRouteVisible
                          ? "bg-green-600 text-white shadow-sm"
                          : "bg-gray-200 text-gray-600"
                      }`}
                    >
                      {isRouteVisible ? "🟢 Ruta ON" : "⚪ Ruta OFF"}
                    </button>
                    <button
                      onClick={() => toggleRouteStops(route.route_id)}
                      className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
                        areStopsVisible
                          ? "bg-blue-600 text-white shadow-sm"
                          : "bg-gray-200 text-gray-600"
                      }`}
                    >
                      {areStopsVisible ? "📍 Paradas ON" : "⚪ Paradas OFF"}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-3 py-2 bg-gray-50 border-t border-gray-100 max-h-64 overflow-y-auto">
                    <p className="text-xs font-semibold text-gray-600 mb-2">
                      Paradas ({stops.length})
                    </p>
                    {stops.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">Sin paradas asociadas</p>
                    ) : (
                      <div className="space-y-1">
                        {stops.map((stop, idx) => (
                          <div
                            key={stop.stop_id}
                            className="flex items-center gap-2 p-1.5 bg-white rounded hover:bg-blue-50 transition-colors"
                          >
                            <span className="text-xs font-mono text-gray-400 w-6">
                              {idx + 1}.
                            </span>
                            <span className="text-xs text-gray-700 flex-1 truncate">
                              {stop.stop_name}
                            </span>
                            <span className="text-xs text-gray-400">#{stop.stop_id}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 🌍 Mapa */}
      <div className="flex-1 relative">
        <MapContainer center={[20.97, -89.62]} zoom={12} className="h-full w-full">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />

          {/* Rutas visibles */}
          {routes.map((route) => {
            if (!routeVisibility[route.route_id]) return null;

            const coords = routeShapes[route.route_id];
            if (!coords || coords.length === 0) return null;

            return (
              <Polyline
                key={`route-${route.route_id}`}
                positions={coords}
                color={formatColor(route.route_color)}
                weight={4}
                opacity={0.7}
              >
                <Popup>
                  <div className="text-sm">
                    <strong>{route.route_short_name}</strong>
                    <br />
                    {route.route_long_name}
                    <br />
                    <span className="text-xs text-gray-500">{coords.length} puntos</span>
                  </div>
                </Popup>
              </Polyline>
            );
          })}

          {/* Paradas visibles */}
          {routes.map((route) => {
            if (!stopVisibility[route.route_id]) return null;

            const stops = getStopsForRoute(route.route_id);
            return stops.map((stop) => (
              <Marker
                key={`${route.route_id}-${stop.stop_id}`}
                position={[Number(stop.stop_lat), Number(stop.stop_lon)]}
                icon={defaultIcon}
              >
                <Popup>
                  <div className="text-sm">
                    <strong>{stop.stop_name}</strong>
                    <br />
                    <span className="text-xs text-gray-600">
                      Ruta: {route.route_short_name}
                    </span>
                    <br />
                    <span className="text-xs text-gray-500">ID: {stop.stop_id}</span>
                  </div>
                </Popup>
              </Marker>
            ));
          })}
        </MapContainer>
      </div>
    </div>
  );
}
