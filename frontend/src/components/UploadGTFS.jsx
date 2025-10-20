// src/components/UploadGTFS.jsx
import { useState } from "react";

export default function UploadGTFS() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(""); // mensaje de estado
  const [loading, setLoading] = useState(false);

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
    formData.append("gtfs_file", file);

    setLoading(true);
    setStatus("");

    try {
      const res = await fetch("http://localhost:8000/admin/upload-gtfs", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setStatus(`✅ Archivo cargado correctamente. ${JSON.stringify(data.imported)}`);
      } else {
        setStatus(`❌ Error al cargar archivo: ${data.message || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      setStatus("❌ Error al conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Cargar GTFS</h2>

      <input
        type="file"
        accept=".zip"
        onChange={handleFileChange}
        className="mb-4"
      />

      <button
        onClick={handleUpload}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Cargando..." : "Subir archivo"}
      </button>

      {status && (
        <p className="mt-4 text-sm whitespace-pre-line">{status}</p>
      )}
    </div>
  );
}
