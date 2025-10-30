import { useState, useEffect } from 'react';

export default function SchedulingParametersV2() {
  const [tabla1, setTabla1] = useState({
    numeroRuta: '',
    nombreRuta: '',
    periodicidad: '',
    horaInicioCentro: '',
    horaInicioBarrio: '',
    horaFinCentro: '',
    horaFinBarrio: '',
    dwellCentro: 0,
    dwellBarrio: 0,
    distanciaCB: 0,
    distanciaBC: 0
  });

  const [tabla2, setTabla2] = useState([]);
  const [tabla3, setTabla3] = useState([]);
  const [tabla4, setTabla4] = useState([]);
  const [tabla5, setTabla5] = useState([]);
  const [tabla6, setTabla6] = useState([]);
  const [tabla7, setTabla7] = useState([]);

  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [status, setStatus] = useState({ message: '', type: '' });

  useEffect(() => {
    loadFromLocalStorage();
  }, []);

  const loadFromLocalStorage = () => {
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
      } catch (err) {
        console.error('Error:', err);
      }
    }
  };

  const isValidTimeFormat = (time) => {
    if (!time) return false;
    return /^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$/.test(time);
  };

  const validateTimes = () => {
    const errors = [];
    const timeFields = [
      { key: 'horaInicioCentro', label: 'Hora Inicio Centro' },
      { key: 'horaInicioBarrio', label: 'Hora Inicio Barrio' },
      { key: 'horaFinCentro', label: 'Hora Fin Centro' },
      { key: 'horaFinBarrio', label: 'Hora Fin Barrio' }
    ];

    timeFields.forEach(field => {
      const value = tabla1[field.key];
      if (!value) {
        errors.push(`${field.label} requerido`);
      } else if (!isValidTimeFormat(value)) {
        errors.push(`${field.label}: formato inválido`);
      }
    });

    tabla2.forEach((row, idx) => {
      if (!isValidTimeFormat(row.desde)) {
        errors.push(`Tabla 2 fila ${idx + 1}: hora inválida`);
      }
    });

    tabla3.forEach((row, idx) => {
      if (!isValidTimeFormat(row.desde)) errors.push(`Tabla 3 fila ${idx + 1}: Desde inválido`);
      if (!isValidTimeFormat(row.tiempoCB)) errors.push(`Tabla 3 fila ${idx + 1}: C→B inválido`);
      if (!isValidTimeFormat(row.tiempoBC)) errors.push(`Tabla 3 fila ${idx + 1}: B→C inválido`);
    });

    return errors;
  };

  const handleTabla1Change = (field, value) => {
    setTabla1(prev => ({ ...prev, [field]: value }));
  };

  const addTabla2Row = () => setTabla2([...tabla2, { desde: '', buses: 0 }]);
  const updateTabla2Row = (index, field, value) => {
    const newTabla2 = [...tabla2];
    newTabla2[index][field] = value;
    setTabla2(newTabla2);
  };
  const deleteTabla2Row = (index) => setTabla2(tabla2.filter((_, i) => i !== index));

  const addTabla3Row = () => setTabla3([...tabla3, { desde: '', tiempoCB: '', tiempoBC: '', tiempoCiclo: '' }]);
  const updateTabla3Row = (index, field, value) => {
    const newTabla3 = [...tabla3];
    newTabla3[index][field] = value;
    
    if (field === 'tiempoCB' || field === 'tiempoBC') {
      const tiempoCB = field === 'tiempoCB' ? value : newTabla3[index].tiempoCB;
      const tiempoBC = field === 'tiempoBC' ? value : newTabla3[index].tiempoBC;
      
      if (isValidTimeFormat(tiempoCB) && isValidTimeFormat(tiempoBC)) {
        const [h1, m1] = tiempoCB.split(':').map(Number);
        const [h2, m2] = tiempoBC.split(':').map(Number);
        const totalMinutes = (h1 * 60 + m1) + (h2 * 60 + m2);
        const h = Math.floor(totalMinutes / 60);
        const m = totalMinutes % 60;
        newTabla3[index].tiempoCiclo = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      }
    }
    
    setTabla3(newTabla3);
  };
  const deleteTabla3Row = (index) => setTabla3(tabla3.filter((_, i) => i !== index));

  const handleCalculate = async () => {
    const errors = validateTimes();
    if (errors.length > 0) {
      setStatus({ message: `❌ Errores:\n${errors.join('\n')}`, type: 'error' });
      return;
    }
    if (tabla2.length === 0) {
      setStatus({ message: '❌ Agregue filas en Tabla 2', type: 'error' });
      return;
    }
    if (tabla3.length === 0) {
      setStatus({ message: '❌ Agregue filas en Tabla 3', type: 'error' });
      return;
    }

    setCalculating(true);
    setStatus({ message: '⏳ Calculando...', type: 'loading' });

    try {
      const payload = { tabla1, tabla2, tabla3 };
      const response = await fetch('http://localhost:8000/scheduling/calculate-intervals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al calcular');
      }

      const result = await response.json();
      setTabla4(result.tabla4 || []);
      setTabla5(result.tabla5 || []);
      setTabla6(result.tabla6 || []);
      setTabla7(result.tabla7 || []);

      setStatus({ message: `✅ Completado en ${result.tiempo_procesamiento}`, type: 'success' });
      setTimeout(() => setStatus({ message: '', type: '' }), 3000);
    } catch (err) {
      setStatus({ message: `❌ ${err.message}`, type: 'error' });
    } finally {
      setCalculating(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setStatus({ message: 'Guardando...', type: 'loading' });
    try {
      const data = { tabla1, tabla2, tabla3, tabla4, tabla5, tabla6, tabla7 };
      localStorage.setItem('schedulingParamsComplete', JSON.stringify(data));
      const response = await fetch('http://localhost:8000/scheduling/parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (response.ok) {
        setStatus({ message: '✅ Guardado', type: 'success' });
        setTimeout(() => setStatus({ message: '', type: '' }), 2000);
      } else {
        throw new Error('Error al guardar');
      }
    } catch (err) {
      setStatus({ message: `❌ ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-3">
      <div className="mb-3">
        <h1 className="text-lg font-bold mb-1">Parámetros de Programación</h1>
        <p className="text-xs text-gray-600">ℹ️ Formato <strong>HH:MM</strong> (ej: 05:30)</p>
      </div>

      <div className="flex gap-2 mb-3">
        <button onClick={handleCalculate} disabled={calculating}
          className="px-3 py-1.5 text-sm rounded font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400">
          {calculating ? '⏳ Calculando...' : '🔢 Calcular'}
        </button>
        <button onClick={handleSave} disabled={loading}
          className="px-3 py-1.5 text-sm rounded font-semibold bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-400">
          {loading ? '💾 Guardando...' : '💾 Guardar'}
        </button>
      </div>

      {status.message && (
        <div className={`p-2 mb-3 rounded text-sm whitespace-pre-line ${
          status.type === 'success' ? 'bg-green-100 text-green-800' :
          status.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
        }`}>
          {status.message}
        </div>
      )}

      {/* TABLA 1 */}
      <div className="bg-white p-3 rounded shadow mb-3">
        <h2 className="text-sm font-semibold mb-2 pb-1 border-b">Tabla 1: Parámetros Generales</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div>
            <label className="block text-xs font-medium mb-1">Número Ruta</label>
            <input type="text" value={tabla1.numeroRuta} onChange={(e) => handleTabla1Change('numeroRuta', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="100" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Nombre Ruta</label>
            <input type="text" value={tabla1.nombreRuta} onChange={(e) => handleTabla1Change('nombreRuta', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="PRUEBA RUTA 100" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Periodicidad</label>
            <input type="text" value={tabla1.periodicidad} onChange={(e) => handleTabla1Change('periodicidad', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="L-V" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Hora Inicio Centro</label>
            <input type="text" value={tabla1.horaInicioCentro} onChange={(e) => handleTabla1Change('horaInicioCentro', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="03:54" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Hora Inicio Barrio</label>
            <input type="text" value={tabla1.horaInicioBarrio} onChange={(e) => handleTabla1Change('horaInicioBarrio', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="04:30" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Hora Fin Centro</label>
            <input type="text" value={tabla1.horaFinCentro} onChange={(e) => handleTabla1Change('horaFinCentro', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="22:58" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Hora Fin Barrio</label>
            <input type="text" value={tabla1.horaFinBarrio} onChange={(e) => handleTabla1Change('horaFinBarrio', e.target.value)}
              className="w-full p-1 text-sm border rounded" placeholder="22:46" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Dwell Centro (seg)</label>
            <input type="number" value={tabla1.dwellCentro} onChange={(e) => handleTabla1Change('dwellCentro', parseInt(e.target.value) || 0)}
              className="w-full p-1 text-sm border rounded" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Dwell Barrio (seg)</label>
            <input type="number" value={tabla1.dwellBarrio} onChange={(e) => handleTabla1Change('dwellBarrio', parseInt(e.target.value) || 0)}
              className="w-full p-1 text-sm border rounded" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Distancia C→B (km)</label>
            <input type="number" step="0.1" value={tabla1.distanciaCB} onChange={(e) => handleTabla1Change('distanciaCB', parseFloat(e.target.value) || 0)}
              className="w-full p-1 text-sm border rounded" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Distancia B→C (km)</label>
            <input type="number" step="0.1" value={tabla1.distanciaBC} onChange={(e) => handleTabla1Change('distanciaBC', parseFloat(e.target.value) || 0)}
              className="w-full p-1 text-sm border rounded" />
          </div>
        </div>
      </div>

      {/* TABLA 2 */}
      <div className="bg-white p-3 rounded shadow mb-3">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-sm font-semibold">Tabla 2: Flota Variable</h2>
          <button onClick={addTabla2Row} className="px-3 py-1 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700">
            ➕ Añadir
          </button>
        </div>
        {tabla2.length === 0 ? (
          <p className="text-xs text-gray-500 italic">Sin filas. Click en "Añadir".</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-1 text-left text-xs">Desde (HH:MM)</th>
                <th className="border p-1 text-left text-xs">Buses</th>
                <th className="border p-1 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {tabla2.map((row, idx) => (
                <tr key={idx}>
                  <td className="border p-1">
                    <input type="text" value={row.desde} onChange={(e) => updateTabla2Row(idx, 'desde', e.target.value)}
                      className="w-full p-1 text-sm border rounded" placeholder="05:00" />
                  </td>
                  <td className="border p-1">
                    <input type="number" value={row.buses} onChange={(e) => updateTabla2Row(idx, 'buses', parseInt(e.target.value) || 0)}
                      className="w-full p-1 text-sm border rounded" />
                  </td>
                  <td className="border p-1 text-center">
                    <button onClick={() => deleteTabla2Row(idx)} className="text-red-600 hover:text-red-800">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* TABLA 3 */}
      <div className="bg-white p-3 rounded shadow mb-3">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-sm font-semibold">Tabla 3: Tiempos de Recorrido</h2>
          <button onClick={addTabla3Row} className="px-3 py-1 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700">
            ➕ Añadir
          </button>
        </div>
        {tabla3.length === 0 ? (
          <p className="text-xs text-gray-500 italic">Sin filas. Click en "Añadir".</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-1 text-left text-xs">Desde</th>
                <th className="border p-1 text-left text-xs">C→B</th>
                <th className="border p-1 text-left text-xs">B→C</th>
                <th className="border p-1 text-left text-xs">Ciclo</th>
                <th className="border p-1 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {tabla3.map((row, idx) => (
                <tr key={idx}>
                  <td className="border p-1">
                    <input type="text" value={row.desde} onChange={(e) => updateTabla3Row(idx, 'desde', e.target.value)}
                      className="w-full p-1 text-sm border rounded" placeholder="05:00" />
                  </td>
                  <td className="border p-1">
                    <input type="text" value={row.tiempoCB} onChange={(e) => updateTabla3Row(idx, 'tiempoCB', e.target.value)}
                      className="w-full p-1 text-sm border rounded" placeholder="00:36" />
                  </td>
                  <td className="border p-1">
                    <input type="text" value={row.tiempoBC} onChange={(e) => updateTabla3Row(idx, 'tiempoBC', e.target.value)}
                      className="w-full p-1 text-sm border rounded" placeholder="00:36" />
                  </td>
                  <td className="border p-1 bg-gray-50">
                    <input type="text" value={row.tiempoCiclo} readOnly
                      className="w-full p-1 text-xs border rounded bg-gray-100" />
                  </td>
                  <td className="border p-1 text-center">
                    <button onClick={() => deleteTabla3Row(idx)} className="text-red-600 hover:text-red-800">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* RESULTADOS */}
      {tabla4.length > 0 && (
        <div className="bg-white p-3 rounded shadow mb-3">
          <h2 className="text-sm font-semibold mb-2">✨ Tabla 4: Intervalos Centro</h2>
          <table className="w-full border-collapse text-xs">
            <thead className="bg-green-100">
              <tr>
                <th className="border p-1">Desde</th>
                <th className="border p-1">Hasta</th>
                <th className="border p-1">Headway</th>
              </tr>
            </thead>
            <tbody>
              {tabla4.map((row, idx) => (
                <tr key={idx} className="bg-green-50">
                  <td className="border p-1">{row.desde}</td>
                  <td className="border p-1">{row.hasta}</td>
                  <td className="border p-1">{row.headway} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tabla5.length > 0 && (
        <div className="bg-white p-3 rounded shadow mb-3">
          <h2 className="text-sm font-semibold mb-2">✨ Tabla 5: Intervalos Barrio</h2>
          <table className="w-full border-collapse text-xs">
            <thead className="bg-blue-100">
              <tr>
                <th className="border p-1">Desde</th>
                <th className="border p-1">Hasta</th>
                <th className="border p-1">Headway</th>
              </tr>
            </thead>
            <tbody>
              {tabla5.map((row, idx) => (
                <tr key={idx} className="bg-blue-50">
                  <td className="border p-1">{row.desde}</td>
                  <td className="border p-1">{row.hasta}</td>
                  <td className="border p-1">{row.headway} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tabla6.length > 0 && (
        <div className="bg-white p-3 rounded shadow mb-3">
          <h2 className="text-sm font-semibold mb-2">✨ Tabla 6: Tiempos C→B</h2>
          <table className="w-full border-collapse text-xs">
            <thead className="bg-yellow-100">
              <tr>
                <th className="border p-1">Desde</th>
                <th className="border p-1">Hasta</th>
                <th className="border p-1">Tiempo</th>
              </tr>
            </thead>
            <tbody>
              {tabla6.map((row, idx) => (
                <tr key={idx} className="bg-yellow-50">
                  <td className="border p-1">{row.desde}</td>
                  <td className="border p-1">{row.hasta}</td>
                  <td className="border p-1">{row.tiempo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tabla7.length > 0 && (
        <div className="bg-white p-3 rounded shadow mb-3">
          <h2 className="text-sm font-semibold mb-2">✨ Tabla 7: Tiempos B→C</h2>
          <table className="w-full border-collapse text-xs">
            <thead className="bg-purple-100">
              <tr>
                <th className="border p-1">Desde</th>
                <th className="border p-1">Hasta</th>
                <th className="border p-1">Tiempo</th>
              </tr>
            </thead>
            <tbody>
              {tabla7.map((row, idx) => (
                <tr key={idx} className="bg-purple-50">
                  <td className="border p-1">{row.desde}</td>
                  <td className="border p-1">{row.hasta}</td>
                  <td className="border p-1">{row.tiempo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}