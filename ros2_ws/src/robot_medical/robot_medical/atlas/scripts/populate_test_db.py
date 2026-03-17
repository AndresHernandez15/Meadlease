"""
Script para poblar la base de datos con datos de prueba realistas.
Ejecutar: python scripts/populate_test_db.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar root del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.logic import medical_db

print('═' * 70)
print('POBLANDO BASE DE DATOS CON DATOS DE PRUEBA')
print('═' * 70)

# Inicializar DB
print('\n1. Inicializando base de datos...')
medical_db.init_db()
print('   ✓ Base de datos inicializada')

# Crear paciente
print('\n2. Creando paciente...')
paciente_id = medical_db.crear_paciente(
    nombre='Juan Pérez',
    notas='Paciente con hipertensión controlada y diabetes tipo 2'
)
print(f'   ✓ Paciente creado: Juan Pérez (ID: {paciente_id})')

# Crear medicamentos
print('\n3. Creando medicamentos...')
losartan_id = medical_db.crear_medicamento(
    nombre='Losartán',
    unidad='tabletas',
    id_compartimento=1,
    descripcion='Antihipertensivo (50mg)',
    stock=30
)
print(f'   ✓ Losartán (ID: {losartan_id}, Compartimento: 1, Stock: 30)')

metformina_id = medical_db.crear_medicamento(
    nombre='Metformina',
    unidad='tabletas',
    id_compartimento=2,
    descripcion='Antidiabético (850mg)',
    stock=60
)
print(f'   ✓ Metformina (ID: {metformina_id}, Compartimento: 2, Stock: 60)')

aspirina_id = medical_db.crear_medicamento(
    nombre='Aspirina',
    unidad='tabletas',
    id_compartimento=3,
    descripcion='Anticoagulante (100mg)',
    stock=50
)
print(f'   ✓ Aspirina (ID: {aspirina_id}, Compartimento: 3, Stock: 50)')

# Crear horarios de medicación
print('\n4. Creando horarios de medicación...')
h1 = medical_db.crear_horario_medicacion(
    id_paciente=paciente_id,
    id_medicamento=losartan_id,
    hora_programada='08:00',
    dias_semana='1234567',  # Todos los días
    dosis_unidades=1
)
print(f'   ✓ Losartán: 08:00 diario, 1 tableta (ID: {h1})')

h2 = medical_db.crear_horario_medicacion(
    id_paciente=paciente_id,
    id_medicamento=metformina_id,
    hora_programada='12:00',
    dias_semana='1234567',
    dosis_unidades=2
)
print(f'   ✓ Metformina: 12:00 diario, 2 tabletas (ID: {h2})')

h3 = medical_db.crear_horario_medicacion(
    id_paciente=paciente_id,
    id_medicamento=metformina_id,
    hora_programada='20:00',
    dias_semana='1234567',
    dosis_unidades=2
)
print(f'   ✓ Metformina: 20:00 diario, 2 tabletas (ID: {h3})')

h4 = medical_db.crear_horario_medicacion(
    id_paciente=paciente_id,
    id_medicamento=aspirina_id,
    hora_programada='08:30',
    dias_semana='1234567',
    dosis_unidades=1
)
print(f'   ✓ Aspirina: 08:30 diario, 1 tableta (ID: {h4})')

# Registrar mediciones de signos vitales (últimos 5 días)
print('\n5. Registrando mediciones de signos vitales...')
mediciones_data = [
    (70, 97, 36.3, 'Medición hace 4 días'),
    (72, 98, 36.4, 'Medición hace 3 días'),
    (74, 99, 36.5, 'Medición hace 2 días'),
    (76, 100, 36.6, 'Medición hace 1 día'),
    (78, 101, 36.7, 'Medición de hoy (mañana)')
]

for i, (bpm, spo2, temp, nota) in enumerate(mediciones_data):
    dias_atras = 4 - i
    medical_db.registrar_signos_vitales(
        id_paciente=paciente_id,
        bpm=bpm,
        spo2=spo2,
        temperatura=temp,
        notas=nota
    )
    print(f'   ✓ Día {i+1}: BPM={bpm}, SpO2={spo2}%, T={temp}°C')

# Registrar algunas dispensaciones (ejemplo: medicamentos de ayer)
print('\n6. Registrando dispensaciones de ejemplo...')
d1 = medical_db.crear_registro_dispensacion(
    id_paciente=paciente_id,
    id_medicamento=losartan_id,
    id_horario=h1,
    estado='exitoso',
    notas='Dispensación automática matutina'
)
print(f'   ✓ Dispensación exitosa: Losartán 08:00 (ID: {d1})')

# Mostrar resumen final
print('\n' + '═' * 70)
print('RESUMEN DE DATOS CARGADOS')
print('═' * 70)

resumen = medical_db.get_resumen_paciente(paciente_id)

print(f'\n📋 Paciente: {resumen["nombre"]}')

print(f'\n💊 Medicamentos activos: {len(resumen["medicamentos_activos"])}')
for med in resumen["medicamentos_activos"]:
    print(f'   • {med["nombre_medicamento"]}: {med["hora_programada"]} ({med["dosis_unidades"]} {med["unidad"]})')

if resumen['ultima_medicion']:
    ult = resumen['ultima_medicion']
    print(f'\n🫀 Última medición de signos vitales:')
    print(f'   • Frecuencia cardíaca: {ult["bpm"]} BPM')
    print(f'   • Saturación de oxígeno: {ult["spo2"]}%')
    print(f'   • Temperatura: {ult["temperatura"]}°C')
    print(f'   • Fecha: {ult["medido_en"][:19]}')

if resumen['proxima_dosis']:
    prox = resumen['proxima_dosis']
    print(f'\n⏰ Próxima dosis:')
    print(f'   • Medicamento: {prox["nombre_medicamento"]}')
    print(f'   • Hora: {prox["hora_programada"]}')
    print(f'   • Dosis: {prox["dosis_unidades"]} {prox["unidad"]}')
else:
    print(f'\n⏰ No hay más dosis pendientes hoy')

print('\n' + '═' * 70)
print('✓ BASE DE DATOS POBLADA EXITOSAMENTE')
print('═' * 70)
print(f'\nUbicación: {medical_db.DB_PATH}')
print('Ahora puedes ejecutar main.py y probar el sistema completo.')

