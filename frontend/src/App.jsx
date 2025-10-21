import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import TableViewer from "./components/TableViewer";
import UploadGTFS from "./components/UploadGTFS";
import CreateRouteFromKML from "./components/CreateRouteFromKML";
import UploadStopsCSV from "./components/UploadStopsCSV";
import ExportGTFS from "./components/ExportGTFS"; // ✅ 1. Importa el nuevo componente

const GTFS_TABLES = [
  "agencies", "calendar", "fare_attributes", "fare_rules",
  "feed_info", "routes", "shapes", "stops", "stop_times", "trips",
];

function App() {
  const [activeView, setActiveView] = useState("upload");
  const [availableTables, setAvailableTables] = useState([]);

   // Cargar tablas (sin cambios)
   useEffect(() => {
        const fetchTables = async () => {
            try {
                const res = await fetch('http://localhost:8000/admin/tables');
                if (res.ok) {
                    const tables = await res.json();
                    setAvailableTables(tables);
                } else { setAvailableTables(GTFS_TABLES); }
            } catch (error) { setAvailableTables(GTFS_TABLES); }
        };
        fetchTables();
   }, []);

  const renderView = () => {
    console.log(`[App] Renderizando vista: ${activeView}`);

    if (availableTables.includes(activeView)) {
      return <TableViewer key={activeView} table={activeView} />;
    }

    switch (activeView) {
      case "map": return <MapView />;
      case "upload": return ( <div className="p-8 bg-gray-100 h-full"><UploadGTFS /></div> );
      case "create_route_kml": return <CreateRouteFromKML />;
      case "upload_stops_csv": return <UploadStopsCSV />;
      case "export_gtfs": return <ExportGTFS />; // ✅ 2. Añade el caso para el componente
      default:
         return ( <div className="p-8 bg-gray-100 h-full flex items-center justify-center"><div className="text-center"><h1 className="text-2xl font-bold mb-2">Bienvenido</h1><p className="text-gray-600">Selecciona una opción del menú.</p></div></div> );
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar setActiveView={setActiveView} activeView={activeView} gtfsTables={availableTables} />
      <main className="flex-1 flex flex-col overflow-hidden">
        {renderView()}
      </main>
    </div>
  );
}

export default App;