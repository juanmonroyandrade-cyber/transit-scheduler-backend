import { useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import TableViewer from "./components/TableViewer";
import UploadGTFS from "./components/UploadGTFS";

const GTFS_TABLES = [
  "agencies", "calendar", "fare_attributes", "fare_rules", 
  "feed_info", "routes", "shapes", "stops", "stop_times", "trips",
];

function App() {
  // Inicia en 'upload' o la tabla que prefieras ('routes'?)
  const [activeView, setActiveView] = useState("upload"); 

  const renderView = () => {
    console.log(`[App] Renderizando vista: ${activeView}`);
    
    // Si es una tabla GTFS, renderiza TableViewer
    if (GTFS_TABLES.includes(activeView)) {
      // Pasamos la tabla como 'key' también para forzar el re-montaje
      // y reseteo completo del estado al cambiar de tabla.
      return <TableViewer key={activeView} table={activeView} />;
    }
    
    // Vistas especiales
    switch (activeView) {
      case "map":
        return <MapView />;
      case "upload":
        return (
          <div className="p-8 bg-gray-100 h-full">
            <UploadGTFS />
          </div>
        );
      // Fallback si la vista no es ninguna tabla ni especial
      default:
         // Muestra un mensaje simple o redirige, pero evita el "Selecciona..."
         return (
             <div className="p-8 bg-gray-100 h-full flex items-center justify-center">
                 <div className="text-center">
                    <h1 className="text-2xl font-bold mb-2">Vista no encontrada</h1>
                    <p className="text-gray-600">Por favor, selecciona una opción válida del menú lateral.</p>
                 </div>
             </div>
         );
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Pasamos la lista completa de tablas al Sidebar */}
      <Sidebar setActiveView={setActiveView} activeView={activeView} gtfsTables={GTFS_TABLES} />
      <main className="flex-1 flex flex-col overflow-hidden">
        {renderView()}
      </main>
    </div>
  );
}

export default App;