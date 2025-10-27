import React, { useState, useEffect } from 'react';

export default function TripsManager() {
  const [routes, setRoutes] = useState([]);
  const [services, setServices] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [tripCount, setTripCount] = useState(null);
  const [tripsFile, setTripsFile] = useState(null);
  const [stoptimesFile, setStoptimesFile] = useState(null);
  const [interpolate, setInterpolate] = useState(true);
  const [calculateDistances, setCalculateDistances] = useState(true);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('delete');

  // Cargar rutas al montar
  useEffect(() => {
    fetchRoutes();
  }, []);

  // Cargar servicios cuando cambia la ruta
  useEffect(() => {
    if (selectedRoute) {
      fetchServices(selectedRoute);
    }
  }, [selectedRoute]);

  // Contar trips cuando cambian los filtros
  useEffect(() => {
    if (selectedRoute) {
      countTrips();
    }
  }, [selectedRoute, selectedService]);

  const fetchRoutes = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/routes');
      if (res.ok) {
        const data = await res.json();
        setRoutes(data);
      }
    } catch (err) {
      console.error('Error cargando rutas:', err);
    }
  };

  const fetchServices = async (routeId) => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/available_services/?route_id=${encodeURIComponent(routeId)}`
      );
      if (res.ok) {
        const data = await res.json();
        setServices(data);
      }
    } catch (err) {
      console.error('Error cargando servicios:', err);
      setServices([]);
    }
  };

  const countTrips = async () => {
    try {
      const params = new URLSearchParams({ route_id: selectedRoute });
      if (selectedService) {
        params.append('service_id', selectedService);
      }

      const res = await fetch(`http://localhost:8000/bulk/count-trips?${params}`);
      if (res.ok) {
        const data = await res.json();
        setTripCount(data);
      }
    } catch (err) {
      console.error('Error contando trips:', err);
      setTripCount(null);
    }
  };

  const handleDelete = async () => {
    if (!selectedRoute) {
      setStatus({ message: 'Selecciona una ruta', type: 'error' });
      return;
    }

    const confirmMsg = selectedService
      ? `¿Eliminar ${tripCount?.trips_count || 0} trips y ${tripCount?.stop_times_count || 0} stop_times de la ruta ${selectedRoute} con servicio ${selectedService}?`
      : `¿Eliminar TODOS los ${tripCount?.trips_count || 0} trips y ${tripCount?.stop_times_count || 0} stop_times de la ruta ${selectedRoute}?`;

    if (!window.confirm(confirmMsg)) {
      return;
    }

    setLoading(true);
    setStatus({ message: 'Eliminando...', type: 'loading' });

    try {
      const params = new URLSearchParams({ route_id: selectedRoute });
      if (selectedService) {
        params.append('service_id', selectedService);
      }

      const res = await fetch(
        `http://localhost:8000/bulk/delete-trips-and-stoptimes?${params}`,
        { method: 'DELETE' }
      );

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.detail || 'Error al eliminar');
      }

      setStatus({
        message: `✅ Eliminados ${result.trips_deleted} trips y ${result.stop_times_deleted} stop_times`,
        type: 'success'
      });

      await countTrips();

    } catch (err) {
      console.error('Error al eliminar:', err);
      setStatus({ message: `❌ Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e, fileType) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const fileName = selectedFile.name.toLowerCase();
      if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
        if (fileType === 'trips') {
          setTripsFile(selectedFile);
        } else {
          setStoptimesFile(selectedFile);
        }
        setStatus({ message: '', type: '' });
      } else {
        if (fileType === 'trips') {
          setTripsFile(null);
        } else {
          setStoptimesFile(null);
        }
        setStatus({ message: 'Solo se permiten archivos Excel (.xlsx, .xls)', type: 'warning' });
      }
    }
  };

  const handleUpload = async () => {
    if (!tripsFile || !stoptimesFile) {
      setStatus({ message: 'Debes seleccionar ambos archivos (trips y stop_times)', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ message: 'Procesando archivos...', type: 'loading' });

    try {
      const formData = new FormData();
      formData.append('trips_file', tripsFile, tripsFile.name);
      formData.append('stoptimes_file', stoptimesFile, stoptimesFile.name);
      formData.append('interpolate_times', interpolate.toString());
      formData.append('calculate_distances', calculateDistances.toString());

      const res = await fetch('http://localhost:8000/bulk/upload-trips-stoptimes', {
        method: 'POST',
        body: formData
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.detail || 'Error al procesar archivos');
      }

      setStatus({
        message: `✅ Importados ${result.trips_imported} trips y ${result.stop_times_imported} stop_times. ${
          result.interpolated ? 'Tiempos interpolados. ' : ''
        }${result.distances_calculated ? 'Distancias calculadas.' : ''}`,
        type: 'success'
      });

      setTripsFile(null);
      setStoptimesFile(null);
      document.getElementById('trips-file-input').value = '';
      document.getElementById('stoptimes-file-input').value = '';

    } catch (err) {
      console.error('Error al cargar archivos:', err);
      setStatus({ message: `❌ Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = () => {
    const template = `ARCHIVO 1: TRIPS
Columnas requeridas (pueden estar en CUALQUIER ORDEN):
route_id, service_id, trip_id, trip_headsign, direction_id, block_id, shape_id, wheelchair_accessible, bikes_allowed

Ejemplo:
trip_id,route_id,service_id,direction_id,block_id,shape_id,trip_headsign,wheelchair_accessible,bikes_allowed
trip_001,1,WD,0,block_1,1.1,Centro,1,1

---

ARCHIVO 2: STOP_TIMES
Columnas requeridas (pueden estar en CUALQUIER ORDEN):
trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_headsign, pickup_type, drop_off_type, continuous_pickup, continuous_drop_off, shape_dist_traveled, timepoint

Ejemplo (solo primera y última parada con tiempos):
trip_id,stop_id,stop_sequence,arrival_time,departure_time,timepoint,stop_headsign,pickup_type,drop_off_type,continuous_pickup,continuous_drop_off,shape_dist_traveled
trip_001,1,1,06:00:00,06:00:00,1,,,,,,,
trip_001,2,2,,,,,,,,,,,
trip_001,3,3,,,,,,,,,,,
trip_001,4,4,06:45:00,06:45:00,1,,,,,,,

NOTAS:
- El ORDEN de las columnas NO importa, solo que los NOMBRES sean exactos
- Para interpolación: Solo llena tiempos en primera y última parada
- Para distancias: Deja shape_dist_traveled vacío
- Columnas opcionales pueden estar vacías`;

    const blob = new Blob([template], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'template_trips_stoptimes.txt';
    link.click();
  };

  const inputClass = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm";
  const labelClass = "block text-sm font-medium text-gray-700";

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">
          🚌 Gestor de Trips y Stop Times
        </h1>

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="flex space-x-4">
            <button
              onClick={() => setActiveTab('delete')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'delete'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🗑️ Eliminar Trips
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'upload'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📥 Cargar desde Excel
            </button>
          </nav>
        </div>

        {/* Mensajes de estado */}
        {status.message && (
          <div className={`p-4 mb-6 rounded-md border ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
            status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' :
            status.type === 'warning' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
            'bg-blue-100 text-blue-800 border-blue-200'
          }`}>
            {status.message}
          </div>
        )}

        {/* TAB: ELIMINAR */}
        {activeTab === 'delete' && (
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">
              Eliminar Trips y Stop Times
            </h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className={labelClass}>Ruta *</label>
                <select
                  value={selectedRoute}
                  onChange={(e) => {
                    setSelectedRoute(e.target.value);
                    setSelectedService('');
                  }}
                  className={inputClass}
                >
                  <option value="">Selecciona una ruta</option>
                  {routes.map(route => (
                    <option key={route.route_id} value={route.route_id}>
                      {route.route_short_name} - {route.route_long_name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedRoute && (
                <div>
                  <label className={labelClass}>
                    Servicio/Periodicidad (opcional)
                  </label>
                  <select
                    value={selectedService}
                    onChange={(e) => setSelectedService(e.target.value)}
                    className={inputClass}
                  >
                    <option value="">TODOS los servicios</option>
                    {services.map(service => (
                      <option key={service.service_id} value={service.service_id}>
                        {service.service_id} - {service.days}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Si no seleccionas un servicio, se eliminarán TODOS los trips de la ruta
                  </p>
                </div>
              )}
            </div>

            {tripCount && selectedRoute && (
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-md mb-6">
                <h3 className="font-semibold text-yellow-800 mb-2">
                  ⚠️ Registros que serán eliminados:
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Trips:</span>
                    <span className="ml-2 font-bold text-yellow-800">
                      {tripCount.trips_count}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Stop Times:</span>
                    <span className="ml-2 font-bold text-yellow-800">
                      {tripCount.stop_times_count}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={handleDelete}
                disabled={loading || !selectedRoute || !tripCount || tripCount.trips_count === 0}
                className="px-6 py-3 bg-red-600 text-white font-semibold rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
              >
                {loading ? 'Eliminando...' : '🗑️ Eliminar Trips y Stop Times'}
              </button>
            </div>
          </div>
        )}

        {/* TAB: CARGAR */}
        {activeTab === 'upload' && (
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-700">
                Cargar Trips y Stop Times desde Excel
              </h2>
              <button
                onClick={downloadTemplate}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                📄 Ver formato requerido
              </button>
            </div>

            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md text-sm">
              <p className="font-semibold text-blue-800 mb-2">
                ✨ Mapeo flexible por nombre de columna:
              </p>
              <ul className="list-disc list-inside space-y-1 text-blue-700">
                <li>El <strong>ORDEN de las columnas NO importa</strong></li>
                <li>Solo importa que los <strong>NOMBRES sean exactos</strong></li>
                <li>El sistema reorganiza automáticamente al formato GTFS</li>
              </ul>
              <p className="mt-2 text-xs text-blue-600 border-t border-blue-300 pt-2">
                💡 <strong>Para interpolación:</strong> Solo proporciona tiempos en primera y última parada<br />
                💡 <strong>Para distancias:</strong> Deja shape_dist_traveled vacío
              </p>
            </div>

            <div className="space-y-4 mb-6">
              {/* Archivo TRIPS */}
              <div className="border-2 border-gray-200 rounded-lg p-4 bg-gray-50">
                <label className={labelClass + " mb-2"}>
                  1️⃣ Archivo de TRIPS (.xlsx, .xls) *
                </label>
                <input
                  id="trips-file-input"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => handleFileChange(e, 'trips')}
                  disabled={loading}
                  className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer disabled:opacity-50"
                />
                {tripsFile && (
                  <p className="text-xs text-gray-600 mt-2 bg-white p-2 rounded border border-gray-300">
                    ✅ {tripsFile.name} ({(tripsFile.size / 1024).toFixed(2)} KB)
                  </p>
                )}
              </div>

              {/* Archivo STOP_TIMES */}
              <div className="border-2 border-gray-200 rounded-lg p-4 bg-gray-50">
                <label className={labelClass + " mb-2"}>
                  2️⃣ Archivo de STOP_TIMES (.xlsx, .xls) *
                </label>
                <input
                  id="stoptimes-file-input"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => handleFileChange(e, 'stoptimes')}
                  disabled={loading}
                  className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100 cursor-pointer disabled:opacity-50"
                />
                {stoptimesFile && (
                  <p className="text-xs text-gray-600 mt-2 bg-white p-2 rounded border border-gray-300">
                    ✅ {stoptimesFile.name} ({(stoptimesFile.size / 1024).toFixed(2)} KB)
                  </p>
                )}
              </div>

              {/* Opciones */}
              <div className="space-y-2 border-t-2 border-gray-200 pt-4">
                <label className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={interpolate}
                    onChange={(e) => setInterpolate(e.target.checked)}
                    disabled={loading}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                  />
                  <span className="text-gray-700">
                    ⏱️ <strong>Interpolar tiempos intermedios</strong>
                  </span>
                </label>

                <label className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={calculateDistances}
                    onChange={(e) => setCalculateDistances(e.target.checked)}
                    disabled={loading}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                  />
                  <span className="text-gray-700">
                    📏 <strong>Calcular shape_dist_traveled automáticamente</strong>
                  </span>
                </label>
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setTripsFile(null);
                  setStoptimesFile(null);
                  setStatus({ message: '', type: '' });
                  document.getElementById('trips-file-input').value = '';
                  document.getElementById('stoptimes-file-input').value = '';
                }}
                disabled={loading || (!tripsFile && !stoptimesFile)}
                className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Limpiar
              </button>
              <button
                onClick={handleUpload}
                disabled={loading || !tripsFile || !stoptimesFile}
                className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
              >
                {loading ? '⏳ Procesando...' : '🚀 Cargar y Procesar'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}