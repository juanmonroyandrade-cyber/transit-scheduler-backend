import React, { useState, useEffect } from 'react';
// Asegúrate de tener un CSS para esto si quieres estilos de tabla
// import './SchedulingSheet.css'; 

/**
 * Muestra la sábana de programación generada.
 * Recibe los datos a través de props desde App.jsx
 */
const SchedulingSheet = ({ parameters, selectedRoute, generatedSheetData }) => {
    
    const [sheetData, setSheetData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        setIsLoading(true);
        setError('');

        if (generatedSheetData && generatedSheetData.length > 0) {
            // Caso 1: Hay datos generados, los mostramos
            console.log("SchedulingSheet: Recibiendo sábana generada:", generatedSheetData.length, "viajes");
            setSheetData(generatedSheetData);
        } else {
            // Caso 2: No hay datos (ej. F5 en la página), mostramos error
            console.log("SchedulingSheet: No hay 'generatedSheetData' en props.");
            setSheetData([]); 
            setError('No hay una sábana generada para mostrar. Ve a Parámetros y crea una.');
        }
        setIsLoading(false);
        
    }, [selectedRoute, generatedSheetData]); // Reacciona a los datos generados

    if (isLoading) {
        return <div className="p-4">Cargando sábana...</div>;
    }

    if (error) {
        return <div className="p-4 text-red-600">{error}</div>;
    }

    if (sheetData.length === 0) {
        // Esto es lo que probablemente veías, pero ahora con un mensaje claro
        return <div className="p-4">No hay datos en la sábana.</div>;
    }

    // --- Renderizado de la Tabla ---
    const headers = Object.keys(sheetData[0]);

    return (
        // Usamos las clases de CSS de tu SchedulingParameters.css para consistencia
        <div className="scheduling-container" style={{ maxWidth: '100%' }}>
            <h1>📄 Sábana de Programación (Ruta: {selectedRoute})</h1>
            
            {/* Opcional: Mostrar los parámetros que se usaron */}
            {parameters && (
                <section className="table-section" style={{ background: '#f8f9fa' }}>
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
                <h2>Viajes Generados ({sheetData.length})</h2>
                <div style={{ width: '100%', overflowX: 'auto' }}>
                    <table className="data-table">
                        <thead>
                            <tr className="bg-gray-100">
                                {headers.map((header) => (
                                    <th key={header}>
                                        {header.replace(/_/g, ' ')}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {sheetData.map((row, index) => (
                                <tr key={row.Corrida || index}>
                                    {headers.map((header) => (
                                        <td key={`${row.Corrida || index}-${header}`} style={{ whitespace: 'nowrap' }}>
                                            {row[header] === null || row[header] === undefined ? '---' : String(row[header])}
                                        </td>
                                    ))}
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