// frontend/src/components/TableViewer.jsx

import { useState, useEffect, useCallback, useRef } from "react";

// (El componente EditModal no necesita cambios)
function EditModal({ item, columns, pkColumn, onSave, onCancel }) {
  const [formData, setFormData] = useState(item || {});
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };
  const handleSubmit = (e) => { e.preventDefault(); onSave(formData); };
  const isCreating = !item[pkColumn];
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">{isCreating ? 'Añadir' : 'Editar'} Registro</h2>
        <form onSubmit={handleSubmit} className="space-y-4">{columns.map(col => (<div key={col.name}><label className="block text-sm font-medium text-gray-700 capitalize">{col.name.replace(/_/g, ' ')}</label><input type={col.type.includes('INTEGER') ? 'number' : col.type.includes('BOOLEAN') ? 'checkbox' : 'text'} name={col.name} value={formData[col.name] ?? ''} checked={col.type.includes('BOOLEAN') ? !!formData[col.name] : undefined} onChange={handleChange} disabled={col.name === pkColumn && !isCreating} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-100"/></div>))}<div className="flex justify-end space-x-3 pt-4"><button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300">Cancelar</button><button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Guardar</button></div></form>
      </div>
    </div>
  );
}

export default function TableViewer({ table }) {
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [pkColumn, setPkColumn] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const observer = useRef();
  const lastRowRef = useCallback(node => {
    if (loading) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        setPage(prevPage => prevPage + 1);
      }
    });
    if (node) observer.current.observe(node);
  }, [loading, hasMore]);

  useEffect(() => {
    // Resetea todo cuando la tabla cambia
    setData([]);
    setColumns([]);
    setPkColumn(null);
    setPage(1);
    setHasMore(true);
  }, [table]);

  useEffect(() => {
    if (!hasMore && page > 1) return; // No cargar más si ya no hay
    setLoading(true);
    setError(null);
    
    let isMounted = true;

    const fetchData = async () => {
      try {
        if (columns.length === 0) {
          const inspectRes = await fetch(`http://localhost:8000/admin/inspect/${table}`);
          const inspectResult = await inspectRes.json();
          if (isMounted) {
            setColumns(inspectResult.columns);
            setPkColumn(inspectResult.pk);
          }
        }
        
        const dataRes = await fetch(`http://localhost:8000/admin/${table}?page=${page}&per_page=50`);
        const result = await dataRes.json();

        if (isMounted) {
          setData(prev => [...prev, ...result.data]);
          setHasMore(result.page < result.total_pages);
        }
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();
    return () => { isMounted = false; };
  }, [table, page]);

  const refreshData = async () => {
    setData([]);
    setPage(1);
    setHasMore(true);
  };
  
  // (Las funciones handleSave, handleDelete y handleCreate se actualizan para llamar a refreshData)
  const handleSave = async (itemToSave) => {
    const isCreating = !itemToSave[pkColumn];
    const url = isCreating ? `http://localhost:8000/admin/${table}` : `http://localhost:8000/admin/${table}/${encodeURIComponent(itemToSave[pkColumn])}`;
    const method = isCreating ? 'POST' : 'PUT';
    
    try {
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(itemToSave) });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Error al guardar.');
      setEditingItem(null);
      refreshData();
    } catch (err) { alert(`Error: ${err.message}`); }
  };

  const handleDelete = async (item) => {
    if (!pkColumn || !item[pkColumn] || !window.confirm("¿Seguro?")) return;
    try {
      const res = await fetch(`http://localhost:8000/admin/${table}/${encodeURIComponent(item[pkColumn])}`, { method: 'DELETE' });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Error al eliminar.');
      refreshData();
    } catch (err) { alert(`Error: ${err.message}`); }
  };
  
  const handleCreate = () => {
    const newItem = columns.reduce((acc, col) => ({...acc, [col.name]: col.type.includes('BOOLEAN') ? false : ''}), {});
    setEditingItem(newItem);
  };
  
  if (columns.length === 0 && loading) return <p className="p-4">Cargando tabla "{table}"...</p>;
  if (error) return <p className="p-4 text-red-500 bg-red-100 rounded">Error: {error}</p>;

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold capitalize">{table.replace(/_/g, ' ')}</h1>
        <button onClick={handleCreate} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700">Añadir Registro</button>
      </div>

      {editingItem && <EditModal item={editingItem} columns={columns} pkColumn={pkColumn} onSave={handleSave} onCancel={() => setEditingItem(null)} />}

      <div className="flex-grow overflow-auto bg-white rounded-lg shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {columns.map(col => <th key={col.name} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{col.name.replace(/_/g, ' ')}</th>)}
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, index) => {
              const rowContent = (
                <tr key={row[pkColumn] || index} className="hover:bg-gray-50">
                  {columns.map(col => <td key={col.name} className="px-6 py-4 whitespace-nowrap text-sm text-gray-800">{typeof row[col.name] === 'boolean' ? (row[col.name] ? 'Sí' : 'No') : String(row[col.name])}</td>)}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4">
                    <button onClick={() => setEditingItem(row)} className="text-indigo-600 hover:text-indigo-900">Editar</button>
                    <button onClick={() => handleDelete(row)} className="text-red-600 hover:text-red-900">Eliminar</button>
                  </td>
                </tr>
              );
              // Asigna la ref al último elemento para disparar la carga
              if (data.length === index + 1) {
                return <>{React.cloneElement(rowContent, { ref: lastRowRef })}</>;
              }
              return rowContent;
            })}
          </tbody>
        </table>
        {loading && <div className="text-center p-4">Cargando más registros...</div>}
        {!hasMore && data.length > 0 && <div className="text-center p-4 text-gray-500">Fin de los registros.</div>}
        {data.length === 0 && !loading && <div className="text-center py-8 text-gray-500">No hay registros en esta tabla.</div>}
      </div>
    </div>
  );
}