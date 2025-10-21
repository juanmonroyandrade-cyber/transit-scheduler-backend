// ✅ Recibe gtfsTables como prop desde App.jsx
export default function Sidebar({ setActiveView, activeView, gtfsTables }) {

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
        {/* Principal */}
        <div>
          <h3 className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Principal</h3>
          <a href="#" onClick={() => setActiveView("upload")} className={getLinkClass("upload")}>Cargar GTFS</a>
          <a href="#" onClick={() => setActiveView("map")} className={getLinkClass("map")}>Visualizador de Mapa</a>
        </div>
        {/* Editor GTFS */}
        <div className="flex-grow overflow-y-auto"> {/* Permite scroll si hay muchas tablas */}
          <h3 className="px-4 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">Editor GTFS</h3>
          {/* Ordena alfabéticamente */}
          {[...gtfsTables].sort().map((table) => ( 
            <a key={table} href="#" onClick={() => setActiveView(table)} className={getLinkClass(table)}>
              {table.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </a>
          ))}
        </div>
      </nav>
      {/* Footer */}
      <div className="mt-auto pt-4 border-t border-gray-200">
          <p className="text-xs text-center text-gray-400">Versión 1.2</p>
      </div>
    </aside>
  );
}
