# recreate_scheduling_table.py

"""
Script para recrear la tabla scheduling_parameters con el esquema correcto
Ejecutar: python recreate_scheduling_table.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, Base
from app.models.scheduling_models import SchedulingParameters
from sqlalchemy import inspect

print("="*70)
print("🔧 RECREANDO TABLA SCHEDULING_PARAMETERS")
print("="*70)

# 1. Verificar si la tabla existe
inspector = inspect(engine)
table_exists = 'scheduling_parameters' in inspector.get_table_names()

if table_exists:
    print("\n📋 Tabla actual encontrada")
    
    # Mostrar columnas actuales
    columns = inspector.get_columns('scheduling_parameters')
    print("\n📊 Columnas actuales:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Preguntar confirmación
    print("\n⚠️  Esta tabla será eliminada y recreada.")
    confirm = input("¿Continuar? (s/n): ").lower()
    
    if confirm != 's':
        print("\n❌ Operación cancelada")
        sys.exit(0)
    
    # Eliminar tabla
    print("\n🗑️  Eliminando tabla anterior...")
    SchedulingParameters.__table__.drop(engine, checkfirst=True)
    print("✅ Tabla anterior eliminada")
else:
    print("\n📋 No existe tabla anterior")

# 2. Crear nueva tabla
print("\n🔨 Creando nueva tabla con esquema correcto...")
Base.metadata.create_all(bind=engine, tables=[SchedulingParameters.__table__])
print("✅ Tabla recreada exitosamente")

# 3. Verificar nueva estructura
inspector = inspect(engine)
new_columns = inspector.get_columns('scheduling_parameters')

print("\n📊 Nueva estructura:")
for col in new_columns:
    print(f"  ✓ {col['name']}: {col['type']}")

print("\n" + "="*70)
print("🎉 PROCESO COMPLETADO")
print("="*70)
print("\n💡 Ahora puedes:")
print("  1. Reiniciar el servidor backend (Ctrl+C y luego: uvicorn main:app --reload)")
print("  2. Probar guardar un escenario nuevamente")
print()