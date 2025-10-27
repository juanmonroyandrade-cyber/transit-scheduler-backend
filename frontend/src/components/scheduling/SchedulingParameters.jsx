import { useState, useEffect } from 'react';

/**
 * Componente DurationInput (sin cambios)
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
  // Estados para las 7 tablas (igual que antes)
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

  // ✅ NUEVO: Estados para resultados del Excel
  const [excelResults, setExcelResults] = useState(null);
  const [processingExcel, setProcessingExcel] = useState(false);

  const [routes, setRoutes] = useState([]);
  const [shapes, setShapes] = useState([]);
  const [status, setStatus] = useState({ message: '', type: '' });
  const [loading, setLoading] = useState(false);

  // Cargar rutas y shapes (igual que antes)
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

  // ✅ NUEVO: Función para ejecutar el procesamiento de Excel
  const handleExecuteExcel = async () => {
    setProcessingExcel(true);
    setStatus({ message: 'Procesando Excel...', type: 'loading' });
    setExcelResults(null);

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
      
      setExcelResults(result.results);
      setStatus({
        message: `✅ Excel procesado correctamente! Se obtuvieron ${
          result.results.tabla4.length + result.results.tabla5.length +
          result.results.tabla6.length + result.results.tabla7.length
        } filas de resultados`,
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

  // Guardar parámetros (igual que antes)
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
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Parámetros de Programación</h1>
          <div className="flex gap-3">
            {/* ✅ NUEVO: Botón para ejecutar el Excel */}
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

        {status.message && (
          <div className={`p-4 mb-6 rounded-md ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
              status.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
                'bg-blue-100 text-blue-800 border border-blue-200'
          }`}>
            {status.message}
          </div>
        )}

        {/* ✅ NUEVO: Mostrar resultados del Excel */}
        {excelResults && (
          <div className={sectionClass}>
            <h2 className="text-xl font-semibold mb-4 text-green-700 border-b pb-2">
              ✅ Resultados del Excel
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tabla 4 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Tabla 4</h3>
                <div className="overflow-auto max-h-60 border rounded">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Columna 1</th>
                        <th className="px-3 py-2 text-left">Columna 2</th>
                        <th className="px-3 py-2 text-left">Columna 3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {excelResults.tabla4.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2">{row[0]}</td>
                          <td className="px-3 py-2">{row[1]}</td>
                          <td className="px-3 py-2">{row[2]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Tabla 5 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Tabla 5</h3>
                <div className="overflow-auto max-h-60 border rounded">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Columna 1</th>
                        <th className="px-3 py-2 text-left">Columna 2</th>
                        <th className="px-3 py-2 text-left">Columna 3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {excelResults.tabla5.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2">{row[0]}</td>
                          <td className="px-3 py-2">{row[1]}</td>
                          <td className="px-3 py-2">{row[2]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Tabla 6 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Tabla 6</h3>
                <div className="overflow-auto max-h-60 border rounded">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Columna 1</th>
                        <th className="px-3 py-2 text-left">Columna 2</th>
                        <th className="px-3 py-2 text-left">Columna 3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {excelResults.tabla6.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2">{row[0]}</td>
                          <td className="px-3 py-2">{row[1]}</td>
                          <td className="px-3 py-2">{row[2]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Tabla 7 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Tabla 7</h3>
                <div className="overflow-auto max-h-60 border rounded">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Columna 1</th>
                        <th className="px-3 py-2 text-left">Columna 2</th>
                        <th className="px-3 py-2 text-left">Columna 3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {excelResults.tabla7.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2">{row[0]}</td>
                          <td className="px-3 py-2">{row[1]}</td>
                          <td className="px-3 py-2">{row[2]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* RESTO DE LAS TABLAS (1-7) - IGUAL QUE ANTES */}
        {/* Por brevedad, no repito todo el código de las tablas */}
        {/* Copia el resto del código de las 7 tablas desde tu archivo original */}

      </div>
    </div>
  );
}