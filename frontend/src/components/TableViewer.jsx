import React, { useState, useEffect, useCallback, useMemo } from "react"; // ✅ 1. Importa useMemo

// --- Componente Formulario (Sin cambios) ---
function RecordForm({ item, columns, pkColumn, isCreating, onSave, onCancel }) {
  const [formData, setFormData] = useState(item || {});
  useEffect(() => { setFormData(item || {}); }, [item]);
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    let finalValue = type === 'checkbox' ? checked : value;
    const column = columns.find(c => c.name === name);
    const columnType = column?.type;
    if (value === '' || value === null) { finalValue = null; }
    else if (columnType) {
        if (columnType.includes('INTEGER')) finalValue = parseInt(value, 10);
        else if (columnType.includes('FLOAT') || columnType.includes('DECIMAL')) finalValue = parseFloat(value);
        else if (columnType.includes('BOOLEAN')) finalValue = Boolean(checked);
    }
    setFormData(prev => ({ ...prev, [name]: finalValue }));
  };
  const handleSubmit = (e) => { e.preventDefault(); onSave(formData, isCreating); };
  return (
    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4 shadow-sm">
      <h2 className="text-lg font-semibold mb-3 text-gray-700">{isCreating ? 'Añadir Nuevo Registro' : 'Editando Registro'}</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {columns.map(col => {
            let inputType = 'text';
            if (col.type.includes('INTEGER')) inputType = 'number';
            else if (col.type.includes('BOOLEAN')) inputType = 'checkbox';
            else if (col.type.includes('DATE')) inputType = 'date';
            else if (col.type.includes('TIME')) inputType = 'time';
            else if (col.type.includes('DECIMAL') || col.type.includes('FLOAT')) inputType = 'number';
            const isDisabled = col.name === pkColumn && !isCreating;
            if (inputType === 'checkbox') {
                return (
                     <div key={col.name} className="flex items-center col-span-1 pt-5">
                        <input type={inputType} name={col.name} checked={!!formData[col.name]} onChange={handleChange} disabled={isDisabled} id={`field-${col.name}`} className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"/>
                         <label htmlFor={`field-${col.name}`} className="ml-2 block text-sm font-medium text-gray-700 capitalize">{col.name.replace(/_/g, ' ')}</label>
                    </div>
                );
            }
            return (
              <div key={col.name} className="col-span-1">
                <label className="block text-sm font-medium text-gray-700 capitalize mb-1">
                  {col.name.replace(/_/g, ' ')} {col.primary_key ? <span className="text-red-500">*</span> : ''}
                </label>
                <input type={inputType} step={inputType === 'number' && (col.type.includes('DECIMAL') || col.type.includes('FLOAT')) ? 'any' : undefined} name={col.name} value={formData[col.name] ?? ''} onChange={handleChange} disabled={isDisabled} required={col.primary_key && isCreating} className={`block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${isDisabled ? 'bg-gray-100 cursor-not-allowed' : ''}`} />
              </div>
            );
          })}
        </div>
        <div className="flex justify-end space-x-2 pt-2">
          <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400 text-sm font-medium">Cancelar</button>
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">Guardar</button>
        </div>
      </form>
    </div>
  );
}


