import React, { useState } from 'react';

export default function ExportGTFS() {
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    setStatus({ message: 'Generando archivo GTFS, esto puede tardar unos segundos...', type: 'loading' });

    try {
      const res = await fetch('http://localhost:8000/export-gtfs/export-zip');

      if (!res.ok) {
        let errorDetail = `Error ${res.status}: ${res.statusText}`;
        try {
          const errData = await res.json();
          errorDetail = errData.detail || errorDetail;
        } catch (e) { /* No es JSON, usa el statusText */ }
        throw new Error(errorDetail);
      }

      // Obtiene el nombre del archivo de la cabecera (opcional pero bueno)
      const contentDisposition = res.headers.get('content-disposition');
      let filename = 'gtfs_export.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }
      
      // Obtiene los datos como un Blob (archivo binario)
      const blob = await res.blob();

      // Crea un enlace temporal en memoria para iniciar la descarga
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      
      document.body.appendChild(a);
      a.click();
      
      // Limpia el enlace temporal
      window.URL.revokeObjectURL(url);
      a.remove();
      
      setStatus({ message: `¡Exportación completada! Se ha descargado ${filename}.`, type: 'success' });

    } catch (err) {
      console.error("Error al exportar GTFS:", err);
      setStatus({ message: `❌ Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 bg-gray-100 h-full">
      <div className="bg-white p-6 rounded-lg shadow-md max-w-xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Exportar GTFS</h1>

        {/* Mensaje de Estado */}
        {status.message && (
          <div className={`p-3 mb-4 rounded-md text-sm border ${
              status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
              status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' :
              'bg-blue-100 text-blue-800 border-blue-200'
          }`}>
            {status.message}
          </div>
        )}

        <div className="mb-4">
          <p className="text-gray-700">
            Haz clic en el botón para descargar un archivo <code>.zip</code> que contiene todas las
            tablas GTFS (<code>agency.txt</code>, <code>routes.txt</code>, <code>stops.txt</code>, etc.) 
            basado en los datos actuales de la base de datos.
          </p>
        </div>

        {/* Botón de Exportar */}
        <div className="flex justify-center pt-4">
          <button
            onClick={handleExport}
            disabled={loading}
            className="px-6 py-3 bg-green-600 text-white font-semibold rounded-md shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Generando .zip...' : 'Exportar GTFS a .zip'}
          </button>
        </div>
      </div>
    </div>
  );
}