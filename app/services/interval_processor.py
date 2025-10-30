# app/services/interval_processor.py

"""
Procesador optimizado de intervalos de paso para rutas de transporte público
Migrado desde VBA con optimizaciones de rendimiento

CORRECCIONES V2.1:
- Los intervalos agrupados ahora tienen "Hasta" = "Desde" del siguiente grupo (igual que VBA)
- Tabla 7 ahora usa horaFinBarrio como último "Hasta"

Autor: Sistema de Programación de Rutas
Versión: 2.1 - Correcciones de agrupación
"""

import time
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta


class IntervalProcessor:
    """
    Procesa parámetros de scheduling y calcula intervalos de paso optimizadamente
    """

    def __init__(self):
        self.debug = True

    def _log(self, message: str):
        """Log solo si debug está activo"""
        if self.debug:
            print(message)

    # ==================== CONVERSIÓN DE TIEMPOS ====================

    def _time_to_decimal(self, time_str: str) -> float:
        """
        Convierte HH:MM a decimal (horas)
        Ejemplo: "05:30" -> 5.5
        """
        if not time_str or ':' not in time_str:
            return 0.0

        try:
            h, m = map(int, time_str.split(':'))
            return h + (m / 60.0)
        except:
            return 0.0

    def _time_to_minutes(self, time_str: str) -> int:
        """
        Convierte HH:MM a minutos totales
        Ejemplo: "01:30" -> 90
        """
        if not time_str or ':' not in time_str:
            return 0

        try:
            h, m = map(int, time_str.split(':'))
            return h * 60 + m
        except:
            return 0

    def _minutes_to_time(self, minutes: int) -> str:
        """
        Convierte minutos totales a HH:MM
        Ejemplo: 90 -> "01:30"
        """
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    # ==================== PREPARACIÓN DE DATOS ====================

    def _prepare_tabla2(self, tabla2: List[Dict]) -> List[Tuple[int, int]]:
        """
        Prepara Tabla 2 (Flota Variable)
        Retorna: [(minuto_desde, cantidad_buses), ...]
        """
        result = []
        for row in tabla2:
            minuto_desde = self._time_to_minutes(row.get('desde', ''))
            buses = int(row.get('buses', 0))
            result.append((minuto_desde, buses))

        # Ordenar por minuto
        result.sort(key=lambda x: x[0])
        return result

    def _prepare_tabla3(self, tabla3: List[Dict]) -> List[Tuple[int, int, int]]:
        """
        Prepara Tabla 3 (Tiempos de Recorrido)
        Retorna: [(minuto_desde, tiempo_cb_min, tiempo_bc_min), ...]
        """
        result = []
        for row in tabla3:
            minuto_desde = self._time_to_minutes(row.get('desde', ''))
            tiempo_cb = self._time_to_minutes(row.get('tiempoCB', ''))
            tiempo_bc = self._time_to_minutes(row.get('tiempoBC', ''))
            result.append((minuto_desde, tiempo_cb, tiempo_bc))

        # Ordenar por minuto
        result.sort(key=lambda x: x[0])
        return result

    # ==================== BÚSQUEDA BINARIA OPTIMIZADA ====================

    def _get_value_at_minute(self, sorted_data: List[Tuple], minute: int, value_index: int) -> Any:
        """
        Búsqueda binaria optimizada para obtener el valor vigente en un minuto dado

        Args:
            sorted_data: Lista ordenada de tuplas (minuto, valor1, valor2, ...)
            minute: Minuto a buscar
            value_index: Índice del valor a retornar (1 para buses, 1-2 para tiempos)

        Returns:
            Valor vigente en ese minuto
        """
        if not sorted_data:
            return 0

        # Si es antes del primer registro, usar el primer valor
        if minute < sorted_data[0][0]:
            return sorted_data[0][value_index]

        # Búsqueda binaria
        left, right = 0, len(sorted_data) - 1
        result_idx = 0

        while left <= right:
            mid = (left + right) // 2
            if sorted_data[mid][0] <= minute:
                result_idx = mid
                left = mid + 1
            else:
                right = mid - 1

        return sorted_data[result_idx][value_index]

    # ==================== CÁLCULO DE INTERVALOS ====================

    def _calculate_intervals_centro(
        self,
        hora_inicio: int,
        hora_fin: int,
        flota_variable: List[Tuple[int, int]],
        tiempos_recorrido: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int]]:
        """
        Calcula intervalos de paso en Centro (headways)

        Retorna: [(minuto_salida, headway), ...]
        """
        salidas = []
        minuto_actual = hora_inicio
        contador_salidas = 0
        max_salidas = 500  # Límite de seguridad

        while minuto_actual < hora_fin and contador_salidas < max_salidas:
            # Obtener parámetros vigentes en este minuto
            buses_vigentes = self._get_value_at_minute(flota_variable, minuto_actual, 1)
            tiempo_cb = self._get_value_at_minute(tiempos_recorrido, minuto_actual, 1)
            tiempo_bc = self._get_value_at_minute(tiempos_recorrido, minuto_actual, 2)

            # Calcular headway = tiempo_ciclo / buses
            tiempo_ciclo = tiempo_cb + tiempo_bc

            if buses_vigentes > 0 and tiempo_ciclo > 0:
                headway = round(tiempo_ciclo / buses_vigentes)
            else:
                headway = 60  # Default 60 minutos si no hay datos

            # Prevenir headway 0
            if headway < 1:
                headway = 1

            salidas.append((minuto_actual, headway))
            minuto_actual += headway
            contador_salidas += 1

        if contador_salidas >= max_salidas:
            self._log(f"⚠️ Límite de {max_salidas} salidas alcanzado en Centro")

        return salidas

    def _calculate_intervals_barrio(
        self,
        intervalos_centro: List[Tuple[int, int]],
        tiempos_recorrido: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int]]:
        """
        Calcula intervalos de paso en Barrio basados en las llegadas desde Centro.
        Retorna: [(minuto_llegada_barrio, headway_en_minutos), ...]
        """
        if not intervalos_centro:
            return []

        # 1) Calcular llegadas a barrio (minutos)
        llegadas: List[int] = []
        for minuto_centro, _headway_centro in intervalos_centro:
            tiempo_cb = self._get_value_at_minute(tiempos_recorrido, minuto_centro, 1)
            minuto_barrio = minuto_centro + tiempo_cb
            # normalizar a entero de minutos (como hace VBA con minutos)
            llegadas.append(int(round(minuto_barrio)))

        # 2) Calcular headways en barrio como diferencia entre llegadas consecutivas
        salidas_barrio: List[Tuple[int, int]] = []
        n = len(llegadas)
        if n == 1:
            salidas_barrio.append((llegadas[0], 60))
            return salidas_barrio

        for i in range(n - 1):
            h = llegadas[i + 1] - llegadas[i]
            if h < 1:
                h = 1  # proteger contra 0 o negativos por imprecisión
            salidas_barrio.append((llegadas[i], h))

        # último headway = igual que el anterior (como en VBA)
        ultimo_headway = salidas_barrio[-1][1] if salidas_barrio else 60
        salidas_barrio.append((llegadas[-1], ultimo_headway))

        return salidas_barrio

    # ==================== AGRUPACIÓN DE INTERVALOS ====================

    def _group_intervals(self, intervalos: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
        """
        Agrupa intervalos consecutivos con el mismo headway

        LÓGICA CORREGIDA (igual que VBA línea 337-382):
        - El "Hasta" de un grupo es el "Desde" del siguiente grupo
        - El último grupo tiene como "Hasta" el último minuto de salida

        Retorna: [{"desde": "HH:MM", "hasta": "HH:MM", "headway": int}, ...]
        """
        if not intervalos:
            return []

        grupos: List[Dict[str, Any]] = []
        grupo_actual = {
            "desde": intervalos[0][0],
            "headway": intervalos[0][1]
        }

        for i in range(1, len(intervalos)):
            minuto, headway = intervalos[i]

            # Si el headway cambia, cerrar grupo actual
            if headway != grupo_actual["headway"]:
                # El "Hasta" es el "Desde" del siguiente intervalo (VBA línea 359)
                grupos.append({
                    "desde": self._minutes_to_time(grupo_actual["desde"]),
                    "hasta": self._minutes_to_time(minuto),  # ← CORRECCIÓN CRÍTICA
                    "headway": grupo_actual["headway"]
                })

                # Iniciar nuevo grupo (VBA línea 362: desde = hasta)
                grupo_actual = {
                    "desde": minuto,
                    "headway": headway
                }

        # Agregar último grupo (VBA líneas 367-369)
        grupos.append({
            "desde": self._minutes_to_time(grupo_actual["desde"]),
            "hasta": self._minutes_to_time(intervalos[-1][0]),
            "headway": grupo_actual["headway"]
        })

        return grupos

    # ==================== AGRUPACIÓN DE TIEMPOS DE RECORRIDO ====================

    def _group_travel_times(
        self,
        intervalos: List[Tuple[int, int]],
        tiempos_recorrido: List[Tuple[int, int, int]],
        direction: str,  # 'CB' o 'BC'
        hora_fin_barrio: int = None  # ← NUEVO PARÁMETRO
    ) -> List[Dict[str, Any]]:
        """
        Agrupa tiempos de recorrido consecutivos iguales

        CORRECCIÓN V2.1:
        - Para dirección 'BC', el último "Hasta" usa hora_fin_barrio (si se proporciona)

        Retorna: [{"desde": "HH:MM", "hasta": "HH:MM", "tiempo": "HH:MM"}, ...]
        """
        if not intervalos:
            return []

        value_index = 1 if direction == 'CB' else 2

        grupos: List[Dict[str, Any]] = []
        tiempo_actual = self._get_value_at_minute(tiempos_recorrido, intervalos[0][0], value_index)
        minuto_inicio = intervalos[0][0]

        for i in range(1, len(intervalos)):
            minuto = intervalos[i][0]
            tiempo = self._get_value_at_minute(tiempos_recorrido, minuto, value_index)

            # Si el tiempo cambia, cerrar grupo actual
            if tiempo != tiempo_actual:
                grupos.append({
                    "desde": self._minutes_to_time(minuto_inicio),
                    "hasta": self._minutes_to_time(intervalos[i - 1][0]),
                    "tiempo": self._minutes_to_time(tiempo_actual)
                })

                tiempo_actual = tiempo
                minuto_inicio = minuto

        # Agregar último grupo
        # CORRECCIÓN: Para BC (Tabla 7), usar hora_fin_barrio si está disponible
        if direction == 'BC' and hora_fin_barrio is not None:
            ultimo_hasta = hora_fin_barrio
        else:
            ultimo_hasta = intervalos[-1][0]

        grupos.append({
            "desde": self._minutes_to_time(minuto_inicio),
            "hasta": self._minutes_to_time(ultimo_hasta),  # ← CORRECCIÓN CRÍTICA
            "tiempo": self._minutes_to_time(tiempo_actual)
        })

        return grupos

    # ==================== MÉTODO PRINCIPAL ====================

    def calculate_intervals(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal: calcula todas las tablas de salida (4-7)

        Args:
            parameters: {
                "tabla1": {...},
                "tabla2": [...],
                "tabla3": [...]
            }

        Returns:
            {
                "tabla4": [...],  # Intervalos Centro
                "tabla5": [...],  # Intervalos Barrio
                "tabla6": [...],  # Tiempos CB agrupados
                "tabla7": [...],  # Tiempos BC agrupados
                "tiempo_procesamiento": "XXXms"
            }
        """
        start_time = time.time()

        self._log("\n" + "=" * 70)
        self._log("🚀 CALCULANDO INTERVALOS DE PASO (Python V2.1 Corregido)")
        self._log("=" * 70)

        try:
            # 1. Extraer parámetros
            tabla1 = parameters.get('tabla1', {})
            tabla2 = parameters.get('tabla2', [])
            tabla3 = parameters.get('tabla3', [])

            hora_inicio = self._time_to_minutes(tabla1.get('horaInicioCentro', ''))
            hora_fin = self._time_to_minutes(tabla1.get('horaFinCentro', ''))
            hora_fin_barrio = self._time_to_minutes(tabla1.get('horaFinBarrio', ''))  # ← NUEVO

            self._log(f"📅 Rango Centro: {self._minutes_to_time(hora_inicio)} - {self._minutes_to_time(hora_fin)}")
            self._log(f"📅 Hora Fin Barrio: {self._minutes_to_time(hora_fin_barrio)}")
            self._log(f"🚌 Flota variable: {len(tabla2)} registros")
            self._log(f"⏱️  Tiempos recorrido: {len(tabla3)} registros")

            # 2. Preparar datos
            t1 = time.time()
            flota_variable = self._prepare_tabla2(tabla2)
            tiempos_recorrido = self._prepare_tabla3(tabla3)
            self._log(f"✅ Datos preparados ({(time.time() - t1) * 1000:.1f}ms)")

            # 3. Calcular intervalos en Centro
            t1 = time.time()
            intervalos_centro = self._calculate_intervals_centro(
                hora_inicio, hora_fin, flota_variable, tiempos_recorrido
            )
            self._log(f"✅ Intervalos Centro: {len(intervalos_centro)} salidas ({(time.time() - t1) * 1000:.1f}ms)")

            # 4. Calcular intervalos en Barrio
            t1 = time.time()
            intervalos_barrio = self._calculate_intervals_barrio(
                intervalos_centro, tiempos_recorrido
            )
            self._log(f"✅ Intervalos Barrio: {len(intervalos_barrio)} salidas ({(time.time() - t1) * 1000:.1f}ms)")

            # 5. Agrupar intervalos (CORRECCIÓN APLICADA)
            t1 = time.time()
            tabla4 = self._group_intervals(intervalos_centro)
            tabla5 = self._group_intervals(intervalos_barrio)
            self._log(f"✅ Intervalos agrupados: T4={len(tabla4)}, T5={len(tabla5)} ({(time.time() - t1) * 1000:.1f}ms)")

            # 6. Agrupar tiempos de recorrido (CORRECCIÓN APLICADA)
            t1 = time.time()
            tabla6 = self._group_travel_times(intervalos_centro, tiempos_recorrido, 'CB')
            tabla7 = self._group_travel_times(
                intervalos_barrio,
                tiempos_recorrido,
                'BC',
                hora_fin_barrio  # ← PASA hora_fin_barrio para Tabla 7
            )
            self._log(f"✅ Tiempos agrupados: T6={len(tabla6)}, T7={len(tabla7)} ({(time.time() - t1) * 1000:.1f}ms)")

            # Resultado
            tiempo_total = (time.time() - start_time) * 1000
            self._log(f"\n✅ PROCESAMIENTO COMPLETADO")
            self._log(f"⏱️  Tiempo total: {tiempo_total:.1f}ms")
            self._log("=" * 70 + "\n")

            return {
                "success": True,
                "tabla4": tabla4,
                "tabla5": tabla5,
                "tabla6": tabla6,
                "tabla7": tabla7,
                "tiempo_procesamiento": f"{tiempo_total:.1f}ms"
            }

        except Exception as e:
            self._log(f"\n❌ ERROR: {e}")
            import traceback
            self._log(traceback.format_exc())

            return {
                "success": False,
                "error": str(e),
                "tabla4": [],
                "tabla5": [],
                "tabla6": [],
                "tabla7": []
            }


# ==================== FUNCIÓN DE UTILIDAD ====================

def process_intervals(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de conveniencia para procesar intervalos
    """
    processor = IntervalProcessor()
    return processor.calculate_intervals(parameters)
