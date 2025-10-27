import React, { useState, useEffect, useCallback, useRef } from "react";

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


// --- Componente Principal (CON SCROLL INFINITO) ---
export default function TableViewer({ table }) {
  const [data, setData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [pkColumn, setPkColumn] = useState(null);
  const [currentItem, setCurrentItem] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true); 
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Estados para paginación
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  
  const observerTarget = useRef(null);
  const ITEMS_PER_PAGE = 50; // Carga 50 registros por vez

  // Función para cargar estructura de tabla
  const fetchStructure = useCallback(async () => {
    try {
      console.log(`[TableViewer ${table}] Cargando estructura...`);
      const inspectRes = await fetch(`http://localhost:8000/admin/inspect/${table}`);
      if (!inspectRes.ok) {
        const errData = await inspectRes.json();
        throw new Error(errData.detail || `Error al cargar estructura ${table}`);
      }
      const inspectResult = await inspectRes.json();
      setColumns(inspectResult.columns || []);
      setPkColumn(inspectResult.pk);
    } catch (err) {
      console.error(`[TableViewer ${table}] Error en fetchStructure:`, err);
      throw err;
    }
  }, [table]);

  // Función para cargar datos con paginación
  const fetchData = useCallback(async (pageNumber = 0, search = "", reset = false) => {
    if (reset) {
      setLoadingMore(true);
    } else if (pageNumber === 0) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    
    setError(null);

    try {
      const offset = pageNumber * ITEMS_PER_PAGE;
      const params = new URLSearchParams({
        limit: ITEMS_PER_PAGE.toString(),
        offset: offset.toString(),
      });
      
      if (search) {
        params.append('search', search);
      }

      console.log(`[TableViewer ${table}] Cargando página ${pageNumber}, offset: ${offset}, search: "${search}"`);
      
      const dataRes = await fetch(`http://localhost:8000/admin/${table}?${params}`);
      if (!dataRes.ok) {
        const errData = await dataRes.json();
        throw new Error(errData.detail || `Error al cargar datos ${table}`);
      }
      
      const result = await dataRes.json();
      
      // Asume que el backend devuelve { data: [...], total: number }
      // Si tu backend solo devuelve un array, ajusta esto
      const newData = Array.isArray(result) ? result : result.data || [];
      const total = result.total ?? newData.length;
      
      console.log(`[TableViewer ${table}] Datos recibidos: ${newData.length} registros, total: ${total}`);
      
      if (reset || pageNumber === 0) {
        setData(newData);
      } else {
        setData(prev => [...prev, ...newData]);
      }
      
      setTotalCount(total);
      setHasMore(newData.length === ITEMS_PER_PAGE && (offset + newData.length) < total);
      
    } catch (err) {
      console.error(`[TableViewer ${table}] Error en fetchData:`, err);
      setError(err.message || 'Error desconocido');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [table]);

  // Cargar estructura al montar
  useEffect(() => {
    const init = async () => {
      try {
        await fetchStructure();
        await fetchData(0, "");
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };
    init();
  }, [fetchStructure, fetchData]);

  // Debounce para búsqueda
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(0);
      setData([]);
      fetchData(0, searchTerm, true);
    }, 500); // Espera 500ms después de que el usuario deje de escribir

    return () => clearTimeout(timer);
  }, [searchTerm, fetchData]);

  // Intersection Observer para scroll infinito
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
          console.log('[TableViewer] Cargando más datos...');
          const nextPage = page + 1;
          setPage(nextPage);
          fetchData(nextPage, searchTerm);
        }
      },
      { threshold: 0.1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [hasMore, loadingMore, loading, page, searchTerm, fetchData]);

  const handleSave = async (itemToSave, creating) => {
    if (!creating && !pkColumn) return alert("Error: PK no definida.");
    const cleanData = { ...itemToSave };
    columns.forEach(col => {
      if ((col.type.includes('INTEGER') || col.type.includes('FLOAT') || col.type.includes('DECIMAL')) && 
          cleanData[col.name] !== '' && cleanData[col.name] !== null) {
        cleanData[col.name] = Number(cleanData[col.name]);
      }
    });
    
    const url = creating 
      ? `http://localhost:8000/admin/${table}` 
      : `http://localhost:8000/admin/${table}/${encodeURIComponent(itemToSave[pkColumn])}`;
    const method = creating ? 'POST' : 'PUT';
    
    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleanData)
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || `Error ${res.status}.`);
      
      setCurrentItem(null);
      setShowForm(false);
      
      // Recargar datos
      setPage(0);
      setData([]);
      fetchData(0, searchTerm, true);
    } catch (err) {
      alert(`Error al guardar: ${err.message}`);
    }
  };

  const handleDelete = async (item) => {
    if (!pkColumn || item[pkColumn] === undefined) return;
    
    // ✅ ESPECIAL: Si es la tabla "routes", preguntar por eliminación en cascada
    if (table === "routes") {
      const routeId = item[pkColumn];
      const routeName = item.route_short_name || routeId;
      
      // Preguntar si desea eliminar datos relacionados
      const confirmDelete = window.confirm(
        `¿Eliminar la ruta "${routeName}"?\n\n` +
        `Esta acción eliminará la ruta de la base de datos.`
      );
      
      if (!confirmDelete) return;
      
      // Preguntar por trips y stop_times
      const deleteTrips = window.confirm(
        `¿Deseas eliminar también los TRIPS y STOP_TIMES de esta ruta?\n\n` +
        `Esto eliminará TODOS los viajes y horarios asociados a la ruta "${routeName}".\n\n` +
        `Haz clic en OK para eliminar trips y stop_times, o Cancelar para mantenerlos.`
      );
      
      // Preguntar por shapes
      const deleteShapes = window.confirm(
        `¿Deseas eliminar también los SHAPES (trazados) de esta ruta?\n\n` +
        `Esto eliminará los trazados geográficos asociados a "${routeName}".\n\n` +
        `Haz clic en OK para eliminar shapes, o Cancelar para mantenerlos.`
      );
      
      try {
        const res = await fetch(
          `http://localhost:8000/bulk/delete-route-cascade/${encodeURIComponent(routeId)}?delete_trips=${deleteTrips}&delete_shapes=${deleteShapes}`,
          { method: 'DELETE' }
        );
        
        const result = await res.json();
        
        if (!res.ok) throw new Error(result.detail || 'Error al eliminar.');
        
        // Mostrar resumen
        alert(
          `✅ Ruta "${routeName}" eliminada exitosamente!\n\n` +
          `Resumen:\n` +
          `- Trips eliminados: ${result.trips_deleted}\n` +
          `- Stop times eliminados: ${result.stop_times_deleted}\n` +
          `- Shapes eliminados: ${result.shapes_deleted}`
        );
        
        // Recargar datos
        setPage(0);
        setData([]);
        fetchData(0, searchTerm, true);
        
      } catch (err) {
        alert(`Error al eliminar: ${err.message}`);
      }
      
      return; // Salir para no ejecutar el delete normal
    }
    
    // ✅ PARA OTRAS TABLAS: Eliminación normal
    if (!window.confirm("¿Seguro que deseas eliminar este registro?")) return;
    
    try {
      const res = await fetch(
        `http://localhost:8000/admin/${table}/${encodeURIComponent(item[pkColumn])}`,
        { method: 'DELETE' }
      );
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Error al eliminar.');
      
      // Recargar datos
      setPage(0);
      setData([]);
      fetchData(0, searchTerm, true);
    } catch (err) {
      alert(`Error al eliminar: ${err.message}`);
    }
  };

  const handleShowCreateForm = () => {
    if (!columns || columns.length === 0) return;
    const newItem = columns.reduce((acc, col) => ({
      ...acc,
      [col.name]: col.type.includes('BOOLEAN') ? false : null
    }), {});
    setCurrentItem(newItem);
    setIsCreating(true);
    setShowForm(true);
  };

  const handleShowEditForm = (row) => {
    setCurrentItem(row);
    setIsCreating(false);
    setShowForm(true);
  };

  const handleCancelForm = () => {
    setShowForm(false);
    setCurrentItem(null);
  };

  // Renderizado
  if (loading && data.length === 0) {
    return <p className="p-4 text-center animate-pulse">Cargando tabla "{table}"...</p>;
  }
  
  if (error && data.length === 0) {
    return <p className="p-4 text-red-600 bg-red-100 rounded text-center">Error al cargar "{table}": {error}</p>;
  }
  
  if (columns.length === 0 && !loading) {
    return <p className="p-4 text-center text-orange-600">No se pudo obtener la estructura para "{table}".</p>;
  }

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold capitalize">{table.replace(/_/g, ' ')}</h1>
        <button 
          onClick={showForm ? handleCancelForm : handleShowCreateForm}
          disabled={columns.length === 0}
          className={`px-4 py-2 text-white rounded-md text-sm font-medium transition-colors ${
            showForm ? 'bg-gray-500 hover:bg-gray-600' : 'bg-green-600 hover:bg-green-700'
          } disabled:opacity-50`}
        >
          {showForm ? (isCreating ? 'Cancelar Añadir' : 'Cancelar Editar') : 'Añadir Registro'}
        </button>
      </div>

      {/* Formulario */}
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

      {/* Barra de Búsqueda y Contador */}
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <input
          type="search"
          placeholder="Buscar en la tabla..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm w-64"
        />
        <span className="text-sm text-gray-600 font-medium">
          Mostrando {data.length} de {totalCount} registros
        </span>
      </div>

      {/* Tabla Scrollable */}
      <div className="flex-grow overflow-auto bg-white rounded-lg shadow border border-gray-200 relative">
        <table className="min-w-full divide-y divide-gray-200 table-auto">
          <thead className="bg-gray-100 sticky top-0 z-10">
            <tr>
              {columns.map(col => (
                <th key={col.name} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {col.name.replace(/_/g, ' ')}
                </th>
              ))}
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider sticky right-0 bg-gray-100 w-32">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, index) => (
              <tr key={pkColumn ? row[pkColumn] : index} className="hover:bg-gray-50">
                {columns.map(col => (
                  <td key={col.name} className="px-6 py-4 whitespace-normal text-sm text-gray-800 break-words max-w-xs">
                    {typeof row[col.name] === 'boolean' 
                      ? (row[col.name] ? 'Sí' : 'No') 
                      : String(row[col.name] ?? '')}
                  </td>
                ))}
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-4 sticky right-0 bg-white hover:bg-gray-50 w-32">
                  <button onClick={() => handleShowEditForm(row)} className="text-indigo-600 hover:text-indigo-900">
                    Editar
                  </button>
                  <button onClick={() => handleDelete(row)} className="text-red-600 hover:text-red-900">
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Indicador de carga para scroll infinito */}
        {loadingMore && (
          <div className="text-center py-4 text-gray-500">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
            <span className="ml-2">Cargando más...</span>
          </div>
        )}

        {/* Elemento observador para scroll infinito */}
        <div ref={observerTarget} className="h-4" />

        {/* Mensajes de estado */}
        {data.length === 0 && !loading && !error && (
          <div className="text-center py-10 text-gray-500">
            {searchTerm 
              ? `No se encontraron registros que coincidan con "${searchTerm}".`
              : `(No hay registros en "${table}")`
            }
          </div>
        )}
        
        {!hasMore && data.length > 0 && (
          <div className="text-center py-4 text-gray-400 text-sm">
            Fin de los resultados
          </div>
        )}
      </div>
    </div>
  );
}