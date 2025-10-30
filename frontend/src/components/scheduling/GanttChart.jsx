import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { parse } from 'date-fns';

// Registrar los componentes de Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
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

export default function GanttChart({ data = [] }) {
  if (!data || data.length === 0) {
    return <div>No hay datos para graficar.</div>;
  }

  // 1. Obtener todos los IDs de buses únicos y ordenarlos
  const busIds = [...new Set(data.map(t => t.bus_id || 'Sin Bus'))]
    .sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));

  // 2. Preparar los datasets (uno para A->B, uno para B->A)
  const dataCB = []; // Centro -> Barrio (Dir A)
  const dataBC = []; // Barrio -> Centro (Dir B)

  // Encontrar el tiempo mínimo y máximo para escalar el eje
  let minTime = parseTime('23:59');
  let maxTime = parseTime('00:00');

  data.forEach(trip => {
    const depTime = parseTime(trip.dep);
    let arrTime = parseTime(trip.arr);

    if (!depTime || !arrTime) return;

    // Manejar cruce de medianoche
    if (arrTime < depTime) {
      arrTime = new Date(arrTime.getTime() + 24 * 60 * 60 * 1000); // Añadir 1 día
    }
    
    if (depTime < minTime) minTime = depTime;
    if (arrTime > maxTime) maxTime = arrTime;

    const ganttEntry = {
      x: [depTime, arrTime], // [inicio, fin]
      y: trip.bus_id || 'Sin Bus', // El ID del bus
    };

    // Colorear por dirección (como en el VBA)
    if (trip.dir === 'A') {
      dataCB.push(ganttEntry);
    } else {
      dataBC.push(ganttEntry);
    }
  });

  const chartData = {
    labels: busIds, // Eje Y: Los buses
    datasets: [
      {
        label: 'Centro -> Barrio (Dir A)',
        data: dataCB,
        backgroundColor: 'rgb(0, 176, 80, 0.7)', // Verde
        borderColor: 'rgb(0, 176, 80)',
        borderWidth: 1,
        barPercentage: 0.8,
      },
      {
        label: 'Barrio -> Centro (Dir B)',
        data: dataBC,
        backgroundColor: 'rgb(0, 112, 192, 0.7)', // Azul
        borderColor: 'rgb(0, 112, 192)',
        borderWidth: 1,
        barPercentage: 0.8,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y', // <-- Esto lo convierte en Gantt (horizontal)
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Gráfica de Gantt por Bus',
        font: { size: 18 }
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || '';
            const val = context.raw.x;
            const startTime = new Date(val[0]).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            const endTime = new Date(val[1]).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            return `${label}: ${startTime} - ${endTime}`;
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time',
        min: minTime, // Usar el min/max calculado
        max: maxTime,
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
        title: {
          display: true,
          text: 'Bus ID'
        },
        grid: {
          color: '#eee'
        }
      }
    }
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Bar options={options} data={chartData} />
    </div>
  );
}