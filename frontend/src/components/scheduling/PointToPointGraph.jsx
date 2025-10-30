import React from 'react';
import { Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { parse, set } from 'date-fns';

// Registrar los componentes de Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// Función helper para parsear "HH:MM" a un objeto Date
const baseDate = new Date();
baseDate.setHours(0, 0, 0, 0);

const parseTime = (timeStr) => {
  if (!timeStr || !timeStr.match(/^\d{1,2}:\d{2}$/)) {
    return null;
  }
  try {
    const [hours, minutes] = timeStr.split(':').map(Number);
    const date = new Date(baseDate);
    date.setHours(hours, minutes, 0, 0);
    return date;
  } catch (e) {
    console.error(`Error parseando tiempo: ${timeStr}`, e);
    return null;
  }
};

// Paleta de colores
const COLORS = [
  '#3e95cd', '#8e5ea2', '#3cba9f', '#e8c3b9', '#c45850',
  '#f0ad4e', '#5bc0de', '#d9534f', '#5cb85c', '#428bca',
  '#ff6384', '#36a2eb', '#cc65fe', '#ffce56', '#2ecc71',
];

export default function PointToPointGraph({ data = [] }) {
  if (!data || data.length === 0) {
    return <div className="p-4 text-red-600">No hay datos para graficar. Revisa que la sábana se haya transformado correctamente.</div>;
  }

  // 1. Agrupar viajes por bus_id
  const busGroups = data.reduce((acc, trip) => {
    const busId = trip.bus_id || 'Sin Bus';
    if (!acc[busId]) {
      acc[busId] = [];
    }
    acc[busId].push(trip);
    return acc;
  }, {});

  // 2. Crear un "dataset" por cada bus
  const datasets = Object.keys(busGroups).map((busId, index) => {
    const trips = busGroups[busId];
    const chartData = [];
    
    trips.sort((a, b) => (a.dep || '99:99').localeCompare(b.dep || '99:99'));

    trips.forEach(trip => {
      const depTime = parseTime(trip.dep);
      let arrTime = parseTime(trip.arr);

      if (!depTime || !arrTime) return; 

      if (arrTime < depTime) {
        arrTime = new Date(arrTime.getTime() + 24 * 60 * 60 * 1000); 
      }

      const yDep = trip.dir === 'A' ? 1 : 0; // A (Centro) = 1
      const yArr = trip.dir === 'A' ? 0 : 1; // B (Barrio) = 0

      chartData.push({ x: depTime, y: yDep });
      chartData.push({ x: arrTime, y: yArr });

      // --- ¡ESTA ES LA CORRECCIÓN! ---
      // Usamos NaN para romper la línea en lugar de null
      chartData.push({ x: arrTime, y: NaN });
    });

    return {
      label: `Bus ${busId}`,
      data: chartData,
      showLine: true,
      borderColor: COLORS[index % COLORS.length],
      backgroundColor: COLORS[index % COLORS.length],
      tension: 0, 
      pointRadius: 2,
    };
  });

  const chartData = {
    datasets: datasets,
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          padding: 10
        }
      },
      title: {
        display: true,
        text: 'Gráfica Punto a Punto (Itinerario por Bus)',
        font: { size: 18 }
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            // No mostrar tooltip para los puntos NaN
            if (isNaN(context.parsed.y)) return null; 
            
            const label = context.dataset.label || '';
            const yVal = context.parsed.y;
            const xVal = context.parsed.x;
            const time = new Date(xVal).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            const location = yVal === 1 ? 'Centro' : 'Barrio';
            return `${label}: ${location} @ ${time}`;
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'hour',
          tooltipFormat: 'HH:mm',
          displayFormats: {
            hour: 'HH:mm'
          }
        },
        title: {
          display: true,
          text: 'Hora del Día'
        },
        grid: {
          color: '#eee'
        }
      },
      y: {
        min: -0.5,
        max: 1.5,
        title: {
          display: true,
          text: 'Ubicación'
        },
        ticks: {
          stepSize: 1,
          callback: (value) => {
            if (value === 1) return 'Centro';
            if (value === 0) return 'Barrio';
            return '';
          }
        },
        grid: {
          color: '#eee',
          drawBorder: false,
        }
      }
    },
    // Ocultar los puntos NaN
    elements: {
      point: {
        radius: (context) => isNaN(context.raw.y) ? 0 : 2
      }
    }
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Scatter options={options} data={chartData} />
    </div>
  );
}