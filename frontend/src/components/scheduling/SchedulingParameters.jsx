// frontend/src/components/scheduling/SchedulingParametersV3.jsx

import React, { useState, useEffect } from 'react';
import './SchedulingParameters.css';

function SchedulingParametersV3() {
  // ==================== ESTADOS ====================
  
  // Rutas disponibles
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  
  // Tabla 1: Parámetros generales
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

  // Tabla 2: Flota Variable
  const [tabla2, setTabla2] = useState([
    { desde: '', buses: 0 }
  ]);

  // Tabla 3: Tiempos de Recorrido
  const [tabla3, setTabla3] = useState([
    { desde: '', tiempoCB: '', tiempoBC: '', tiempoCiclo: '' }
  ]);

  // Tablas 4-7: Resultados (solo lectura)
  const [tabla4, setTabla4] = useState([]);
  const [tabla5, setTabla5] = useState([]);
  const [tabla6, setTabla6] = useState([]);
  const [tabla7, setTabla7] = useState([]);

  // Estados de UI
  const [loading, setLoading] = useState(false);
  const [calculando, setCalculando] = useState(false);
  const [status, setStatus] = useState({ message: '', type: '' });
  
  // Estados para modales
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [scenarioName, setScenarioName] = useState('');
  const [savedScenarios, setSavedScenarios] = useState([]);
  const [loadingScenarios, setLoadingScenarios] = useState(false);

  // ==================== EFECTOS ====================

  // Cargar rutas al montar
  useEffect(() => {
    fetchRoutes();
  }, []);

  // Cargar distancias cuando cambia la ruta seleccionada
  useEffect(() => {
    if (tabla1.numeroRuta) {
      fetchShapesDistances(tabla1.numeroRuta);
    }
  }, [tabla1.numeroRuta]);

  // Calcular tiempoCiclo automáticamente en Tabla 3
  useEffect(() => {
    const updatedTabla3 = tabla3.map(row => {
      const tiempoCiclo = calculateTiempoCiclo(row.tiempoCB, row.tiempoBC);
      return { ...row, tiempoCiclo };
    });
    
    // Solo actualizar si hay cambios
    if (JSON.stringify(updatedTabla3) !== JSON.stringify(tabla3)) {
      setTabla3(updatedTabla3);
    }
  }, [tabla3.map(r => r.tiempoCB + r.tiempoBC).join(',')]);

  // ==================== FUNCIONES DE CARGA ====================

  const fetchRoutes = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/routes');
      if (res.ok) {
        const data = await res.json();
        setRoutes(data);
        console.log('✅ Rutas cargadas:', data.length);
      }
    } catch (err) {
      console.error('Error cargando rutas:', err);
      setStatus({
        message: '❌ Error cargando rutas',
        type: 'error'
      });
    }
  };

  const fetchShapesDistances = async (routeId) => {
    try {
      console.log(`📏 Obteniendo distancias para ruta ${routeId}...`);
      const res = await fetch(`http://localhost:8000/scheduling/shapes-distances/${routeId}`);
      
      if (res.ok) {
        const data = await res.json();
        console.log('✅ Distancias obtenidas:', data);
        
        setTabla1(prev => ({
          ...prev,
          distanciaCB: data.centro_barrio || 0,
          distanciaBC: data.barrio_centro || 0
        }));
        
        setStatus({
          message: `📏 Distancias cargadas: C→B ${data.centro_barrio}km, B→C ${data.barrio_centro}km`,
          type: 'success'
        });
      } else {
        console.warn('⚠️ No se encontraron shapes para esta ruta');
        setStatus({
          message: '⚠️ No se encontraron shapes para esta ruta. Ingresa las distancias manualmente.',
          type: 'warning'
        });
      }
    } catch (err) {
      console.error('Error obteniendo distancias:', err);
    }
  };

  const fetchSavedScenarios = async () => {
    setLoadingScenarios(true);
    try {
      const routeFilter = tabla1.numeroRuta ? `?route_id=${tabla1.numeroRuta}` : '';
      const res = await fetch(`http://localhost:8000/scheduling/parameters${routeFilter}`);
      
      if (res.ok) {
        const data = await res.json();
        setSavedScenarios(data);
        console.log('✅ Escenarios cargados:', data.length);
      }
    } catch (err) {
      console.error('Error cargando escenarios:', err);
      setStatus({
        message: '❌ Error cargando escenarios guardados',
        type: 'error'
      });
    } finally {
      setLoadingScenarios(false);
    }
  };

  // ==================== HANDLERS ====================

  const handleRouteChange = (e) => {
    const routeId = e.target.value;
    const route = routes.find(r => r.route_id === routeId);
    
    if (route) {
      setSelectedRoute(route);
      setTabla1(prev => ({
        ...prev,
        numeroRuta: route.route_id,
        nombreRuta: route.route_long_name || route.route_short_name || ''
      }));
    }
  };

  const handleTabla1Change = (field, value) => {
    setTabla1(prev => ({ ...prev, [field]: value }));
  };

  const handleTabla2Change = (index, field, value) => {
    const updated = [...tabla2];
    updated[index] = { ...updated[index], [field]: value };
    setTabla2(updated);
  };

  const handleTabla3Change = (index, field, value) => {
    const updated = [...tabla3];
    updated[index] = { ...updated[index], [field]: value };
    setTabla3(updated);
  };

  const addRowTabla2 = () => {
    setTabla2([...tabla2, { desde: '', buses: 0 }]);
  };

  const removeRowTabla2 = (index) => {
    if (tabla2.length > 1) {
      setTabla2(tabla2.filter((_, i) => i !== index));
    }
  };

  const addRowTabla3 = () => {
    setTabla3([...tabla3, { desde: '', tiempoCB: '', tiempoBC: '', tiempoCiclo: '' }]);
  };

  const removeRowTabla3 = (index) => {
    if (tabla3.length > 1) {
      setTabla3(tabla3.filter((_, i) => i !== index));
    }
  };

  // ==================== CÁLCULO DE INTERVALOS ====================

  const handleCalculate = async () => {
    setCalculando(true);
    setStatus({ message: '🔄 Calculando intervalos...', type: 'loading' });

    try {
      // Validar datos
      if (!tabla1.numeroRuta) {
        throw new Error('Selecciona una ruta');
      }
      if (tabla2.some(r => !r.desde || r.buses === 0)) {
        throw new Error('Completa todos los datos de Flota Variable');
      }
      if (tabla3.some(r => !r.desde || !r.tiempoCB || !r.tiempoBC)) {
        throw new Error('Completa todos los datos de Tiempos de Recorrido');
      }

      const requestData = {
        tabla1,
        tabla2,
        tabla3
      };

      console.log('📤 Enviando datos:', requestData);

      const res = await fetch('http://localhost:8000/scheduling/calculate-intervals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Error al calcular');
      }

      const result = await res.json();
      console.log('✅ Resultados:', result);

      // Actualizar tablas de resultados
      setTabla4(result.tabla4 || []);
      setTabla5(result.tabla5 || []);
      setTabla6(result.tabla6 || []);
      setTabla7(result.tabla7 || []);

      setStatus({
        message: `✅ Intervalos calculados correctamente! (${result.tiempo_procesamiento})`,
        type: 'success'
      });

    } catch (err) {
      console.error('❌ Error:', err);
      setStatus({
        message: `❌ Error: ${err.message}`,
        type: 'error'
      });
    } finally {
      setCalculando(false);
    }
  };

  // ==================== GUARDAR/CARGAR ESCENARIOS ====================

  const handleSave = async () => {
    if (!scenarioName.trim()) {
      setStatus({ message: '❌ Ingresa un nombre para el escenario', type: 'error' });
      return;
    }

    setLoading(true);
    setStatus({ message: '💾 Guardando escenario...', type: 'loading' });

    try {
      const requestData = {
        name: scenarioName.trim(),
        tabla1,
        tabla2,
        tabla3
      };

      const res = await fetch('http://localhost:8000/scheduling/parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Error al guardar');
      }

      const result = await res.json();
      console.log('✅ Guardado:', result);

      // Guardar también en localStorage
      localStorage.setItem(`scheduling_scenario_${result.id}`, JSON.stringify(requestData));

      setStatus({
        message: `✅ ${result.message}`,
        type: 'success'
      });

      setShowSaveModal(false);
      setScenarioName('');

    } catch (err) {
      console.error('❌ Error:', err);
      setStatus({
        message: `❌ Error: ${err.message}`,
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLoad = async (scenarioId) => {
    setLoading(true);
    setStatus({ message: '📥 Cargando escenario...', type: 'loading' });

    try {
      const res = await fetch(`http://localhost:8000/scheduling/parameters/${scenarioId}`);

      if (!res.ok) {
        throw new Error('Error al cargar escenario');
      }

      const data = await res.json();
      console.log('✅ Escenario cargado:', data);

      // Cargar datos
      setTabla1(data.tabla1);
      setTabla2(data.tabla2 || [{ desde: '', buses: 0 }]);
      setTabla3(data.tabla3 || [{ desde: '', tiempoCB: '', tiempoBC: '', tiempoCiclo: '' }]);

      // Limpiar resultados
      setTabla4([]);
      setTabla5([]);
      setTabla6([]);
      setTabla7([]);

      setStatus({
        message: `✅ Escenario "${data.name}" cargado correctamente`,
        type: 'success'
      });

      setShowLoadModal(false);

    } catch (err) {
      console.error('❌ Error:', err);
      setStatus({
        message: `❌ Error: ${err.message}`,
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (scenarioId, scenarioName) => {
    if (!window.confirm(`¿Eliminar el escenario "${scenarioName}"?`)) {
      return;
    }

    try {
      const res = await fetch(`http://localhost:8000/scheduling/parameters/${scenarioId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        throw new Error('Error al eliminar');
      }

      setStatus({
        message: `✅ Escenario "${scenarioName}" eliminado`,
        type: 'success'
      });

      // Recargar lista
      fetchSavedScenarios();

    } catch (err) {
      console.error('❌ Error:', err);
      setStatus({
        message: `❌ Error al eliminar: ${err.message}`,
        type: 'error'
      });
    }
  };

  // ==================== UTILIDADES ====================

  const calculateTiempoCiclo = (tiempoCB, tiempoBC) => {
    if (!tiempoCB || !tiempoBC) return '';

    const [h1, m1] = tiempoCB.split(':').map(Number);
    const [h2, m2] = tiempoBC.split(':').map(Number);

    const totalMinutes = (h1 * 60 + m1) + (h2 * 60 + m2);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  };

  const formatHeadway = (headway) => {
    if (typeof headway === 'number') {
      return `${headway} min`;
    }
    return headway || '';
  };

  // ==================== RENDER ====================

  return (
    <div className="scheduling-container">
      <h1>📋 Programación de Rutas</h1>

      {/* Barra de estado */}
      {status.message && (
        <div className={`status-message ${status.type}`}>
          {status.message}
        </div>
      )}

      {/* Botones principales */}
      <div className="main-buttons">
        <button onClick={() => { setShowLoadModal(true); fetchSavedScenarios(); }} className="btn-secondary">
          📥 Cargar Escenario
        </button>
        <button onClick={() => setShowSaveModal(true)} className="btn-secondary">
          💾 Guardar Escenario
        </button>
        <button onClick={handleCalculate} disabled={calculando} className="btn-primary">
          {calculando ? '⏳ Calculando...' : '🔢 Calcular Intervalos'}
        </button>
      </div>

      {/* ========== TABLA 1: PARÁMETROS GENERALES ========== */}
      <section className="table-section">
        <h2>📊 Tabla 1: Parámetros Generales</h2>

        <div className="form-grid">
          {/* Selector de Ruta */}
          <div className="form-group">
            <label>Ruta *</label>
            <select 
              value={tabla1.numeroRuta} 
              onChange={handleRouteChange}
              className="form-control"
            >
              <option value="">-- Seleccionar Ruta --</option>
              {routes.map(route => (
                <option key={route.route_id} value={route.route_id}>
                  {route.route_short_name} - {route.route_long_name || route.route_id}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Nombre de Ruta</label>
            <input
              type="text"
              value={tabla1.nombreRuta}
              onChange={(e) => handleTabla1Change('nombreRuta', e.target.value)}
              placeholder="Nombre descriptivo"
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Periodicidad</label>
            <select
              value={tabla1.periodicidad}
              onChange={(e) => handleTabla1Change('periodicidad', e.target.value)}
              className="form-control"
            >
              <option value="">-- Seleccionar --</option>
              <option value="Lunes-Viernes">Lunes-Viernes</option>
              <option value="Sábado">Sábado</option>
              <option value="Domingo">Domingo</option>
              <option value="L-M">Lunes-Martes</option>
              <option value="X-V">Miércoles-Viernes</option>
            </select>
          </div>

          <div className="form-group">
            <label>Hora Inicio Centro (HH:MM)</label>
            <input
              type="text"
              value={tabla1.horaInicioCentro}
              onChange={(e) => handleTabla1Change('horaInicioCentro', e.target.value)}
              placeholder="05:00"
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Hora Inicio Barrio (HH:MM)</label>
            <input
              type="text"
              value={tabla1.horaInicioBarrio}
              onChange={(e) => handleTabla1Change('horaInicioBarrio', e.target.value)}
              placeholder="05:30"
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Hora Fin Centro (HH:MM)</label>
            <input
              type="text"
              value={tabla1.horaFinCentro}
              onChange={(e) => handleTabla1Change('horaFinCentro', e.target.value)}
              placeholder="22:00"
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Hora Fin Barrio (HH:MM)</label>
            <input
              type="text"
              value={tabla1.horaFinBarrio}
              onChange={(e) => handleTabla1Change('horaFinBarrio', e.target.value)}
              placeholder="22:30"
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Dwell Centro (min)</label>
            <input
              type="number"
              value={tabla1.dwellCentro}
              onChange={(e) => handleTabla1Change('dwellCentro', parseInt(e.target.value) || 0)}
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Dwell Barrio (min)</label>
            <input
              type="number"
              value={tabla1.dwellBarrio}
              onChange={(e) => handleTabla1Change('dwellBarrio', parseInt(e.target.value) || 0)}
              className="form-control"
            />
          </div>

          <div className="form-group">
            <label>Distancia C→B (km) 🔄</label>
            <input
              type="number"
              step="0.01"
              value={tabla1.distanciaCB}
              onChange={(e) => handleTabla1Change('distanciaCB', parseFloat(e.target.value) || 0)}
              className="form-control"
              readOnly
              title="Se obtiene automáticamente del shape .1"
            />
          </div>

          <div className="form-group">
            <label>Distancia B→C (km) 🔄</label>
            <input
              type="number"
              step="0.01"
              value={tabla1.distanciaBC}
              onChange={(e) => handleTabla1Change('distanciaBC', parseFloat(e.target.value) || 0)}
              className="form-control"
              readOnly
              title="Se obtiene automáticamente del shape .2"
            />
          </div>
        </div>
      </section>

      {/* ========== TABLA 2: FLOTA VARIABLE ========== */}
      <section className="table-section">
        <h2>🚌 Tabla 2: Flota Variable</h2>
        
        <table className="data-table">
          <thead>
            <tr>
              <th>Desde (HH:MM)</th>
              <th>Cantidad de Buses</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {tabla2.map((row, idx) => (
              <tr key={idx}>
                <td>
                  <input
                    type="text"
                    value={row.desde}
                    onChange={(e) => handleTabla2Change(idx, 'desde', e.target.value)}
                    placeholder="07:00"
                    className="form-control"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    value={row.buses}
                    onChange={(e) => handleTabla2Change(idx, 'buses', parseInt(e.target.value) || 0)}
                    className="form-control"
                  />
                </td>
                <td>
                  <button onClick={() => removeRowTabla2(idx)} className="btn-delete">
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <button onClick={addRowTabla2} className="btn-add">
          ➕ Agregar Fila
        </button>
      </section>

      {/* ========== TABLA 3: TIEMPOS DE RECORRIDO ========== */}
      <section className="table-section">
        <h2>⏱️ Tabla 3: Tiempos de Recorrido</h2>
        
        <table className="data-table">
          <thead>
            <tr>
              <th>Desde (HH:MM)</th>
              <th>Tiempo C→B (HH:MM)</th>
              <th>Tiempo B→C (HH:MM)</th>
              <th>Tiempo Ciclo 🔄</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {tabla3.map((row, idx) => (
              <tr key={idx}>
                <td>
                  <input
                    type="text"
                    value={row.desde}
                    onChange={(e) => handleTabla3Change(idx, 'desde', e.target.value)}
                    placeholder="00:00"
                    className="form-control"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={row.tiempoCB}
                    onChange={(e) => handleTabla3Change(idx, 'tiempoCB', e.target.value)}
                    placeholder="00:30"
                    className="form-control"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={row.tiempoBC}
                    onChange={(e) => handleTabla3Change(idx, 'tiempoBC', e.target.value)}
                    placeholder="00:30"
                    className="form-control"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={row.tiempoCiclo}
                    readOnly
                    className="form-control readonly"
                    title="Se calcula automáticamente"
                  />
                </td>
                <td>
                  <button onClick={() => removeRowTabla3(idx)} className="btn-delete">
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <button onClick={addRowTabla3} className="btn-add">
          ➕ Agregar Fila
        </button>
      </section>

      {/* ========== RESULTADOS ========== */}
      {(tabla4.length > 0 || tabla5.length > 0) && (
        <>
          {/* Tabla 4: Intervalos Centro */}
          <section className="table-section results">
            <h2>📊 Tabla 4: Intervalos de Paso en Centro</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Headway</th>
                </tr>
              </thead>
              <tbody>
                {tabla4.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.desde}</td>
                    <td>{row.hasta}</td>
                    <td>{formatHeadway(row.headway)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Tabla 5: Intervalos Barrio */}
          <section className="table-section results">
            <h2>📊 Tabla 5: Intervalos de Paso en Barrio</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Headway</th>
                </tr>
              </thead>
              <tbody>
                {tabla5.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.desde}</td>
                    <td>{row.hasta}</td>
                    <td>{formatHeadway(row.headway)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Tabla 6: Tiempos C→B */}
          <section className="table-section results">
            <h2>⏱️ Tabla 6: Tiempos de Recorrido C→B</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Tiempo</th>
                </tr>
              </thead>
              <tbody>
                {tabla6.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.desde}</td>
                    <td>{row.hasta}</td>
                    <td>{row.tiempo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Tabla 7: Tiempos B→C */}
          <section className="table-section results">
            <h2>⏱️ Tabla 7: Tiempos de Recorrido B→C</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Tiempo</th>
                </tr>
              </thead>
              <tbody>
                {tabla7.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.desde}</td>
                    <td>{row.hasta}</td>
                    <td>{row.tiempo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {/* ========== MODAL GUARDAR ========== */}
      {showSaveModal && (
        <div className="modal-overlay" onClick={() => setShowSaveModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>💾 Guardar Escenario</h3>
            
            <div className="form-group">
              <label>Nombre del Escenario *</label>
              <input
                type="text"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                placeholder="Ej: Programación Ruta 1 L-V"
                className="form-control"
                autoFocus
              />
              <small className="help-text">
                Ejemplo: "Programación Ruta {tabla1.numeroRuta || '1'} {tabla1.periodicidad || 'L-V'}"
              </small>
            </div>

            <div className="modal-buttons">
              <button onClick={() => setShowSaveModal(false)} className="btn-secondary">
                Cancelar
              </button>
              <button onClick={handleSave} disabled={loading} className="btn-primary">
                {loading ? '⏳ Guardando...' : '💾 Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========== MODAL CARGAR ========== */}
      {showLoadModal && (
        <div className="modal-overlay" onClick={() => setShowLoadModal(false)}>
          <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
            <h3>📥 Cargar Escenario</h3>

            {loadingScenarios ? (
              <p className="text-center">⏳ Cargando escenarios...</p>
            ) : savedScenarios.length === 0 ? (
              <p className="text-center empty-state">
                No hay escenarios guardados
              </p>
            ) : (
              <div className="scenarios-list">
                {savedScenarios.map((scenario) => (
                  <div key={scenario.id} className="scenario-card">
                    <div className="scenario-info">
                      <h4>{scenario.name}</h4>
                      <p className="scenario-meta">
                        Ruta: {scenario.route_id} • {scenario.periodicidad}
                      </p>
                      <p className="scenario-date">
                        Actualizado: {new Date(scenario.updated_at).toLocaleString('es-MX')}
                      </p>
                    </div>
                    <div className="scenario-actions">
                      <button
                        onClick={() => handleLoad(scenario.id)}
                        className="btn-primary"
                      >
                        📥 Cargar
                      </button>
                      <button
                        onClick={() => handleDelete(scenario.id, scenario.name)}
                        className="btn-delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="modal-buttons">
              <button onClick={() => setShowLoadModal(false)} className="btn-secondary">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SchedulingParametersV3;