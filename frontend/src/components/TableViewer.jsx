import React, { useState, useEffect, useCallback, useRef } from "react";

// --- Componente Formulario (Integrado ahora, no es un modal separado) ---
function RecordForm({ item, columns, pkColumn, isCreating, onSave, onCancel }) {
  const [formData, setFormData] = useState(item || {});

  useEffect(() => {
    // Actualiza el formulario si el item cambia (ej. al pasar de 'Añadir' a 'Editar')
    setFormData(item || {});
  }, [item]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    let finalValue = type === 'checkbox' ? checked : value;
    const column = columns.find(c => c.name === name);
    const columnType = column?.type;

    if (value === '' || value === null) {
      finalValue = null;
    } else if (columnType) {
        if (columnType.includes('INTEGER')) finalValue = parseInt(value, 10);
        else if (columnType.includes('FLOAT') || columnType.includes('DECIMAL')) finalValue = parseFloat(value);
        else if (columnType.includes('BOOLEAN')) finalValue = Boolean(checked);
    }
    setFormData(prev => ({ ...prev, [name]: finalValue }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData, isCreating);
  };

  return (
    // Sección del formulario con fondo y borde
    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4 shadow-sm">
      <h2 className="text-lg font-semibold mb-3 text-gray-700">{isCreating ? 'Añadir Nuevo Registro' : 'Editando Registro'}</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Grid para mejor disposición en pantallas más grandes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {columns.map(col => {
            let inputType = 'text';
            if (col.type.includes('INTEGER')) inputType = 'number';
            else if (col.type.includes('BOOLEAN')) inputType = 'checkbox';
            else if (col.type.includes('DATE')) inputType = 'date';
            else if (col.type.includes('TIME')) inputType = 'time';
            else if (col.type.includes('DECIMAL') || col.type.includes('FLOAT')) inputType = 'number';
            
            const isDisabled = col.name === pkColumn && !isCreating;

            return (
              <div key={col.name} className={inputType === 'checkbox' ? 'flex items-center col-span-1 md:col-span-2' : 'col-span-1'}>
                <label className={`block text-sm font-medium text-gray-700 capitalize ${inputType === 'checkbox' ? 'mr-2' : 'mb-1'}`}>
                  {col.name.replace(/_/g, ' ')} {col.primary_key ? <span className="text-red-500">*</span> : ''}
                </label>
                <input
                  type={inputType}
                  step={inputType === 'number' && (col.type.includes('DECIMAL') || col.type.includes('FLOAT')) ? 'any' : undefined}
                  name={col.name}
                  value={formData[col.name] ?? ''}
                  checked={inputType === 'checkbox' ? !!formData[col.name] : undefined}
                  onChange={handleChange}
                  disabled={isDisabled}
                  required={col.primary_key && isCreating}
                  className={`block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${isDisabled ? 'bg-gray-100 cursor-not-allowed' : ''} ${inputType === 'checkbox' ? 'h-4 w-4 rounded' : ''}`}
                />
              </div>
            )}
          )}
        </div>
        {/* Botones */}
        <div className="flex justify-end space-x-2 pt-2">
          <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400 text-sm font-medium">Cancelar</button>
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">Guardar</button>
        </div>
      </form>
    </div>
  );
}


// --- Componente Principal (Usa RecordForm en lugar de EditModal) ---
export default function TableViewer({ table }) {
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [pkColumn, setPkColumn] = useState(null);
  const [currentItem, setCurrentItem] = useState(null); // Item actual (para añadir o editar)
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false); // ✅ Controla visibilidad del formulario
  
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true); 
  const [loadingMore, setLoadingMore] = useState(false); 
  const [error, setError] = useState(null);
  const [totalRecords, setTotalRecords] = useState(0);

  const observer = useRef();
  const lastRowRef = useCallback(node => {
    if (loadingMore || !hasMore) return; 
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) { setPage(prevPage => prevPage + 1); }
    });
    if (node) observer.current.observe(node);
  }, [loadingMore, hasMore]);

  // Resetear estado
  useEffect(() => {
    setData([]); setColumns([]); setPkColumn(null); setPage(1); 
    setHasMore(true); setLoading(true); setError(null); setTotalRecords(0);
    setShowForm(false); setCurrentItem(null); // ✅ Resetea formulario
  }, [table]);

  // Cargar datos
  useEffect(() => {
    if (!hasMore && page > 1) { setLoading(false); setLoadingMore(false); return; }
    if(page === 1) setLoading(true); else setLoadingMore(true);
    setError(null);
    let isMounted = true; 

    const fetchData = async () => {
      try {
        if (page === 1 && columns.length === 0) {
          const inspectRes = await fetch(`http://localhost:8000/admin/inspect/${table}`);
          if (!isMounted || !inspectRes.ok) throw new Error(`Error estructura ${table}: ${inspectRes.statusText}`);
          const inspectResult = await inspectRes.json();
          if (isMounted) { setColumns(inspectResult.columns || []); setPkColumn(inspectResult.pk); }
        }
        const dataRes = await fetch(`http://localhost:8000/admin/${table}?page=${page}&per_page=50`);
        if (!isMounted || !dataRes.ok) throw new Error(`Error datos ${table} p.${page}: ${dataRes.statusText}`);
        const result = await dataRes.json();
        if (isMounted) {
            setData(prev => (page === 1 ? result.data : [...prev, ...result.data])); 
            setHasMore(result.page < result.total_pages);
            setTotalRecords(result.total_records);
        }
      } catch (err) { if (isMounted) setError(err.message || 'Error desconocido');
      } finally { if (isMounted) { setLoading(false); setLoadingMore(false); } }
    };
    fetchData();
    return () => { isMounted = false; if (observer.current) observer.current.disconnect(); };
  }, [table, page]); 

  // Refrescar
  const refreshData = () => { setData([]); setPage(1); setHasMore(true); };
  
  // Guardado (usa flag 'creating' explícito)
  const handleSave = async (itemToSave, creating) => {
    if (!creating && !pkColumn) return alert("Error: PK no definida para actualizar.");
    const cleanData = { ...itemToSave };
    columns.forEach(col => { if ((col.type.includes('INTEGER') || col.type.includes('FLOAT') || col.type.includes('DECIMAL')) && cleanData[col.name] !== '' && cleanData[col.name] !== null) { cleanData[col.name] = Number(cleanData[col.name]); }});
    const url = creating ? `http://localhost:8000/admin/${table}` : `http://localhost:8000/admin/${table}/${encodeURIComponent(itemToSave[pkColumn])}`;
    const method = creating ? 'POST' : 'PUT';
    
    try {
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cleanData) });
      const result = await res.json();
       if (!res.ok) throw new Error(result.detail || `Error ${res.status}.`);
      setCurrentItem(null); // Limpia item
      setShowForm(false);  // ✅ Oculta formulario
      refreshData();
    } catch (err) { alert(`Error al guardar: ${err.message}`); }
  };

  // Borrado
  const handleDelete = async (item) => {
     if (!pkColumn || item[pkColumn] === undefined || !window.confirm("¿Seguro?")) return;
    try {
      const res = await fetch(`http://localhost:8000/admin/${table}/${encodeURIComponent(item[pkColumn])}`, { method: 'DELETE' });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Error al eliminar.');
      refreshData();
    } catch (err) { alert(`Error al eliminar: ${err.message}`); }
  };
  
  // ✅ Prepara para crear y muestra el formulario
  const handleShowCreateForm = () => {
    if (!columns || columns.length === 0) return; 
    const newItem = columns.reduce((acc, col) => ({...acc, [col.name]: col.type.includes('BOOLEAN') ? false : null}), {});
    setCurrentItem(newItem);
    setIsCreating(true);
    setShowForm(true); // Muestra el formulario
  };

  // ✅ Prepara para editar y muestra el formulario
  const handleShowEditForm = (row) => {
    setCurrentItem(row);
    setIsCreating(false);
    setShowForm(true); // Muestra el formulario
  };
  
  // ✅ Oculta el formulario
  const handleCancelForm = () => {
      setShowForm(false);
      setCurrentItem(null);
  };
  
  // --- Renderizado ---
  if (loading && page === 1 && columns.length === 0) return <p className="p-4 text-center animate-pulse">Cargando "{table}"...</p>;
  if (error && !loadingMore) return <p className="p-4 text-red-600 bg-red-100 rounded text-center">Error al cargar "{table}": {error}</p>;
  if (columns.length === 0 && !loading) return <p className="p-4 text-center text-orange-600">No se pudo obtener la estructura para "{table}".</p>;

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold capitalize">{table.replace(/_/g, ' ')}</h1>
        {/* El botón ahora solo muestra/oculta el formulario */}
        <button onClick={showForm ? handleCancelForm : handleShowCreateForm} 
                disabled={columns.length === 0} 
                className={`px-4 py-2 text-white rounded-md text-sm font-medium ${showForm ? 'bg-gray-500 hover:bg-gray-600' : 'bg-green-600 hover:bg-green-700'} disabled:opacity-50`}>
          {showForm ? 'Cancelar' : 'Añadir Registro'}
        </button>
      </div>

      {/* ✅ Renderiza el formulario aquí si showForm es true */}
      {showForm && currentItem && columns.length > 0 && (
          <RecordForm 
              item={currentItem} 
              columns={columns} 
              pkColumn={pkColumn} 
              isCreating={isCreating} 
              onSave={handleSave} 
              onCancel={handleCancelForm} 
          />
      )}

      {/* Tabla Scrollable */}
      <div className="flex-grow overflow-auto bg-white rounded-lg shadow border border-gray-200 relative">
        <table className="min-w-full divide-y divide-gray-200 table-auto">
          <thead className="bg-gray-100 sticky top-0 z-10">
            <tr>
              {columns.map(col => <th key={col.name} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{col.name.replace(/_/g, ' ')}</th>)}
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider sticky right-0 bg-gray-100 w-32">Acciones</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, index) => (
              <tr ref={data.length === index + 1 ? lastRowRef : null} key={pkColumn ? row[pkColumn] : index} className="hover:bg-gray-50">
                {columns.map(col => ( <td key={col.name} className="px-6 py-4 whitespace-normal text-sm text-gray-800 break-words max-w-xs">{typeof row[col.name] === 'boolean' ? (row[col.name] ? 'Sí' : 'No') : String(row[col.name] ?? '')}</td> ))}
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4 sticky right-0 bg-white hover:bg-gray-50 w-32"> 
                    {/* Botón editar ahora llama a handleShowEditForm */}
                    <button onClick={() => handleShowEditForm(row)} className="text-indigo-600 hover:text-indigo-900">Editar</button> 
                    <button onClick={() => handleDelete(row)} className="text-red-600 hover:text-red-900">Eliminar</button> 
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {/* Indicadores */}
        {loadingMore && <div className="text-center p-4 text-sm text-gray-500 animate-pulse">Cargando más...</div>}
        {!hasMore && data.length > 0 && <div className="text-center p-4 text-sm text-gray-500">-- Fin ({totalRecords}) --</div>}
        {data.length === 0 && !loading && !loadingMore && !error && <div className="text-center py-10 text-gray-500">(No hay registros en "{table}")</div>}
      </div>
    </div>
  );
}