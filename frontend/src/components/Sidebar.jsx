// frontend/src/components/Sidebar.jsx

export default function Sidebar({ setActiveView, activeView, gtfsTables = [] }) {

  const getLinkClass = (view) =>
    `block px-4 py-2 text-sm rounded-md transition-colors duration-150 ${
      activeView === view
        ? "bg-blue-600 text-white font-semibold"
        : "text-gray-700 hover:bg-gray-200 hover:text-gray-900"
    }`;

  return (
    <aside className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col shadow-sm">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Transit Scheduler</h1>
      <nav className="flex flex-col space-y-4">
        
        {/* Sección Principal */}
        <div>
          <h3 className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Principal</h3>
          <a href="#" onClick={() => setActiveView("upload")} className={getLinkClass("upload")}>Cargar GTFS</a>
          <a href="#" onClick={() => setActiveView("map")} className={getLinkClass("map")}>Visualizador de Mapa</a>
          <a href="#" onClick={() => setActiveView("create_route_kml")} className={getLinkClass("create_route_kml")}>Crear Ruta KML</a>
          <a href="#" onClick={() => setActiveView("upload_stops_csv")} className={getLinkClass("upload_stops_csv")}>Cargar Paradas CSV</a>
          <a href="#" onClick={() => setActiveView("export_gtfs")} className={getLinkClass("export_gtfs")}>Exportar GTFS</a>
        </div>

        {/* ✅ Nueva Sección: Programación de Rutas */}
        <div>
          <h3 className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Programación</h3>
          <a href="#" onClick={() => setActiveView("sched_params")} className={getLinkClass("sched_params")}>
            Parámetros
          </a>
          <a href="#" onClick={() => setActiveView("sched_sheet")} className={getLinkClass("sched_sheet")}>
            Sábana de Programación
          </a>
          <a href="#" onClick={() => setActiveView("sched_gantt")} className={getLinkClass("sched_gantt")}>
            Gráfica de Gantt
          </a>
           <a href="#" onClick={() => setActiveView("sched_line_graph")} className={getLinkClass("sched_line_graph")}>
            Gráfica Punto a Punto
          </a>
        </div>

        {/* Editor GTFS */}
        <div className="flex-grow overflow-y-auto">
          <h3 className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Editor GTFS</h3>
          {[...gtfsTables].sort().map((table) => (
            <a key={table} href="#" onClick={() => setActiveView(table)} className={getLinkClass(table)}>
              {table.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </a>
          ))}
        </div>
        
      </nav>
      {/* Footer */}
      <div className="mt-auto pt-4 border-t border-gray-200">
          <p className="text-xs text-center text-gray-400">Versión 1.6</p>
      </div>
    </aside>
  );
}