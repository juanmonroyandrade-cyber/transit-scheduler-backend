import { useState, useEffect } from 'react';

export default function SchedulingParameters() {
  // ===== TABLA 1: Parámetros Generales =====
  const [tabla1, setTabla1] = useState({
    numeroRuta: '',
    nombreRuta: '',
    periodicidad: '',
    horaInicioCentro: '03:54',
    horaInicioBarrio: '04:30',
    horaFinCentro: '22:58',
    horaFinBarrio: '22:46',
    tiempoRecorridoCB: '00:36',
    tiempoRecorridoBC: '00:36',
    dwellCentro: 0,
    dwellBarrio: 0,
    distanciaCB: 0,
    distanciaBC: 0
  });

  // ===== TABLA 2: Buses Variables por Hora =====
  const [tabla2, setTabla2] = useState([
    { hora: 4, buses: 5 },
    { hora: 5, buses: 8 },
    { hora: 23, buses: 5 }
  ]);

  // ===== TABLA 3: Tiempos de Ciclo Variables =====
  const [tabla3, setTabla3] = useState([
    { hora: 4, tCicloAB: '01:12', tCicloBA: '01:12' },
    { hora: 5, tCicloAB: '01:15', tCicloBA: '01:15' },
    { hora: 23, tCicloAB: '01:10', tCicloBA: '01:10' }
  ]);

  // ===== TABLA 4: Intervalos Centro (Headways A→B) =====
  const [tabla4, setTabla4] = useState([
    { desde: '03:54', hasta: '07:00', headway: 15 },
    { desde: '07:00', hasta: '09:00', headway: 10 },
    { desde: '09:00', hasta: '17:00', headway: 20 },
    { desde: '17:00', hasta: '19:00', headway: 12 },
    { desde: '19:00', hasta: '22:58', headway: 20 }
  ]);

  // ===== TABLA 5: Intervalos Barrio (Headways B→A) =====
  const [tabla5, setTabla5] = useState([
    { desde: '04:30', hasta: '07:30', headway: 15 },
    { desde: '07:30', hasta: '09:30', headway: 10 },
    { desde: '09:30', hasta: '17:30', headway: 20 },
    { desde: '17:30', hasta: '19:30', headway: 12 },
    { desde: '19:30', hasta: '22:46', headway: 20 }
  ]);

  // ===== TABLA 6: Tiempos Recorrido Variables Centro (A→B) =====
  const [tabla6, setTabla6] = useState([
    { desde: '03:54', hasta: '07:00', recorridoAB: '00:36' },
    { desde: '07:00', hasta: '09:00', recorridoAB: '00:40' },
    { desde: '09:00', hasta: '17:00', recorridoAB: '00:36' },
    { desde: '17:00', hasta: '19:00', recorridoAB: '00:38' },
    { desde: '19:00', hasta: '22:58', recorridoAB: '00:36' }
  ]);

  // ===== TABLA 7: Tiempos Recorrido Variables Barrio (B→A) =====
  const [tabla7, setTabla7] = useState([
    { desde: '04:30', hasta: '07:30', recorridoBA: '00:36' },
    { desde: '07:30', hasta: '09:30', recorridoBA: '00:42' },
    { desde: '09:30', hasta: '17:30', recorridoBA: '00:36' },
    { desde: '17:30', hasta: '19:30', recorridoBA: '00:40' },
    { desde: '19:30', hasta: '22:46', recorridoBA: '00:36' }
  ]);

  const [routes, setRoutes] = useState([]);
  const [shapes, setShapes] = useState([]);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);

  // ===== CARGAR RUTAS =====
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

  // ===== CARGAR SHAPES CUANDO SE SELECCIONA UNA RUTA =====
  useEffect(() => {
    if (!tabla1.numeroRuta) return;

    const fetchShapes = async () => {
      try {
        const res = await fetch('http://localhost:8000/admin/shapes');
        if (res.ok) {
          const data = await res.json();
          const routeShapes = data.filter(s => 
            s.shape_id && s.shape_id.startsWith(`${tabla1.numeroRuta}.`)
          );
          setShapes(routeShapes);
        }
      } catch (err) {
        console.error('Error cargando shapes:', err);
      }
    };
    fetchShapes();
  }, [tabla1.numeroRuta]);

  // ===== CALCULAR DISTANCIA MÁXIMA DE SHAPES =====
  useEffect(() => {
    if (shapes.length === 0) return;

    const shapeGroups = {};
    shapes.forEach(s => {
      if (!shapeGroups[s.shape_id]) {
        shapeGroups[s.shape_id] = [];
      }
      shapeGroups[s.shape_id].push(s);
    });

    const maxDistances = {};
    Object.keys(shapeGroups).forEach(shapeId => {
      const distances = shapeGroups[shapeId]
        .map(s => parseFloat(s.shape_dist_traveled || 0))
        .filter(d => !isNaN(d));
      maxDistances[shapeId] = distances.length > 0 ? Math.max(...distances) : 0;
    });

    const shapeIdCB = `${tabla1.numeroRuta}.1`;
    const shapeIdBC = `${tabla1.numeroRuta}.2`;

    setTabla1(prev => ({
      ...prev,
      distanciaCB: (maxDistances[shapeIdCB] || 0) / 1000,
      distanciaBC: (maxDistances[shapeIdBC] || 0) / 1000
    }));
  }, [shapes, tabla1.numeroRuta]);

  // ===== MANEJADORES =====
  const handleTabla1Change = (field, value) => {
    setTabla1(prev => ({ ...prev, [field]: value }));

    if (field === 'numeroRuta') {
      const route = routes.find(r => r.route_id === value);
      if (route) {
        setTabla1(prev => ({ 
          ...prev, 
          numeroRuta: value,
          nombreRuta: route.route_long_name || route.route_short_name || ''
        }));
      }
    }
  };

  const handleTableChange = (tableIndex, rowIndex, field, value, setter) => {
    setter(prev => {
      const updated = [...prev];
      updated[rowIndex] = { ...updated[rowIndex], [field]: value };
      return updated;
    });
  };

  const addRow = (setter, template) => {
    setter(prev => [...prev, { ...template }]);
  };

  const removeRow = (setter, index) => {
    setter(prev => prev.filter((_, i) => i !== index));
  };

  // ===== GUARDAR =====
  const handleSave = async () => {
    setLoading(true);
    setStatus({ message: 'Guardando parámetros...', type: 'loading' });

    try {
      const data = {
        tabla1,
        tabla2,
        tabla3,
        tabla4,
        tabla5,
        tabla6,
        tabla7
      };

      localStorage.setItem('schedulingParamsComplete', JSON.stringify(data));

      const response = await fetch('http://localhost:8000/scheduling/parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        const result = await response.json();
        setStatus({ 
          message: `✅ Parámetros guardados correctamente (ID: ${result.id})`, 
          type: 'success' 
        });
      } else {
        throw new Error('Error al guardar en el servidor');
      }
    } catch (err) {
      console.error('Error:', err);
      setStatus({ 
        message: `✅ Parámetros guardados localmente (servidor no disponible)`, 
        type: 'success' 
      });
    } finally {
      setLoading(false);
    }
  };

  // ===== CARGAR DATOS GUARDADOS =====
  useEffect(() => {
    const saved = localStorage.getItem('schedulingParamsComplete');
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (data.tabla1) setTabla1(data.tabla1);
        if (data.tabla2) setTabla2(data.tabla2);
        if (data.tabla3) setTabla3(data.tabla3);
        if (data.tabla4) setTabla4(data.tabla4);
        if (data.tabla5) setTabla5(data.tabla5);
        if (data.tabla6) setTabla6(data.tabla6);
        if (data.tabla7) setTabla7(data.tabla7);
      } catch (e) {
        console.error('Error cargando datos guardados:', e);
      }
    }
  }, []);

  // ===== ESTILOS =====
  const inputClass = "px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const sectionClass = "bg-white p-6 rounded-lg shadow-md mb-6";
  const tableClass = "min-w-full divide-y divide-gray-200";
  const thClass = "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50";
  const tdClass = "px-4 py-3";

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Parámetros de Programación</h1>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-6 py-2 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 disabled:opacity-50 shadow-md"
          >
            {loading ? 'Guardando...' : '💾 Guardar Parámetros'}
          </button>
        </div>

        {status.message && (
          <div className={`p-4 mb-6 rounded-md ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
            status.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
            'bg-blue-100 text-blue-800 border border-blue-200'
          }`}>
            {status.message}
          </div>
        )}

        {/* TABLA 1 */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold mb-4 text-gray-700 border-b pb-2">
            📋 Tabla 1: Parámetros Generales
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Número de Ruta</label>
              <select value={tabla1.numeroRuta} onChange={(e) => handleTabla1Change('numeroRuta', e.target.value)} className={inputClass + ' w-full'}>
                <option value="">Selecciona una ruta</option>
                {routes.map(r => (
                  <option key={r.route_id} value={r.route_id}>{r.route_id} - {r.route_short_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Nombre de la Ruta</label>
              <input type="text" value={tabla1.nombreRuta} onChange={(e) => handleTabla1Change('nombreRuta', e.target.value)} className={inputClass + ' w-full'} placeholder="Nombre de la ruta" />
            </div>
            <div>
              <label className={labelClass}>Periodicidad</label>
              <input type="text" value={tabla1.periodicidad} onChange={(e) => handleTabla1Change('periodicidad', e.target.value)} className={inputClass + ' w-full'} placeholder="Ej: Diario, L-V, S-D" />
            </div>
            <div>
              <label className={labelClass}>Hora Inicio Servicio en Centro</label>
              <input type="time" value={tabla1.horaInicioCentro} onChange={(e) => handleTabla1Change('horaInicioCentro', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Hora Inicio Servicio en Barrio</label>
              <input type="time" value={tabla1.horaInicioBarrio} onChange={(e) => handleTabla1Change('horaInicioBarrio', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Hora Fin Servicio en Centro</label>
              <input type="time" value={tabla1.horaFinCentro} onChange={(e) => handleTabla1Change('horaFinCentro', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Hora Fin Servicio en Barrio</label>
              <input type="time" value={tabla1.horaFinBarrio} onChange={(e) => handleTabla1Change('horaFinBarrio', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Tiempo Recorrido C→B (hh:mm)</label>
              <input type="time" value={tabla1.tiempoRecorridoCB} onChange={(e) => handleTabla1Change('tiempoRecorridoCB', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Tiempo Recorrido B→C (hh:mm)</label>
              <input type="time" value={tabla1.tiempoRecorridoBC} onChange={(e) => handleTabla1Change('tiempoRecorridoBC', e.target.value)} className={inputClass + ' w-full'} />
            </div>
            <div>
              <label className={labelClass}>Dwell en Centro (minutos)</label>
              <input type="number" value={tabla1.dwellCentro} onChange={(e) => handleTabla1Change('dwellCentro', Number(e.target.value))} className={inputClass + ' w-full'} min="0" />
            </div>
            <div>
              <label className={labelClass}>Dwell en Barrio (minutos)</label>
              <input type="number" value={tabla1.dwellBarrio} onChange={(e) => handleTabla1Change('dwellBarrio', Number(e.target.value))} className={inputClass + ' w-full'} min="0" />
            </div>
            <div>
              <label className={labelClass}>Distancia C→B (km)</label>
              <input type="number" step="0.01" value={tabla1.distanciaCB} onChange={(e) => handleTabla1Change('distanciaCB', Number(e.target.value))} className={inputClass + ' w-full'} min="0" />
              <p className="text-xs text-gray-500 mt-1">Auto-calculada desde shapes</p>
            </div>
            <div>
              <label className={labelClass}>Distancia B→C (km)</label>
              <input type="number" step="0.01" value={tabla1.distanciaBC} onChange={(e) => handleTabla1Change('distanciaBC', Number(e.target.value))} className={inputClass + ' w-full'} min="0" />
              <p className="text-xs text-gray-500 mt-1">Auto-calculada desde shapes</p>
            </div>
          </div>
        </div>

        {/* TABLA 2 */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">🚌 Tabla 2: Buses Variables por Hora</h2>
            <button onClick={() => addRow(setTabla2, { hora: 0, buses: 0 })} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir Fila</button>
          </div>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Hora</th>
                  <th className={thClass}>Buses</th>
                  <th className={thClass}></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla2.map((row, idx) => (
                  <tr key={idx}>
                    <td className={tdClass}>
                      <input type="number" value={row.hora} onChange={(e) => handleTableChange(2, idx, 'hora', Number(e.target.value), setTabla2)} className={inputClass} min="0" max="23" />
                    </td>
                    <td className={tdClass}>
                      <input type="number" value={row.buses} onChange={(e) => handleTableChange(2, idx, 'buses', Number(e.target.value), setTabla2)} className={inputClass} min="0" />
                    </td>
                    <td className={tdClass}>
                      <button onClick={() => removeRow(setTabla2, idx)} className="text-red-600 hover:text-red-800 text-sm">Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 3 */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">⏱️ Tabla 3: Tiempos de Ciclo Variables</h2>
            <button onClick={() => addRow(setTabla3, { hora: 0, tCicloAB: '00:00', tCicloBA: '00:00' })} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir Fila</button>
          </div>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Hora</th>
                  <th className={thClass}>T Ciclo A→B (hh:mm)</th>
                  <th className={thClass}>T Ciclo B→A (hh:mm)</th>
                  <th className={thClass}></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla3.map((row, idx) => (
                  <tr key={idx}>
                    <td className={tdClass}>
                      <input type="number" value={row.hora} onChange={(e) => handleTableChange(3, idx, 'hora', Number(e.target.value), setTabla3)} className={inputClass} min="0" max="23" />
                    </td>
                    <td className={tdClass}>
                      <input type="time" value={row.tCicloAB} onChange={(e) => handleTableChange(3, idx, 'tCicloAB', e.target.value, setTabla3)} className={inputClass} />
                    </td>
                    <td className={tdClass}>
                      <input type="time" value={row.tCicloBA} onChange={(e) => handleTableChange(3, idx, 'tCicloBA', e.target.value, setTabla3)} className={inputClass} />
                    </td>
                    <td className={tdClass}>
                      <button onClick={() => removeRow(setTabla3, idx)} className="text-red-600 hover:text-red-800 text-sm">Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLAS 4 Y 5 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-700">📊 Tabla 4: Intervalos Centro (A→B)</h2>
              <button onClick={() => addRow(setTabla4, { desde: '00:00', hasta: '00:00', headway: 0 })} className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir</button>
            </div>
            <div className="overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>Desde</th>
                    <th className={thClass}>Hasta</th>
                    <th className={thClass}>Headway (min)</th>
                    <th className={thClass}></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tabla4.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input type="time" value={row.desde} onChange={(e) => handleTableChange(4, idx, 'desde', e.target.value, setTabla4)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.hasta} onChange={(e) => handleTableChange(4, idx, 'hasta', e.target.value, setTabla4)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="number" value={row.headway} onChange={(e) => handleTableChange(4, idx, 'headway', Number(e.target.value), setTabla4)} className={inputClass + ' w-full'} min="1" />
                      </td>
                      <td className={tdClass}>
                        <button onClick={() => removeRow(setTabla4, idx)} className="text-red-600 hover:text-red-800 text-sm">×</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-700">📊 Tabla 5: Intervalos Barrio (B→A)</h2>
              <button onClick={() => addRow(setTabla5, { desde: '00:00', hasta: '00:00', headway: 0 })} className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir</button>
            </div>
            <div className="overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>Desde</th>
                    <th className={thClass}>Hasta</th>
                    <th className={thClass}>Headway (min)</th>
                    <th className={thClass}></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tabla5.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input type="time" value={row.desde} onChange={(e) => handleTableChange(5, idx, 'desde', e.target.value, setTabla5)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.hasta} onChange={(e) => handleTableChange(5, idx, 'hasta', e.target.value, setTabla5)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="number" value={row.headway} onChange={(e) => handleTableChange(5, idx, 'headway', Number(e.target.value), setTabla5)} className={inputClass + ' w-full'} min="1" />
                      </td>
                      <td className={tdClass}>
                        <button onClick={() => removeRow(setTabla5, idx)} className="text-red-600 hover:text-red-800 text-sm">×</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* TABLAS 6 Y 7 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-700">🕐 Tabla 6: Tiempos Variables Centro</h2>
              <button onClick={() => addRow(setTabla6, { desde: '00:00', hasta: '00:00', recorridoAB: '00:00' })} className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir</button>
            </div>
            <div className="overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>Desde</th>
                    <th className={thClass}>Hasta</th>
                    <th className={thClass}>Recorrido A→B</th>
                    <th className={thClass}></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tabla6.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input type="time" value={row.desde} onChange={(e) => handleTableChange(6, idx, 'desde', e.target.value, setTabla6)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.hasta} onChange={(e) => handleTableChange(6, idx, 'hasta', e.target.value, setTabla6)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.recorridoAB} onChange={(e) => handleTableChange(6, idx, 'recorridoAB', e.target.value, setTabla6)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <button onClick={() => removeRow(setTabla6, idx)} className="text-red-600 hover:text-red-800 text-sm">×</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-700">🕐 Tabla 7: Tiempos Variables Barrio</h2>
              <button onClick={() => addRow(setTabla7, { desde: '00:00', hasta: '00:00', recorridoBA: '00:00' })} className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm">+ Añadir</button>
            </div>
            <div className="overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>Desde</th>
                    <th className={thClass}>Hasta</th>
                    <th className={thClass}>Recorrido B→A</th>
                    <th className={thClass}></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tabla7.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input type="time" value={row.desde} onChange={(e) => handleTableChange(7, idx, 'desde', e.target.value, setTabla7)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.hasta} onChange={(e) => handleTableChange(7, idx, 'hasta', e.target.value, setTabla7)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <input type="time" value={row.recorridoBA} onChange={(e) => handleTableChange(7, idx, 'recorridoBA', e.target.value, setTabla7)} className={inputClass + ' w-full'} />
                      </td>
                      <td className={tdClass}>
                        <button onClick={() => removeRow(setTabla7, idx)} className="text-red-600 hover:text-red-800 text-sm">×</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* BOTÓN GUARDAR FINAL */}
        <div className="flex justify-end mt-6 mb-8">
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-8 py-3 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 disabled:opacity-50 shadow-lg"
          >
            {loading ? 'Guardando...' : '💾 Guardar Todos los Parámetros'}
          </button>
        </div>
      </div>
    </div>
  );
}