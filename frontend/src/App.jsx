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
import SchedulingParameters from "./components/scheduling/SchedulingParameters";
import SchedulingSheet from "./components/scheduling/SchedulingSheet";
import GanttChart from "./components/scheduling/GanttChart";
import PointToPointGraph from "./components/scheduling/PointToPointGraph";

// ✅ Componente de Timetables
import TimetableGenerator from "./components/timetables/TimetableGenerator";

const GTFS_TABLES = [
  "agencies", "calendar", "fare_attributes", "fare_rules",
  "feed_info", "routes", "shapes", "stops", "stop_times", "trips",
];

function App() {
  const [activeView, setActiveView] = useState("upload");
  const [availableTables, setAvailableTables] = useState([]);

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const res = await fetch('http://localhost:8000/admin/tables');
        if (res.ok) {
          const tables = await res.json();
          setAvailableTables(tables);
        } else {
          setAvailableTables(GTFS_TABLES);
        }
      } catch (error) {
        setAvailableTables(GTFS_TABLES);
      }
    };
    fetchTables();
  }, []);

  const renderView = () => {
    console.log(`[App] Renderizando vista: ${activeView}`);

    // Revisa si es una tabla GTFS
    if (availableTables.includes(activeView)) {
      return <TableViewer key={activeView} table={activeView} />;
    }

    // Revisa las vistas especiales
    switch (activeView) {
      // Principal
      case "trips_manager":
  return <TripsManager />;
      case "map":
        return <MapView />;
      case "upload":
        return (
          <div className="p-8 bg-gray-100 h-full">
            <UploadGTFS />
          </div>
        );
      case "create_route_kml":
        return <CreateRouteFromKML />;
      case "upload_stops_csv":
        return <UploadStopsCSV />;
      case "export_gtfs":
        return <ExportGTFS />;
      
      // Programación
      case "sched_params":
        return <SchedulingParameters />;
      case "sched_sheet":
        return <SchedulingSheet />;
      case "sched_gantt":
        return <GanttChart />;
      case "sched_line_graph":
        return <PointToPointGraph />;

      // ✅ Timetables
      case "timetables":
        return <TimetableGenerator />;

      // Vista por defecto
      default:
        return (
          <div className="p-8 bg-gray-100 h-full flex items-center justify-center">
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
        setActiveView={setActiveView}
        activeView={activeView}
        gtfsTables={availableTables}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        {renderView()}
      </main>
    </div>
  );
}

// Agregar en App.jsx o crear un nuevo componente
<input type="file" onChange={async (e) => {
  const file = e.target.files[0];
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch('http://localhost:8000/excel/upload-base-excel', {
    method: 'POST',
    body: formData
  });
  
  const result = await res.json();
  console.log(result);
}} />

export default App;