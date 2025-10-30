import pandas as pd
from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional

# --- Constantes (valores por defecto) ---
DEFAULT_IDLE_THRESHOLD_MIN = 30
DEFAULT_MAX_WAIT_MINUTES_PAIRING = 15

# --- Funciones de Ayuda para Tiempos (port de VBA) ---

def str_to_time(time_str: str) -> Optional[time]:
    """Convierte 'HH:MM' o 'HH:MM:SS' a objeto time. Devuelve None si es inválido."""
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        return datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        try:
            return datetime.strptime(time_str, '%H:%M:%S').time()
        except ValueError:
            print(f"Advertencia: Formato de tiempo inválido '{time_str}', se usará 00:00")
            return None

def time_to_minutes(t: time) -> int:
    """Convierte un objeto time a minutos desde la medianoche."""
    if not isinstance(t, time):
        return 0
    return t.hour * 60 + t.minute

def time_str_to_minutes(time_str: str) -> int:
    """Convierte un string 'HH:MM' o 'HH:MM:SS' a minutos."""
    t = str_to_time(time_str)
    if t:
        return time_to_minutes(t)
    return 0

def minutes_to_time(m: int) -> time:
    """Convierte minutos desde la medianoche a un objeto time."""
    m = int(m)
    hours = (m // 60) % 24
    minutes = m % 60
    return time(hours, minutes)

def add_minutes(t: time, minutes: int) -> time:
    """Suma minutos a un objeto time."""
    total_mins = time_to_minutes(t) + int(minutes)
    return minutes_to_time(total_mins)

def time_diff_minutes(t1: time, t2: time) -> int:
    """Calcula diferencia en minutos entre t2 - t1."""
    return time_to_minutes(t2) - time_to_minutes(t1)

# -----------------------------------------------------------------
# --- Lógica de Búsqueda de Tiempos (Port de VBA) ---
# -----------------------------------------------------------------

def get_travel_time_for_departure(dep_time: time, travel_table: List[Dict], default_time: int) -> int:
    """
    Busca el tiempo de viaje (en minutos) para una hora de salida.
    'travel_table' es (tabla6 o tabla7)
    """
    dep_minutes = time_to_minutes(dep_time)
    
    for row in travel_table:
        # Tus tablas (6 y 7) tienen 'desde', 'hasta', 'tiempo'
        desde_min = time_str_to_minutes(row.get('desde'))
        hasta_min = time_str_to_minutes(row.get('hasta'))
        tiempo_str = row.get('tiempo')
        
        if not tiempo_str: continue

        if hasta_min < desde_min: # Maneja cruce de medianoche (ej: 22:00 a 01:00)
             if dep_minutes >= desde_min or dep_minutes <= hasta_min:
                return time_str_to_minutes(tiempo_str)
        else:
            if desde_min <= dep_minutes <= hasta_min:
                return time_str_to_minutes(tiempo_str)
                
    return default_time

# -----------------------------------------------------------------
# --- Clase para gestionar Buses (Lógica VBA) ---
# -----------------------------------------------------------------

class BusFleet:
    """
    Gestiona el estado de los buses replicando la lógica del VBA.
    Variables de módulo VBA: BusNextAvail, BusNextLoc, BusInOperation, OutOfOperation
    """
    
    def __init__(self, idle_threshold_min: int = DEFAULT_IDLE_THRESHOLD_MIN):
        self.idle_threshold = idle_threshold_min
        self.buses = []  # Lista de diccionarios con estado de cada bus
        self.out_of_operation = []  # Buses fuera de operación
    
    def create_bus(self, location: str, avail_time: time) -> int:
        """Crea un nuevo bus (VBA: CrearBus, línea 329)."""
        bus_id = len(self.buses) + 1
        self.buses.append({
            'id': bus_id,
            'location': location,
            'available_at': avail_time,
            'in_operation': True
        })
        return bus_id
    
    def mark_out_of_operation(self, bus_id: int, out_time: time):
        """Marca un bus como fuera de operación (VBA: líneas 577-584)."""
        if bus_id < 1 or bus_id > len(self.buses):
            return
        bus = self.buses[bus_id - 1]
        bus['in_operation'] = False
        self.out_of_operation.append({
            'id': bus_id,
            'end_of_last_op': out_time
        })
    
    def pop_oldest_out_bus(self) -> Optional[int]:
        """
        Obtiene el bus más antiguo fuera de operación y lo reactiva.
        (VBA: PopOldestOutBus, líneas 311-326)
        """
        if not self.out_of_operation:
            return None
        
        # Encontrar el más antiguo
        oldest_idx = 0
        oldest_time = self.out_of_operation[0]['end_of_last_op']
        
        for i in range(1, len(self.out_of_operation)):
            if time_to_minutes(self.out_of_operation[i]['end_of_last_op']) < time_to_minutes(oldest_time):
                oldest_idx = i
                oldest_time = self.out_of_operation[i]['end_of_last_op']
        
        bus_id = self.out_of_operation.pop(oldest_idx)['id']
        return bus_id
    
    def find_best_available_bus(self, dep_time: time, origin: str) -> Optional[int]:
        """
        Busca el mejor bus disponible (VBA: líneas 566-623).
        
        Lógica:
        1. Mover a OUT los buses con wait > idle_threshold
        2. Buscar bus EN OPERACIÓN con menor wait >= 0
        3. Si no hay, usar el más antiguo de OUT
        """
        
        # 1. Mover a OUT los buses con espera muy larga (VBA: líneas 566-589)
        for bus in self.buses:
            if bus['in_operation'] and bus['location'] == origin:
                wait = time_diff_minutes(bus['available_at'], dep_time)
                # Solo considerar cruces de medianoche si el wait es muy negativo (> 12 horas)
                if wait < -720:  # Cruce de medianoche
                    wait += 1440
                
                if wait > self.idle_threshold:
                    self.mark_out_of_operation(bus['id'], bus['available_at'])
        
        # 2. Buscar bus en operación con menor wait >= 0 (VBA: líneas 591-613)
        best_bus_id = None
        best_wait = 999999
        
        for bus in self.buses:
            if bus['in_operation'] and bus['location'] == origin:
                wait = time_diff_minutes(bus['available_at'], dep_time)
                
                # CRÍTICO: NO sumar 1440 si wait < 0 para la selección de buses
                # Si wait < 0, significa que el bus AÚN NO está disponible (todavía en tránsito)
                # Solo considerar buses con wait >= 0 (ya disponibles)
                
                if wait >= 0 and wait < best_wait:
                    best_wait = wait
                    best_bus_id = bus['id']
        
        # 3. Si no hay bus en operación, usar el más antiguo OUT (VBA: líneas 615-623)
        if best_bus_id is None:
            best_bus_id = self.pop_oldest_out_bus()
            if best_bus_id:
                self.buses[best_bus_id - 1]['in_operation'] = True
        
        return best_bus_id
    
    def update_bus(self, bus_id: int, new_location: str, avail_time: time):
        """Actualiza la ubicación y disponibilidad de un bus (VBA: líneas 652-656)."""
        if bus_id < 1 or bus_id > len(self.buses):
            return
        bus = self.buses[bus_id - 1]
        bus['location'] = new_location
        bus['available_at'] = avail_time
        bus['in_operation'] = True

# -----------------------------------------------------------------
# FUNCIÓN 1: Generar Viajes Crudos (CON RASTREO DE BUSES)
# -----------------------------------------------------------------

def generate_sheet_from_tables(
    tabla1_data: Dict,
    headways_centro: List[Dict], # Tabla 4
    headways_barrio: List[Dict], # Tabla 5
    travel_times_cb: List[Dict], # Tabla 6
    travel_times_bc: List[Dict]  # Tabla 7
) -> List[Dict[str, Any]]:
    """
    Genera la lista de viajes crudos (Timetables_Variable)
    usando RASTREO DE DISPONIBILIDAD de buses (como en el VBA).
    
    Replica la lógica del VBA líneas 560-673.
    """
    
    # 1. Extraer Parámetros de Tabla 1
    start_a = str_to_time(tabla1_data.get('horaInicioCentro'))
    end_a = str_to_time(tabla1_data.get('horaFinCentro'))
    start_b = str_to_time(tabla1_data.get('horaInicioBarrio'))
    end_b = str_to_time(tabla1_data.get('horaFinBarrio'))
    
    dwell_a = int(tabla1_data.get('dwellCentro', 5))
    dwell_b = int(tabla1_data.get('dwellBarrio', 5))
    
    # Umbral de inactividad para buses
    idle_threshold = int(tabla1_data.get('idle_threshold', DEFAULT_IDLE_THRESHOLD_MIN))
    
    default_travel_ab = time_str_to_minutes(travel_times_cb[0].get('tiempo')) if travel_times_cb else 30
    default_travel_ba = time_str_to_minutes(travel_times_bc[0].get('tiempo')) if travel_times_bc else 30

    # 2. Generar todas las partidas (Puerto de 'TryAddDeparture' y loops de headway)
    all_departures = set() 
    
    # Salidas A -> B (Centro)
    if start_a and end_a:
        for row in headways_centro: # Tabla 4
            desde_t = str_to_time(row.get('desde'))
            hasta_t = str_to_time(row.get('hasta'))
            headway_min = int(row.get('headway', 15))

            if not desde_t or not hasta_t or headway_min <= 0:
                continue

            start_loop = max(start_a, desde_t)
            end_loop = min(end_a, hasta_t)

            current_time = start_loop
            while current_time <= end_loop:
                all_departures.add((current_time, "A"))
                current_time = add_minutes(current_time, headway_min)

    # Salidas B -> A (Barrio)
    if start_b and end_b:
        for row in headways_barrio: # Tabla 5
            desde_t = str_to_time(row.get('desde'))
            hasta_t = str_to_time(row.get('hasta'))
            headway_min = int(row.get('headway', 15))

            if not desde_t or not hasta_t or headway_min <= 0:
                continue
                
            start_loop = max(start_b, desde_t)
            end_loop = min(end_b, hasta_t)

            current_time = start_loop
            while current_time <= end_loop:
                all_departures.add((current_time, "B"))
                current_time = add_minutes(current_time, headway_min)
    
    if not all_departures:
        return []

    # 3. Ordenar partidas cronológicamente
    sorted_departures = sorted(list(all_departures), key=lambda x: x[0])

    # 4. Inicializar flota de buses
    fleet = BusFleet(idle_threshold_min=idle_threshold)
    
    # 5. Procesar viajes con RASTREO DE DISPONIBILIDAD (VBA: líneas 561-673)
    raw_trips = []
    corrida_id = 0
    
    for (dep_time, origin) in sorted_departures:
        corrida_id += 1
        
        # Calcular tiempos de viaje según tabla (VBA: líneas 626-641)
        if origin == "A":
            travel_min = get_travel_time_for_departure(dep_time, travel_times_cb, default_travel_ab)
            dwell_other = dwell_b
            other_loc = "B"
        else: # origin == "B"
            travel_min = get_travel_time_for_departure(dep_time, travel_times_bc, default_travel_ba)
            dwell_other = dwell_a
            other_loc = "A"

        arrive_other = add_minutes(dep_time, travel_min)
        depart_other = add_minutes(arrive_other, dwell_other)
        
        # Calcular tiempo de regreso (para RoundTripMin)
        if origin == "A":
            back_min = get_travel_time_for_departure(depart_other, travel_times_bc, default_travel_ba)
        else:
            back_min = get_travel_time_for_departure(depart_other, travel_times_cb, default_travel_ab)
        
        return_origin = add_minutes(depart_other, back_min)
        round_trip_min = time_diff_minutes(dep_time, return_origin)
        if round_trip_min < 0:
            round_trip_min += 1440
        
        # *** LÓGICA CLAVE: Buscar o crear bus (VBA: líneas 591-656) ***
        bus_id = fleet.find_best_available_bus(dep_time, origin)
        
        if bus_id is None:
            # No hay buses disponibles, crear uno nuevo (VBA: línea 650)
            # El bus nuevo queda en el DESTINO después del dwell
            bus_id = fleet.create_bus(other_loc, depart_other)
        else:
            # Actualizar bus existente (VBA: líneas 652-656)
            fleet.update_bus(bus_id, other_loc, depart_other)
        
        # Registrar viaje
        raw_trips.append({
            "Corrida": corrida_id,
            "DepartureTime": dep_time,
            "Origin": origin,
            "BusID": bus_id,
            "ArriveAtDest": arrive_other,
            "DepartFromDest": depart_other,
            "ReturnToOrigin": return_origin,
            "RoundTripMin": round_trip_min
        })

    print(f"Sábana cruda generada con {len(raw_trips)} viajes usando {len(fleet.buses)} buses.")
    return raw_trips

# -----------------------------------------------------------------
# FUNCIÓN 2: Consolidar Sábana (Puerto de ConsolidarTimetable)
# -----------------------------------------------------------------

def consolidate_sheet(raw_trips: List[Dict[str, Any]], max_wait_minutes: int = DEFAULT_MAX_WAIT_MINUTES_PAIRING) -> List[Dict[str, Any]]:
    """
    Consolida la lista de viajes crudos en una sábana final.
    Esta es la lógica EXACTA de 'ConsolidarTimetable' del VBA (líneas 923-1049).
    
    Lógica de emparejamiento:
    1. Para cada viaje no usado, busca su par del MISMO BUS donde:
       a) COINCIDENCIA EXACTA: salida en destino == llegada en destino (normalizado a minutos)
       b) Si no hay exacta: salida >= llegada y <= llegada + MAX_WAIT (menor espera)
    """
    
    n = len(raw_trips)
    if n == 0:
        return []

    # 1. Ordenar por hora de salida (como en VBA líneas 878-905)
    raw_trips.sort(key=lambda x: x["DepartureTime"] if isinstance(x["DepartureTime"], time) else time(0,0))
    
    # Array para marcar viajes ya usados
    used = [False] * n
    
    final_sheet = []
    corrida = 0

    # 2. Recorrer todos los viajes y emparejar (VBA líneas 924-1049)
    for i in range(n):
        if used[i]:
            continue
            
        used[i] = True
        trip_i = raw_trips[i]
        
        origin_i = trip_i["Origin"]
        bus_i = trip_i["BusID"]
        dep_i = trip_i["DepartureTime"]
        arr_i = trip_i["ArriveAtDest"]
        
        paired = False
        j_match = -1
        
        # --- LÓGICA DE EMPAREJAMIENTO EXACTA DEL VBA ---
        
        if origin_i == "A":  # Viaje Centro -> Barrio
            # Buscar viaje B->A del mismo bus
            
            # 1) COINCIDENCIA EXACTA (VBA línea 946)
            arr_i_normalized = time_to_minutes(arr_i)
            
            for j in range(n):
                if used[j]:
                    continue
                trip_j = raw_trips[j]
                
                if trip_j["Origin"] == "B" and trip_j["BusID"] == bus_i:
                    dep_j_normalized = time_to_minutes(trip_j["DepartureTime"])
                    
                    if dep_j_normalized == arr_i_normalized:
                        paired = True
                        j_match = j
                        break
            
            # 2) Si no hay exacta, buscar la MENOR ESPERA posible (VBA líneas 953-970)
            if not paired:
                best_wait = 999999
                
                for j in range(n):
                    if used[j]:
                        continue
                    trip_j = raw_trips[j]
                    
                    if trip_j["Origin"] == "B" and trip_j["BusID"] == bus_i:
                        wait_min = time_diff_minutes(arr_i, trip_j["DepartureTime"])
                        
                        if wait_min < 0:
                            wait_min += 1440  # Cruce de medianoche
                        
                        if 0 <= wait_min <= max_wait_minutes:
                            if wait_min < best_wait:
                                best_wait = wait_min
                                j_match = j
                                paired = True
        
        elif origin_i == "B":  # Viaje Barrio -> Centro
            # Buscar viaje A->B del mismo bus
            
            # 1) COINCIDENCIA EXACTA (VBA línea 976)
            arr_i_normalized = time_to_minutes(arr_i)
            
            for j in range(n):
                if used[j]:
                    continue
                trip_j = raw_trips[j]
                
                if trip_j["Origin"] == "A" and trip_j["BusID"] == bus_i:
                    dep_j_normalized = time_to_minutes(trip_j["DepartureTime"])
                    
                    if dep_j_normalized == arr_i_normalized:
                        paired = True
                        j_match = j
                        break
            
            # 2) Si no hay exacta, buscar la MENOR ESPERA posible (VBA líneas 983-1000)
            if not paired:
                best_wait = 999999
                
                for j in range(n):
                    if used[j]:
                        continue
                    trip_j = raw_trips[j]
                    
                    if trip_j["Origin"] == "A" and trip_j["BusID"] == bus_i:
                        wait_min = time_diff_minutes(arr_i, trip_j["DepartureTime"])
                        
                        if wait_min < 0:
                            wait_min += 1440  # Cruce de medianoche
                        
                        if 0 <= wait_min <= max_wait_minutes:
                            if wait_min < best_wait:
                                best_wait = wait_min
                                j_match = j
                                paired = True
        
        # 3. Crear fila de salida (VBA líneas 1004-1047)
        if paired:
            used[j_match] = True
            trip_j = raw_trips[j_match]
            corrida += 1
            
            # Convertir a string si son objetos time
            dep_i_str = dep_i.strftime('%H:%M') if isinstance(dep_i, time) else dep_i
            arr_i_str = arr_i.strftime('%H:%M') if isinstance(arr_i, time) else arr_i
            dep_j_str = trip_j["DepartureTime"].strftime('%H:%M') if isinstance(trip_j["DepartureTime"], time) else trip_j["DepartureTime"]
            arr_j_str = trip_j["ArriveAtDest"].strftime('%H:%M') if isinstance(trip_j["ArriveAtDest"], time) else trip_j["ArriveAtDest"]
            
            if origin_i == "A":  # i es A->B, j es B->A
                rt = time_diff_minutes(dep_i, trip_j["ArriveAtDest"])
                if rt < 0:
                    rt += 1440
                
                final_sheet.append({
                    "Corrida": corrida,
                    "BusID": bus_i,
                    "Salida en Centro": dep_i_str,
                    "Llegada en Barrio": arr_i_str,
                    "Salida en Barrio": dep_j_str,
                    "Llegada en Centro": arr_j_str,
                    "Tiempo de recorrido": round(rt, 2)
                })
            
            else:  # i es B->A, j es A->B
                rt = time_diff_minutes(trip_j["DepartureTime"], arr_i)
                if rt < 0:
                    rt += 1440
                
                final_sheet.append({
                    "Corrida": corrida,
                    "BusID": bus_i,
                    "Salida en Centro": dep_j_str,
                    "Llegada en Barrio": arr_j_str,
                    "Salida en Barrio": dep_i_str,
                    "Llegada en Centro": arr_i_str,
                    "Tiempo de recorrido": round(rt, 2)
                })
        
        else:  # No emparejado (VBA líneas 1032-1047)
            corrida += 1
            rt = time_diff_minutes(dep_i, arr_i)
            if rt < 0:
                rt += 1440
            
            # Convertir a string
            dep_i_str = dep_i.strftime('%H:%M') if isinstance(dep_i, time) else dep_i
            arr_i_str = arr_i.strftime('%H:%M') if isinstance(arr_i, time) else arr_i
            
            if origin_i == "A":
                final_sheet.append({
                    "Corrida": corrida,
                    "BusID": bus_i,
                    "Salida en Centro": dep_i_str,
                    "Llegada en Barrio": arr_i_str,
                    "Salida en Barrio": '---',
                    "Llegada en Centro": '---',
                    "Tiempo de recorrido": round(rt, 2)
                })
            else:
                final_sheet.append({
                    "Corrida": corrida,
                    "BusID": bus_i,
                    "Salida en Centro": '---',
                    "Llegada en Barrio": '---',
                    "Salida en Barrio": dep_i_str,
                    "Llegada en Centro": arr_i_str,
                    "Tiempo de recorrido": round(rt, 2)
                })
    
    print(f"Tabla consolidada generada con {len(final_sheet)} filas.")
    return final_sheet