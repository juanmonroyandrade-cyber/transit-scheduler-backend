// frontend/src/components/Sidebar.jsx

export default function Sidebar({ setActiveView, activeView }) {
  // ✅ Lista completa y en orden de todas las tablas GTFS.
  const gtfsTables = [
    "agencies",
    "routes",
    "trips",
    "stops",
    "stop_times",
    "calendar",
    "fare_attributes",
    "fare_rules",
    "shapes",
    "feed_info",
  ];

  const handleViewChange = (view) => {
    setActiveView(view);
  };

  const getLinkClass = (view) => 
    `block px-4 py-2 text-sm rounded-md ${
      activeView === view
        ? "bg-blue-600 text-white"
        : "text-gray-700 hover:bg-gray-200"
    }`;

  return (
    <aside className="w-64 bg-white border-r p-4 flex flex-col">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Transit Scheduler</h1>
      <nav className="flex flex-col space-y-2">
        <div>
          <h3 className="px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Principal</h3>
          <a href="#" onClick={() => handleViewChange("upload")} className={getLinkClass("upload")}>
            Cargar GTFS
          </a>
          <a href="#" onClick={() => handleViewChange("map")} className={getLinkClass("map")}>
            Visualizador de Mapa
          </a>
        </div>
        <div>
          <h3 className="px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider mt-4 mb-1">Editor GTFS</h3>
          {gtfsTables.map((table) => (
            <a
              key={table}
              href="#"
              onClick={() => handleViewChange(table)}
              className={getLinkClass(table)}
            >
              {table.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </a>
          ))}
        </div>
      </nav>
      <div className="mt-auto">
        <p className="text-xs text-center text-gray-400">Versión 1.0</p>
      </div>
    </aside>
  );
}
