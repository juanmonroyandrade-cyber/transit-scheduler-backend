// SchedulingSheet.jsx - Versión corregida: siempre envía FormData para evitar 422 por campos faltantes

import React, { useState, useEffect, useRef, useMemo } from 'react';
import PointToPointGraph from './PointToPointGraph';
import GanttChart from './GanttChart';

const Modal = ({ children, onClose }) => (
  <div style={modalOverlayStyle}>
    <div style={modalContentStyle}>
      <button onClick={onClose} style={modalCloseButtonStyle}>&times;</button>
      <div style={modalChartContainerStyle}>
        {children}
      </div>
    </div>
  </div>
);

const SchedulingSheet = ({
  parameters,
  selectedRoute,
  generatedSheetData = [],
  onSheetChange = () => {}
}) => {
  const [sheetData, setSheetData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const nextId = useRef(1);
  const originalRef = useRef([]);

  const [chartToShow, setChartToShow] = useState(null);

  const [showGTFSModal, setShowGTFSModal] = useState(false);
  const [gtfsConfig, setGtfsConfig] = useState({
    shapeIdS1: '',
    shapeIdS2: '',
    stopsFile: null
  });
  const [generatingGTFS, setGeneratingGTFS] = useState(false);
  const [gtfsResult, setGtfsResult] = useState(null);
  const [showReplaceDialog, setShowReplaceDialog] = useState(false);
  const [existingTripsInfo, setExistingTripsInfo] = useState(null);
  const [hasExistingTrips, setHasExistingTrips] = useState(false);
  const [checkingTrips, setCheckingTrips] = useState(false);

  const [showTripsView, setShowTripsView] = useState(false);
  const [createdTrips, setCreatedTrips] = useState([]);
  const [createdStopTimes, setCreatedStopTimes] = useState([]);
  const [loadingTripsView, setLoadingTripsView] = useState(false);

  // Extraer ruta y periodicidad de los parámetros
  const routeId = parameters?.general?.numeroRuta;
  const periodicidad = parameters?.general?.periodicidad;

  const normalizeIncoming = (incoming = []) => {
    return incoming.map((r) => {
      if (r && r.__id) {
        const num = Number(r.__id?.toString().replace('__', '')) || null;
        if (num && num >= nextId.current) nextId.current = num + 1;
        return r;
      }
      const newRow = { ...r, __id: `__${nextId.current++}` };
      return newRow;
    });
  };

  useEffect(() => {
    setIsLoading(true);
    setError('');

    if (generatedSheetData && generatedSheetData.length > 0) {
      const normalized = normalizeIncoming(generatedSheetData);
      setSheetData(normalized);
      originalRef.current = normalized.map((r) => ({ ...r }));
    } else {
      setSheetData([]);
      originalRef.current = [];
      setError('No hay una sábana generada para mostrar. Ve a Parámetros y crea una.');
    }

    setIsLoading(false);
  }, [generatedSheetData]);

  const emitChange = (data) => {
    const cleaned = data.map((r) => {
      const copy = { ...r };
      delete copy.__id;
      return copy;
    });
    onSheetChange(cleaned);
  };

  const handleCellChange = (rowId, header, value) => {
    setSheetData((prev) => {
      const updated = prev.map((r) => {
        if (r.__id === rowId) {
          return { ...r, [header]: value };
        }
        return r;
      });
      emitChange(updated);
      return updated;
    });
  };

  const handleAddRow = () => {
    const headers = sheetData.length > 0 ? Object.keys(sheetData[0]).filter(h => h !== '__id') : [];
    const newRow = headers.reduce((acc, h) => ({ ...acc, [h]: '' }), {});
    newRow.__id = `__${nextId.current++}`;
    setSheetData((prev) => {
      const updated = [...prev, newRow];
      emitChange(updated);
      return updated;
    });
  };

  const handleDeleteRow = (rowId) => {
    setSheetData((prev) => {
      const updated = prev.filter((r) => r.__id !== rowId);
      emitChange(updated);
      return updated;
    });
  };

  const handleRevert = () => {
    const copy = originalRef.current.map((r) => ({ ...r }));
    setSheetData(copy);
    emitChange(copy);
  };

  const handleDownloadCSV = () => {
    if (!sheetData || sheetData.length === 0) return;
    const headers = Object.keys(sheetData[0]).filter(h => h !== '__id');
    const rows = sheetData.map(r =>
      headers.map(h => {
        const cell = r[h];
        if (cell === null || cell === undefined) return '';
        return `"${String(cell).replace(/"/g, '""')}"`;
      }).join(',')
    );
    const csv = [headers.join(','), ...rows].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const fileName = `sábana_${routeId || 'ruta'}_${periodicidad || ''}.csv`;
    a.setAttribute('download', fileName);
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  // MODIFICADO: Verificar trips sin filtrar por periodicidad
  const checkExistingTrips = async (rId) => {
    try {
      const response = await fetch(
        `http://localhost:8000/bulk/count-trips?route_id=${encodeURIComponent(rId)}`
      );
      if (!response.ok) throw new Error('Error al verificar trips existentes');
      return await response.json();
    } catch (error) {
      console.error('Error al verificar trips:', error);
      throw error;
    }
  };

  const deleteExistingTrips = async (rId, servId) => {
    try {
      const response = await fetch(
        `http://localhost:8000/bulk/delete-trips-and-stoptimes?route_id=${encodeURIComponent(rId)}&service_id=${encodeURIComponent(servId)}`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Error al eliminar trips existentes');
      return await response.json();
    } catch (error) {
      console.error('Error al eliminar trips:', error);
      throw error;
    }
  };

  const fetchCreatedTripsAndStops = async (rId, servId) => {
    setLoadingTripsView(true);
    try {
      const tripsResponse = await fetch(`http://localhost:8000/gtfs/trips?route_id=${rId}&service_id=${servId}`);
      if (!tripsResponse.ok) throw new Error('Error al obtener trips');
      const trips = await tripsResponse.json();
      setCreatedTrips(Array.isArray(trips) ? trips : []);

      if (trips.length > 0) {
        const tripIds = trips.map(t => t.trip_id).join(',');
        const stopTimesResponse = await fetch(`http://localhost:8000/gtfs/stop_times?trip_ids=${tripIds}`);
        if (!stopTimesResponse.ok) throw new Error('Error al obtener stop_times');
        const stopTimes = await stopTimesResponse.json();
        setCreatedStopTimes(Array.isArray(stopTimes) ? stopTimes : []);
      } else {
        setCreatedStopTimes([]);
      }
    } catch (error) {
      console.error('Error al cargar trips/stop_times:', error);
      setCreatedTrips([]);
      setCreatedStopTimes([]);
    } finally {
      setLoadingTripsView(false);
    }
  };

  const handleOpenGTFSModal = async () => {
    if (!routeId || !periodicidad) {
      alert('❌ No hay información de ruta y periodicidad en los parámetros');
      return;
    }

    setShowGTFSModal(true);
    setCheckingTrips(true);

    try {
      // MODIFICADO: Verificar trips sin filtrar por periodicidad
      const existingData = await checkExistingTrips(routeId);

      if (existingData.trips_count > 0) {
        setHasExistingTrips(true);
        setExistingTripsInfo(existingData);
      } else {
        setHasExistingTrips(false);
        setExistingTripsInfo(null);
      }
    } catch (error) {
      console.error('Error al verificar trips:', error);
      setHasExistingTrips(false);
    } finally {
      setCheckingTrips(false);
    }
  };

  const handleConfirmReplace = async () => {
    setShowReplaceDialog(false);
    setGeneratingGTFS(true);

    try {
      await deleteExistingTrips(routeId, periodicidad);
      await generateGTFS();
    } catch (error) {
      alert(`Error al reemplazar trips: ${error.message}`);
    } finally {
      setGeneratingGTFS(false);
      setExistingTripsInfo(null);
    }
  };

  const handleGenerateGTFSClick = async () => {
    if (hasExistingTrips) {
      setShowReplaceDialog(true);
    } else {
      await generateGTFS();
    }
  };

  // ---------- CORRECCIÓN PRINCIPAL: enviar SIEMPRE FormData ----------
  const generateGTFS = async () => {
    setGeneratingGTFS(true);

    try {
      // preparar sheet_data
      let cleanedData = [];
      if (sheetData && sheetData.length > 0) {
        cleanedData = sheetData.map(r => {
          const copy = { ...r };
          delete copy.__id;
          return copy;
        });
      }

      // Si NO hay trips existentes, obligamos a tener stopsFile (como antes)
      if (!hasExistingTrips && !gtfsConfig.stopsFile) {
        alert('❌ Debes cargar un archivo Excel con las paradas');
        setGeneratingGTFS(false);
        return;
      }

      const url = 'http://localhost:8000/scheduling/generate-gtfs-from-sheet';

      // Construir FormData con todos los campos esperables
      const formData = new FormData();

      // Campos base (incluye route_id que a veces espera el backend)
      formData.append('route_id', routeId || '');
      formData.append('route_name', parameters?.general?.nombreRuta || routeId || '');
      formData.append('service_id', periodicidad || '');
      formData.append('periodicity', periodicidad || '');
      formData.append('existing_route_id', routeId || '');
      formData.append('use_existing_route', hasExistingTrips ? 'true' : 'false');
      formData.append('bikes_allowed', String(1));

      // sheet_data como JSON string
      formData.append('sheet_data_json', JSON.stringify(cleanedData));

      // shape ids (opcional)
      if (gtfsConfig.shapeIdS1) formData.append('shape_id_s1', gtfsConfig.shapeIdS1);
      if (gtfsConfig.shapeIdS2) formData.append('shape_id_s2', gtfsConfig.shapeIdS2);

      // stops file: si existe, agrégalo; si no existe y no hay trips, ya habíamos bloqueado antes
      if (gtfsConfig.stopsFile) {
        formData.append('stops_file', gtfsConfig.stopsFile);
      }

      // Enviar siempre multipart/form-data (el navegador pondrá el boundary)
      const response = await fetch(url, {
        method: 'POST',
        body: formData
      });

      // manejar respuesta robustamente (puede venir JSON o texto)
      const contentType = response.headers.get('content-type') || '';
      let result;
      if (contentType.includes('application/json')) {
        result = await response.json();
      } else {
        const text = await response.text();
        result = { detail: text };
      }

      if (!response.ok) {
        // FastAPI devuelve a veces detail como array de errores o string
        let message = 'Error al generar GTFS';
        if (result) {
          if (Array.isArray(result.detail)) {
            message = result.detail.map(d => (d.msg || d.detail || JSON.stringify(d))).join('; ');
          } else if (typeof result.detail === 'string') {
            message = result.detail;
          } else if (result.message) {
            message = result.message;
          } else {
            message = JSON.stringify(result);
          }
        }
        throw new Error(message);
      }

      setGtfsResult(result);
      setShowGTFSModal(false);

      await fetchCreatedTripsAndStops(routeId, periodicidad);
      setShowTripsView(true);

      alert(`✅ GTFS generado exitosamente!\n\nTrips creados: ${result.trips_created || 'N/A'}\nStop times creados: ${result.stop_times_created || 'N/A'}`);

      setGtfsConfig({ shapeIdS1: '', shapeIdS2: '', stopsFile: null });
      setHasExistingTrips(true);
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
      console.error('generateGTFS error:', error);
    } finally {
      setGeneratingGTFS(false);
    }
  };
  // ---------- FIN CORRECCIÓN ----------

  const timetableData = useMemo(() => {
    if (!sheetData || sheetData.length === 0) return [];
    const transformed = [];
    const busKey = 'BusID';
    for (const row of sheetData) {
      const busId = row[busKey] || 'Sin Bus';
      const salidaCentro = row["Salida en Centro"];
      const llegadaBarrio = row["Llegada en Barrio"];
      const salidaBarrio = row["Salida en Barrio"];
      const llegadaCentro = row["Llegada en Centro"];
      if (salidaCentro && salidaCentro !== '---' && llegadaBarrio && llegadaBarrio !== '---') {
        transformed.push({
          bus_id: busId,
          dep: salidaCentro,
          arr: llegadaBarrio,
          dir: 'A'
        });
      }
      if (salidaBarrio && salidaBarrio !== '---' && llegadaCentro && llegadaCentro !== '---') {
        transformed.push({
          bus_id: busId,
          dep: salidaBarrio,
          arr: llegadaCentro,
          dir: 'B'
        });
      }
    }
    return transformed;
  }, [sheetData]);

  if (isLoading) {
    return <div className="p-4">Cargando sábana...</div>;
  }

  if (error && sheetData.length === 0) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  if (!sheetData || sheetData.length === 0) {
    return <div className="p-4">No hay datos en la sábana.</div>;
  }

  const headers = Object.keys(sheetData[0]).filter(h => h !== '__id');

  return (
    <div className="scheduling-container" style={{ maxWidth: '100%' }}>
      <h1>📄 Sábana de Programación</h1>

      {routeId && periodicidad && (
        <div style={{ background: '#e0f2fe', padding: 12, borderRadius: 6, marginBottom: 12 }}>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>
            <strong>Ruta:</strong> {routeId} • <strong>Periodicidad:</strong> {periodicidad}
          </p>
        </div>
      )}

      {/* MODIFICADO: Mostrar parámetros de forma legible */}
      {parameters?.general && (
        <section className="table-section" style={{ background: '#f8f9fa', marginBottom: 12, padding: '1rem' }}>
          <h2>Parámetros Utilizados</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px', fontSize: '0.875rem' }}>
            <div><strong>Ruta:</strong> {parameters.general.numeroRuta}</div>
            <div><strong>Nombre:</strong> {parameters.general.nombreRuta}</div>
            <div><strong>Periodicidad:</strong> {parameters.general.periodicidad}</div>
            <div><strong>Inicio Centro:</strong> {parameters.general.horaInicioCentro}</div>
            <div><strong>Inicio Barrio:</strong> {parameters.general.horaInicioBarrio}</div>
            <div><strong>Fin Centro:</strong> {parameters.general.horaFinCentro}</div>
            <div><strong>Fin Barrio:</strong> {parameters.general.horaFinBarrio}</div>
            <div><strong>Dwell Centro:</strong> {parameters.general.dwellCentro} min</div>
            <div><strong>Dwell Barrio:</strong> {parameters.general.dwellBarrio} min</div>
            <div><strong>Distancia C→B:</strong> {parameters.general.distanciaCB} km</div>
            <div><strong>Distancia B→C:</strong> {parameters.general.distanciaBC} km</div>
            <div><strong>Pool Buses:</strong> {parameters.general.num_buses_pool}</div>
          </div>
        </section>
      )}

      {gtfsResult && (
        <section className="table-section" style={{ background: '#d1fae5', marginBottom: 12, padding: 12, borderRadius: 6 }}>
          <h3>✅ Último GTFS Generado</h3>
          <div style={{ fontSize: '0.875rem' }}>
            <p><strong>Trips creados:</strong> {gtfsResult.trips_created || 0}</p>
            <p><strong>Stop times creados:</strong> {gtfsResult.stop_times_created || 0}</p>
            {gtfsResult.message && <p><strong>Mensaje:</strong> {gtfsResult.message}</p>}
          </div>
          <button onClick={() => setGtfsResult(null)} style={{ marginTop: 8, padding: '4px 8px', fontSize: '0.75rem' }}>
            Ocultar
          </button>
        </section>
      )}

      {showTripsView && (
        <section className="table-section" style={{ background: '#e0f2fe', marginBottom: 12, padding: 12, borderRadius: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3>📋 Trips y Stop Times Creados</h3>
            <button 
              onClick={() => setShowTripsView(false)}
              style={{ padding: '4px 8px', fontSize: '0.75rem', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 4, cursor: 'pointer' }}
            >
              Ocultar
            </button>
          </div>

          {loadingTripsView ? (
            <p>Cargando...</p>
          ) : (
            <>
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8 }}>Trips ({createdTrips.length})</h4>
                <div style={{ maxHeight: 200, overflowY: 'auto', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 4 }}>
                  <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#f9fafb' }}>
                      <tr>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Trip ID</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Headsign</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Direction</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Shape ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {createdTrips.map((trip, idx) => (
                        <tr key={idx}>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{trip.trip_id}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{trip.trip_headsign || '—'}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{trip.direction_id}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{trip.shape_id || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8 }}>Stop Times ({createdStopTimes.length})</h4>
                <div style={{ maxHeight: 200, overflowY: 'auto', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 4 }}>
                  <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#f9fafb' }}>
                      <tr>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Trip ID</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Stop ID</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Arrival</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Departure</th>
                        <th style={{ padding: '6px 8px', borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>Sequence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {createdStopTimes.map((st, idx) => (
                        <tr key={idx}>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{st.trip_id}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{st.stop_id}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{st.arrival_time}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{st.departure_time}</td>
                          <td style={{ padding: '6px 8px', borderBottom: '1px solid #f3f4f6' }}>{st.stop_sequence}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      <section className="table-section results">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2>Viajes Generados ({sheetData.length})</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={handleAddRow} style={{ padding: '6px 10px', borderRadius: 6 }}>➕ Agregar fila</button>
            <button onClick={handleRevert} style={{ padding: '6px 10px', borderRadius: 6 }}>↩️ Revertir</button>
            <button onClick={handleDownloadCSV} style={{ padding: '6px 10px', borderRadius: 6 }}>⬇️ Descargar CSV</button>

            <button 
              onClick={handleOpenGTFSModal} 
              disabled={!sheetData || sheetData.length === 0}
              style={{ 
                padding: '6px 10px', 
                borderRadius: 6, 
                background: '#3b82f6', 
                color: 'white',
                border: 'none',
                cursor: sheetData.length > 0 ? 'pointer' : 'not-allowed',
                opacity: sheetData.length > 0 ? 1 : 0.5
              }}
            >
              🚀 Generar GTFS
            </button>

            <button onClick={() => setChartToShow('p2p')} style={graphButtonStyle} title="Gráfica de itinerario punto a punto">
              📊 Gráfica P2P
            </button>
            <button onClick={() => setChartToShow('gantt')} style={graphButtonStyle} title="Gráfica de Gantt por bus">
              📈 Gráfica Gantt
            </button>
          </div>
        </div>

        <div style={{ width: '100%', overflowX: 'auto', marginTop: 8 }}>
          <table className="data-table" style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                {headers.map((header) => (
                  <th
                    key={header}
                    style={{
                      textAlign: 'left',
                      padding: '8px 10px',
                      borderBottom: '1px solid #e2e8f0',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {header.replace(/_/g, ' ')}
                  </th>
                ))}
                <th style={{ padding: '8px 10px', borderBottom: '1px solid #e2e8f0' }}>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {sheetData.map((row, rowIndex) => (
                <tr key={row.__id}>
                  {headers.map((header) => (
                    <td
                      key={`${row.__id}-${header}`}
                      style={{
                        padding: '6px 8px',
                        borderBottom: '1px solid #f1f5f9',
                        verticalAlign: 'top',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      <input
                        type="text"
                        value={row[header] === null || row[header] === undefined ? '' : String(row[header])}
                        onChange={(e) => handleCellChange(row.__id, header, e.target.value)}
                        style={{
                          width: 70,
                          minWidth: 50,
                          padding: '6px 8px',
                          borderRadius: 4,
                          border: '1px solid #d1d5db',
                          fontSize: '0.875rem'
                        }}
                      />
                    </td>
                  ))}

                  <td style={{ padding: '6px 8px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'top' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        onClick={() => handleDeleteRow(row.__id)}
                        title="Eliminar fila"
                        style={{
                          padding: '6px 8px',
                          borderRadius: 6,
                          background: '#fee2e2',
                          border: '1px solid #fca5a5'
                        }}
                      >
                        🗑️
                      </button>
                      <button
                        onClick={() => {
                          const clone = { ...row, __id: `__${nextId.current++}` };
                          setSheetData(prev => {
                            const updated = [...prev.slice(0, rowIndex + 1), clone, ...prev.slice(rowIndex + 1)];
                            emitChange(updated);
                            return updated;
                          });
                        }}
                        title="Duplicar fila"
                        style={{
                          padding: '6px 8px',
                          borderRadius: 6,
                          border: '1px solid #d1d5db'
                        }}
                      >
                        📄
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      

      {showGTFSModal && (
        <div style={modalOverlayStyle}>
          <div style={{ ...modalContentStyle, width: '500px', height: 'auto', maxHeight: '80vh' }}>
            <button onClick={() => setShowGTFSModal(false)} style={modalCloseButtonStyle}>&times;</button>
            <h2 style={{ marginBottom: 16 }}>🚀 Generar GTFS</h2>

            {checkingTrips && <p style={{ color: '#6b7280' }}>Verificando trips existentes...</p>}

            {!checkingTrips && (
              <>
                <div style={{ marginBottom: 16, padding: 12, background: '#f3f4f6', borderRadius: 6 }}>
                  <p style={{ fontSize: '0.875rem', marginBottom: 4 }}>
                    <strong>Ruta:</strong> {routeId || 'N/A'}
                  </p>
                  <p style={{ fontSize: '0.875rem' }}>
                    <strong>Periodicidad:</strong> {periodicidad || 'N/A'}
                  </p>
                </div>

                {hasExistingTrips ? (
                  <>
                    <div style={{ padding: 12, background: '#d1fae5', borderRadius: 6, marginBottom: 12 }}>
                      <p style={{ fontSize: '0.875rem', color: '#065f46' }}>
                        ✅ Esta ruta tiene {existingTripsInfo?.trips_count || 0} trips existentes. Se usarán sus stops.
                      </p>
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Shape ID Sentido 1 (opcional)</label>
                      <input
                        type="text"
                        value={gtfsConfig.shapeIdS1}
                        onChange={(e) => setGtfsConfig({ ...gtfsConfig, shapeIdS1: e.target.value })}
                        placeholder="Dejar vacío para usar existente"
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #d1d5db' }}
                      />
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Shape ID Sentido 2 (opcional)</label>
                      <input
                        type="text"
                        value={gtfsConfig.shapeIdS2}
                        onChange={(e) => setGtfsConfig({ ...gtfsConfig, shapeIdS2: e.target.value })}
                        placeholder="Dejar vacío para usar existente"
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #d1d5db' }}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ padding: 12, background: '#dbeafe', borderRadius: 6, marginBottom: 12 }}>
                      <p style={{ fontSize: '0.875rem', color: '#1e40af' }}>
                        ℹ️ No hay trips para esta ruta. Carga un Excel con las paradas.
                      </p>
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Archivo Excel de Paradas *</label>
                      <input
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={(e) => setGtfsConfig({ ...gtfsConfig, stopsFile: e.target.files[0] })}
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #d1d5db' }}
                      />
                      <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 4 }}>
                        Encabezados: route_id, service_id, stop_id, stop_name, direction_id, sequence, shape_id
                      </p>
                    </div>
                      
                      {/* ----- INICIO DE LA MODIFICACIÓN ----- */}
                    <div style={{ marginBottom: 12 }}>
                      <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Shape ID Sentido 1 (Opcional)</label>
                      <input
                        type="text"
                        value={gtfsConfig.shapeIdS1}
                        onChange={(e) => setGtfsConfig({ ...gtfsConfig, shapeIdS1: e.target.value })}
                        placeholder="Dejar vacío para leer del Excel"
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #d1d5db' }}
                      />
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Shape ID Sentido 2 (Opcional)</label>
                      <input
                        type="text"
                        value={gtfsConfig.shapeIdS2}
                        onChange={(e) => setGtfsConfig({ ...gtfsConfig, shapeIdS2: e.target.value })}
                        placeholder="Dejar vacío para leer del Excel"
                        style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid #d1d5db' }}
                      />
                    </div>
                      {/* ----- FIN DE LA MODIFICACIÓN ----- */}

                  </>
                )}

                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 20 }}>
                  <button
                    onClick={() => setShowGTFSModal(false)}
                    disabled={generatingGTFS}
                    style={{ padding: '8px 16px', borderRadius: 6, background: '#e5e7eb', border: 'none', cursor: 'pointer' }}
                  >
                    Cancelar
                  </button>
                  <button
                onClick={handleGenerateGTFSClick}
                disabled={generatingGTFS}
                style={{ 
                  padding: '8px 16px', 
                  borderRadius: 6, 
                  background: '#3b82f6', // <-- ASÍ DEBE SER
                  color: 'white', 
                  border: 'none', 
                  cursor: generatingGTFS ? 'not-allowed' : 'pointer',
                  opacity: generatingGTFS ? 0.5 : 1
                }}
              >
                    {generatingGTFS ? 'Generando...' : 'Generar'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}


      {showReplaceDialog && existingTripsInfo && (
        <div style={modalOverlayStyle}>
          <div style={{ ...modalContentStyle, width: '450px', height: 'auto', padding: 24 }}>
            <h3 style={{ color: '#f59e0b', marginBottom: 16 }}>⚠️ Viajes Existentes Detectados</h3>

            <div style={{ marginBottom: 16, background: '#fef3c7', padding: 12, borderRadius: 6 }}>
              <p style={{ marginBottom: 8 }}>
                Ya existen <strong>{existingTripsInfo.trips_count} trips</strong> y{' '}
                <strong>{existingTripsInfo.stop_times_count} stop_times</strong> para esta ruta.
              </p>
              <p style={{ fontSize: '0.875rem', color: '#92400e' }}>
                Al generar los nuevos viajes para <strong>{periodicidad}</strong>, se usarán los stops existentes.
              </p>
            </div>

            <p style={{ marginBottom: 20 }}>
              ¿Deseas continuar?
            </p>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowReplaceDialog(false);
                  setExistingTripsInfo(null);
                  setGeneratingGTFS(false);
                }}
                style={{ padding: '8px 16px', borderRadius: 6, background: '#e5e7eb', border: 'none', cursor: 'pointer' }}
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmReplace}
                style={{ padding: '8px 16px', borderRadius: 6, background: '#3b82f6', color: 'white', border: 'none', cursor: 'pointer' }}
              >
                Sí, Continuar
              </button>
            </div>
          </div>
        </div>
      )}

      {chartToShow && (
        <Modal onClose={() => setChartToShow(null)}>
          {chartToShow === 'p2p' && (
            <PointToPointGraph data={timetableData} />
          )}
          {chartToShow === 'gantt' && (
            <GanttChart data={timetableData} />
          )}
        </Modal>
      )}
    </div>
  );
};

const graphButtonStyle = {
  padding: '6px 10px',
  borderRadius: 6,
  background: '#e0f2fe',
  border: '1px solid #7dd3fc',
  cursor: 'pointer',
  fontWeight: 500
};

const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modalContentStyle = {
  background: 'white',
  padding: '20px',
  paddingTop: '40px',
  borderRadius: '8px',
  position: 'relative',
  width: '90vw',
  height: '90vh',
  boxShadow: '0 4px 20px rgba(0,0,0,0.25)'
};

const modalCloseButtonStyle = {
  position: 'absolute',
  top: '10px',
  right: '15px',
  background: 'transparent',
  border: 'none',
  fontSize: '2rem',
  cursor: 'pointer',
  lineHeight: 1,
  color: '#333'
};

const modalChartContainerStyle = {
  width: '100%',
  height: '100%',
  overflow: 'auto'
};

export default SchedulingSheet;