import { useState, useEffect } from "react"; // Importa useEffect si es necesario
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import TableViewer from "./components/TableViewer";
import UploadGTFS from "./components/UploadGTFS";
import CreateRouteFromKML from "./components/CreateRouteFromKML"; // ✅ Importa el nuevo componente

// Lista completa de tablas para el Sidebar y el routing
const GTFS_TABLES = [
  "agencies", "calendar", "fare_attributes", "fare_rules", 
  "feed_info", "routes", "shapes", "stops", "stop_times", "trips",
];

function App() {
  const [activeView, setActiveView] = useState("upload"); 
  const [availableTables, setAvailableTables] = useState([]); // Podríamos cargar esto dinámicamente

   // Opcional: Cargar lista de tablas desde el backend
   useEffect(() => {
        const fetchTables = async () => {
             try {
                // Asume que tienes un endpoint /admin/tables
                 const res = await fetch('http://localhost:8000/admin/tables');
                 if (res.ok) {
                     const tables = await res.json();
                     setAvailableTables(tables);
                 } else {
                     console.error("No se pudieron cargar las tablas del admin");
                     setAvailableTables(GTFS_TABLES); // Usa la lista estática como fallback
                 }
             } catch (error) {
                 console.error("Error al conectar con backend para obtener tablas:", error);
                  setAvailableTables(GTFS_TABLES); // Fallback
             }
        };
        fetchTables();
   }, []);

  const renderView = () => {
    console.log(`[App] Renderizando vista: ${activeView}`);
    
    // Si es una tabla GTFS, muestra TableViewer
    if (availableTables.includes(activeView)) {
      return <TableViewer key={activeView} table={activeView} />;
    }
    
    // Vistas especiales
    switch (activeView) {
      case "map":
        return <MapView />;
      case "upload":
        return ( <div className="p-8 bg-gray-100 h-full"> <UploadGTFS /> </div> );
      // ✅ Caso para el nuevo componente
      case "create_route_kml":
           return <CreateRouteFromKML />; 
      default:
         return ( <div className="p-8 bg-gray-100 h-full flex items-center justify-center"> <div className="text-center"> <h1 className="text-2xl font-bold mb-2">Bienvenido</h1> <p className="text-gray-600">Selecciona una opción del menú.</p> </div> </div> );
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