import React, { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:8000';

const TimetableGenerator = () => {
  const [routes, setRoutes] = useState([]);
  const [services, setServices] = useState([]);
  const [stops, setStops] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedStops, setSelectedStops] = useState([]);
  const [timetableData, setTimetableData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingStops, setLoadingStops] = useState(false);
  const [loadingServices, setLoadingServices] = useState(false);

  useEffect(() => {
    fetchRoutes();
  }, []);

  useEffect(() => {
    if (selectedRoute) {
      setSelectedService('');
      setSelectedStops([]);
      setTimetableData(null);
      fetchServices(selectedRoute);
      fetchStops(selectedRoute);
    }
  }, [selectedRoute]);

  const fetchRoutes = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/gtfs/routes-with-details`);
      if (!response.ok) throw new Error('Error al cargar rutas');
      const data = await response.json();
      setRoutes(data);
    } catch (err) {
      console.error('Error al cargar rutas:', err);
      setError('Error al cargar rutas. Verifica que el backend esté funcionando.');
    }
  };

  const fetchServices = async (routeId) => {
    setLoadingServices(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/available_services/?route_id=${encodeURIComponent(routeId)}`
      );
      if (!response.ok) throw new Error('Error al cargar servicios');
      const data = await response.json();
      setServices(data);
      setError(null);
    } catch (err) {
      console.error('Error al cargar servicios:', err);
      setError('Error al cargar servicios para esta ruta.');
      setServices([]);
    } finally {
      setLoadingServices(false);
    }
  };

  const fetchStops = async (routeId) => {
    setLoadingStops(true);
    try {
      const [direction0Response, direction1Response] = await Promise.all([
        fetch(`${API_BASE_URL}/api/route_stops/?route_id=${encodeURIComponent(routeId)}&direction_id=0`),
        fetch(`${API_BASE_URL}/api/route_stops/?route_id=${encodeURIComponent(routeId)}&direction_id=1`)
      ]);

      let allStops = [];

      if (direction0Response.ok) {
        const data0 = await direction0Response.json();
        allStops = [...allStops, ...data0.map(stop => ({ ...stop, direction_id: 0 }))];
      }

      if (direction1Response.ok) {
        const data1 = await direction1Response.json();
        allStops = [...allStops, ...data1.map(stop => ({ ...stop, direction_id: 1 }))];
      }

      if (allStops.length === 0) {
        const responseAll = await fetch(`${API_BASE_URL}/api/route_stops/?route_id=${encodeURIComponent(routeId)}`);
        if (responseAll.ok) {
          const dataAll = await responseAll.json();
          allStops = dataAll.map(stop => ({ ...stop, direction_id: 0 }));
        }
      }

      allStops.sort((a, b) => {
        if (a.direction_id !== b.direction_id) {
          return a.direction_id - b.direction_id;
        }
        return a.stop_sequence - b.stop_sequence;
      });

      setStops(allStops);
      setError(null);
    } catch (err) {
      console.error('Error al cargar paradas:', err);
      setError('Error al cargar paradas para esta ruta.');
      setStops([]);
    } finally {
      setLoadingStops(false);
    }
  };

  const handleStopSelection = (stopId) => {
    setSelectedStops(prev => {
      if (prev.includes(stopId)) {
        return prev.filter(id => id !== stopId);
      } else {
        return [...prev, stopId];
      }
    });
  };

  

  const handleGenerateTimetable = async () => {
    if (!selectedRoute || !selectedService || selectedStops.length < 2) {
      setError('Debe seleccionar una ruta, servicio y al menos 2 paradas');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('route_id', selectedRoute);
      params.append('service_id', selectedService);
      
      selectedStops.forEach(stopId => {
        params.append('selected_stop_ids', stopId);
      });

      console.log('🔍 Solicitando horarios...');

      const response = await fetch(
        `${API_BASE_URL}/api/generate_chained_timetable/?${params.toString()}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al generar horario');
      }

      const data = await response.json();
      console.log('✅ Horarios recibidos:', data);
      console.log(`📊 Total de corridas: ${data.total_corridas}`);
      console.log(`📊 Corridas en array: ${data.corridas?.length || 0}`);
      
      setTimetableData(data);
      setError(null);
    } catch (err) {
      console.error('❌ Error:', err);
      setError(err.message || 'Error al generar horario.');
      setTimetableData(null);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (!timetableData) return;

    const { headers, corridas, stop_ids_ordered } = timetableData;
    
    let csv = headers.join(',') + '\n';
    
    corridas.forEach(corrida => {
      const row = [
        corrida.corrida_num,
        corrida.bus || '-',
        ...stop_ids_ordered.map(stopId => {
          return corrida.times[stopId] || '-';
        })
      ];
      csv += row.join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `horario_${selectedRoute}_${selectedService}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const getStopName = (stopId) => {
    const stop = stops.find(s => s.stop_id === stopId);
    return stop ? stop.stop_name : stopId;
  };

  const clearSelection = () => {
    setSelectedStops([]);
    setTimetableData(null);
  };

  const selectAllStops = () => {
    setSelectedStops(stops.map(stop => stop.stop_id));
  };

  const stopsByDirection = stops.reduce((acc, stop) => {
    const dir = stop.direction_id ?? 0;
    if (!acc[dir]) acc[dir] = [];
    acc[dir].push(stop);
    return acc;
  }, {});

  const getDirectionLabel = (directionId) => {
    return directionId === 0 ? 'IDA (Centro → Barrio)' : 'VUELTA (Barrio → Centro)';
  };

  return (
    <div className="min-h-screen bg-gray-100 py-6 overflow-y-auto">
      <div className="container mx-auto px-4 max-w-[98vw]">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">
          🚌 Generador de Horarios Encadenados
        </h1>

        <div className="bg-white shadow-lg rounded-lg p-6 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  📍 Seleccionar Ruta
                </label>
                <select
                  className="w-full p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  value={selectedRoute}
                  onChange={(e) => setSelectedRoute(e.target.value)}
                >
                  <option value="">-- Seleccione una ruta --</option>
                  {routes.map(route => (
                    <option key={route.route_id} value={route.route_id}>
                      {route.route_short_name} - {route.route_long_name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedRoute && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    📅 Seleccionar Servicio/Periodicidad
                  </label>
                  {loadingServices ? (
                    <p className="text-gray-500 italic">Cargando servicios...</p>
                  ) : services.length === 0 ? (
                    <p className="text-red-500">No se encontraron servicios</p>
                  ) : (
                    <select
                      className="w-full p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      value={selectedService}
                      onChange={(e) => setSelectedService(e.target.value)}
                    >
                      <option value="">-- Seleccione un servicio --</option>
                      {services.map(service => (
                        <option key={service.service_id} value={service.service_id}>
                          {service.service_id} - {service.days}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>

            {selectedRoute && (
              <div className="flex flex-col">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  🚏 Seleccionar Paradas (mínimo 2)
                </label>
                <p className="text-xs text-gray-600 mb-3">
                  Las paradas están ordenadas por sentido y secuencia
                </p>
                
                {loadingStops ? (
                  <p className="text-gray-500 italic">Cargando paradas...</p>
                ) : stops.length === 0 ? (
                  <p className="text-red-500">No se encontraron paradas</p>
                ) : (
                  <>
                    <div className="flex flex-wrap gap-2 mb-3">
                      <button
                        onClick={selectAllStops}
                        className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                      >
                        ✓ Seleccionar todas ({stops.length})
                      </button>
                      <button
                        onClick={clearSelection}
                        className="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition-colors"
                      >
                        ✕ Limpiar selección
                      </button>
                      <span className="ml-auto self-center text-sm text-gray-700 font-semibold">
                        Seleccionadas: {selectedStops.length} / {stops.length}
                      </span>
                    </div>

                    <div 
                      className="border-2 border-gray-300 rounded-lg bg-white overflow-hidden flex-1"
                      style={{ maxHeight: '40vh' }}
                    >
                      <div className="overflow-y-auto h-full p-3 space-y-4">
                        {Object.entries(stopsByDirection).map(([directionId, directionStops]) => (
                          <div key={directionId} className="mb-3">
                            <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-3 py-2 rounded-lg mb-2 shadow-md z-10">
                              <h3 className="font-bold text-sm flex items-center">
                                <span className="text-lg mr-2">
                                  {parseInt(directionId) === 0 ? '→' : '←'}
                                </span>
                                {getDirectionLabel(parseInt(directionId))}
                                <span className="ml-auto text-xs bg-white text-blue-700 px-2 py-1 rounded">
                                  {directionStops.length} paradas
                                </span>
                              </h3>
                            </div>

                            <div className="space-y-1 pl-2">
                              {directionStops.map((stop) => (
                                <div 
                                  key={stop.stop_id} 
                                  className={`flex items-center p-2 rounded-lg transition-all ${
                                    selectedStops.includes(stop.stop_id)
                                      ? 'bg-blue-50 border-2 border-blue-300'
                                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    id={stop.stop_id}
                                    checked={selectedStops.includes(stop.stop_id)}
                                    onChange={() => handleStopSelection(stop.stop_id)}
                                    className="mr-3 h-5 w-5 text-blue-600 focus:ring-2 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                                  />
                                  <label 
                                    htmlFor={stop.stop_id} 
                                    className="cursor-pointer flex-1 flex items-center"
                                  >
                                    <span className="font-mono text-xs text-gray-500 mr-2 min-w-[30px]">
                                      {stop.stop_sequence}
                                    </span>
                                    <span className="font-medium text-sm text-gray-800">
                                      {stop.stop_name}
                                    </span>
                                  </label>
                                  {selectedStops.includes(stop.stop_id) && (
                                    <span className="ml-2 bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded-full">
                                      #{selectedStops.indexOf(stop.stop_id) + 1}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          

          <div className="flex gap-4 mt-6">
            <button
              onClick={handleGenerateTimetable}
              disabled={loading || !selectedRoute || !selectedService || selectedStops.length < 2}
              className="px-8 py-4 bg-blue-600 text-white font-bold text-lg rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all shadow-lg"
            >
              {loading ? 'Generando...' : '🚀 Generar Horario Completo'}
            </button>

            {timetableData && timetableData.corridas && timetableData.corridas.length > 0 && (
              <button
                onClick={exportToCSV}
                className="px-8 py-4 bg-green-600 text-white font-bold text-lg rounded-lg hover:bg-green-700 transition-all shadow-lg"
              >
                📥 Exportar CSV ({timetableData.total_corridas} corridas)
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 px-6 py-4 rounded-lg mb-6 shadow-lg">
            <p className="font-bold text-lg">⚠️ Error</p>
            <p className="mt-1">{error}</p>
          </div>
        )}

        {timetableData && timetableData.corridas && timetableData.corridas.length > 0 && (
          <div className="bg-white shadow-xl rounded-lg p-6">
            <div className="mb-4">
              <h2 className="text-3xl font-bold text-gray-800 mb-3">
                📋 Horario Completo - Ruta {timetableData.route_id}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                <p>
                  <span className="font-semibold">Servicio:</span> {timetableData.service_id}
                </p>
                <p>
                  <span className="font-semibold">Total corridas:</span> 
                  <span className="text-blue-600 font-bold text-xl ml-2">{timetableData.total_corridas}</span>
                </p>
                <p>
                  <span className="font-semibold">Paradas:</span> {timetableData.stop_ids_ordered.length}
                </p>
                <p>
                  <span className="font-semibold">Buses únicos:</span> 
                  {new Set(timetableData.corridas.map(c => c.bus).filter(b => b)).size}
                </p>
              </div>
            </div>

            <div 
              className="overflow-auto shadow-lg border-2 border-gray-300 rounded-lg"
              style={{ maxHeight: '60vh' }}
            >
              <table className="min-w-full bg-white border-collapse">
                <thead className="sticky top-0 z-20">
                  <tr className="bg-gradient-to-r from-blue-600 to-blue-800 text-white">
                    <th className="px-4 py-3 text-left font-bold text-sm border-r-2 border-blue-500 sticky left-0 bg-blue-700 z-30">
                      Corrida
                    </th>
                    <th className="px-4 py-3 text-left font-bold text-sm border-r-2 border-blue-500 sticky left-[80px] bg-blue-700 z-30">
                      Bus
                    </th>
                    {timetableData.headers.slice(2).map((header, index) => (
                      <th
                        key={index}
                        className="px-4 py-3 text-left font-bold text-xs border-r border-blue-400 last:border-r-0 min-w-[140px]"
                      >
                        <div className="truncate" title={header}>
                          {header}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {timetableData.corridas.map((corrida, index) => (
                    <tr
                      key={corrida.id}
                      className={`${
                        index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                      } hover:bg-blue-50 transition-colors border-b border-gray-200`}
                    >
                      <td className="px-4 py-3 text-sm font-semibold text-gray-700 sticky left-0 bg-inherit z-10 border-r border-gray-300">
                        {corrida.corrida_num}
                      </td>
                      <td className="px-4 py-3 text-sm sticky left-[80px] bg-inherit z-10 border-r border-gray-300">
                        <span className="inline-flex items-center justify-center px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
                          Bus {corrida.bus || '-'}
                        </span>
                      </td>
                      {timetableData.stop_ids_ordered.map((stopId) => (
                        <td
                          key={stopId}
                          className="px-4 py-3 text-center text-sm font-mono border-r border-gray-200 last:border-r-0"
                        >
                          {corrida.times[stopId] ? (
                            <span className="font-bold text-gray-900">
                              {corrida.times[stopId]}
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 p-4 bg-gray-50 rounded-lg text-xs text-gray-600 space-y-1">
              <p>💡 <strong>Total de corridas en tabla:</strong> {timetableData.corridas.length}</p>
              <p>📌 Un guión (-) indica que el bus no pasa por esa parada</p>
              <p>🔄 Usa scroll horizontal/vertical para ver toda la información</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TimetableGenerator;