import React, { useState, useEffect, useRef } from 'react';

/**
 * SchedulingSheet editable
 *
 * Props:
 *  - parameters: objeto con parámetros usados (opcional)
 *  - selectedRoute: nombre/id de la ruta (opcional, sólo para mostrar)
 *  - generatedSheetData: array de objetos (cada objeto = fila) recibido desde App
 *  - onSheetChange: función optional (sheetData) => void, llamada cuando los datos cambian
 *
 * Comportamiento:
 *  - Todas las celdas se muestran como inputs editables (texto).
 *  - Botones: Agregar fila, Eliminar fila (en la fila), Revertir (resetear a generatedSheetData),
 *    Descargar CSV (descarga los datos actuales).
 */

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
  const originalRef = useRef([]); // guarda copia para revertir

  // Añade un id interno __id a cada fila (si no existe) para usar como key estable
  const normalizeIncoming = (incoming = []) => {
    return incoming.map((r) => {
      // si ya trae __id no lo sobreescribimos
      if (r && r.__id) {
        // aseguramos que nextId avance para no chocar al crear nuevas filas
        const num = Number(r.__id?.toString().replace('__', '')) || null;
        if (num && num >= nextId.current) nextId.current = num + 1;
        return r;
      }
      const newRow = { ...r, __id: `__${nextId.current++}` };
      return newRow;
    });
  };

  // Cuando recibimos new generatedSheetData lo normalizamos
  useEffect(() => {
    setIsLoading(true);
    setError('');

    if (generatedSheetData && generatedSheetData.length > 0) {
      const normalized = normalizeIncoming(generatedSheetData);
      setSheetData(normalized);
      originalRef.current = normalized.map((r) => ({ ...r })); // copia para revertir
    } else {
      setSheetData([]);
      originalRef.current = [];
      setError('No hay una sábana generada para mostrar. Ve a Parámetros y crea una.');
    }

    setIsLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generatedSheetData]); // actualiza cuando cambian los datos generados

  // Función para propagar cambios al padre (sin el __id interno)
  const emitChange = (data) => {
    const cleaned = data.map((r) => {
      const copy = { ...r };
      delete copy.__id;
      return copy;
    });
    onSheetChange(cleaned);
  };

  // Maneja el cambio en una celda
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

  // Agregar fila vacía (manteniendo las columnas actuales)
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

  // Eliminar fila por __id
  const handleDeleteRow = (rowId) => {
    setSheetData((prev) => {
      const updated = prev.filter((r) => r.__id !== rowId);
      emitChange(updated);
      return updated;
    });
  };

  // Revertir al original (generado)
  const handleRevert = () => {
    const copy = originalRef.current.map((r) => ({ ...r }));
    setSheetData(copy);
    emitChange(copy);
  };

  // Descargar CSV de los datos actuales (sin __id)
  const handleDownloadCSV = () => {
    if (!sheetData || sheetData.length === 0) return;
    const headers = Object.keys(sheetData[0]).filter(h => h !== '__id');
    const rows = sheetData.map(r =>
      headers.map(h => {
        const cell = r[h];
        // escapamos comillas dobles
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

  if (isLoading) {
    return <div className="p-4">Cargando sábana...</div>;
  }

  if (error && sheetData.length === 0) {
    return <div className="p-4 text-red-600">{error}</div>;
  }

  if (!sheetData || sheetData.length === 0) {
    return <div className="p-4">No hay datos en la sábana.</div>;
  }

  // Headers para la tabla (ordenados y sin __id)
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h2>Viajes Generados ({sheetData.length})</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleAddRow} style={{ padding: '6px 10px', borderRadius: 6 }}>➕ Agregar fila</button>
            <button onClick={handleRevert} style={{ padding: '6px 10px', borderRadius: 6 }}>↩️ Revertir</button>
            <button onClick={handleDownloadCSV} style={{ padding: '6px 10px', borderRadius: 6 }}>⬇️ Descargar CSV</button>
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
                      {/* Input controlado para cada celda */}
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
                        // onBlur opcional: podrías ejecutar validaciones aquí
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
                      {/* Botón para copiar fila actual (útil para replicar viajes similares) */}
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
    </div>
  );
};

export default SchedulingSheet;
