import { useState, useEffect } from 'react';

export default function TimetableGenerator() {
  // Estados principales
  const [routes, setRoutes] = useState([]);
  const [services, setServices] = useState([]);
  const [stops, setStops] = useState([]);
  
  // Selecciones del usuario
  const [selectedRoute, setSelectedRoute] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedStops, setSelectedStops] = useState(new Set());
  const [timeRange, setTimeRange] = useState({ start: '00:00', end: '23:59' });
  
  // Datos procesados
  const [timetableData, setTimetableData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ message: '', type: '' });

  // Cargar rutas al iniciar
  useEffect(() => {
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
    fetchRoutes();
  }, []);

  // Cargar services (calendars) al iniciar
  useEffect(() => {
    const fetchServices = async () => {
      try {
        const res = await fetch('http://localhost:8000/admin/calendar');
        if (res.ok) {
          const data = await res.json();
          setServices(data);
        }
      } catch (err) {
        console.error('Error cargando servicios:', err);
      }
    };
    fetchServices();
  }, []);

  // Cargar paradas cuando se selecciona una ruta
  useEffect(() => {
    if (!selectedRoute) {
      setStops([]);
      return;
    }

    const fetchStops = async () => {
      try {
        setStatus({ message: 'Cargando paradas...', type: 'loading' });
        const res = await fetch(`http://localhost:8000/timetables/route-stops/${selectedRoute}`);
        if (res.ok) {
          const data = await res.json();
          setStops(data.stops || []);
          setStatus({ message: '', type: '' });
        }
      } catch (err) {
        console.error('Error cargando paradas:', err);
        setStatus({ message: 'Error al cargar paradas', type: 'error' });
      }
    };
    fetchStops();
  }, [selectedRoute]);

  // Manejar selección de paradas
  const toggleStop = (stopId) => {
    const newSelected = new Set(selectedStops);
    if (newSelected.has(stopId)) {
      newSelected.delete(stopId);
    } else {
      newSelected.add(stopId);
    }
    setSelectedStops(newSelected);
  };

  const selectAllStops = () => {
    setSelectedStops(new Set(stops.map(s => s.stop_id)));
  };

  const clearAllStops = () => {
    setSelectedStops(new Set());
  };

  // Generar timetable
  const generateTimetable = async () => {
    if (!selectedRoute || !selectedService || selectedStops.size === 0) {
      setStatus({ 
        message: 'Por favor selecciona ruta, servicio y al menos una parada', 
        type: 'error' 
      });
      return;
    }

    setLoading(true);
    setStatus({ message: 'Generando timetable...', type: 'loading' });

    try {
      const requestData = {
        route_id: selectedRoute,
        service_id: selectedService,
        stop_ids: Array.from(selectedStops),
        time_range: timeRange
      };

      const res = await fetch('http://localhost:8000/timetables/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Error al generar timetable');
      }

      const data = await res.json();
      setTimetableData(data);
      setStatus({ message: '✅ Timetable generado correctamente', type: 'success' });
    } catch (err) {
      console.error('Error:', err);
      setStatus({ message: `❌ ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Descargar CSV
  const downloadCSV = () => {
    if (!timetableData) return;

    // Construir CSV
    let csv = '';
    
    // Header principal
    csv += `"${timetableData.route_name}"\n`;
    csv += `"${timetableData.service_days}"\n`;
    csv += `\n`;
    
    // Headers de columnas
    const headers = ['Bus', 'Trip'];
    timetableData.selected_stops.forEach(stop => {
      headers.push(stop.stop_name);
    });
    csv += headers.map(h => `"${h}"`).join(',') + '\n';
    
    // Datos
    timetableData.trips.forEach(trip => {
      const row = [
        trip.bus_number,
        trip.trip_sequence
      ];
      
      trip.stop_times.forEach(st => {
        row.push(st.arrival_time || '');
      });
      
      csv += row.map(v => `"${v}"`).join(',') + '\n';
    });

    // Descargar
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `timetable_${selectedRoute}_${selectedService}.csv`;
    link.click();
  };

  // Obtener descripción de días del servicio
  const getServiceDays = (service) => {
    if (!service) return '';
    const days = [];
    if (service.monday) days.push('L');
    if (service.tuesday) days.push('Ma');
    if (service.wednesday) days.push('Mi');
    if (service.thursday) days.push('J');
    if (service.friday) days.push('V');
    if (service.saturday) days.push('S');
    if (service.sunday) days.push('D');
    return days.join(', ');
  };

  // Estilos
  const inputClass = "px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const sectionClass = "bg-white p-6 rounded-lg shadow-md mb-6";
  const buttonClass = "px-4 py-2 rounded-md font-medium transition-colors";

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">🕐 Generador de Timetables</h1>
          <p className="text-gray-600">Genera horarios personalizados en formato HTML y CSV</p>
        </div>

        {/* Status */}
        {status.message && (
          <div className={`p-4 mb-6 rounded-md ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
            status.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
            'bg-blue-100 text-blue-800 border border-blue-200'
          }`}>
            {status.message}
          </div>
        )}

        {/* Paso 1: Selección de Ruta y Servicio */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold mb-4 text-gray-700">
            📍 Paso 1: Seleccionar Ruta y Servicio
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Ruta</label>
              <select
                value={selectedRoute}
                onChange={(e) => setSelectedRoute(e.target.value)}
                className={inputClass + ' w-full'}
              >
                <option value="">Selecciona una ruta</option>
                {routes.map(r => (
                  <option key={r.route_id} value={r.route_id}>
                    {r.route_short_name} - {r.route_long_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Periodicidad / Servicio</label>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                className={inputClass + ' w-full'}
              >
                <option value="">Selecciona un servicio</option>
                {services.map(s => (
                  <option key={s.service_id} value={s.service_id}>
                    {s.service_id} ({getServiceDays(s)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Rango de horas */}
          <div className="mt-4">
            <label className={labelClass}>Rango de Horas (opcional)</label>
            <div className="flex items-center gap-4">
              <input
                type="time"
                value={timeRange.start}
                onChange={(e) => setTimeRange(prev => ({ ...prev, start: e.target.value }))}
                className={inputClass}
              />
              <span className="text-gray-500">a</span>
              <input
                type="time"
                value={timeRange.end}
                onChange={(e) => setTimeRange(prev => ({ ...prev, end: e.target.value }))}
                className={inputClass}
              />
            </div>
          </div>
        </div>

        {/* Paso 2: Selección de Paradas */}
        {stops.length > 0 && (
          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-700">
                🚏 Paso 2: Seleccionar Paradas a Mostrar
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={selectAllStops}
                  className={buttonClass + ' bg-blue-600 text-white hover:bg-blue-700'}
                >
                  Seleccionar Todas
                </button>
                <button
                  onClick={clearAllStops}
                  className={buttonClass + ' bg-gray-300 text-gray-700 hover:bg-gray-400'}
                >
                  Limpiar
                </button>
              </div>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Seleccionadas: {selectedStops.size} de {stops.length}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto p-2 border border-gray-200 rounded-md">
              {stops.map(stop => (
                <label
                  key={stop.stop_id}
                  className={`flex items-center p-3 rounded-md cursor-pointer transition-colors ${
                    selectedStops.has(stop.stop_id)
                      ? 'bg-blue-50 border-2 border-blue-500'
                      : 'bg-white border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedStops.has(stop.stop_id)}
                    onChange={() => toggleStop(stop.stop_id)}
                    className="mr-3 h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {stop.stop_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Seq: {stop.stop_sequence} | Dir: {stop.direction_id}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Paso 3: Generar */}
        <div className="flex justify-end gap-4">
          <button
            onClick={generateTimetable}
            disabled={loading || !selectedRoute || !selectedService || selectedStops.size === 0}
            className={buttonClass + ' bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-lg px-8 py-3'}
          >
            {loading ? 'Generando...' : '🔍 Generar Timetable'}
          </button>
        </div>

        {/* Vista Previa y Descarga */}
        {timetableData && (
          <div className={sectionClass + ' mt-6'}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-700">
                📄 Vista Previa del Timetable
              </h2>
              <button
                onClick={downloadCSV}
                className={buttonClass + ' bg-blue-600 text-white hover:bg-blue-700'}
              >
                💾 Descargar CSV
              </button>
            </div>

            {/* Info de la ruta */}
            <div className="mb-4 p-4 bg-gray-50 rounded-md">
              <h3 className="font-bold text-lg">{timetableData.route_name}</h3>
              <p className="text-sm text-gray-600">Servicio: {timetableData.service_days}</p>
              <p className="text-sm text-gray-600">
                Total de viajes: {timetableData.trips.length}
              </p>
            </div>

            {/* Tabla de horarios */}
            <div className="overflow-x-auto border border-gray-300 rounded-lg">
              <table className="min-w-full divide-y divide-gray-300">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider sticky left-0 bg-gray-100">
                      Bus
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Viaje
                    </th>
                    {timetableData.selected_stops.map(stop => (
                      <th key={stop.stop_id} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        {stop.stop_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {timetableData.trips.map((trip, idx) => (
                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-inherit">
                        Bus {trip.bus_number}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {trip.trip_sequence}
                      </td>
                      {trip.stop_times.map((st, stIdx) => (
                        <td key={stIdx} className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {st.arrival_time || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}