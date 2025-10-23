import React, { useState } from 'react';

export default function UploadStopsCSV() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(true);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    if (selectedFile) {
      const fileName = selectedFile.name.toLowerCase();
      
      // Validar que sea CSV o XLSX
      if (fileName.endsWith('.csv') || fileName.endsWith('.xlsx')) {
        setFile(selectedFile);
        setStatus({ message: '', type: '' });
        console.log('Archivo seleccionado:', selectedFile.name, 'Tamaño:', selectedFile.size);
      } else {
        setFile(null);
        setStatus({ 
          message: 'Por favor selecciona un archivo .csv o .xlsx válido.', 
          type: 'warning' 
        });
      }
    }
    
    // NO limpiar el input aquí para permitir ver el archivo seleccionado
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus({ message: '⚠️ Selecciona un archivo primero.', type: 'warning' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file, file.name); // Importante: incluir el nombre del archivo
    formData.append('replace_existing', replaceExisting.toString());

    setLoading(true);
    setStatus({ message: 'Subiendo y procesando archivo...', type: 'loading' });

    try {
      console.log('Enviando archivo:', file.name, 'al servidor');
      
      const res = await fetch('http://localhost:8000/csv/import', {
        method: 'POST',
        body: formData,
        // NO agregar headers de Content-Type, FormData lo maneja automáticamente
      });

      console.log('Respuesta recibida, status:', res.status);
      
      const result = await res.json();
      console.log('Datos recibidos:', result);

      if (!res.ok) {
        throw new Error(result.detail || result.error || `Error ${res.status}: ${res.statusText || 'Error del servidor'}`);
      }

      if (result.success) {
        const fileType = result.file_type ? result.file_type.toUpperCase() : 'archivo';
        setStatus({
          message: `✅ ${fileType} procesado exitosamente! Insertadas: ${result.stops_inserted ?? 0}, Actualizadas: ${result.stops_updated ?? 0}, Omitidas: ${result.stops_skipped ?? 0}`,
          type: 'success',
        });
        
        // Limpiar el input y el estado del archivo
        setFile(null);
        document.getElementById('csv-file-input').value = '';
      } else {
        throw new Error(result.error || 'Error al procesar el archivo');
      }

    } catch (err) {
      console.error("Error al subir archivo:", err);
      setStatus({ message: `❌ Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 bg-gray-100 h-full">
      <div className="bg-white p-6 rounded-lg shadow-md max-w-xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">📍 Cargar Paradas desde CSV/XLSX</h1>

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

        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
          <p className="font-semibold">ℹ️ Formatos soportados:</p>
          <ul className="list-disc list-inside mt-1">
            <li>CSV con codificación UTF-8 (con o sin BOM)</li>
            <li>Excel (.xlsx)</li>
          </ul>
        </div>

        <div className="mb-4">
          <label htmlFor="csv-file-input" className="block text-sm font-medium text-gray-700 mb-2">
            Selecciona el archivo:
          </label>
          <input
            id="csv-file-input"
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileChange}
            disabled={loading}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {file && (
            <p className="text-xs text-gray-600 mt-2 bg-gray-50 p-2 rounded">
              📄 Archivo seleccionado: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
            </p>
          )}
        </div>

        <div className="mb-4">
          <label className="flex items-center space-x-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={replaceExisting}
              onChange={(e) => setReplaceExisting(e.target.checked)}
              disabled={loading}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span>Reemplazar paradas existentes (actualizar si ya existen)</span>
          </label>
        </div>

        <div className="mb-6 p-3 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-700">
          <p className="font-semibold mb-2">Formato esperado del archivo:</p>
          <p className="mb-1">Columnas requeridas:</p>
          <div className="flex flex-wrap gap-2 mb-2">
            <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">stop_id</code>
            <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">stop_name</code>
            <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">stop_lat</code>
            <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">stop_lon</code>
            <code className="bg-gray-200 px-2 py-0.5 rounded text-xs">wheelchair_boarding</code>
          </div>
          <p className="text-xs text-gray-600">
            💡 Las paradas con <code className="bg-gray-200 px-1 rounded">stop_id</code> existente serán actualizadas o ignoradas según la opción seleccionada.
          </p>
        </div>

        <div className="flex justify-end space-x-3">
          <button
            onClick={() => {
              setFile(null);
              setStatus({ message: '', type: '' });
              document.getElementById('csv-file-input').value = '';
            }}
            disabled={loading || !file}
            className="px-6 py-2 bg-gray-200 text-gray-700 font-semibold rounded-md shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancelar
          </button>
          
          <button
            onClick={handleUpload}
            disabled={loading || !file}
            className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '⏳ Procesando...' : '🚀 Subir y Procesar'}
          </button>
        </div>
      </div>
    </div>
  );
}