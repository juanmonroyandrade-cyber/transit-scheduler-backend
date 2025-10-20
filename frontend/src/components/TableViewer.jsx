// src/components/TableViewer.jsx
import { useEffect, useState } from "react";

const TABLES = [
  "agency", "routes", "stops", "trips", "stop_times",
  "calendar", "fare_attributes", "fare_rules", "feed_info"
];

export default function TableViewer() {
  const [table, setTable] = useState("routes");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editedData, setEditedData] = useState({});
  const [newRow, setNewRow] = useState({});
  const [message, setMessage] = useState(null);
  const API_URL = "http://localhost:8000/admin";

  const fetchData = () => {
    setLoading(true);
    setMessage(null);
    fetch(`${API_URL}/${table}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        setData(Array.isArray(json) ? json : []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error cargando datos:", err);
        setMessage({ type: "error", text: `Error cargando datos: ${err.message}` });
        setData([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
    setEditingRow(null);
    setNewRow({});
    setMessage(null);
  }, [table]);

  // Determinar la clave primaria según la tabla
  const getPrimaryKey = (row) => {
    if (table === "stops") return row.stop_id;
    if (table === "routes") return row.route_id;
    if (table === "trips") return row.trip_id;
    if (table === "stop_times") return row.id;
    if (table === "agency") return row.agency_id;
    if (table === "calendar") return row.service_id;
    if (table === "fare_attributes") return row.fare_id;
    if (table === "fare_rules") return row.id;
    return row.id;
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleDelete = async (row) => {
    if (!confirm(`¿Estás seguro de eliminar este registro?`)) return;
    
    const pk = getPrimaryKey(row);
    
    try {
      const res = await fetch(`${API_URL}/${table}/${pk}`, { 
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      });
      
      const result = await res.json();
      
      if (res.ok) {
        showMessage("success", result.message || "Registro eliminado correctamente");
        fetchData();
      } else {
        showMessage("error", result.detail || "Error al eliminar");
      }
    } catch (err) {
      console.error("Error:", err);
      showMessage("error", `Error de conexión: ${err.message}`);
    }
  };

  const handleEdit = (row) => {
    setEditingRow(row);
    setEditedData({...row});
  };

  const handleCancelEdit = () => {
    setEditingRow(null);
    setEditedData({});
  };

  const handleSave = async () => {
    const pk = getPrimaryKey(editingRow);
    
    try {
      const res = await fetch(`${API_URL}/${table}/${pk}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editedData),
      });
      
      const result = await res.json();
      
      if (res.ok) {
        showMessage("success", result.message || "Registro actualizado correctamente");
        setEditingRow(null);
        setEditedData({});
        fetchData();
      } else {
        showMessage("error", result.detail || "Error al actualizar");
      }
    } catch (err) {
      console.error("Error:", err);
      showMessage("error", `Error de conexión: ${err.message}`);
    }
  };

  const handleAdd = async () => {
    // Validar que haya al menos un campo lleno
    const filledFields = Object.entries(newRow).filter(([k, v]) => v && v.toString().trim() !== "");
    
    if (filledFields.length === 0) {
      showMessage("error", "Completa al menos un campo");
      return;
    }

    // Limpiar campos vacíos
    const cleanedData = {};
    filledFields.forEach(([k, v]) => {
      cleanedData[k] = v;
    });

    try {
      const res = await fetch(`${API_URL}/${table}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cleanedData),
      });
      
      const result = await res.json();
      
      if (res.ok) {
        showMessage("success", result.message || "Registro agregado correctamente");
        setNewRow({});
        fetchData();
      } else {
        showMessage("error", result.detail || "Error al agregar");
      }
    } catch (err) {
      console.error("Error:", err);
      showMessage("error", `Error de conexión: ${err.message}`);
    }
  };

  const handleInputChange = (key, value, isEdit = false) => {
    if (isEdit) {
      setEditedData(prev => ({...prev, [key]: value}));
    } else {
      setNewRow(prev => ({...prev, [key]: value}));
    }
  };

  const keys = data[0] ? Object.keys(data[0]) : [];

  return (
    <div className="p-6 w-full h-screen overflow-y-auto bg-gray-50">
      <div className="max-w-full">
        <h2 className="text-3xl font-bold mb-6 text-gray-800">📊 Editor de Tablas GTFS</h2>
        
        {/* Mensaje de feedback */}
        {message && (
          <div className={`mb-4 p-4 rounded-lg ${
            message.type === "success" 
              ? "bg-green-100 border border-green-400 text-green-700" 
              : "bg-red-100 border border-red-400 text-red-700"
          }`}>
            <div className="flex items-center gap-2">
              <span className="text-xl">{message.type === "success" ? "✅" : "❌"}</span>
              <span className="font-medium">{message.text}</span>
            </div>
          </div>
        )}
        
        {/* Selector de tablas */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {TABLES.map((t) => (
            <button
              key={t}
              onClick={() => setTable(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all transform hover:scale-105 ${
                table === t 
                  ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg" 
                  : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-300"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Cargando datos...</p>
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500 text-lg">📭 No hay datos en esta tabla</p>
            <p className="text-gray-400 text-sm mt-2">Agrega el primer registro usando el formulario abajo</p>
          </div>
        ) : (
          <>
            {/* Tabla de datos */}
            <div className="bg-white rounded-lg shadow-lg overflow-hidden mb-6">
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="bg-gradient-to-r from-gray-100 to-gray-200">
                    <tr>
                      {keys.map((k) => (
                        <th key={k} className="px-4 py-3 text-left font-semibold text-gray-700 border-b-2 border-gray-300">
                          {k}
                        </th>
                      ))}
                      <th className="px-4 py-3 text-left font-semibold text-gray-700 border-b-2 border-gray-300 sticky right-0 bg-gray-100">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, i) => (
                      <tr 
                        key={i} 
                        className={`${
                          editingRow === row 
                            ? "bg-blue-50" 
                            : "odd:bg-white even:bg-gray-50"
                        } hover:bg-blue-100 transition-colors`}
                      >
                        {keys.map((k) => (
                          <td key={k} className="px-4 py-3 border-b border-gray-200">
                            {editingRow === row ? (
                              <input
                                type="text"
                                value={editedData[k] ?? ""}
                                onChange={(e) => handleInputChange(k, e.target.value, true)}
                                className="w-full border border-blue-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                              />
                            ) : (
                              <span className="text-gray-800">
                                {row[k]?.toString() || <span className="text-gray-400 italic">null</span>}
                              </span>
                            )}
                          </td>
                        ))}
                        <td className="px-4 py-3 border-b border-gray-200 sticky right-0 bg-inherit">
                          {editingRow === row ? (
                            <div className="flex gap-2">
                              <button 
                                onClick={handleSave} 
                                className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-md text-xs font-medium transition-all shadow-sm hover:shadow-md"
                              >
                                💾 Guardar
                              </button>
                              <button 
                                onClick={handleCancelEdit} 
                                className="bg-gray-400 hover:bg-gray-500 text-white px-3 py-1.5 rounded-md text-xs font-medium transition-all"
                              >
                                ✖️ Cancelar
                              </button>
                            </div>
                          ) : (
                            <div className="flex gap-2">
                              <button 
                                onClick={() => handleEdit(row)} 
                                className="bg-yellow-400 hover:bg-yellow-500 text-gray-800 px-3 py-1.5 rounded-md text-xs font-medium transition-all shadow-sm hover:shadow-md"
                              >
                                ✏️ Editar
                              </button>
                              <button 
                                onClick={() => handleDelete(row)} 
                                className="bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-md text-xs font-medium transition-all shadow-sm hover:shadow-md"
                              >
                                🗑️ Eliminar
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Contador de registros */}
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                <p className="text-sm text-gray-600">
                  📊 Total de registros: <span className="font-semibold">{data.length}</span>
                </p>
              </div>
            </div>
          </>
        )}

        {/* Formulario para agregar nueva fila */}
        <div className="bg-white rounded-lg shadow-lg p-6 border-2 border-dashed border-gray-300">
          <h3 className="font-bold text-xl mb-4 text-gray-800 flex items-center gap-2">
            <span className="text-2xl">➕</span>
            Agregar nuevo registro en <span className="text-blue-600">{table}</span>
          </h3>
          
          {keys.length === 0 ? (
            <p className="text-gray-400 italic">Primero carga una tabla con datos para ver los campos</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-4">
                {keys.map((k) => (
                  <div key={k} className="flex flex-col">
                    <label className="text-xs font-semibold text-gray-600 mb-1.5">
                      {k}
                    </label>
                    <input
                      type="text"
                      placeholder={`Ingresa ${k}...`}
                      value={newRow[k] || ""}
                      onChange={(e) => handleInputChange(k, e.target.value, false)}
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition-all"
                    />
                  </div>
                ))}
              </div>
              
              <div className="flex gap-3">
                <button 
                  onClick={handleAdd} 
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-6 py-3 rounded-lg font-semibold transition-all transform hover:scale-105 shadow-lg hover:shadow-xl"
                >
                  ➕ Agregar Registro
                </button>
                
                <button 
                  onClick={() => setNewRow({})} 
                  className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-6 py-3 rounded-lg font-medium transition-all"
                >
                  🗑️ Limpiar Formulario
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}