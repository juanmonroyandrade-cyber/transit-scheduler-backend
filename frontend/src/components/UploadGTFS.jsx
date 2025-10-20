// src/components/UploadGTFS.jsx
import { useState } from "react";

export default function UploadGTFS() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [agencyName, setAgencyName] = useState(""); // Opcional: para el nombre de la agencia

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setStatus("");
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus("⚠️ Por favor selecciona un archivo .zip");
      return;
    }

    const formData = new FormData();
    // ✅ CAMBIO 1: El nombre del campo ahora es "file" para que coincida con /gtfs/import
    formData.append("file", file);
    
    // Si el nombre de la agencia no está vacío, lo añadimos
    if (agencyName) {
      formData.append("agency_name", agencyName);
    }

    setLoading(true);
    setStatus("Cargando y procesando archivo...");

    try {
      // ✅ CAMBIO 2: Apuntamos al endpoint /gtfs/import
      const res = await fetch("http://localhost:8000/gtfs/import", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setStatus(`✅ Archivo cargado correctamente: ${JSON.stringify(data.imported)}`);
      } else {
        setStatus(`❌ Error al cargar archivo: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      setStatus("❌ Error de conexión. Asegúrate de que el servidor backend esté funcionando en http://localhost:8000");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Cargar Archivo GTFS</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Nombre de la Agencia (Opcional)
        </label>
        <input
          type="text"
          value={agencyName}
          onChange={(e) => setAgencyName(e.target.value)}
          placeholder="Ej: Mi Agencia de Transporte"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Archivo GTFS (.zip)
        </label>
        <input
          type="file"
          accept=".zip"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
      </div>


      <button
        onClick={handleUpload}
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Cargando..." : "Subir y Procesar"}
      </button>

      {status && (
        <div className="mt-4 p-3 rounded-md bg-gray-50">
            <p className="text-sm text-gray-700 whitespace-pre-wrap break-words">{status}</p>
        </div>
      )}
    </div>
  );
}
