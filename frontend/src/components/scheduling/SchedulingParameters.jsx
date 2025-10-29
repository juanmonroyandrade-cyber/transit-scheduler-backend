// frontend/src/components/scheduling/SchedulingParametersV2.jsx
import React, { useState, useEffect } from 'react';

export default function SchedulingParametersV2() {
  // ============================================================
  // ESTADOS - TABLAS DE ENTRADA (1-3)
  // ============================================================
  const [tabla1, setTabla1] = useState({
    horaInicio: '',
    horaFin: '',
    dwellCentro: '00:00',
    dwellBarrio: '00:00'
  });

  const [tabla2, setTabla2] = useState([]); // Flota Variable: [{desde: "HH:MM", buses: 0}]
  const [tabla3, setTabla3] = useState([]); // Tiempos Recorrido: [{horaCambio: "HH:MM", tCentroBarrio: "HH:MM", tBarrioCentro: "HH:MM"}]

  // ============================================================
  // ESTADOS - TABLAS DE RESULTADOS (4-7)
  // ============================================================
  const [tabla4, setTabla4] = useState([]); // Intervalos Centro: [{desde: "HH:MM", hasta: "HH:MM", headway: 0}]
  const [tabla5, setTabla5] = useState([]); // Intervalos Barrio: [{desde: "HH:MM", hasta: "HH:MM", headway: 0}]
  const [tabla6, setTabla6] = useState([]); // Recorridos C→B: [{desde: "HH:MM", hasta: "HH:MM", recorridoCentroBarrio: "HH:MM"}]
  const [tabla7, setTabla7] = useState([]); // Recorridos B→C: [{desde: "HH:MM", hasta: "HH:MM", recorridoBarrioCentro: "HH:MM"}]

  // ============================================================
  // ESTADOS GENERALES
  // ============================================================
  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [status, setStatus] = useState({ message: '', type: '' });

  // ============================================================
  // ESTILOS REUTILIZABLES
  // ============================================================
  const sectionClass = "bg-white p-6 rounded-lg shadow-md mb-6";
  const tableClass = "min-w-full table-auto border-collapse border border-gray-300";
  const thClass = "bg-blue-600 text-white px-4 py-2 border border-gray-300 text-sm font-semibold";
  const tdClass = "px-4 py-2 border border-gray-300 text-center";
  const inputClass = "px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const buttonClass = "px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm font-medium";
  const resultThClass = "bg-green-600 text-white px-4 py-2 border border-gray-300 text-sm font-semibold";

  // ============================================================
  // CARGAR DATOS ACTIVOS AL MONTAR COMPONENTE
  // ============================================================
  useEffect(() => {
    loadActiveParameters();
  }, []);

  const loadActiveParameters = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/scheduling/parameters/active');
      
      if (res.ok) {
        const data = await res.json();
        if (data) {
          // Cargar tablas 1-3 (entradas)
          setTabla1(data.tabla1 || { horaInicio: '', horaFin: '', dwellCentro: '00:00', dwellBarrio: '00:00' });
          setTabla2(data.tabla2 || []);
          setTabla3(data.tabla3 || []);
          
          // Cargar tablas 4-7 (resultados)
          setTabla4(data.tabla4 || []);
          setTabla5(data.tabla5 || []);
          setTabla6(data.tabla6 || []);
          setTabla7(data.tabla7 || []);
          
          setStatus({ message: 'Datos cargados correctamente', type: 'success' });
        } else {
          setStatus({ message: 'No hay parámetros guardados. Comienza ingresando nuevos datos.', type: 'info' });
        }
      }
    } catch (error) {
      console.error('Error al cargar parámetros:', error);
      setStatus({ message: `Error: ${error.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // FUNCIONES PARA AÑADIR/ELIMINAR FILAS
  // ============================================================
  const addRowTabla2 = () => {
    setTabla2([...tabla2, { desde: '00:00', buses: 0 }]);
  };

  const removeRowTabla2 = (index) => {
    setTabla2(tabla2.filter((_, i) => i !== index));
  };

  const updateRowTabla2 = (index, field, value) => {
    const updated = [...tabla2];
    updated[index][field] = value;
    setTabla2(updated);
  };

  const addRowTabla3 = () => {
    setTabla3([...tabla3, { horaCambio: '', tCentroBarrio: '', tBarrioCentro: '' }]);
  };

  const removeRowTabla3 = (index) => {
    setTabla3(tabla3.filter((_, i) => i !== index));
  };

  const updateRowTabla3 = (index, field, value) => {
    const updated = [...tabla3];
    updated[index][field] = value;
    setTabla3(updated);
  };

  // ============================================================
  // VALIDACIÓN Y CÁLCULO
  // ============================================================
  const handleCalculate = async () => {
    // Validar datos obligatorios
    if (!tabla1.horaInicio || !tabla1.horaFin) {
      setStatus({ message: 'Por favor completa Hora Inicio y Hora Fin', type: 'error' });
      return;
    }

    if (!tabla1.dwellCentro || !tabla1.dwellBarrio) {
      setStatus({ message: 'Por favor completa los tiempos de Dwell (parada) en Centro y Barrio', type: 'error' });
      return;
    }

    if (tabla2.length === 0) {
      setStatus({ message: 'Por favor añade al menos una fila en Flota Variable (Tabla 2)', type: 'error' });
      return;
    }

    if (tabla3.length === 0) {
      setStatus({ message: 'Por favor añade al menos una fila en Tiempos de Recorrido (Tabla 3)', type: 'error' });
      return;
    }

    try {
      setCalculating(true);
      setStatus({ message: 'Calculando intervalos de paso...', type: 'loading' });

      const payload = {
        tabla1,
        tabla2,
        tabla3
      };

      console.log('📤 Enviando datos al backend:', payload);

      const res = await fetch('http://localhost:8000/scheduling/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Error al calcular');
      }

      const result = await res.json();
      console.log('✅ Resultados recibidos:', result);

      // Actualizar tablas 4-7 con los resultados
      setTabla4(result.tabla4 || []);
      setTabla5(result.tabla5 || []);
      setTabla6(result.tabla6 || []);
      setTabla7(result.tabla7 || []);

      setStatus({ message: '¡Cálculo completado exitosamente!', type: 'success' });

    } catch (error) {
      console.error('Error al calcular:', error);
      setStatus({ message: `Error: ${error.message}`, type: 'error' });
    } finally {
      setCalculating(false);
    }
  };

  // ============================================================
  // LIMPIAR FORMULARIO
  // ============================================================
  const handleClear = () => {
    setTabla1({ horaInicio: '', horaFin: '', dwellCentro: '00:00', dwellBarrio: '00:00' });
    setTabla2([]);
    setTabla3([]);
    setTabla4([]);
    setTabla5([]);
    setTabla6([]);
    setTabla7([]);
    setStatus({ message: 'Formulario limpiado', type: 'info' });
  };

  // ============================================================
  // RENDERIZADO
  // ============================================================
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-700 text-lg">Cargando parámetros...</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-100 min-h-screen">
      <div className="max-w-7xl mx-auto">
        
        {/* ENCABEZADO */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Cálculo de Intervalos de Paso
          </h1>
          <p className="text-gray-600">
            Ingresa los parámetros de operación (Tablas 1-3) y calcula los intervalos de paso (Tablas 4-7)
          </p>
        </div>

        {/* MENSAJES DE ESTADO */}
        {status.message && (
          <div className={`p-4 mb-6 rounded-md text-sm border ${
            status.type === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
            status.type === 'error' ? 'bg-red-100 text-red-800 border-red-200' :
            status.type === 'info' ? 'bg-blue-100 text-blue-800 border-blue-200' :
            'bg-yellow-100 text-yellow-800 border-yellow-200'
          }`}>
            {status.message}
          </div>
        )}

        {/* BOTONES DE ACCIÓN PRINCIPALES */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-6 flex gap-4 justify-end">
          <button
            onClick={handleCalculate}
            disabled={calculating}
            className="px-6 py-3 bg-green-600 text-white font-semibold rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {calculating ? '⏳ Calculando...' : '🚀 Calcular Intervalos'}
          </button>
          <button
            onClick={handleClear}
            className="px-6 py-3 bg-gray-600 text-white font-semibold rounded-md hover:bg-gray-700"
          >
            🗑️ Limpiar Todo
          </button>
        </div>

        {/* ========== TABLAS DE ENTRADA (1-3) ========== */}
        
        {/* TABLA 1: Parámetros Generales */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Tabla 1: Parámetros Generales
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hora Inicio (HH:MM) <span className="text-red-500">*</span>
              </label>
              <input
                type="time"
                value={tabla1.horaInicio}
                onChange={(e) => setTabla1({ ...tabla1, horaInicio: e.target.value })}
                className={inputClass + " w-full"}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hora Fin (HH:MM) <span className="text-red-500">*</span>
              </label>
              <input
                type="time"
                value={tabla1.horaFin}
                onChange={(e) => setTabla1({ ...tabla1, horaFin: e.target.value })}
                className={inputClass + " w-full"}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dwell Centro (HH:MM) <span className="text-red-500">*</span>
              </label>
              <input
                type="time"
                value={tabla1.dwellCentro}
                onChange={(e) => setTabla1({ ...tabla1, dwellCentro: e.target.value })}
                className={inputClass + " w-full"}
                placeholder="00:00"
              />
              <p className="text-xs text-gray-500 mt-1">Tiempo de parada en Centro</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dwell Barrio (HH:MM) <span className="text-red-500">*</span>
              </label>
              <input
                type="time"
                value={tabla1.dwellBarrio}
                onChange={(e) => setTabla1({ ...tabla1, dwellBarrio: e.target.value })}
                className={inputClass + " w-full"}
                placeholder="00:00"
              />
              <p className="text-xs text-gray-500 mt-1">Tiempo de parada en Barrio</p>
            </div>
          </div>
        </div>

        {/* TABLA 2: Flota Variable */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 2: Flota Variable
            </h2>
            <button onClick={addRowTabla2} className={buttonClass}>
              ➕ Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Desde (HH:MM)</th>
                  <th className={thClass}>Cantidad de Buses</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white">
                {tabla2.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="text-center py-4 text-gray-500">
                      No hay datos. Haz clic en "Añadir Fila" para empezar.
                    </td>
                  </tr>
                ) : (
                  tabla2.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input
                          type="time"
                          value={row.desde}
                          onChange={(e) => updateRowTabla2(idx, 'desde', e.target.value)}
                          className={inputClass}
                        />
                      </td>
                      <td className={tdClass}>
                        <input
                          type="number"
                          min="0"
                          value={row.buses}
                          onChange={(e) => updateRowTabla2(idx, 'buses', parseInt(e.target.value) || 0)}
                          className={inputClass + " w-24"}
                        />
                      </td>
                      <td className={tdClass}>
                        <button
                          onClick={() => removeRowTabla2(idx)}
                          className="text-red-600 hover:text-red-800 font-semibold"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 3: Tiempos de Recorrido */}
        <div className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-700">
              Tabla 3: Tiempos de Recorrido Variables
            </h2>
            <button onClick={addRowTabla3} className={buttonClass}>
              ➕ Añadir Fila
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Hora Cambio</th>
                  <th className={thClass}>T. Centro → Barrio</th>
                  <th className={thClass}>T. Barrio → Centro</th>
                  <th className={thClass}>Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white">
                {tabla3.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="text-center py-4 text-gray-500">
                      No hay datos. Haz clic en "Añadir Fila" para empezar.
                    </td>
                  </tr>
                ) : (
                  tabla3.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>
                        <input
                          type="time"
                          value={row.horaCambio}
                          onChange={(e) => updateRowTabla3(idx, 'horaCambio', e.target.value)}
                          className={inputClass}
                          placeholder="HH:MM"
                        />
                      </td>
                      <td className={tdClass}>
                        <input
                          type="time"
                          value={row.tCentroBarrio}
                          onChange={(e) => updateRowTabla3(idx, 'tCentroBarrio', e.target.value)}
                          className={inputClass}
                          placeholder="HH:MM"
                        />
                      </td>
                      <td className={tdClass}>
                        <input
                          type="time"
                          value={row.tBarrioCentro}
                          onChange={(e) => updateRowTabla3(idx, 'tBarrioCentro', e.target.value)}
                          className={inputClass}
                          placeholder="HH:MM"
                        />
                      </td>
                      <td className={tdClass}>
                        <button
                          onClick={() => removeRowTabla3(idx)}
                          className="text-red-600 hover:text-red-800 font-semibold"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            💡 El tiempo de ciclo se calcula automáticamente: T.C-B + T.B-C + Dwell Centro + Dwell Barrio
          </p>
        </div>

        {/* ========== TABLAS DE RESULTADOS (4-7) ========== */}
        
        {/* TABLA 4: Intervalos de Paso en Centro */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Tabla 4: Intervalos de Paso en Centro (Resultados)
          </h2>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={resultThClass}>Desde</th>
                  <th className={resultThClass}>Hasta</th>
                  <th className={resultThClass}>Headway (min)</th>
                </tr>
              </thead>
              <tbody className="bg-gray-50">
                {tabla4.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="text-center py-4 text-gray-500">
                      No hay resultados. Haz clic en "Calcular Intervalos" para generar.
                    </td>
                  </tr>
                ) : (
                  tabla4.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>{row.desde}</td>
                      <td className={tdClass}>{row.hasta}</td>
                      <td className={tdClass}>{row.headway}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 5: Intervalos de Paso en Barrio */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Tabla 5: Intervalos de Paso en Barrio (Resultados)
          </h2>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={resultThClass}>Desde</th>
                  <th className={resultThClass}>Hasta</th>
                  <th className={resultThClass}>Headway (min)</th>
                </tr>
              </thead>
              <tbody className="bg-gray-50">
                {tabla5.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="text-center py-4 text-gray-500">
                      No hay resultados. Haz clic en "Calcular Intervalos" para generar.
                    </td>
                  </tr>
                ) : (
                  tabla5.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>{row.desde}</td>
                      <td className={tdClass}>{row.hasta}</td>
                      <td className={tdClass}>{row.headway}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 6: Tiempos de Recorrido Centro→Barrio */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Tabla 6: Tiempos de Recorrido Centro→Barrio (Resultados)
          </h2>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={resultThClass}>Desde</th>
                  <th className={resultThClass}>Hasta</th>
                  <th className={resultThClass}>Recorrido Centro→Barrio</th>
                </tr>
              </thead>
              <tbody className="bg-gray-50">
                {tabla6.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="text-center py-4 text-gray-500">
                      No hay resultados. Haz clic en "Calcular Intervalos" para generar.
                    </td>
                  </tr>
                ) : (
                  tabla6.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>{row.desde}</td>
                      <td className={tdClass}>{row.hasta}</td>
                      <td className={tdClass}>{row.recorridoCentroBarrio}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* TABLA 7: Tiempos de Recorrido Barrio→Centro */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            Tabla 7: Tiempos de Recorrido Barrio→Centro (Resultados)
          </h2>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={resultThClass}>Desde</th>
                  <th className={resultThClass}>Hasta</th>
                  <th className={resultThClass}>Recorrido Barrio→Centro</th>
                </tr>
              </thead>
              <tbody className="bg-gray-50">
                {tabla7.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="text-center py-4 text-gray-500">
                      No hay resultados. Haz clic en "Calcular Intervalos" para generar.
                    </td>
                  </tr>
                ) : (
                  tabla7.map((row, idx) => (
                    <tr key={idx}>
                      <td className={tdClass}>{row.desde}</td>
                      <td className={tdClass}>{row.hasta}</td>
                      <td className={tdClass}>{row.recorridoBarrioCentro}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}