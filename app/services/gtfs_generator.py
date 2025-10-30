import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

def create_gtfs_from_sheet(
    sheet_data: List[Dict[str, Any]], 
    route_data_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Genera DataFrames para trips.txt y stop_times.txt.
    
    'sheet_data' es la sábana final consolidada.
    'route_data_df' es el DataFrame del Excel con los arcos de línea.
    
    Columnas esperadas en route_data_df:
    - 'stop_id': ID de la parada (ej. 'P001')
    - 'stop_sequence': Orden de la parada en el viaje (1, 2, 3...)
    - 'direction_id': 0 para ida (A->B), 1 para vuelta (B->A)
    - 'time_from_start_min': Minutos acumulados desde el inicio de ese 'direction_id'
    - 'stop_headsign': (Opcional) Texto de cabecera para esta parada
    """
    
    trips_list = []
    stop_times_list = []
    
    # Asumimos que la ruta y servicio son constantes por ahora
    # En el futuro, deberías pasar esto desde 'params'
    ROUTE_ID = "R1"
    SERVICE_ID = "S1"

    # 1. Validar columnas del Excel de arcos
    required_cols = ['stop_id', 'stop_sequence', 'direction_id', 'time_from_start_min']
    if not all(col in route_data_df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in route_data_df.columns]
        raise ValueError(f"Faltan columnas en el Excel de arcos de línea: {', '.join(missing)}")

    # Separar arcos por dirección
    try:
        arcos_ida = route_data_df[route_data_df['direction_id'] == 0].sort_values(by='stop_sequence')
        arcos_vuelta = route_data_df[route_data_df['direction_id'] == 1].sort_values(by='stop_sequence')
        
        # Obtener cabeceras (ej. el 'stop_headsign' de la última parada)
        headsign_ida = arcos_ida.iloc[-1]['stop_headsign'] if 'stop_headsign' in arcos_ida.columns and not arcos_ida.empty else "Sentido Ida"
        headsign_vuelta = arcos_vuelta.iloc[-1]['stop_headsign'] if 'stop_headsign' in arcos_vuelta.columns and not arcos_vuelta.empty else "Sentido Vuelta"

    except Exception as e:
        raise ValueError(f"Error procesando el Excel de arcos. Verifica 'direction_id' (0 y 1). Error: {e}")

    # 2. Iterar sobre la Sábana Final para crear Trips y StopTimes
    for row in sheet_data:
        corrida_id = row["Corrida"]
        bus_id = row["BusID"] # Opcional, para 'block_id'

        # --- Viaje de IDA (A->B, "Salida en Centro") ---
        if row.get("Salida en Centro"):
            trip_id_ida = f"T_{corrida_id}_IDA"
            start_time_ida_str = row["Salida en Centro"]
            
            try:
                start_time_ida_dt = datetime.strptime(start_time_ida_str, '%H:%M')
            except (ValueError, TypeError):
                print(f"Omitiendo viaje IDA de corrida {corrida_id} por tiempo inválido: {start_time_ida_str}")
                continue

            trips_list.append({
                "route_id": ROUTE_ID,
                "service_id": SERVICE_ID,
                "trip_id": trip_id_ida,
                "trip_headsign": headsign_ida,
                "direction_id": 0,
                "block_id": f"B_{bus_id}" # Agrupa el trabajo por bus
            })
            
            # Generar stop_times para este viaje de IDA
            for _, arco in arcos_ida.iterrows():
                stop_time_dt = start_time_ida_dt + timedelta(minutes=float(arco['time_from_start_min']))
                # Formato GTFS es HH:MM:SS
                stop_time_str = stop_time_dt.strftime('%H:%M:%S') 
                
                stop_times_list.append({
                    "trip_id": trip_id_ida,
                    "arrival_time": stop_time_str,
                    "departure_time": stop_time_str,
                    "stop_id": arco['stop_id'],
                    "stop_sequence": int(arco['stop_sequence']),
                    "pickup_type": 0, # 0 = Regular
                    "drop_off_type": 0 # 0 = Regular
                })

        # --- Viaje de VUELTA (B->A, "Salida en Barrio") ---
        if row.get("Salida en Barrio"):
            trip_id_vuelta = f"T_{corrida_id}_VUELTA"
            start_time_vuelta_str = row["Salida en Barrio"]

            try:
                start_time_vuelta_dt = datetime.strptime(start_time_vuelta_str, '%H:%M')
            except (ValueError, TypeError):
                print(f"Omitiendo viaje VUELTA de corrida {corrida_id} por tiempo inválido: {start_time_vuelta_str}")
                continue
            
            trips_list.append({
                "route_id": ROUTE_ID,
                "service_id": SERVICE_ID,
                "trip_id": trip_id_vuelta,
                "trip_headsign": headsign_vuelta,
                "direction_id": 1,
                "block_id": f"B_{bus_id}" 
            })
            
            # Generar stop_times para este viaje de VUELTA
            for _, arco in arcos_vuelta.iterrows():
                stop_time_dt = start_time_vuelta_dt + timedelta(minutes=float(arco['time_from_start_min']))
                stop_time_str = stop_time_dt.strftime('%H:%M:%S')
                
                stop_times_list.append({
                    "trip_id": trip_id_vuelta,
                    "arrival_time": stop_time_str,
                    "departure_time": stop_time_str,
                    "stop_id": arco['stop_id'],
                    "stop_sequence": int(arco['stop_sequence']),
                    "pickup_type": 0,
                    "drop_off_type": 0
                })

    trips_df = pd.DataFrame(trips_list)
    stop_times_df = pd.DataFrame(stop_times_list)

    return trips_df, stop_times_df