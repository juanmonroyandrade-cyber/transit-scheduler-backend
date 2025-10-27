# app/services/excel_processor.py

import xlwings as xw
from typing import Dict, List, Any
import os
from datetime import datetime
import traceback


class ExcelProcessor:
    """
    Procesador de Excel para escribir parámetros, recalcular y extraer resultados
    """
    
    def __init__(self, excel_path: str):
        """
        Args:
            excel_path: Ruta al archivo Excel base
        """
        self.excel_path = excel_path
        self.app = None
        self.wb = None
        
    def __enter__(self):
        """Context manager para abrir Excel"""
        try:
            # Abrir Excel (visible=False para que sea más rápido)
            self.app = xw.App(visible=False)
            self.wb = self.app.books.open(self.excel_path)
            return self
        except Exception as e:
            print(f"❌ Error al abrir Excel: {e}")
            traceback.print_exc()
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager para cerrar Excel"""
        try:
            if self.wb:
                self.wb.close()
            if self.app:
                self.app.quit()
        except:
            pass
    
    def write_to_cells(self, sheet_name: str, cell_data: Dict[str, Any]):
        """
        Escribe datos en celdas específicas
        
        Args:
            sheet_name: Nombre de la hoja
            cell_data: Dict con formato {"celda": valor}, ej: {"C5": "03:54"}
        """
        try:
            sheet = self.wb.sheets[sheet_name]
            
            for cell_ref, value in cell_data.items():
                print(f"  ✍️ Escribiendo en {sheet_name}!{cell_ref}: {value}")
                sheet.range(cell_ref).value = value
                
        except Exception as e:
            print(f"❌ Error escribiendo en {sheet_name}: {e}")
            raise
    
    def write_range(self, sheet_name: str, start_cell: str, data: List[List[Any]], 
                   direction: str = 'horizontal'):
        """
        Escribe un rango de datos
        
        Args:
            sheet_name: Nombre de la hoja
            start_cell: Celda inicial (ej: "K3")
            data: Lista de listas con los datos
            direction: 'horizontal' o 'vertical'
        """
        try:
            sheet = self.wb.sheets[sheet_name]
            
            if direction == 'horizontal':
                # Escribir filas horizontales
                for i, row in enumerate(data):
                    # Obtener la celda inicial de esta fila
                    cell = sheet.range(start_cell).offset(row_offset=i)
                    # Escribir toda la fila
                    for j, value in enumerate(row):
                        cell.offset(column_offset=j).value = value
                        
            elif direction == 'vertical':
                # Escribir columnas verticales
                for i, col in enumerate(data):
                    cell = sheet.range(start_cell).offset(column_offset=i)
                    for j, value in enumerate(col):
                        cell.offset(row_offset=j).value = value
            
            print(f"  ✅ Rango escrito en {sheet_name}!{start_cell}")
            
        except Exception as e:
            print(f"❌ Error escribiendo rango en {sheet_name}: {e}")
            raise
    
    def recalculate(self):
        """Fuerza el recálculo de todas las fórmulas"""
        try:
            print("  🔄 Recalculando fórmulas...")
            self.wb.app.calculate()
            print("  ✅ Recálculo completado")
        except Exception as e:
            print(f"❌ Error en recálculo: {e}")
            raise
    
    def read_from_cells(self, sheet_name: str, cell_list: List[str]) -> Dict[str, Any]:
        """
        Lee valores de celdas específicas
        
        Args:
            sheet_name: Nombre de la hoja
            cell_list: Lista de referencias de celdas, ej: ["F12", "G20"]
            
        Returns:
            Dict con formato {"celda": valor}
        """
        try:
            sheet = self.wb.sheets[sheet_name]
            results = {}
            
            for cell_ref in cell_list:
                value = sheet.range(cell_ref).value
                results[cell_ref] = value
                print(f"  📖 Leído de {sheet_name}!{cell_ref}: {value}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error leyendo de {sheet_name}: {e}")
            raise
    
    def read_range(self, sheet_name: str, start_cell: str, num_rows: int, 
                  num_cols: int) -> List[List[Any]]:
        """
        Lee un rango de celdas
        
        Args:
            sheet_name: Nombre de la hoja
            start_cell: Celda inicial (ej: "AN3")
            num_rows: Número de filas a leer
            num_cols: Número de columnas a leer
            
        Returns:
            Lista de listas con los valores
        """
        try:
            sheet = self.wb.sheets[sheet_name]
            
            # Leer el rango completo
            end_cell = sheet.range(start_cell).offset(
                row_offset=num_rows-1, 
                column_offset=num_cols-1
            )
            
            values = sheet.range(f"{start_cell}:{end_cell.address}").value
            
            # Si es una sola fila o columna, convertir a lista de listas
            if not isinstance(values[0], (list, tuple)):
                values = [values]
            
            print(f"  📖 Rango leído de {sheet_name}!{start_cell}: {len(values)} filas")
            return values
            
        except Exception as e:
            print(f"❌ Error leyendo rango de {sheet_name}: {e}")
            raise
    
    def read_dynamic_range(self, sheet_name: str, start_cell: str, 
                          num_cols: int, max_rows: int = 1000) -> List[List[Any]]:
        """
        Lee un rango hasta encontrar una celda vacía
        
        Args:
            sheet_name: Nombre de la hoja
            start_cell: Celda inicial
            num_cols: Número de columnas a leer
            max_rows: Máximo de filas a revisar
            
        Returns:
            Lista de listas con los valores (sin filas vacías)
        """
        try:
            sheet = self.wb.sheets[sheet_name]
            results = []
            
            for i in range(max_rows):
                row_data = []
                all_empty = True
                
                for j in range(num_cols):
                    cell = sheet.range(start_cell).offset(row_offset=i, column_offset=j)
                    value = cell.value
                    row_data.append(value)
                    
                    if value is not None and value != "":
                        all_empty = False
                
                # Si toda la fila está vacía, terminar
                if all_empty:
                    break
                
                results.append(row_data)
            
            print(f"  📖 Rango dinámico leído de {sheet_name}!{start_cell}: {len(results)} filas")
            return results
            
        except Exception as e:
            print(f"❌ Error leyendo rango dinámico de {sheet_name}: {e}")
            raise
    
    def save_as(self, output_path: str):
        """Guarda el archivo Excel modificado"""
        try:
            self.wb.save(output_path)
            print(f"  💾 Excel guardado en: {output_path}")
        except Exception as e:
            print(f"❌ Error guardando Excel: {e}")
            raise


def process_scheduling_parameters(excel_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa los parámetros de programación:
    1. Escribe los parámetros en las celdas del Excel
    2. Recalcula las fórmulas
    3. Extrae los resultados
    
    Args:
        excel_path: Ruta al archivo Excel base
        parameters: Diccionario con los parámetros (tabla1 a tabla7)
        
    Returns:
        Dict con los resultados extraídos
    """
    print("\n" + "="*70)
    print("🚀 INICIANDO PROCESAMIENTO DE EXCEL")
    print("="*70)
    
    try:
        with ExcelProcessor(excel_path) as processor:
            
            # ===== PASO 1: ESCRIBIR PARÁMETROS =====
            print("\n📝 PASO 1: Escribiendo parámetros en Excel...")
            
            tabla1 = parameters.get('tabla1', {})
            tabla2 = parameters.get('tabla2', [])
            tabla3 = parameters.get('tabla3', [])
            
            # Tabla 1: Hora de inicio/fin en Oferta Comercial
            processor.write_to_cells('Oferta Comercial', {
                'C5': tabla1.get('horaInicioCentro', ''),
                'C6': tabla1.get('horaFinCentro', '')
            })
            
            # Tabla 2: Buses variables en Flota Variable
            if tabla2:
                horas = [[item['hora'] for item in tabla2]]
                buses = [[item['buses'] for item in tabla2]]
                
                processor.write_range('Flota Variable', 'K3', horas, 'horizontal')
                processor.write_range('Flota Variable', 'K4', buses, 'horizontal')
            
            # Tabla 3: Tiempos de ciclo en Tiempos de ciclo
            if tabla3:
                horas_col = [[item['hora']] for item in tabla3]
                tciclo_ab = [[item['tCicloAB']] for item in tabla3]
                tciclo_ba = [[item['tCicloBA']] for item in tabla3]
                
                processor.write_range('Tiempos de ciclo', 'E3', horas_col, 'vertical')
                processor.write_range('Tiempos de ciclo', 'H3', tciclo_ab, 'vertical')
                processor.write_range('Tiempos de ciclo', 'J3', tciclo_ba, 'vertical')
            
            # ===== PASO 2: RECALCULAR =====
            print("\n🔄 PASO 2: Recalculando fórmulas...")
            processor.recalculate()
            
            # ===== PASO 3: EXTRAER RESULTADOS =====
            print("\n📖 PASO 3: Extrayendo resultados...")
            
            # Tabla 4: Oferta Comercial AN3:AP3 hacia abajo
            tabla4_data = processor.read_dynamic_range('Oferta Comercial', 'AN3', 3)
            
            # Tabla 5: Oferta Comercial AX3:AZ3 hacia abajo
            tabla5_data = processor.read_dynamic_range('Oferta Comercial', 'AX3', 3)
            
            # Tabla 6: Tiempos de ciclo Z3:AB3 hacia abajo
            tabla6_data = processor.read_dynamic_range('Tiempos de ciclo', 'Z3', 3)
            
            # Tabla 7: Tiempos de ciclo AK3:AM3 hacia abajo
            tabla7_data = processor.read_dynamic_range('Tiempos de ciclo', 'AK3', 3)
            
            results = {
                'success': True,
                'tabla4': tabla4_data,
                'tabla5': tabla5_data,
                'tabla6': tabla6_data,
                'tabla7': tabla7_data,
                'timestamp': datetime.now().isoformat()
            }
            
            print("\n✅ Procesamiento completado exitosamente")
            print(f"  - Tabla 4: {len(tabla4_data)} filas")
            print(f"  - Tabla 5: {len(tabla5_data)} filas")
            print(f"  - Tabla 6: {len(tabla6_data)} filas")
            print(f"  - Tabla 7: {len(tabla7_data)} filas")
            print("="*70 + "\n")
            
            return results
            
    except Exception as e:
        print(f"\n❌ ERROR EN PROCESAMIENTO: {e}")
        traceback.print_exc()
        print("="*70 + "\n")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }