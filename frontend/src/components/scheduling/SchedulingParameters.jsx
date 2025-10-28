import { useState, useEffect } from 'react';

/**
 * Componente DurationInput - Permite entrada de duraciones en formato HH:MM o minutos
 */
function DurationInput({ value, onChange, className = '' }) {
  const [local, setLocal] = useState(value ?? '');

  useEffect(() => {
    setLocal(value ?? '');
  }, [value]);

  const normalize = (raw) => {
    if (raw == null) return '00:00';
    const s = String(raw).trim();
    if (s === '') return '';

    const hhmm = s.match(/^(\d{1,2}):(\d{1,2})$/);
    if (hhmm) {
      let hh = parseInt(hhmm[1], 10);
      let mm = parseInt(hhmm[2], 10);
      if (isNaN(hh)) hh = 0;
      if (isNaN(mm)) mm = 0;
      if (mm < 0) mm = 0;
      if (mm > 59) mm = 59;
      hh = Math.max(0, hh);
      const HH = String(hh).padStart(2, '0');
      const MM = String(mm).padStart(2, '0');
      return `${HH}:${MM}`;
    }

    const onlyMin = s.match(/^(\d{1,4})$/);
    if (onlyMin) {
      let totalMin = parseInt(onlyMin[1], 10);
      if (isNaN(totalMin)) totalMin = 0;
      const hh = Math.floor(totalMin / 60);
      const mm = totalMin % 60;
      const HH = String(hh).padStart(2, '0');
      const MM = String(mm).padStart(2, '0');
      return `${HH}:${MM}`;
    }

    return '';
  };

  const handleChange = (e) => {
    const v = e.target.value;
    if (/^[0-9:\s]*$/.test(v)) {
      setLocal(v);
      const normalized = normalize(v);
      if (normalized) onChange(normalized);
      else onChange(v);
    }
  };

  const handleBlur = () => {
    const normalized = normalize(local);
    if (normalized) {
      setLocal(normalized);
      onChange(normalized);
    } else {
      onChange(local);
    }
  };

  return (
    <input
      type="text"
      inputMode="numeric"
      pattern="\d{1,3}:?\d{1,2}"
      value={local}
      onChange={handleChange}
      onBlur={handleBlur}
      placeholder="hh:mm"
      className={className}
    />
  );
}

export default function SchedulingParameters() {
  // Estados para las 7 tablas
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

  const [tabla2, setTabla2] = useState([
    { hora: 4, buses: 5 },
    { hora: 5, buses: 8 },
    { hora: 23, buses: 5 }
  ]);

  const [tabla3, setTabla3] = useState([
    { hora: 4, tCicloAB: '01:12', tCicloBA: '01:12' },
    { hora: 5, tCicloAB: '01:15', tCicloBA: '01:15' },
    { hora: 23, tCicloAB: '01:10', tCicloBA: '01:10' }
  ]);

  const [tabla4, setTabla4] = useState([
    { desde: '03:54', hasta: '07:00', headway: 15 },
    { desde: '07:00', hasta: '09:00', headway: 10 },
    { desde: '09:00', hasta: '17:00', headway: 20 },
    { desde: '17:00', hasta: '19:00', headway: 12 },
    { desde: '19:00', hasta: '22:58', headway: 20 }
  ]);

  const [tabla5, setTabla5] = useState([
    { desde: '04:30', hasta: '07:30', headway: 15 },
    { desde: '07:30', hasta: '09:30', headway: 10 },
    { desde: '09:30', hasta: '17:30', headway: 20 },
    { desde: '17:30', hasta: '19:30', headway: 12 },
    { desde: '19:30', hasta: '22:46', headway: 20 }
  ]);

  const [tabla6, setTabla6] = useState([
    { desde: '03:54', hasta: '07:00', recorridoAB: '00:36' },
    { desde: '07:00', hasta: '09:00', recorridoAB: '00:40' },
    { desde: '09:00', hasta: '17:00', recorridoAB: '00:36' },
    { desde: '17:00', hasta: '19:00', recorridoAB: '00:38' },
    { desde: '19:00', hasta: '22:58', recorridoAB: '00:36' }
  ]);

  const [tabla7, setTabla7] = useState([
    { desde: '04:30', hasta: '07:30', recorridoBA: '00:36' },
    { desde: '07:30', hasta: '09:30', recorridoBA: '00:42' },
    { desde: '09:30', hasta: '17:30', recorridoBA: '00:36' },
    { desde: '17:30', hasta: '19:30', recorridoBA: '00:40' },
    { desde: '19:30', hasta: '22:46', recorridoBA: '00:36' }
  ]);

  const [processingExcel, setProcessingExcel] = useState(false);
  const [routes, setRoutes] = useState([]);
  const [shapes, setShapes] = useState([]);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);

  // Cargar rutas
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

  // Cargar shapes cuando cambia la ruta
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

  // Calcular distancias desde shapes
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

  // ✅ FUNCIÓN AUXILIAR: Convierte número decimal de Excel a formato HH:MM
  const excelTimeToHHMM = (decimalTime) => {
    if (typeof decimalTime === 'string' && decimalTime.includes(':')) {
      return decimalTime; // Ya está en formato correcto
    }
    
    const totalMinutes = Math.round(decimalTime * 24 * 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  };

  // ✅ NUEVA FUNCIÓN: Ejecutar procesamiento de Excel y actualizar tablas 4-7
  const handleExecuteExcel = async () => {
    setProcessingExcel(true);
    setStatus({ message: 'Procesando Excel...', type: 'loading' });

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

      console.log('📤 Enviando parámetros al backend para procesamiento de Excel...');

      const response = await fetch('http://localhost:8000/excel/process-parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al procesar Excel');
      }

      const result = await response.json();
      
      console.log('✅ Resultados del Excel:', result);

      // ✅ ACTUALIZAR TABLA 4 (Headways Centro)
      // Formato esperado: [[desde, hasta, headway], ...]
      if (result.results.tabla4 && result.results.tabla4.length > 0) {
        const newTabla4 = result.results.tabla4.map(row => ({
          desde: excelTimeToHHMM(row[0]),
          hasta: excelTimeToHHMM(row[1]),
          headway: parseInt(row[2]) || 0
        }));
        setTabla4(newTabla4);
        console.log('✅ Tabla 4 actualizada con', newTabla4.length, 'filas');
      }

      // ✅ ACTUALIZAR TABLA 5 (Headways Barrio)
      if (result.results.tabla5 && result.results.tabla5.length > 0) {
        const newTabla5 = result.results.tabla5.map(row => ({
          desde: excelTimeToHHMM(row[0]),
          hasta: excelTimeToHHMM(row[1]),
          headway: parseInt(row[2]) || 0
        }));
        setTabla5(newTabla5);
        console.log('✅ Tabla 5 actualizada con', newTabla5.length, 'filas');
      }

      // ✅ ACTUALIZAR TABLA 6 (Recorridos Centro)
      if (result.results.tabla6 && result.results.tabla6.length > 0) {
        const newTabla6 = result.results.tabla6.map(row => ({
          desde: excelTimeToHHMM(row[0]),
          hasta: excelTimeToHHMM(row[1]),
          recorridoAB: excelTimeToHHMM(row[2])
        }));
        setTabla6(newTabla6);
        console.log('✅ Tabla 6 actualizada con', newTabla6.length, 'filas');
      }

      // ✅ ACTUALIZAR TABLA 7 (Recorridos Barrio)
      if (result.results.tabla7 && result.results.tabla7.length > 0) {
        const newTabla7 = result.results.tabla7.map(row => ({
          desde: excelTimeToHHMM(row[0]),
          hasta: excelTimeToHHMM(row[1]),
          recorridoBA: excelTimeToHHMM(row[2])
        }));
        setTabla7(newTabla7);
        console.log('✅ Tabla 7 actualizada con', newTabla7.length, 'filas');
      }

      setStatus({
        message: `✅ Excel procesado y tablas actualizadas correctamente! (T4: ${result.results.tabla4.length}, T5: ${result.results.tabla5.length}, T6: ${result.results.tabla6.length}, T7: ${result.results.tabla7.length} filas)`,
        type: 'success'
      });

    } catch (err) {
      console.error('❌ Error:', err);
      setStatus({
        message: `❌ Error al procesar Excel: ${err.message}`,
        type: 'error'
      });
    } finally {
      setProcessingExcel(false);
    }
  };

  // Guardar parámetros
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

  // Cargar datos guardados
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

  // Estilos
  const inputClass = "px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const sectionClass = "bg-white p-6 rounded-lg shadow-md mb-6";
  const tableClass = "min-w-full divide-y divide-gray-200";
  const thClass = "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase bg-gray-50";
  const tdClass = "px-4 py-3";

  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header con botones */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Parámetros de Programación</h1>
          <div className="flex gap-3">
            <button
              onClick={handleExecuteExcel}
              disabled={processingExcel}
              className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-md hover:bg-blue-700 disabled:opacity-50 shadow-md flex items-center gap-2"
            >
              {processingExcel ? (
                <>
                  <span className="animate-spin">⚙️</span>
                  Procesando...
                </>
              ) : (
                <>
                  ▶️ Ejecutar Excel
                </>
              )}
            </button>

            <button
              onClick={handleSave}
              disabled={loading}
              className="px-6 py-2 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 disabled:opacity-50 shadow-md"
            >
              {loading ? 'Guardando...' : '💾 Guardar Parámetros'}
            </button>
          </div>
        </div>

        {/* Mensajes de estado */}
        {status.message && (
          <div className={`p-4 mb-6 rounded-md border ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
              status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' :
                'bg-blue-100 text-blue-800 border-blue-200 animate-pulse'
          }`}>
            {status.message}
          </div>
        )}

        {/* TABLA 1: Parámetros Generales */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold mb-4 text-gray-700 border-b pb-2">
            Tabla 1: Parámetros Generales
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Número de Ruta</label>
              <select
                value={tabla1.numeroRuta}
                onChange={(e) => handleTabla1Change('numeroRuta', e.target.value)}
                className={inputClass + " w-full"}
              >
                <option value="">Seleccionar...</option>
                {routes.map(route => (
                  <option key={route.route_id} value={route.route_id}>
                    {route.route_short_name} - {route.route_long_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Nombre de Ruta</label>
              <input
                type="text"
                value={tabla1.nombreRuta}
                onChange={(e) => handleTabla1Change('nombreRuta', e.target.value)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Periodicidad</label>
              <input
                type="text"
                value={tabla1.periodicidad}
                onChange={(e) => handleTabla1Change('periodicidad', e.target.value)}
                className={inputClass + " w-full"}
                placeholder="Ej: Diario, Lun-Vie"
              />
            </div>

            <div>
              <label className={labelClass}>Hora Inicio Centro</label>
              <input
                type="time"
                value={tabla1.horaInicioCentro}
                onChange={(e) => handleTabla1Change('horaInicioCentro', e.target.value)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Hora Inicio Barrio</label>
              <input
                type="time"
                value={tabla1.horaInicioBarrio}
                onChange={(e) => handleTabla1Change('horaInicioBarrio', e.target.value)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Hora Fin Centro</label>
              <input
                type="time"
                value={tabla1.horaFinCentro}
                onChange={(e) => handleTabla1Change('horaFinCentro', e.target.value)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Hora Fin Barrio</label>
              <input
                type="time"
                value={tabla1.horaFinBarrio}
                onChange={(e) => handleTabla1Change('horaFinBarrio', e.target.value)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Tiempo Recorrido C→B</label>
              <DurationInput
                value={tabla1.tiempoRecorridoCB}
                onChange={(v) => handleTabla1Change('tiempoRecorridoCB', v)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Tiempo Recorrido B→C</label>
              <DurationInput
                value={tabla1.tiempoRecorridoBC}
                onChange={(v) => handleTabla1Change('tiempoRecorridoBC', v)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Dwell Centro (seg)</label>
              <input
                type="number"
                value={tabla1.dwellCentro}
                onChange={(e) => handleTabla1Change('dwellCentro', parseInt(e.target.value) || 0)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Dwell Barrio (seg)</label>
              <input
                type="number"
                value={tabla1.dwellBarrio}
                onChange={(e) => handleTabla1Change('dwellBarrio', parseInt(e.target.value) || 0)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Distancia C→B (km)</label>
              <input
                type="number"
                step="0.01"
                value={tabla1.distanciaCB}
                onChange={(e) => handleTabla1Change('distanciaCB', parseFloat(e.target.value) || 0)}
                className={inputClass + " w-full"}
              />
            </div>

            <div>
              <label className={labelClass}>Distancia B→C (km)</label>
              <input
                type="number"
                step="0.01"
                value={tabla1.distanciaBC}
                onChange={(e) => handleTabla1Change('distanciaBC', parseFloat(e.target.value) || 0)}
                className={inputClass + " w-full"}
              />
            </div>
          </div>
        </div>

        {/* TABLA 2: Buses Variables por Hora */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 2: Buses Variables por Hora
            </h2>
            <button
              onClick={() => addRow(setTabla2, { hora: 0, buses: 0 })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Hora</th>
                  <th className={thClass}>Buses</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla2.map((row, idx) => (
                  <tr key={idx}>
                    <td className={tdClass}>
                      <input
                        type="number"
                        min="0"
                        max="23"
                        value={row.hora}
                        onChange={(e) => handleTableChange(2, idx, 'hora', parseInt(e.target.value) || 0, setTabla2)}
                        className={inputClass + " w-20"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="number"
                        min="0"
                        value={row.buses}
                        onChange={(e) => handleTableChange(2, idx, 'buses', parseInt(e.target.value) || 0, setTabla2)}
                        className={inputClass + " w-20"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla2, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 3: Tiempos de Ciclo Variables */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 3: Tiempos de Ciclo Variables
            </h2>
            <button
              onClick={() => addRow(setTabla3, { hora: 0, tCicloAB: '00:00', tCicloBA: '00:00' })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Hora</th>
                  <th className={thClass}>T Ciclo A→B</th>
                  <th className={thClass}>T Ciclo B→A</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla3.map((row, idx) => (
                  <tr key={idx}>
                    <td className={tdClass}>
                      <input
                        type="number"
                        min="0"
                        max="23"
                        value={row.hora}
                        onChange={(e) => handleTableChange(3, idx, 'hora', parseInt(e.target.value) || 0, setTabla3)}
                        className={inputClass + " w-20"}
                      />
                    </td>
                    <td className={tdClass}>
                      <DurationInput
                        value={row.tCicloAB}
                        onChange={(v) => handleTableChange(3, idx, 'tCicloAB', v, setTabla3)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <DurationInput
                        value={row.tCicloBA}
                        onChange={(v) => handleTableChange(3, idx, 'tCicloBA', v, setTabla3)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla3, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 4: Headways Centro (SE ACTUALIZARÁ CON EXCEL) */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 4: Headways Centro Calculados ✨
            </h2>
            <button
              onClick={() => addRow(setTabla4, { desde: '00:00', hasta: '00:00', headway: 0 })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Desde</th>
                  <th className={thClass}>Hasta</th>
                  <th className={thClass}>Headway (min)</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla4.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.desde}
                        onChange={(e) => handleTableChange(4, idx, 'desde', e.target.value, setTabla4)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.hasta}
                        onChange={(e) => handleTableChange(4, idx, 'hasta', e.target.value, setTabla4)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="number"
                        min="0"
                        value={row.headway}
                        onChange={(e) => handleTableChange(4, idx, 'headway', parseInt(e.target.value) || 0, setTabla4)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla4, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 5: Headways Barrio (SE ACTUALIZARÁ CON EXCEL) */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 5: Headways Barrio Calculados ✨
            </h2>
            <button
              onClick={() => addRow(setTabla5, { desde: '00:00', hasta: '00:00', headway: 0 })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Desde</th>
                  <th className={thClass}>Hasta</th>
                  <th className={thClass}>Headway (min)</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla5.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.desde}
                        onChange={(e) => handleTableChange(5, idx, 'desde', e.target.value, setTabla5)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.hasta}
                        onChange={(e) => handleTableChange(5, idx, 'hasta', e.target.value, setTabla5)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="number"
                        min="0"
                        value={row.headway}
                        onChange={(e) => handleTableChange(5, idx, 'headway', parseInt(e.target.value) || 0, setTabla5)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla5, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 6: Recorridos Centro (SE ACTUALIZARÁ CON EXCEL) */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 6: Recorridos Centro Calculados ✨
            </h2>
            <button
              onClick={() => addRow(setTabla6, { desde: '00:00', hasta: '00:00', recorridoAB: '00:00' })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Desde</th>
                  <th className={thClass}>Hasta</th>
                  <th className={thClass}>Recorrido</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla6.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.desde}
                        onChange={(e) => handleTableChange(6, idx, 'desde', e.target.value, setTabla6)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.hasta}
                        onChange={(e) => handleTableChange(6, idx, 'hasta', e.target.value, setTabla6)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <DurationInput
                        value={row.recorridoAB}
                        onChange={(v) => handleTableChange(6, idx, 'recorridoAB', v, setTabla6)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla6, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 7: Recorridos Barrio (SE ACTUALIZARÁ CON EXCEL) */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 7: Recorridos Barrio Calculados ✨
            </h2>
            <button
              onClick={() => addRow(setTabla7, { desde: '00:00', hasta: '00:00', recorridoBA: '00:00' })}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
            >
              + Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Desde</th>
                  <th className={thClass}>Hasta</th>
                  <th className={thClass}>Recorrido</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tabla7.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.desde}
                        onChange={(e) => handleTableChange(7, idx, 'desde', e.target.value, setTabla7)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <input
                        type="time"
                        value={row.hasta}
                        onChange={(e) => handleTableChange(7, idx, 'hasta', e.target.value, setTabla7)}
                        className={inputClass + " w-32"}
                      />
                    </td>
                    <td className={tdClass}>
                      <DurationInput
                        value={row.recorridoBA}
                        onChange={(v) => handleTableChange(7, idx, 'recorridoBA', v, setTabla7)}
                        className={inputClass + " w-24"}
                      />
                    </td>
                    <td className={tdClass}>
                      <button
                        onClick={() => removeRow(setTabla7, idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}