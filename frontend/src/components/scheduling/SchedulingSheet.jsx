import React, { useState, useEffect, useRef, useMemo } from 'react';
// --- NUEVOS IMPORTS ---
import PointToPointGraph from './PointToPointGraph';
import GanttChart from './GanttChart';
// --- FIN NUEVOS IMPORTS ---

/**
 * SchedulingSheet editable
 * ... (resto de tus props)
 */

// --- NUEVO: Componente Modal simple ---
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
// --- FIN MODAL ---


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

  // --- NUEVO ESTADO ---
  const [chartToShow, setChartToShow] = useState(null); // null, 'p2p', 'gantt'
  // --- FIN NUEVO ESTADO ---

  // ... (normalizeIncoming, useEffect, emitChange, handleCellChange, etc. no cambian) ...
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    const fileName = `sábana_${selectedRoute ? selectedRoute : 'ruta'}.csv`;
    a.setAttribute('download', fileName);
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  // --- LÓGICA CORREGIDA: Transformar Sábana a "Timetable" ---
  // Esto replica la primera parte de tu macro VBA
  const timetableData = useMemo(() => {
    if (!sheetData || sheetData.length === 0) return [];
    
    const transformed = [];

    // Usamos la clave "BusID" que genera tu backend
    const busKey = 'BusID'; 

    for (const row of sheetData) {
      const busId = row[busKey] || 'Sin Bus';

      // --- ¡LA CORRECCIÓN ESTÁ AQUÍ! ---
      // Leemos las claves con espacios que vienen del backend
      const salidaCentro = row["Salida en Centro"];
      const llegadaBarrio = row["Llegada en Barrio"];
      const salidaBarrio = row["Salida en Barrio"];
      const llegadaCentro = row["Llegada en Centro"];
      // --- FIN DE LA CORRECCIÓN ---

      // Dirección A->B (Centro->Barrio)
      // Comprobamos que no sea '---' (viaje solo de ida)
      if (salidaCentro && salidaCentro !== '---' && llegadaBarrio && llegadaBarrio !== '---') {
        transformed.push({
          bus_id: busId,
          dep: salidaCentro,
          arr: llegadaBarrio,
          dir: 'A' // A = Centro (1) -> Barrio (0)
        });
      }
      
      // Dirección B->A (Barrio->Centro)
      if (salidaBarrio && salidaBarrio !== '---' && llegadaCentro && llegadaCentro !== '---') {
        transformed.push({
          bus_id: busId,
          dep: salidaBarrio,
          arr: llegadaCentro,
          dir: 'B' // B = Barrio (0) -> Centro (1)
        });
      }
    }
    return transformed;
  }, [sheetData]);
  // --- FIN LÓGICA CORREGIDA ---


  if (isLoading) {
    return <div className="p-4">Cargando sábana...</div>;
  }

  if (error && sheetData.length === 0) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  if (!sheetData || sheetData.length === 0) {
    return <div className="p-4">No hay datos en la sábana.</div>;
  }

  // ... (resto del componente render sin cambios) ...
  const headers = Object.keys(sheetData[0]).filter(h => h !== '__id');

  return (
    <div className="scheduling-container" style={{ maxWidth: '100%' }}>
      <h1>📄 Sábana de Programación (Ruta: {selectedRoute || '—'})</h1>

      {parameters && (
        <section className="table-section" style={{ background: '#f8f9fa', marginBottom: 12 }}>
          <h2>Parámetros Utilizados</h2>
          <pre style={{
            background: '#fff',
            border: '1px solid #e2e8f0',
            padding: '10px',
            borderRadius: '6px',
            maxHeight: '200px',
            overflow: 'auto',
            fontSize: '0.75rem'
          }}>
            {JSON.stringify(parameters.general, null, 2)}
          </pre>
        </section>
      )}
      
      <section className="table-section results">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2>Viajes Generados ({sheetData.length})</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={handleAddRow} style={{ padding: '6px 10px', borderRadius: 6 }}>➕ Agregar fila</button>
            <button onClick={handleRevert} style={{ padding: '6px 10px', borderRadius: 6 }}>↩️ Revertir</button>
            <button onClick={handleDownloadCSV} style={{ padding: '6px 10px', borderRadius: 6 }}>⬇️ Descargar CSV</button>
            
            {/* --- NUEVOS BOTONES DE GRÁFICAS --- */}
            <button onClick={() => setChartToShow('p2p')} style={graphButtonStyle} title="Gráfica de itinerario punto a punto">
              📊 Gráfica P2P
            </button>
            <button onClick={() => setChartToShow('gantt')} style={graphButtonStyle} title="Gráfica de Gantt por bus">
              📈 Gráfica Gantt
            </button>
            {/* --- FIN NUEVOS BOTONES --- */}
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

      {/* --- NUEVO: RENDERIZADO DE MODAL --- */}
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
      {/* --- FIN RENDERIZADO DE MODAL --- */}
    </div>
  );
};

// --- NUEVOS ESTILOS (al final del archivo) ---
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
// --- FIN NUEVOS ESTILOS ---

export default SchedulingSheet;