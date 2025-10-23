import React, { useState, useEffect } from 'react';

function TimetableGenerator() {
    const [routes, setRoutes] = useState([]);
    const [services, setServices] = useState([]);
    const [stops, setStops] = useState([]); // Todas las paradas disponibles
    const [selectedRoute, setSelectedRoute] = useState('');
    const [selectedService, setSelectedService] = useState('');
    const [selectedStopIds, setSelectedStopIds] = useState([]); // IDs ordenados
    const [timetableData, setTimetableData] = useState({ headers: [], corridas: [], stop_ids_ordered: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // --- Cargar datos iniciales ---
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Cargar Rutas
                const routesRes = await fetch('/api/routes/'); // Ajusta a tu endpoint
                if (!routesRes.ok) throw new Error('Failed to fetch routes');
                const routesData = await routesRes.json();
                setRoutes(routesData);

                // Cargar Servicios (Calendars/CalendarDates con descripciones si es posible)
                // Asume endpoint /api/services/ que devuelve algo como [{service_id: 'LAB', description: 'Laborables'}, ...]
                const servicesRes = await fetch('/api/services/'); // Ajusta a tu endpoint
                 if (!servicesRes.ok) throw new Error('Failed to fetch services');
                const servicesData = await servicesRes.json();
                // Intenta crear una descripción si no existe
                const formattedServices = servicesData.map(s => ({
                    ...s,
                    display_name: s.description || `Servicio ID: ${s.service_id}`
                }));
                setServices(formattedServices);


                // Cargar Paradas (Stops)
                 const stopsRes = await fetch('/api/stops/'); // Ajusta a tu endpoint
                 if (!stopsRes.ok) throw new Error('Failed to fetch stops');
                 const stopsData = await stopsRes.json();
                 setStops(stopsData); // Espera [{stop_id: 'S1', stop_name: 'Parada 1'}, ...]

            } catch (err) {
                console.error("Error fetching initial data:", err);
                setError(`Error al cargar datos iniciales: ${err.message}`);
            }
        };
        fetchData();
    }, []);

     // --- Manejador para la selección múltiple de paradas ---
     const handleStopSelectionChange = (event) => {
        const selectedOptions = Array.from(event.target.selectedOptions);
        const selectedValues = selectedOptions.map(option => option.value);

        if (selectedValues.length >= 2) {
            setSelectedStopIds(selectedValues); // El orden lo da la selección del usuario
            if (error && error.includes("al menos dos paradas")) setError(null); // Limpiar error si se cumple
        } else {
            setSelectedStopIds(selectedValues); // Permitir seleccionar 1 temporalmente
            // No mostrar error aún, esperar al botón "Generar"
        }
    };


    // --- Manejador para generar el timetable ---
    const handleGenerateTimetable = async () => {
        if (!selectedRoute) {
            setError("Por favor selecciona una ruta.");
            return;
        }
         if (!selectedService) {
            setError("Por favor selecciona un servicio.");
            return;
        }
        if (selectedStopIds.length < 2) {
            setError("Por favor selecciona al menos dos paradas (origen y destino).");
            return;
        }

        setLoading(true);
        setError(null);
        setTimetableData({ headers: [], corridas: [], stop_ids_ordered: [] });

        const params = new URLSearchParams({
            route_id: selectedRoute,
            service_id: selectedService,
        });
        selectedStopIds.forEach(stopId => params.append('selected_stop_ids', stopId));

        try {
            // Usa la URL completa si el frontend y backend están en diferentes dominios/puertos durante el desarrollo
            // const apiUrl = `http://localhost:8000/api/generate_chained_timetable/?${params.toString()}`;
            // Si están en el mismo dominio o usas proxy:
            const apiUrl = `/api/generate_chained_timetable/?${params.toString()}`;

            const response = await fetch(apiUrl);

            if (!response.ok) {
                 let errorDetail = `Error ${response.status}: ${response.statusText}`;
                 try {
                     const errorData = await response.json();
                     errorDetail = errorData.detail || errorDetail;
                 } catch (e) {
                     // No se pudo parsear el JSON de error
                 }
                throw new Error(errorDetail);
            }
            const data = await response.json();
            if (!data.corridas) {
                // Manejar caso donde el backend devuelve éxito pero sin corridas
                setError("No se encontraron corridas para los criterios seleccionados.");
                 setTimetableData({ headers: [], corridas: [], stop_ids_ordered: [] });
            } else {
                 setTimetableData(data);
            }
        } catch (err) {
            setError(err.message || "Ocurrió un error al generar el horario.");
            console.error("Error generating timetable:", err);
             setTimetableData({ headers: [], corridas: [], stop_ids_ordered: [] });
        } finally {
            setLoading(false);
        }
    };


    return (
        <div className="container mx-auto p-4 space-y-6 bg-gray-50 rounded-lg shadow">
            <h2 className="text-2xl font-bold text-gray-800 border-b pb-2">Generador de Horarios por Bus</h2>

            {/* --- Selectores --- */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
                <div>
                    <label htmlFor="routeSelect" className="block text-sm font-medium text-gray-700 mb-1">Ruta:</label>
                    <select
                        id="routeSelect"
                        value={selectedRoute}
                        onChange={(e) => {setSelectedRoute(e.target.value); setError(null);}} // Limpiar error al cambiar
                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm"
                    >
                        <option value="">Selecciona una ruta</option>
                        {routes.map(route => (
                            <option key={route.route_id} value={route.route_id}>
                                {route.route_short_name || 'Ruta'} - {route.route_long_name || route.route_id}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label htmlFor="serviceSelect" className="block text-sm font-medium text-gray-700 mb-1">Servicio (Periodicidad):</label>
                    <select
                        id="serviceSelect"
                        value={selectedService}
                        onChange={(e) => {setSelectedService(e.target.value); setError(null);}} // Limpiar error al cambiar
                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm"
                    >
                        <option value="">Selecciona un servicio</option>
                        {services.map(service => (
                            <option key={service.service_id} value={service.service_id}>
                                {service.display_name} {/* Usar display_name */}
                            </option>
                        ))}
                    </select>
                </div>
                 <div>
                    <label htmlFor="stopSelect" className="block text-sm font-medium text-gray-700 mb-1">
                        Paradas <span className="text-gray-500">(min. 2, en orden)</span>:
                    </label>
                    <select
                        id="stopSelect"
                        multiple={true}
                        value={selectedStopIds}
                        onChange={handleStopSelectionChange}
                        className="mt-1 block w-full h-40 pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md shadow-sm"
                        aria-describedby="stops-description"
                    >
                        {stops
                         .sort((a, b) => a.stop_name.localeCompare(b.stop_name)) // Ordenar alfabéticamente
                         .map(stop => (
                            <option key={stop.stop_id} value={stop.stop_id}>
                                {stop.stop_name}
                            </option>
                        ))}
                    </select>
                     <p id="stops-description" className="text-xs text-gray-500 mt-1">
                         Mantén <kbd className="px-1 py-0.5 border border-gray-400 rounded bg-gray-200 text-gray-700">Ctrl</kbd> (o <kbd className="px-1 py-0.5 border border-gray-400 rounded bg-gray-200 text-gray-700">Cmd</kbd>) para seleccionar/deseleccionar múltiples. El orden de selección importa (Centro, ..., Barrio, ..., Centro).
                     </p>
                </div>
            </div>

            {/* --- Botón Generar --- */}
            <div className="flex justify-start">
                <button
                    onClick={handleGenerateTimetable}
                    disabled={loading || !selectedRoute || !selectedService || selectedStopIds.length < 2}
                    className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading && (
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    )}
                    {loading ? 'Generando...' : 'Generar Horario'}
                </button>
            </div>

            {/* --- Mensaje de Error --- */}
            {error && <div className="text-red-700 bg-red-100 p-3 rounded-md border border-red-300">{error}</div>}

            {/* --- Tabla de Resultados --- */}
            {!loading && timetableData.corridas && (
                 timetableData.corridas.length > 0 ? (
                    <div className="overflow-x-auto mt-6 shadow border-b border-gray-200 sm:rounded-lg">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-100 sticky top-0">
                                <tr>
                                    {timetableData.headers.map((header, index) => (
                                        <th
                                            key={index}
                                            scope="col"
                                            className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap"
                                        >
                                            {header}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {timetableData.corridas.map((corrida) => (
                                    <tr key={corrida.id} className="hover:bg-indigo-50 transition-colors duration-150 ease-in-out">
                                        {/* Columna Corridas */}
                                        <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{corrida.corrida_num}</td>
                                        {/* Columna Bus */}
                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">{corrida.bus ?? 'N/A'}</td>
                                        {/* Columnas de Tiempos (usar stop_ids_ordered para el orden) */}
                                        {timetableData.stop_ids_ordered.map(stopId => (
                                            <td key={`${corrida.id}-${stopId}`} className="px-4 py-2 whitespace-nowrap text-sm text-gray-700">
                                                {corrida.times[stopId] || <span className="text-gray-400">--:--</span>}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                 ) : (
                    // Mostrar mensaje si no hay corridas pero no hay error (ej. filtrado vacío)
                     timetableData.headers.length > 0 && !error && <p className="text-gray-600 mt-4">No se encontraron viajes que coincidan con los criterios seleccionados.</p>
                 )
            )}
        </div>
    );
}

export default TimetableGenerator;