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
      // TableViewer puede ocupar la altura disponible; aseguramos que su contenedor pueda scrollear
      return (
        <div className="p-6 min-h-0">
          <TableViewer key={activeView} table={activeView} />
        </div>
      );
    }

    // Revisa las vistas especiales
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
          // no usar h-full aquí: usar min-h-0 para permitir que el contenedor padre controle el scroll
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

      // Programación
      case "sched_params":
        return (
          <div className="p-6 min-h-0">
            <SchedulingParameters />
          </div>
        );
      case "sched_sheet":
        return (
          <div className="p-6 min-h-0">
            <SchedulingSheet />
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

      // ✅ Timetables
      case "timetables":
        return (
          <div className="p-6 min-h-0">
            <TimetableGenerator />
          </div>
        );

      // Vista por defecto
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
    // Layout principal: aside fijo + main flexible
    <div className="flex h-screen bg-gray-100">
      <Sidebar
        setActiveView={setActiveView}
        activeView={activeView}
        gtfsTables={availableTables}
      />

      {/*
        main: debe permitir scroll cuando el contenido excede la altura del viewport.
        - overflow-auto permite scroll sólo si es necesario
        - min-h-0 es crítico dentro de un contenedor flex para que el overflow funcione correctamente
      */}
      <main className="flex-1 flex flex-col overflow-auto min-h-0">
        {renderView()}
      </main>
    </div>
  );
}

export default App;