// --- Componente Principal (CON FILTRO) ---
export default function TableViewer({ table }) {
  const [data, setData] = useState([]); // Almacena TODOS los datos
  const [columns, setColumns] = useState([]);
  const [pkColumn, setPkColumn] = useState(null);
  const [currentItem, setCurrentItem] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true); 
  const [error, setError] = useState(null);
  
  // ✅ 2. Añade estado para el término de búsqueda
  const [searchTerm, setSearchTerm] = useState("");

  // Función de carga (sin cambios, carga todo)
  const fetchData = useCallback(async () => {
    console.log(`[TableViewer] Cargando TODOS los datos para: ${table}`);
    setLoading(true); setError(null); setShowForm(false); setCurrentItem(null);
    try {
      console.log(`[TableViewer ${table}] Cargando estructura...`);
      const inspectRes = await fetch(`http://localhost:8000/admin/inspect/${table}`);
      if (!inspectRes.ok) { const errData = await inspectRes.json(); throw new Error(errData.detail || `Error al cargar estructura ${table}`); }
      const inspectResult = await inspectRes.json();
      setColumns(inspectResult.columns || []);
      setPkColumn(inspectResult.pk);

      console.log(`[TableViewer ${table}] Cargando datos...`);
      const dataRes = await fetch(`http://localhost:8000/admin/${table}`);
      if (!dataRes.ok) { const errData = await dataRes.json(); throw new Error(errData.detail || `Error al cargar datos ${table}`); }
      const dataResult = await dataRes.json();
      
      console.log(`[TableViewer ${table}] Datos recibidos: ${dataResult.length} registros.`);
      setData(dataResult);
    } catch (err) { 
      console.error(`[TableViewer ${table}] Error en fetchData:`, err);
      setError(err.message || 'Error desconocido');
    } finally { 
      setLoading(false); 
    }
  }, [table]);

  useEffect(() => { fetchData(); }, [fetchData]);

  
  // (Funciones handleSave, handleDelete se mantienen igual, solo llaman a fetchData)
  const handleSave = async (itemToSave, creating) => {
    // ... (código sin cambios)
    if (!creating && !pkColumn) return alert("Error: PK no definida.");
    const cleanData = { ...itemToSave };
    columns.forEach(col => { if ((col.type.includes('INTEGER') || col.type.includes('FLOAT') || col.type.includes('DECIMAL')) && cleanData[col.name] !== '' && cleanData[col.name] !== null) { cleanData[col.name] = Number(cleanData[col.name]); }});
    const url = creating ? `http://localhost:8000/admin/${table}` : `http://localhost:8000/admin/${table}/${encodeURIComponent(itemToSave[pkColumn])}`;
    const method = creating ? 'POST' : 'PUT';
    try {
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cleanData) });
      const result = await res.json();
       if (!res.ok) throw new Error(result.detail || `Error ${res.status}.`);
      setCurrentItem(null); setShowForm(false);
      fetchData(); // Recarga todos los datos
    } catch (err) { alert(`Error al guardar: ${err.message}`); }
  };
  const handleDelete = async (item) => {
    // ... (código sin cambios)
     if (!pkColumn || item[pkColumn] === undefined || !window.confirm("¿Seguro?")) return;
    try {
      const res = await fetch(`http://localhost:8000/admin/${table}/${encodeURIComponent(item[pkColumn])}`, { method: 'DELETE' });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Error al eliminar.');
      fetchData(); // Recarga todos los datos
    } catch (err) { alert(`Error al eliminar: ${err.message}`); }
  };
  
  // (Funciones de formulario sin cambios)
  const handleShowCreateForm = () => {
    if (!columns || columns.length === 0) return; 
    const newItem = columns.reduce((acc, col) => ({...acc, [col.name]: col.type.includes('BOOLEAN') ? false : null}), {});
    setCurrentItem(newItem); setIsCreating(true); setShowForm(true); 
  };
  const handleShowEditForm = (row) => {
    setCurrentItem(row); setIsCreating(false); setShowForm(true); 
  };
  const handleCancelForm = () => {
      setShowForm(false); setCurrentItem(null);
  };
  
  // ✅ 3. Filtra los datos usando useMemo para eficiencia
  const filteredData = useMemo(() => {
    // Si no hay término de búsqueda, devuelve todos los datos
    if (!searchTerm) {
      return data;
    }
    const lowerSearchTerm = searchTerm.toLowerCase();

    // Filtra los datos
    return data.filter(row => {
      // Revisa cada columna de la fila
      return columns.some(col => {
        const value = row[col.name];
        // Convierte el valor (número, booleano, null) a string para buscar
        const stringValue = String(value ?? '').toLowerCase(); 
        return stringValue.includes(lowerSearchTerm);
      });
    });
  }, [data, columns, searchTerm]); // Se recalcula solo si data, columns, o searchTerm cambian


  // --- Renderizado ---
  if (loading) return <p className="p-4 text-center animate-pulse">Cargando tabla "{table}"...</p>;
  if (error) return <p className="p-4 text-red-600 bg-red-100 rounded text-center">Error al cargar "{table}": {error}</p>;
  if (columns.length === 0 && !loading) return <p className="p-4 text-center text-orange-600">No se pudo obtener la estructura para "{table}".</p>;

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold capitalize">{table.replace(/_/g, ' ')}</h1>
        <button onClick={showForm ? handleCancelForm : handleShowCreateForm} 
                disabled={columns.length === 0} 
                className={`px-4 py-2 text-white rounded-md text-sm font-medium transition-colors ${showForm ? 'bg-gray-500 hover:bg-gray-600' : 'bg-green-600 hover:bg-green-700'} disabled:opacity-50`}>
          {showForm ? (isCreating ? 'Cancelar Añadir' : 'Cancelar Editar') : 'Añadir Registro'}
        </button>
      </div>

      {/* Formulario (renderizado condicional) */}
      {showForm && currentItem && columns.length > 0 && (
          <RecordForm item={currentItem} columns={columns} pkColumn={pkColumn} isCreating={isCreating} onSave={handleSave} onCancel={handleCancelForm} />
      )}
      
      {/* ✅ 4. Barra de Búsqueda y Contador */}
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <input
          type="search"
          placeholder="Buscar en la tabla..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
        <span className="text-sm text-gray-600 font-medium">
          {/* Muestra el conteo de registros filtrados vs total */}
          {searchTerm 
            ? `Mostrando ${filteredData.length} de ${data.length} registros`
            : `Total: ${data.length} registros`
          }
        </span>
      </div>

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
            {/* ✅ 5. Mapea sobre 'filteredData' en lugar de 'data' */}
            {filteredData.map((row, index) => (
              <tr key={pkColumn ? row[pkColumn] : index} className="hover:bg-gray-50">
                {columns.map(col => ( <td key={col.name} className="px-6 py-4 whitespace-normal text-sm text-gray-800 break-words max-w-xs">{typeof row[col.name] === 'boolean' ? (row[col.name] ? 'Sí' : 'No') : String(row[col.name] ?? '')}</td> ))}
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4 sticky right-0 bg-white hover:bg-gray-50 w-32"> 
                    <button onClick={() => handleShowEditForm(row)} className="text-indigo-600 hover:text-indigo-900">Editar</button> 
                    <button onClick={() => handleDelete(row)} className="text-red-600 hover:text-red-900">Eliminar</button> 
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {/* ✅ 6. Mensajes de estado actualizados */}
        {/* Muestra si el filtro no arrojó resultados */}
        {filteredData.length === 0 && data.length > 0 && !loading && (
          <div className="text-center py-10 text-gray-500">No se encontraron registros que coincidan con "{searchTerm}".</div>
        )}
        {/* Muestra si la tabla está vacía */}
        {data.length === 0 && !loading && !error && (
          <div className="text-center py-10 text-gray-500">(No hay registros en "{table}")</div>
        )}
      </div>
    </div>
  );
}