import React, { useState, useEffect } from "react";

/*
  TimetableGenerator.jsx
  - Componente corregido y funcional
  - Formato de tiempos: HH:MM
  - Ordena ciclos por hora de salida ascendente (primer tiempo disponible en dir_0 o dir_1)
  - Extrae número de bus desde block_id (por ejemplo "458.1" -> "1")
  - Protecciones contra accesos a propiedades undefined
  - Exportado como componente por defecto
*/

export default function TimetableGenerator() {
  // Estados principales
  const [routes, setRoutes] = useState([]);
  const [services, setServices] = useState([]);
  const [stops, setStops] = useState([]);

  // Selecciones del usuario
  const [selectedRoute, setSelectedRoute] = useState("");
  const [selectedService, setSelectedService] = useState("");
  const [selectedStops, setSelectedStops] = useState(new Set());
  const [timeRange, setTimeRange] = useState({ start: "00:00", end: "23:59" });

  // Datos procesados
  const [timetableData, setTimetableData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ message: "", type: "" });

  // --- Fetch inicial de rutas y servicios ---
  useEffect(() => {
    const fetchRoutes = async () => {
      try {
        const res = await fetch("http://localhost:8000/admin/routes");
        if (res.ok) {
          const data = await res.json();
          setRoutes(data || []);
        }
      } catch (err) {
        console.error("Error cargando rutas:", err);
      }
    };
    fetchRoutes();
  }, []);

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const res = await fetch("http://localhost:8000/admin/calendar");
        if (res.ok) {
          const data = await res.json();
          setServices(data || []);
        }
      } catch (err) {
        console.error("Error cargando servicios:", err);
      }
    };
    fetchServices();
  }, []);

  // Cargar paradas cuando se selecciona una ruta
  useEffect(() => {
    if (!selectedRoute) {
      setStops([]);
      setSelectedStops(new Set());
      return;
    }

    const fetchStops = async () => {
      try {
        setStatus({ message: "Cargando paradas...", type: "loading" });
        const res = await fetch(`http://localhost:8000/timetables/route-stops/${selectedRoute}`);
        if (res.ok) {
          const data = await res.json();
          // data.stops esperado como array de stops con stop_id, stop_name, stop_sequence, direction_id
          setStops(data.stops || []);
          setStatus({ message: "", type: "" });
        } else {
          throw new Error("Error al cargar paradas");
        }
      } catch (err) {
        console.error("Error cargando paradas:", err);
        setStatus({ message: "Error al cargar paradas", type: "error" });
        setStops([]);
      }
    };
    fetchStops();
  }, [selectedRoute]);

  // Manejar selección de paradas
  const toggleStop = (stopId) => {
    const newSelected = new Set(selectedStops);
    if (newSelected.has(stopId)) newSelected.delete(stopId);
    else newSelected.add(stopId);
    setSelectedStops(newSelected);
  };

  const selectAllStops = () => setSelectedStops(new Set(stops.map((s) => s.stop_id)));
  const clearAllStops = () => setSelectedStops(new Set());

  // --- Helpers ---
  const pad = (n) => String(n).padStart(2, "0");

  // calcula diferencia en HH:MM entre time1 y time2 (ambos "HH:MM"), ajusta si cruza medianoche
  const calculateInterval = (time1, time2) => {
    if (!time1 || !time2) return "";
    const [h1, m1] = time1.split(":").map(Number);
    const [h2, m2] = time2.split(":").map(Number);
    if (Number.isNaN(h1) || Number.isNaN(m1) || Number.isNaN(h2) || Number.isNaN(m2)) return "";

    const total1 = h1 * 60 + m1;
    let total2 = h2 * 60 + m2;
    let diff = total2 - total1;
    if (diff < 0) diff += 24 * 60; // cruzó medianoche
    const hours = Math.floor(diff / 60);
    const minutes = diff % 60;
    return `${pad(hours)}:${pad(minutes)}`;
  };

  // extrae número de bus desde block_id formato "458.1" => "1"
  const parseBusNumber = (blockId) => {
    if (!blockId) return "";
    const parts = String(blockId).split(".");
    return parts.length > 1 ? parts[1] : parts[0];
  };

  // Ordena ciclos por hora de salida (primer tiempo disponible dir_0 o dir_1)
  const sortCyclesByDeparture = (cycles) => {
    if (!Array.isArray(cycles)) return cycles || [];
    return [...cycles].sort((a, b) => {
      const ta =
        (a?.dir_0?.first_stop_time || a?.dir_1?.first_stop_time || "00:00");
      const tb =
        (b?.dir_0?.first_stop_time || b?.dir_1?.first_stop_time || "00:00");
      // Comparar como strings "HH:MM" funciona para formato 24h
      return ta.localeCompare(tb);
    });
  };

  // --- Generar timetable (llamada backend) ---
  const generateTimetable = async () => {
    if (!selectedRoute || !selectedService || selectedStops.size === 0) {
      setStatus({ message: "Por favor selecciona ruta, servicio y al menos una parada", type: "error" });
      return;
    }

    setLoading(true);
    setStatus({ message: "Generando timetable...", type: "loading" });

    try {
      const requestData = {
        route_id: selectedRoute,
        service_id: selectedService,
        stop_ids: Array.from(selectedStops),
        time_range: timeRange,
      };

      const res = await fetch("http://localhost:8000/timetables/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Error al generar timetable");
      }

      const data = await res.json();

      // Normalizaciones y protecciones
      data.stops_by_direction = data.stops_by_direction || { dir_0: [], dir_1: [] };
      data.selected_stops = data.selected_stops || []; // si backend devuelve selected_stops
      data.cycles = data.cycles || [];

      // Extraer bus_number y asegurar campos dir_0 / dir_1
      data.cycles = data.cycles.map((c) => {
        const clone = { ...c };
        clone.bus_number = parseBusNumber(c.block_id || c.block_id?.toString?.() || "");
        clone.dir_0 = clone.dir_0 || { first_stop_time: "", last_stop_time: "" };
        clone.dir_1 = clone.dir_1 || { first_stop_time: "", last_stop_time: "" };
        return clone;
      });

      // Ordenar por hora de salida (asc)
      data.cycles = sortCyclesByDeparture(data.cycles);

      setTimetableData(data);
      setStatus({ message: "✅ Timetable generado correctamente", type: "success" });
    } catch (err) {
      console.error("Error:", err);
      setStatus({ message: `❌ ${err.message}`, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  // --- Descargar CSV ---
  const downloadCSV = () => {
    if (!timetableData) return;
    const selectedStopsList = Array.isArray(timetableData.selected_stops)
      ? timetableData.selected_stops
      : []; // protección

    let csv = "";
    csv += `"${timetableData.service_days || ""}"\n`;
    csv += `"${timetableData.route_name || ""}"\n\n`;

    // Cabecera
    const headers = ["Recorrido", "Bus"];
    // Para cada parada seleccionada incluir nombre, intervalo, duración (como pediste)
    selectedStopsList.forEach((stop) => {
      headers.push(stop.stop_name || "");
      headers.push("Intervalo");
      headers.push("Duración");
    });
    headers.push("Total");
    headers.push("Kms");
    csv += headers.map((h) => `"${h}"`).join(",") + "\n";

    // Filas
    let prevTimesByStop = {}; // para calcular intervalos por parada (si aplica)
    timetableData.cycles.forEach((cycle) => {
      const row = [cycle.recorrido || "", cycle.bus_number || ""];

      selectedStopsList.forEach((stop) => {
        // Intentamos leer el tiempo en la estructura que el backend entrega:
        // se asume cycle.dir_X puede contener propiedades por stop_id (si así lo entregó el backend),
        // pero muchas APIs devuelven sólo first_stop_time/last_stop_time. Ajustamos:
        const dir = stop.direction_id != null ? `dir_${stop.direction_id}` : "dir_0";
        let time = "";

        // Primer intento: Buscar por stop_id dentro de dir object (si el backend lo provee así)
        if (cycle[dir] && typeof cycle[dir] === "object") {
          // si cycle[dir][stop_id] es una hora
          if (cycle[dir][stop.stop_id]) time = cycle[dir][stop.stop_id];
          // si hay un map de times en cycle.stop_times por ejemplo (no es obligatorio)
          if (!time && cycle.stop_times && cycle.stop_times[stop.stop_id]) time = cycle.stop_times[stop.stop_id];
        }

        // Fallbacks: usar first_stop_time / last_stop_time según posición (para la primera/última parada)
        if (!time) {
          if (stop.stop_sequence === 1 && cycle[dir]?.first_stop_time) time = cycle[dir].first_stop_time;
          else if (cycle[dir]?.last_stop_time) time = cycle[dir].last_stop_time;
        }

        time = time || "";

        // Intervalo con respecto al previo en esa parada (porcing)
        const prevKey = `${stop.stop_id}`;
        const interval = prevTimesByStop[prevKey] && time ? calculateInterval(prevTimesByStop[prevKey], time) : "";

        // Duración desde la primera parada de ese sentido hasta esta parada
        const firstOfDir = cycle[dir]?.first_stop_time || "";
        const duration = firstOfDir && time ? calculateInterval(firstOfDir, time) : "";

        row.push(time || "");
        row.push(interval || "");
        row.push(duration || "");

        // actualizar prev para la próxima fila
        prevTimesByStop[prevKey] = time || prevTimesByStop[prevKey] || "";
      });

      // Total (desde primer inicio en dir_0 hasta última llegada en dir_1 si existen)
      const first0 = cycle.dir_0?.first_stop_time || "";
      const last1 = cycle.dir_1?.last_stop_time || "";
      const total = first0 && last1 ? calculateInterval(first0, last1) : "";
      row.push(total || "");

      // kms
      row.push(cycle.distance_km || timetableData.route_distance_km || "");

      csv += row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `timetable_${selectedRoute || "route"}_${selectedService || "service"}.csv`;
    link.click();
  };

  // --- Util para obtener descripción compacta de servicio ---
  const getServiceDays = (service) => {
    if (!service) return "";
    const days = [];
    if (service.monday) days.push("L");
    if (service.tuesday) days.push("Ma");
    if (service.wednesday) days.push("Mi");
    if (service.thursday) days.push("J");
    if (service.friday) days.push("V");
    if (service.saturday) days.push("S");
    if (service.sunday) days.push("D");
    return days.join(", ");
  };

  // Estilos (clases tailwind usadas en el markup)
  const inputClass = "px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const sectionClass = "bg-white p-6 rounded-lg shadow-md mb-6";
  const buttonClass = "px-4 py-2 rounded-md font-medium transition-colors";

  // --- Render ---
  return (
    <div className="p-6 bg-gray-100 h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">🕐 Generador de Timetables</h1>
          <p className="text-gray-600">Genera horarios personalizados en formato tabla y CSV</p>
        </div>

        {/* Status */}
        {status.message && (
          <div
            className={`p-4 mb-6 rounded-md ${
              status.type === "success"
                ? "bg-green-100 text-green-800 border border-green-200"
                : status.type === "error"
                ? "bg-red-100 text-red-800 border border-red-200"
                : "bg-blue-100 text-blue-800 border border-blue-200"
            }`}
          >
            {status.message}
          </div>
        )}

        {/* Paso 1 */}
        <div className={sectionClass}>
          <h2 className="text-xl font-semibold mb-4 text-gray-700">📍 Paso 1: Seleccionar Ruta y Servicio</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Ruta</label>
              <select
                value={selectedRoute}
                onChange={(e) => {
                  setSelectedRoute(e.target.value);
                  setTimetableData(null);
                }}
                className={inputClass + " w-full"}
              >
                <option value="">Selecciona una ruta</option>
                {routes.map((r) => (
                  <option key={r.route_id} value={r.route_id}>
                    {r.route_short_name} - {r.route_long_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Periodicidad / Servicio</label>
              <select
                value={selectedService}
                onChange={(e) => {
                  setSelectedService(e.target.value);
                  setTimetableData(null);
                }}
                className={inputClass + " w-full"}
              >
                <option value="">Selecciona un servicio</option>
                {services.map((s) => (
                  <option key={s.service_id} value={s.service_id}>
                    {s.service_id} ({getServiceDays(s)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-4">
            <label className={labelClass}>Rango de Horas (opcional)</label>
            <div className="flex items-center gap-4">
              <input type="time" value={timeRange.start} onChange={(e) => setTimeRange((p) => ({ ...p, start: e.target.value }))} className={inputClass} />
              <span className="text-gray-500">a</span>
              <input type="time" value={timeRange.end} onChange={(e) => setTimeRange((p) => ({ ...p, end: e.target.value }))} className={inputClass} />
            </div>
          </div>
        </div>

        {/* Paso 2 */}
        {stops.length > 0 && (
          <div className={sectionClass}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-700">🚏 Paso 2: Seleccionar Paradas a Mostrar</h2>
              <div className="flex gap-2">
                <button onClick={selectAllStops} className={buttonClass + " bg-blue-600 text-white hover:bg-blue-700"}>Seleccionar Todas</button>
                <button onClick={clearAllStops} className={buttonClass + " bg-gray-300 text-gray-700 hover:bg-gray-400"}>Limpiar</button>
              </div>
            </div>

            <p className="text-sm text-gray-600 mb-4">Seleccionadas: {selectedStops.size} de {stops.length}</p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto p-2 border border-gray-200 rounded-md">
              {stops.map((stop) => {
                const isSelected = selectedStops.has(stop.stop_id);
                const cls = `flex items-center p-3 rounded-md cursor-pointer transition-colors ${isSelected ? "bg-blue-50 border-2 border-blue-500" : "bg-white border border-gray-300 hover:bg-gray-50"}`;
                return (
                  <label key={`${stop.stop_id}-${stop.direction_id}`} className={cls}>
                    <input type="checkbox" checked={isSelected} onChange={() => toggleStop(stop.stop_id)} className="mr-3 h-4 w-4 text-blue-600 rounded focus:ring-blue-500" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{stop.stop_name}</p>
                      <p className="text-xs text-gray-500">Seq: {stop.stop_sequence} | Dir: {stop.direction_id}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Botón generar */}
        <div className="flex justify-end gap-4">
          <button onClick={generateTimetable} disabled={loading || !selectedRoute || !selectedService || selectedStops.size === 0} className={buttonClass + " bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-lg px-8 py-3"}>
            {loading ? "Generando..." : "🔍 Generar Timetable"}
          </button>
        </div>

        {/* Vista previa */}
        {timetableData && (
          <div className={sectionClass + " mt-6"}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-700">📄 Vista Previa del Timetable</h2>
              <button onClick={downloadCSV} className={buttonClass + " bg-blue-600 text-white hover:bg-blue-700"}>💾 Descargar CSV</button>
            </div>

            <div className="mb-4 p-4 bg-gray-50 rounded-md">
              <h3 className="font-bold text-lg">{timetableData.route_name || ""}</h3>
              <p className="text-sm text-gray-600">Servicio: {timetableData.service_days || ""}</p>
              <p className="text-sm text-gray-600">Total de viajes: {Array.isArray(timetableData.cycles) ? timetableData.cycles.length : 0} | Buses: {Array.isArray(timetableData.cycles) ? timetableData.cycles.length : 0}</p>
            </div>

            <div className="overflow-x-auto border border-gray-300 rounded-lg">
              <table className="min-w-full divide-y divide-gray-300">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider sticky left-0 bg-gray-100 z-10">Bus</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Viaje</th>

                    {/* cabeceras dinámicas de paradas seleccionadas */}
                    {(timetableData.selected_stops || []).map((stop) => (
                      <th key={`${stop.stop_id}-hdr`} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        {stop.stop_name}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Total</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Kms</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(timetableData.cycles || []).map((cycle, idx) => (
                    <tr key={cycle.trip_id || cycle.block_id || idx}>
                      <td className="px-3 py-2 text-sm text-gray-900">{cycle.bus_number}</td>
                      <td className="px-3 py-2 text-sm text-gray-900">{cycle.recorrido || idx + 1}</td>

                      {(timetableData.selected_stops || []).map((stop) => {
                        const dir = stop.direction_id != null ? `dir_${stop.direction_id}` : "dir_0";
                        let time = "";
                        if (cycle[dir] && cycle[dir][stop.stop_id]) time = cycle[dir][stop.stop_id];
                        // fallbacks
                        if (!time) {
                          if (stop.stop_sequence === 1 && cycle[dir]?.first_stop_time) time = cycle[dir].first_stop_time;
                          else if (cycle[dir]?.last_stop_time) time = cycle[dir].last_stop_time;
                        }
                        return <td key={`${cycle.trip_id || idx}-${stop.stop_id}`} className="px-3 py-2 text-sm text-gray-900">{time || "-"}</td>;
                      })}

                      <td className="px-3 py-2 text-sm text-gray-900">
                        {(() => {
                          const first0 = cycle.dir_0?.first_stop_time || "";
                          const last1 = cycle.dir_1?.last_stop_time || "";
                          return first0 && last1 ? calculateInterval(first0, last1) : "-";
                        })()}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-900">{cycle.distance_km || timetableData.route_distance_km || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}