import React, { useState } from 'react';

export default function UploadStopsCSV() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'text/csv') {
      setFile(selectedFile);
      setStatus({ message: '', type: '' });
    } else {
      setFile(null);
      setStatus({ message: 'Por favor selecciona un archivo .csv válido.', type: 'warning' });
    }
    e.target.value = null; // Permite reseleccionar el mismo archivo
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus({ message: '⚠️ Selecciona un archivo .csv primero.', type: 'warning' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    // Podrías añadir opciones como replace_existing si tu backend lo soporta
    // formData.append('replace_existing', true); // Ejemplo

    setLoading(true);
    setStatus({ message: 'Subiendo y procesando CSV...', type: 'loading' });

    try {
      // ✅ *** CORRECCIÓN AQUÍ: URL ajustada a /csv/import ***
      const res = await fetch('http://localhost:8000/csv/import', {
        method: 'POST',
        body: formData,
      });

      const result = await res.json();

      if (!res.ok) {
        // Muestra el detalle del error del backend si existe
        throw new Error(result.detail || `Error ${res.status}: ${res.statusText || 'Error del servidor'}`);
      }

      // Asume que el backend devuelve 'created' y 'updated' como en el HTML de ejemplo
      // Ajusta las claves ('stops_inserted', 'stops_updated') si son diferentes
      setStatus({
        message: `✅ Archivo procesado! Creadas: ${result.stops_inserted ?? result.created ?? 0}, Actualizadas: ${result.stops_updated ?? result.updated ?? 0}. Omitidas: ${result.stops_skipped ?? 0}`,
        type: 'success',
      });
      setFile(null); // Limpia selección

    } catch (err) {
      console.error("Error al subir CSV de paradas:", err);
      setStatus({ message: `❌ Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // --- Renderizado (sin cambios estructurales) ---
  return (
    <div className="p-8 bg-gray-100 h-full">
      <div className="bg-white p-6 rounded-lg shadow-md max-w-xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Cargar Paradas desde CSV</h1>

        {status.message && (
          <div className={`p-3 mb-4 rounded-md text-sm border ${
              status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
              status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' :
              status.type === 'warning' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
              'bg-blue-100 text-blue-800 border-blue-200 animate-pulse'
          }`}>
            {status.message}
          </div>
        )}

        <div className="mb-4">
          <label htmlFor="csv-file-input" className="block text-sm font-medium text-gray-700 mb-2">
            Selecciona el archivo CSV:
          </label>
          <input
            id="csv-file-input"
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
          />
          {file && <p className="text-xs text-gray-500 mt-1">Archivo: {file.name}</p>}
        </div>

        <div className="mb-6 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
          <p className="font-semibold">Formato esperado:</p>
          <p>Columnas: <code className="bg-blue-100 px-1 rounded">stop_id</code>, <code className="bg-blue-100 px-1 rounded">stop_name</code>, <code className="bg-blue-100 px-1 rounded">stop_lat</code>, <code className="bg-blue-100 px-1 rounded">stop_lon</code>, <code className="bg-blue-100 px-1 rounded">wheelchair_boarding</code> (opcional).</p>
          <p className="mt-1"><code className="bg-blue-100 px-1 rounded">stop_id</code> existentes serán **actualizadas**.</p>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleUpload}
            disabled={loading || !file}
            className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Procesando...' : 'Subir y Procesar'}
          </button>
        </div>
      </div>
    </div>
  );
}