// src/components/Sidebar.jsx
import { useState } from "react";

const MODULES = [
  { key: "tables", name: "Tablas GTFS" },
  { key: "network", name: "Red (Mapa)" },
  { key: "upload", name: "Cargar GTFS" }, // nuevo
];


export default function Sidebar({ onSelect }) {
  const [active, setActive] = useState("tables");

  return (
    <div className="w-64 bg-gray-900 text-white h-screen flex flex-col">
      <h1 className="text-xl font-bold p-4 border-b border-gray-700">
        Transit Scheduler
      </h1>
      <ul className="flex-1">
        {MODULES.map((m) => (
          <li
            key={m.key}
            onClick={() => {
              setActive(m.key);
              onSelect(m.key); // El componente padre decide qué mostrar
            }}
            className={`p-3 cursor-pointer hover:bg-gray-700 ${
              active === m.key ? "bg-gray-700" : ""
            }`}
          >
            {m.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

