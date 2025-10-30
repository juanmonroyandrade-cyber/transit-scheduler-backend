import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import TableViewer from "./components/TableViewer";
import UploadGTFS from "./components/UploadGTFS";
import CreateRouteFromKML from "./components/CreateRouteFromKML";
import UploadStopsCSV from "./components/UploadStopsCSV";
import ExportGTFS from "./components/ExportGTFS";
import TripsManager from "./components/TripsManager";

// Componentes de Programación
// Asumo que 'SchedulingParameters' es tu archivo 'SchedulingParametersV3.jsx'
import SchedulingParameters from "./components/scheduling/SchedulingParameters"; 
import SchedulingSheet from "./components/scheduling/SchedulingSheet";
import GanttChart from "./components/scheduling/GanttChart";
import PointToPointGraph from "./components/scheduling/PointToPointGraph";

// Componente de Timetables
import TimetableGenerator from "./components/timetables/TimetableGenerator";

const GTFS_TABLES = [
  "agencies", "calendar", "fare_attributes", "fare_rules",
  "feed_info", "routes", "shapes", "stops", "stop_times", "trips",
];

function App() {
  // --- CORRECCIÓN: Vista inicial cambiada a "upload" ---
  const [activeView, setActiveView] = useState("upload"); 
  const [availableTables, setAvailableTables] = useState([]);

  // Estados para la integración de sábanas
  const [selectedRoute, setSelectedRoute] = useState('1'); 
  const [generatedSheet, setGeneratedSheet] = useState(null);
  const [currentParameters, setCurrentParameters] = useState(null); 

  useEffect(() => {
    const fetchTables = async () => {
      try {
        // --- CORRECCIÓN: URL cambiada a relativa para usar el proxy ---
        const res = await fetch('/api/admin/tables'); 
        if (res.ok) {
          const tables = await res.json();
          setAvailableTables(tables);
        } else {
          console.error("Error al cargar tablas (res.ok false), usando defaults. ¿Está el backend corriendo?");
          setAvailableTables(GTFS_TABLES);
        }
      } catch (error) {
        // Este error ("Unexpected token '<'") ocurre si el backend no responde
        console.error("Error fetching tables (catch):", error, "Esto suele pasar si el backend no responde y se recibe HTML.");
        setAvailableTables(GTFS_TABLES);
      }
    };
    fetchTables();
  }, []);

  // Handlers para la integración de sábanas
  const handleSheetGenerated = (sheetData, parameters) => {
    console.log("App.jsx: Sábana recibida, navegando a 'sched_sheet'");
    setGeneratedSheet(sheetData);
    setCurrentParameters(parameters); // Guarda los parámetros usados
    setActiveView('sched_sheet'); // Navega a la vista de la sábana
  };

  // Este es el handler que el Sidebar espera (basado en tu log de error)
  const handleViewChange = (view) => {
    if (view !== 'sched_sheet') {
      setGeneratedSheet(null); // Limpia la sábana si salimos de esa vista
    }
    setActiveView(view);
  };


  const renderView = () => {
    console.log(`[App] Renderizando vista: ${activeView}`);

    if (availableTables.includes(activeView)) {
      return (
        <div className="p-6 min-h-0">
          <TableViewer key={activeView} table={activeView} />
        </div>
      );
    }

    switch (activeView) {
      case "trips_manager":
        return (
          <div className="p-6 min-h-0">
            <TripsManager />
          </div>
        );
      case "map":
        return (
          <div className="p-6 min-h-0">
            <MapView />
          </div>
        );
      case "upload":
        return (
          <div className="p-8 bg-gray-100 min-h-0">
            <UploadGTFS />
          </div>
        );
      case "create_route_kml":
        return (
          <div className="p-6 min-h-0">
            <CreateRouteFromKML />
          </div>
        );
      case "upload_stops_csv":
        return (
          <div className="p-6 min-h-0">
            <UploadStopsCSV />
          </div>
        );
      case "export_gtfs":
        return (
          <div className="p-6 min-h-0">
            <ExportGTFS />
          </div>
        );

      // --- VISTAS DE PROGRAMACIÓN INTEGRADAS ---
      case "sched_params":
        return (
          <div className="p-6 min-h-0">
            {/* Pasamos los props que 'SchedulingParametersV3.jsx' (renombrado a SchedulingParameters) necesita
            */}
            <SchedulingParameters
              selectedRoute={selectedRoute} 
              onSheetGenerated={handleSheetGenerated}
              onViewChange={handleViewChange} // Pasamos el handler correcto
            />
          </div>
        );
      case "sched_sheet":
        return (
          <div className="p-6 min-h-0">
            {/* Pasamos la sábana generada y los parámetros 
            */}
            <SchedulingSheet
              parameters={currentParameters} // Parámetros que generaron la sábana
              selectedRoute={selectedRoute}
              generatedSheetData={generatedSheet} 
            />
          </div>
        );
      case "sched_gantt":
        return (
          <div className="p-6 min-h-0">
            <GanttChart />
          </div>
        );
      case "sched_line_graph":
        return (
          <div className="p-6 min-h-0">
            <PointToPointGraph />
          </div>
        );

      case "timetables":
        return (
          <div className="p-6 min-h-0">
            <TimetableGenerator />
          </div>
        );

      default:
        return (
          <div className="p-8 bg-gray-100 min-h-0 flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-2xl font-bold mb-2">Bienvenido</h1>
              <p className="text-gray-600">Selecciona una opción del menú.</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar
        // --- CORRECCIÓN ---
        // Pasamos 'handleViewChange' (que llama a setActiveView)
        // a la prop 'setActiveView' que tu Sidebar espera (según el log).
        setActiveView={handleViewChange} 
        activeView={activeView}
        gtfsTables={availableTables}
        
        // Props para selección de ruta
        selectedRoute={selectedRoute} 
        setSelectedRoute={setSelectedRoute}
      />

      <main className="flex-1 flex flex-col overflow-auto min-h-0">
        {renderView()}
      </main>
    </div>
  );
}

export default App;