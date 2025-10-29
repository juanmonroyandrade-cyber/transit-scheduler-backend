# app/services/interval_processor.py
"""
Procesador de Intervalos de Paso
Migración de Macro_Version2_Compacta_PorMinutos.vba a Python
"""

from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import math


class IntervalProcessor:
    """
    Procesa los parámetros de programación y calcula los intervalos de paso
    """
    
    def __init__(self):
        self.MINUTES_PER_DAY = 1440  # 24 horas * 60 minutos
        self.EPSILON = 0.0000001
    
    def process_parameters(self, tabla1: Dict, tabla2: List[Dict], tabla3: List[Dict]) -> Dict[str, List]:
        """
        Procesa los parámetros y genera las tablas de resultados 4-7
        
        Args:
            tabla1: Parámetros generales (hora inicio/fin)
            tabla2: Flota variable (hora, cantidad de buses)
            tabla3: Tiempos de recorrido (hora, Centro→Barrio, Barrio→Centro, Tiempo Ciclo)
        
        Returns:
            Dict con tabla4, tabla5, tabla6, tabla7
        """
        try:
            print("\n" + "="*60)
            print("🚀 INICIANDO PROCESAMIENTO DE INTERVALOS")
            print("="*60)
            
            # 1. Leer y validar datos de entrada
            hora_inicio = self._parse_time(tabla1.get("horaInicio", "00:00"))
            hora_fin = self._parse_time(tabla1.get("horaFin", "23:59"))
            
            print(f"\n📅 Rango de operación:")
            print(f"   Inicio: {self._time_to_string(hora_inicio)}")
            print(f"   Fin: {self._time_to_string(hora_fin)}")
            
            # 2. Convertir tiempos de recorrido y calcular tiempo de ciclo
            tiempos_recorrido = self._prepare_tiempos_recorrido(tabla1, tabla3)
            print(f"\n📊 Tiempos de recorrido procesados: {len(tiempos_recorrido)} períodos")
            print(f"   (Tiempo de ciclo calculado automáticamente: T.C-B + T.B-C + dwells)")
            
            # 3. Convertir flota variable
            flota_variable = self._prepare_flota_variable(tabla2)
            print(f"🚌 Flota variable procesada: {len(flota_variable)} períodos")
            
            # 4. Calcular tabla de parámetros por minuto (1440 filas)
            print(f"\n⚙️  Calculando tabla de parámetros...")
            tabla_parametros = self._calcular_tabla_parametros(tiempos_recorrido, flota_variable)
            print(f"✅ Tabla de parámetros generada: {len(tabla_parametros)} minutos")
            
            # 5. Calcular intervalos en Centro
            print(f"\n🏙️  Calculando intervalos en Centro...")
            intervalos_centro = self._calcular_intervalos_centro(
                hora_inicio, hora_fin, tabla_parametros, tiempos_recorrido
            )
            print(f"✅ Intervalos en Centro: {len(intervalos_centro)} salidas")
            
            # 6. Calcular intervalos en Barrio
            print(f"\n🏘️  Calculando intervalos en Barrio...")
            intervalos_barrio = self._calcular_intervalos_barrio(
                intervalos_centro, tiempos_recorrido
            )
            print(f"✅ Intervalos en Barrio: {len(intervalos_barrio)} salidas")
            
            # 7. Agrupar intervalos
            print(f"\n📊 Agrupando intervalos...")
            intervalos_centro_agrupados = self._agrupar_intervalos(intervalos_centro, es_centro=True)
            intervalos_barrio_agrupados = self._agrupar_intervalos(intervalos_barrio, es_centro=False)
            print(f"✅ Intervalos Centro agrupados: {len(intervalos_centro_agrupados)} períodos")
            print(f"✅ Intervalos Barrio agrupados: {len(intervalos_barrio_agrupados)} períodos")
            
            # 8. Agrupar tiempos de recorrido
            print(f"\n🛣️  Agrupando tiempos de recorrido...")
            tiempos_centro = self._agrupar_tiempos_recorrido(tiempos_recorrido, True)
            tiempos_barrio = self._agrupar_tiempos_recorrido(tiempos_recorrido, False)
            print(f"✅ Tiempos Centro→Barrio: {len(tiempos_centro)} períodos")
            print(f"✅ Tiempos Barrio→Centro: {len(tiempos_barrio)} períodos")
            
            # 9. Formatear resultados
            tabla4 = self._format_tabla4(intervalos_centro_agrupados)
            tabla5 = self._format_tabla5(intervalos_barrio_agrupados)
            tabla6 = self._format_tabla6(tiempos_centro)
            tabla7 = self._format_tabla7(tiempos_barrio)
            
            print("\n" + "="*60)
            print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
            print("="*60 + "\n")
            
            return {
                "tabla4": tabla4,
                "tabla5": tabla5,
                "tabla6": tabla6,
                "tabla7": tabla7
            }
            
        except Exception as e:
            print(f"\n❌ ERROR EN PROCESAMIENTO: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_time(self, time_str: str) -> float:
        """
        Convierte string HH:MM a fracción del día (0.0 - 1.0)
        """
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return (hours * 60 + minutes) / (24.0 * 60.0)
        except:
            return 0.0
    
    def _time_to_string(self, time_fraction: float) -> str:
        """
        Convierte fracción del día a string HH:MM
        """
        total_minutes = int(time_fraction * 24 * 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"
    
    def _prepare_tiempos_recorrido(self, tabla1: Dict, tabla3: List[Dict]) -> List[Tuple]:
        """
        Prepara los tiempos de recorrido para el cálculo
        Calcula automáticamente el tiempo de ciclo = T.C-B + T.B-C + dwellCentro + dwellBarrio
        Retorna: [(tiempo_desde, tiempo_CB, tiempo_BC, tiempo_ciclo), ...]
        """
        # Obtener dwells de la tabla 1
        dwell_centro = self._parse_time(tabla1.get("dwellCentro", "00:00"))
        dwell_barrio = self._parse_time(tabla1.get("dwellBarrio", "00:00"))
        
        result = []
        for item in tabla3:
            tiempo_desde = self._parse_time(item.get("horaCambio", "00:00"))
            tiempo_cb = self._parse_time(item.get("tCentroBarrio", "00:00"))
            tiempo_bc = self._parse_time(item.get("tBarrioCentro", "00:00"))
            
            # CALCULAR tiempo de ciclo automáticamente
            tiempo_ciclo = tiempo_cb + tiempo_bc + dwell_centro + dwell_barrio
            
            result.append((tiempo_desde, tiempo_cb, tiempo_bc, tiempo_ciclo))
        
        # Ordenar por tiempo
        result.sort(key=lambda x: x[0])
        return result
    
    def _prepare_flota_variable(self, tabla2: List[Dict]) -> List[Tuple]:
        """
        Prepara la flota variable
        Retorna: [(tiempo_desde, cantidad_buses), ...]
        """
        result = []
        for item in tabla2:
            tiempo_desde = self._parse_time(item.get("desde", "00:00"))
            buses = int(item.get("buses", 0))
            result.append((tiempo_desde, buses))
        
        # Ordenar por tiempo
        result.sort(key=lambda x: x[0])
        return result
    
    def _calcular_tabla_parametros(self, tiempos_recorrido: List[Tuple], 
                                   flota_variable: List[Tuple]) -> List[Dict]:
        """
        Calcula la tabla de parámetros por cada minuto del día (1440 filas)
        """
        tabla = []
        primer_buses = flota_variable[0][1] if flota_variable else 0
        primer_tciclo = tiempos_recorrido[0][3] if tiempos_recorrido else 0
        
        for minuto_del_dia in range(self.MINUTES_PER_DAY):
            tiempo_actual = minuto_del_dia / (24.0 * 60.0)
            
            # Buscar cantidad de buses
            buses = self._buscar_buses_por_tiempo(tiempo_actual, flota_variable)
            if buses == 0:
                buses = primer_buses
            
            # Buscar tiempo de ciclo
            t_ciclo = self._buscar_tiempo_ciclo_por_tiempo(tiempo_actual, tiempos_recorrido)
            
            # Calcular intervalo
            if buses > 0:
                intervalo = t_ciclo / buses
            else:
                intervalo = 0
            
            tabla.append({
                "tiempo": tiempo_actual,
                "buses": buses,
                "t_ciclo": t_ciclo,
                "intervalo": intervalo
            })
        
        return tabla
    
    def _buscar_buses_por_tiempo(self, tiempo: float, flota_variable: List[Tuple]) -> int:
        """
        Busca la cantidad de buses correspondiente al tiempo dado
        """
        buses = 0
        for tiempo_actual, cantidad in flota_variable:
            if tiempo_actual <= tiempo:
                buses = cantidad
        return buses
    
    def _buscar_tiempo_ciclo_por_tiempo(self, tiempo: float, tiempos_recorrido: List[Tuple]) -> float:
        """
        Busca el tiempo de ciclo correspondiente al tiempo dado
        """
        t_ciclo = tiempos_recorrido[0][3] if tiempos_recorrido else 0
        for tiempo_actual, _, _, ciclo in tiempos_recorrido:
            if tiempo_actual <= tiempo:
                t_ciclo = ciclo
        return t_ciclo
    
    def _buscar_intervalo_por_tiempo(self, tiempo: float, tabla_parametros: List[Dict]) -> float:
        """
        Busca el intervalo correspondiente al tiempo dado en la tabla de parámetros
        """
        minuto_del_dia = int(tiempo * 24 * 60 + self.EPSILON)
        if minuto_del_dia < 0:
            minuto_del_dia = 0
        if minuto_del_dia >= self.MINUTES_PER_DAY:
            minuto_del_dia = self.MINUTES_PER_DAY - 1
        
        return tabla_parametros[minuto_del_dia]["intervalo"]
    
    def _calcular_intervalos_centro(self, hora_inicio: float, hora_fin: float,
                                   tabla_parametros: List[Dict],
                                   tiempos_recorrido: List[Tuple]) -> List[Dict]:
        """
        Calcula los intervalos de paso en Centro
        """
        resultados = []
        salida_num = 1
        desde = hora_inicio
        
        while desde < hora_fin:
            intervalo = self._buscar_intervalo_por_tiempo(desde, tabla_parametros)
            hasta_calculado = desde + intervalo
            
            # Ajustar "desde" según corrección por tráfico
            tiempo_correccion_bc = self._buscar_tiempo_recorrido_bc(desde, tiempos_recorrido)
            desde_corregido = desde + tiempo_correccion_bc
            
            resultados.append({
                "salida": salida_num,
                "desde_corregido": desde_corregido,
                "hasta": hasta_calculado,
                "intervalo": intervalo
            })
            
            desde = hasta_calculado
            salida_num += 1
        
        return resultados
    
    def _buscar_tiempo_recorrido_bc(self, tiempo: float, tiempos_recorrido: List[Tuple]) -> float:
        """
        Busca el tiempo de recorrido Barrio→Centro
        """
        t_recorrido = tiempos_recorrido[0][2] if tiempos_recorrido else 0
        for tiempo_actual, _, tiempo_bc, _ in tiempos_recorrido:
            if tiempo_actual <= tiempo:
                t_recorrido = tiempo_bc
        return t_recorrido
    
    def _calcular_intervalos_barrio(self, intervalos_centro: List[Dict],
                                   tiempos_recorrido: List[Tuple]) -> List[Dict]:
        """
        Calcula los intervalos de paso en Barrio
        """
        resultados = []
        
        for item in intervalos_centro:
            desde_corregido = item["desde_corregido"]
            tiempo_recorrido_cb = self._buscar_tiempo_recorrido_cb(desde_corregido, tiempos_recorrido)
            desde_barrio = desde_corregido + tiempo_recorrido_cb
            
            resultados.append({
                "desde": desde_barrio,
                "intervalo": 0  # Se calculará después
            })
        
        # Calcular intervalos
        for i in range(len(resultados) - 1):
            resultados[i]["intervalo"] = resultados[i + 1]["desde"] - resultados[i]["desde"]
        
        # Último intervalo = penúltimo
        if len(resultados) > 1:
            resultados[-1]["intervalo"] = resultados[-2]["intervalo"]
        
        return resultados
    
    def _buscar_tiempo_recorrido_cb(self, tiempo: float, tiempos_recorrido: List[Tuple]) -> float:
        """
        Busca el tiempo de recorrido Centro→Barrio
        """
        t_recorrido = tiempos_recorrido[0][1] if tiempos_recorrido else 0
        for tiempo_actual, tiempo_cb, _, _ in tiempos_recorrido:
            if tiempo_actual <= tiempo:
                t_recorrido = tiempo_cb
        return t_recorrido
    
    def _agrupar_intervalos(self, intervalos: List[Dict], es_centro: bool) -> List[Dict]:
        """
        Agrupa intervalos consecutivos con el mismo headway
        """
        if not intervalos:
            return []
        
        agrupados = []
        
        if es_centro:
            # Para Centro, usar desde_corregido
            desde = intervalos[0]["desde_corregido"]
            intervalo_anterior = intervalos[0]["intervalo"] * 24 * 60  # Convertir a minutos
            
            for i in range(1, len(intervalos)):
                intervalo_actual = intervalos[i]["intervalo"] * 24 * 60
                
                # Si cambió el intervalo, guardar grupo
                if abs(intervalo_actual - intervalo_anterior) > 0.5:
                    hasta = intervalos[i]["desde_corregido"]
                    agrupados.append({
                        "desde": desde,
                        "hasta": hasta,
                        "intervalo": intervalos[i - 1]["intervalo"]
                    })
                    desde = hasta
                    intervalo_anterior = intervalo_actual
            
            # Último grupo
            agrupados.append({
                "desde": desde,
                "hasta": intervalos[-1]["desde_corregido"],
                "intervalo": intervalos[-1]["intervalo"]
            })
        else:
            # Para Barrio, usar desde
            desde = intervalos[0]["desde"]
            intervalo_anterior = intervalos[0]["intervalo"] * 24 * 60
            
            for i in range(1, len(intervalos)):
                intervalo_actual = intervalos[i]["intervalo"] * 24 * 60
                
                if abs(intervalo_actual - intervalo_anterior) > 0.5:
                    hasta = intervalos[i]["desde"]
                    agrupados.append({
                        "desde": desde,
                        "hasta": hasta,
                        "intervalo": intervalos[i - 1]["intervalo"]
                    })
                    desde = hasta
                    intervalo_anterior = intervalo_actual
            
            # Último grupo
            agrupados.append({
                "desde": desde,
                "hasta": intervalos[-1]["desde"],
                "intervalo": intervalos[-1]["intervalo"]
            })
        
        return agrupados
    
    def _agrupar_tiempos_recorrido(self, tiempos_recorrido: List[Tuple], 
                                  es_centro_barrio: bool) -> List[Dict]:
        """
        Agrupa tiempos de recorrido para las tablas 6 y 7
        """
        resultados = []
        
        for i, item in enumerate(tiempos_recorrido):
            tiempo_desde = item[0]
            
            # Calcular tiempo hasta
            if i < len(tiempos_recorrido) - 1:
                tiempo_hasta = tiempos_recorrido[i + 1][0]
            else:
                # Última fila: 23:59
                tiempo_hasta = (23 * 60 + 59) / (24.0 * 60.0)
            
            if es_centro_barrio:
                tiempo = item[1]  # Centro→Barrio
            else:
                tiempo = item[2]  # Barrio→Centro
            
            resultados.append({
                "desde": tiempo_desde,
                "hasta": tiempo_hasta,
                "tiempo": tiempo
            })
        
        return resultados
    
    def _format_tabla4(self, intervalos_centro: List[Dict]) -> List[Dict]:
        """
        Formatea tabla 4: Intervalos de paso en Centro
        """
        result = []
        for item in intervalos_centro:
            # Convertir intervalo de fracción de día a minutos
            headway_minutos = int(item["intervalo"] * 24 * 60)
            
            result.append({
                "desde": self._time_to_string(item["desde"]),
                "hasta": self._time_to_string(item["hasta"]),
                "headway": headway_minutos
            })
        return result
    
    def _format_tabla5(self, intervalos_barrio: List[Dict]) -> List[Dict]:
        """
        Formatea tabla 5: Intervalos de paso en Barrio
        """
        result = []
        for item in intervalos_barrio:
            headway_minutos = int(item["intervalo"] * 24 * 60)
            
            result.append({
                "desde": self._time_to_string(item["desde"]),
                "hasta": self._time_to_string(item["hasta"]),
                "headway": headway_minutos
            })
        return result
    
    def _format_tabla6(self, tiempos_centro: List[Dict]) -> List[Dict]:
        """
        Formatea tabla 6: Tiempos de recorrido Centro→Barrio
        """
        result = []
        for item in tiempos_centro:
            result.append({
                "desde": self._time_to_string(item["desde"]),
                "hasta": self._time_to_string(item["hasta"]),
                "recorridoCentroBarrio": self._time_to_string(item["tiempo"])
            })
        return result
    
    def _format_tabla7(self, tiempos_barrio: List[Dict]) -> List[Dict]:
        """
        Formatea tabla 7: Tiempos de recorrido Barrio→Centro
        """
        result = []
        for item in tiempos_barrio:
            result.append({
                "desde": self._time_to_string(item["desde"]),
                "hasta": self._time_to_string(item["hasta"]),
                "recorridoBarrioCentro": self._time_to_string(item["tiempo"])
            })
        return result