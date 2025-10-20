import { useState } from "react";
import Sidebar from "./components/Sidebar";
import TableViewer from "./components/TableViewer";
import MapView from "./components/MapView";
import UploadGTFS from "./components/UploadGTFS";


export default function App() {
  const [view, setView] = useState("tables");

  return (
    <div className="flex h-screen">
      <Sidebar onSelect={setView} />
      import UploadGTFS from "./components/UploadGTFS";

<main className="flex-1 overflow-auto bg-gray-50">
  {view === "tables" && <TableViewer />}
  {view === "network" && <MapView />}
  {view === "upload" && <UploadGTFS />}  {/* nueva vista */}
</main>

    </div>
  );
}
