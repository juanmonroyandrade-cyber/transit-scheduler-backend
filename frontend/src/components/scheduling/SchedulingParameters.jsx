// frontend/src/components/scheduling/SchedulingParametersV3.jsx

import React, { useState, useEffect } from 'react';
import './SchedulingParameters.css';

// --- IMPORTANTE ---
// Asumo que este componente SÍ recibe las props 'onSheetGenerated' y 'onViewChange' 
// de un componente 'App.jsx' similar al que te mostré en la respuesta anterior.
// Si NO las recibe, la sábana se mostrará igualmente al final (en 'Tabla 8').
function SchedulingParametersV3({ onSheetGenerated, onViewChange }) {
  
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
    distanciaBC: 0,
    // --- NUEVOS CAMPOS AÑADIDOS (Basados en tu VBA) ---
    // Estos son necesarios para la lógica de 'Crear Sábana'
    idle_threshold_min: 30,       // Umbral de inactividad (IDLE_THRESHOLD_MIN)
    max_wait_minutes_pairing: 15, // Umbral de espera para consolidar
    num_buses_pool: 20            // Pool de buses inicial (BusCountMod2)
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

  // --- NUEVOS ESTADOS PARA GENERACIÓN DE SÁBANA ---
  const [isNewRoute, setIsNewRoute] = useState(false);
  const [routeExcelFile, setRouteExcelFile] = useState(null);
  const [isGeneratingSheet, setIsGeneratingSheet] = useState(false);
  const [generatedSheet, setGeneratedSheet] = useState([]); // Para Tabla 8

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // --- NUEVOS HANDLERS PARA SÁBANA ---
  const handleFileChange = (e) => {
    setRouteExcelFile(e.target.files[0]);
  };

  // ==================== CÁLCULO DE INTERVALOS ====================

  const handleCalculate = async () => {
    setCalculando(true);
    setGeneratedSheet([]); // Limpiar sábana si se recalculan intervalos
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

  // ==================== NUEVA FUNCIÓN: GENERAR SÁBANA ====================

  const handleGenerateSheet = async () => {
    setIsGeneratingSheet(true);
    setGeneratedSheet([]); // Limpiar sábana anterior
    setStatus({ message: '🔄 Generando Sábana...', type: 'loading' });

    // 1. Validar que los intervalos se hayan calculado
    if (tabla4.length === 0 || tabla5.length === 0 || tabla6.length === 0 || tabla7.length === 0) {
      setStatus({
        message: '❌ Error: Debes "Calcular Intervalos" exitosamente antes de generar la sábana.',
        type: 'error'
      });
      setIsGeneratingSheet(false);
      return;
    }

    // 2. Validar el archivo si el checkbox está marcado
    if (isNewRoute && !routeExcelFile) {
      setStatus({
        message: '❌ Error: Marcaste "Ruta Nueva" pero no has seleccionado un archivo Excel.',
        type: 'error'
      });
      setIsGeneratingSheet(false);
      return;
    }

    try {
      const formData = new FormData();
      
      // 3. Empaquetar TODOS los parámetros que necesita el backend (lógica VBA)
      // El backend usará 'general' para start/end/dwell
      // y las tablas de headway/travel time para generar las salidas
      const parameters = {
        general: tabla1,          // Contiene inicios, fines, dwells, y los nuevos params de VBA
        headways_centro: tabla4,  // Tabla 4 (Desde, Hasta, Headway)
        headways_barrio: tabla5,  // Tabla 5 (Desde, Hasta, Headway)
        travel_times_cb: tabla6,  // Tabla 6 (Desde, Hasta, Tiempo)
        travel_times_bc: tabla7,  // Tabla 7 (Desde, Hasta, Tiempo)
      };
      
      formData.append('parameters', JSON.stringify(parameters));
      
      // 4. Adjuntar el archivo Excel si existe
      if (isNewRoute && routeExcelFile) {
        formData.append('route_file', routeExcelFile);
      }

      console.log("📤 Enviando datos para generar sábana:", parameters);

      // 5. Llamar al nuevo endpoint del backend
      // (Este endpoint debe ser creado en 'app/api/scheduling.py' 
      // y usar la lógica de 'sheet_generator.py' que te pasé)
      const res = await fetch('http://localhost:8000/scheduling/generate-sheet-from-intervals', {
        method: 'POST',
        body: formData
        // No setear 'Content-Type', FormData lo hace automáticamente
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Error al generar la sábana');
      }

      const sabanaResult = await res.json();
      
      if (!sabanaResult || sabanaResult.length === 0) {
         throw new Error('El backend no devolvió datos para la sábana.');
      }

      console.log('✅ Sábana generada:', sabanaResult);
      setGeneratedSheet(sabanaResult); // Guardar en estado para Tabla 8
      setStatus({
        message: `✅ Sábana de programación generada con ${sabanaResult.length} viajes.`,
        type: 'success'
      });

      // Opcional: Si el componente recibe props de App.jsx, las usa para navegar
      if (onSheetGenerated) {
        onSheetGenerated(sabanaResult);
      }
      if (onViewChange) {
        onViewChange('sched_sheet');
      }

    } catch (err) {
      console.error('❌ Error en handleGenerateSheet:', err);
      setStatus({
        message: `❌ Error al generar sábana: ${err.message}`,
        type: 'error'
      });
    } finally {
      setIsGeneratingSheet(false);
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
      setGeneratedSheet([]); // Limpiar sábana también

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

    const [h1, m1] = String(tiempoCB).split(':').map(Number);
    const [h2, m2] = String(tiempoBC).split(':').map(Number);
    
    if (isNaN(h1) || isNaN(m1) || isNaN(h2) || isNaN(m2)) return '';

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

  // --- NUEVA FUNCIÓN DE RENDER (para Tabla 8) ---
  const renderGeneratedSheet = () => {
    if (!generatedSheet || generatedSheet.length === 0) {
      return null;
    }
    
    const headers = Object.keys(generatedSheet[0]);
    
    return (
      <section className="table-section results">
        <h2>📄 Tabla 8: Sábana de Programación Generada</h2>
        <table className="data-table">
          <thead>
            <tr>
              {headers.map(header => <th key={header}>{header}</th>)}
            </tr>
          </thead>
          <tbody>
            {generatedSheet.map((row, idx) => (
              <tr key={idx}>
                {headers.map(header => (
                  <td key={`${idx}-${header}`}>
                    {row[header] === null || row[header] === undefined ? '---' : row[header]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
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
        
        {/* --- NUEVO BOTÓN AÑADIDO --- */}
        <button 
          onClick={handleGenerateSheet} 
          disabled={isGeneratingSheet || calculando || tabla4.length === 0}
          className="btn-primary"
          style={{ backgroundColor: '#28a745', borderColor: '#28a745' }} // Verde
          title={tabla4.length === 0 ? "Debes 'Calcular Intervalos' primero" : "Generar la sábana de programación"}
        >
          {isGeneratingSheet ? '⏳ Generando Sábana...' : '📄 Crear Sábana de Programación'}
        </button>
      </div>

      {/* --- NUEVA SECCIÓN PARA OPCIONES DE SÁBANA --- */}
      <section className="table-section" style={{ border: '2px dashed #007bff', backgroundColor: '#f8f9fa', padding: '1rem' }}>
        <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>Opciones para "Crear Sábana de Programación"</h2>
        <div className="form-grid">
          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <input
                type="checkbox"
                checked={isNewRoute}
                onChange={(e) => setIsNewRoute(e.target.checked)}
                style={{ width: 'auto', margin: 0, transform: 'scale(1.2)' }}
              />
              Es una Ruta Nueva (para generar GTFS)
            </label>
            <small className="help-text">
              Marca esto si quieres cargar los arcos de línea (paradas/secuencia) para generar trips y stop_times.
            </small>
          </div>
          
          {isNewRoute && (
            <div className="form-group" style={{ gridColumn: 'span 2', margin: 0 }}>
              <label>Cargar Excel de Arcos de Línea (.xlsx)</label>
              <input
                type="file"
                accept=".xlsx, .xls"
                onChange={handleFileChange}
                className="form-control"
              />
            </div>
          )}
        </div>
      </section>

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
          
          {/* --- NUEVOS CAMPOS UI AÑADIDOS A TABLA 1 --- */}
          <div className="form-group">
            <label>Pool de Buses (Lógica VBA)</label>
            <input
              type="number"
              value={tabla1.num_buses_pool}
              onChange={(e) => handleTabla1Change('num_buses_pool', parseInt(e.target.value) || 0)}
              className="form-control"
              title="Nº de buses para la simulación de la sábana (Lógica VBA)"
            />
          </div>
          
          <div className="form-group">
            <label>Umbral Inactividad (min)</label>
            <input
              type="number"
              value={tabla1.idle_threshold_min}
              onChange={(e) => handleTabla1Change('idle_threshold_min', parseInt(e.target.value) || 0)}
              className="form-control"
              title="Minutos de espera antes de que un bus pase a 'Fuera de Operación' (Lógica VBA)"
            />
          </div>
          
          <div className="form-group">
            <label>Espera Máx. Emparejar (min)</label>
            <input
              type="number"
              value={tabla1.max_wait_minutes_pairing}
              onChange={(e) => handleTabla1Change('max_wait_minutes_pairing', parseInt(e.target.value) || 0)}
              className="form-control"
              title="Tiempo máximo de espera para consolidar un viaje de ida y vuelta (Lógica VBA)"
            />
          </div>

        </div>
      </section>

      {/* ========== TABLA 2: FLOTA VARIABLE ========== */}
      <section className="table-section">
        <h2>🚌 Tabla 2: Flota Variable (para 'Calcular Intervalos')</h2>
        
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
        <h2>⏱️ Tabla 3: Tiempos de Recorrido (para 'Calcular Intervalos')</h2>
        
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

      {/* ========== RESULTADOS (Tablas 4-7) ========== */}
      {(tabla4.length > 0 || tabla5.length > 0) && (
        <>
          {/* Tabla 4: Intervalos Centro */}
          <section className="table-section results">
            <h2>📊 Tabla 4: Intervalos de Paso en Centro (Headways)</h2>
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
            <h2>📊 Tabla 5: Intervalos de Paso en Barrio (Headways)</h2>
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
            <h2>⏱️ Tabla 6: Tiempos de Recorrido C→B (Interpolados)</h2>
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
            <h2>⏱️ Tabla 7: Tiempos de Recorrido B→C (Interpolados)</h2>
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

      {/* --- NUEVA TABLA DE RESULTADO (Tabla 8) --- */}
      {renderGeneratedSheet()}


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
                No hay escenarios guardados {tabla1.numeroRuta ? `para la ruta ${tabla1.numeroRuta}` : ''}
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