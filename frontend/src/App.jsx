// frontend/src/App.jsx

import { useState } from "react";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import TableViewer from "./components/TableViewer";
import UploadGTFS from "./components/UploadGTFS";

function App() {
  // ✅ CAMBIO: La vista inicial ahora es "routes" para ir directo a la tabla de rutas.
  const [activeView, setActiveView] = useState("routes");

  const renderView = () => {
    switch (activeView) {
      case "map":
        return <MapView />;
      case "upload":
        return (
          <div className="p-8 bg-gray-100 h-full">
            <UploadGTFS />
          </div>
        );
      case "routes":
        return <TableViewer table="routes" />;
      case "stops":
        return <TableViewer table="stops" />;
      case "agencies":
        return <TableViewer table="agencies" />;
      case "calendar":
        return <TableViewer table="calendar" />;
      case "trips":
        return <TableViewer table="trips" />;
      case "feed_info":
        return <TableViewer table="feed_info" />;
      default:
        return (
            <div className="p-8 bg-gray-100 h-full">
                <h1 className="text-2xl font-bold">Bienvenido</h1>
                <p>Selecciona una opción del menú lateral para comenzar.</p>
            </div>
        );
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar setActiveView={setActiveView} activeView={activeView} />
      <main className="flex-1 flex flex-col overflow-hidden">
        {renderView()}
      </main>
    </div>
  );
}

export default App;