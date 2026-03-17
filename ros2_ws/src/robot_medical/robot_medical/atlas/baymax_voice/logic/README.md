# 🧠 Módulo Logic — Lógica de Negocio del Sistema

## Descripción

Este módulo contiene la lógica central del sistema conversacional Atlas:
- **FSM (Máquina de Estados Finitos)** — Control del flujo conversacional
- **Base de Datos Médica** — Gestión de pacientes, medicamentos y signos vitales
- **Clasificador de Intenciones** — Detección de intents sin LLM (pendiente)

---

## Módulos

### `state_machine.py`
**Máquina de Estados Finitos (FSM) del sistema conversacional**

**Estados:**
```
IDLE → LISTENING → PROCESSING_LOCAL/CLOUD → SPEAKING → IDLE
                        ↓
                      ERROR → IDLE
```

**API:**
```python
from baymax_voice.logic import state_machine

# Inicializar
state_machine.initialize()

# Loop principal (llamar repetidamente)
state_machine.update()

# Obtener estado actual
estado = state_machine.get_current_state()

# Cerrar
state_machine.shutdown()
```

**Transiciones:**
- `IDLE → LISTENING`: Wake word detectado
- `LISTENING → PROCESSING_LOCAL`: Comando local reconocido
- `LISTENING → PROCESSING_CLOUD`: Audio completo para STT
- `PROCESSING_LOCAL/CLOUD → SPEAKING`: Respuesta generada
- `SPEAKING → IDLE`: Reproducción completada
- `*→ ERROR`: Error en cualquier estado
- `ERROR → IDLE`: Recuperación automática

**Características:**
- Thread-safe con sistema de eventos
- Timeouts configurables por estado
- Validación de transiciones
- Logging detallado
- Procesamiento cloud en thread separado

---

### `medical_db.py`
**Base de datos SQLite para gestión médica**

**Tablas:**
1. `pacientes` — Pacientes del sistema
2. `medicamentos` — Medicamentos (6 compartimentos)
3. `horarios_medicacion` — Horarios programados
4. `signos_vitales` — Mediciones de salud
5. `registros_dispensacion` — Historial de dispensaciones

**Arquitectura en 3 capas:**

#### CAPA 1 — Inicialización
```python
from baymax_voice.logic import medical_db

# Crear tablas y directorio data/
medical_db.init_db()
```

#### CAPA 2 — CRUD por Entidad

**Pacientes:**
```python
id_paciente = medical_db.crear_paciente(nombre='Juan Pérez')
paciente = medical_db.obtener_paciente(id_paciente)
pacientes = medical_db.obtener_pacientes_activos()
medical_db.desactivar_paciente(id_paciente)  # Soft delete
```

**Medicamentos:**
```python
id_med = medical_db.crear_medicamento(
    nombre='Losartán',
    unidad='tabletas',
    id_compartimento=1,  # 1-6
    stock=30
)
medical_db.actualizar_stock_medicamento(id_med, nuevo_stock=25)
```

**Horarios:**
```python
id_horario = medical_db.crear_horario_medicacion(
    id_paciente=1,
    id_medicamento=1,
    hora_programada='08:00',
    dias_semana='1234567',  # Todos los días
    dosis_unidades=1
)
```

**Signos Vitales:**
```python
id_medicion = medical_db.registrar_signos_vitales(
    id_paciente=1,
    bpm=72,
    spo2=98,
    temperatura=36.5
)
```

**Dispensaciones:**
```python
id_registro = medical_db.crear_registro_dispensacion(
    id_paciente=1,
    id_medicamento=1,
    id_horario=1,
    estado='exitoso'
)
medical_db.actualizar_estado_dispensacion(id_registro, 'exitoso')
```

#### CAPA 3 — Queries Compuestas (Para Atlas y Scheduler)

**Consultas principales:**
```python
# Horarios del día para un paciente
horarios = medical_db.get_horarios_hoy(id_paciente=1)

# Próxima dosis pendiente
proxima = medical_db.get_proxima_dosis(id_paciente=1)

# Últimas mediciones
mediciones = medical_db.get_ultimos_signos_vitales(id_paciente=1, n=5)

# Resumen completo para contexto del LLM
resumen = medical_db.get_resumen_paciente(id_paciente=1)
# → Retorna: nombre, medicamentos, última medición, próxima dosis

# Verificar dispensación duplicada
dispensada = medical_db.verificar_dosis_dispensada_hoy(
    id_paciente=1,
    id_horario=1
)
```

**Características:**
- Sin dependencias externas (solo stdlib)
- Foreign keys habilitadas
- Soft delete (campo `activo`)
- Thread-safe (SQLite maneja concurrencia)
- Validaciones integradas
- Logging completo

---

### `intent_classifier.py`
**Clasificador de intenciones local** *(Pendiente de implementación)*

**Propósito futuro:**
Clasificar consultas simples sin llamar al LLM, consultando directamente la DB.

**Ejemplos de intents:**
- "¿Cuál es mi próxima dosis?" → Consulta medical_db directamente
- "¿Cuándo fue mi última medición?" → Consulta signos vitales
- "¿Qué medicamentos tomo?" → Lista de medicamentos activos

**Beneficio:**
- Ahorro: 100% tokens + ~3.5s latencia en 20-30% de consultas
- Precisión: 100% (respuesta exacta de la DB)

**Estado:** Placeholder (archivo vacío)

---

## Flujo de Lógica

### Conversación Típica

```
1. [IDLE] Wake word "Atlas" detectado
   ↓
2. [LISTENING] Captura audio mientras usuario habla
   ↓
3. ¿Es comando local? 
   ├─ Sí → [PROCESSING_LOCAL]
   │         ├─ "ven aquí" → Respuesta inmediata
   │         └─ [SPEAKING] → Reproduce respuesta
   │
   └─ No  → [PROCESSING_CLOUD]
             ├─ STT: Audio → Texto
             ├─ LLM: Texto → Respuesta (con contexto del paciente)
             └─ TTS: Respuesta → Audio
             ↓
4. [SPEAKING] Reproduce respuesta
   ↓
5. [IDLE] Vuelve a esperar wake word
```

---

## Integración con Otros Módulos

### FSM ↔ Audio
```python
# state_machine.py
def handle_listening():
    if vad.process_frame(...) == 'speech_end':
        audio = audio_buffer.get_buffer_as_bytes()
        # Lanzar procesamiento...
```

### FSM ↔ Cloud
```python
# state_machine.py
def handle_processing_cloud():
    text, _ = speech_to_text.transcribe(audio)
    
    # Obtener contexto del paciente
    context = build_patient_context(patient_id=1)
    
    result = groq_llm.generate_response(text, patient_context=context)
    audio_response = text_to_speech.synthesize(result['response'])
```

### FSM ↔ Medical DB
```python
# En llm_config.py → build_patient_context()
resumen = medical_db.get_resumen_paciente(patient_id)
# Se inyecta en el system prompt del LLM
```

---

## Configuración

### State Machine
```python
# En config/settings.py
MAX_LISTENING_TIME = 10.0       # Timeout escucha
AUDIO_MIN_DURATION = 0.5        # Duración mínima de audio
```

### Medical DB
```python
# Ubicación automática
DB_PATH = 'robot_project/data/patient.db'

# Número de compartimentos
COMPARTIMENTOS = 6  # 1-6

# Estados de dispensación
ESTADOS = ['exitoso', 'fallido', 'omitido', 'pendiente']
```

---

## Testing

### State Machine
```python
# Test interactivo
python baymax_voice/test/test_integration_full.py
```

### Medical DB
```python
# Test automático
python baymax_voice/logic/medical_db.py

# Poblado de datos de prueba
python scripts/populate_test_db.py
```

---

## Ejemplos de Uso

### Uso Típico de FSM

```python
from baymax_voice.logic import state_machine
import threading

# Inicializar
state_machine.initialize()

# Thread FSM (loop infinito)
def fsm_loop():
    while running:
        state_machine.update()
        time.sleep(0.01)  # 100 Hz

fsm_thread = threading.Thread(target=fsm_loop, daemon=True)
fsm_thread.start()
```

### Uso Típico de Medical DB

```python
from baymax_voice.logic import medical_db

# Inicializar
medical_db.init_db()

# Crear paciente
patient_id = medical_db.crear_paciente('Juan Pérez')

# Agregar medicamento
med_id = medical_db.crear_medicamento(
    nombre='Losartán',
    unidad='tabletas',
    id_compartimento=1,
    stock=30
)

# Programar horario
horario_id = medical_db.crear_horario_medicacion(
    id_paciente=patient_id,
    id_medicamento=med_id,
    hora_programada='08:00',
    dias_semana='1234567'
)

# Obtener resumen para Atlas
resumen = medical_db.get_resumen_paciente(patient_id)
print(f"Próxima dosis: {resumen['proxima_dosis']['nombre_medicamento']}")
```

---

## Migración a ROS2

### State Machine
```python
# En atlas_ros2_node.py
class AtlasNode(Node):
    def __init__(self):
        # La FSM se ejecuta internamente
        state_machine.initialize()
    
    def timer_callback(self):
        # Update en cada ciclo del nodo ROS2
        state_machine.update()
```

### Medical DB
```python
# Sin cambios necesarios, es 100% Python puro
# Se importa directamente desde el nodo ROS2
from baymax_voice.logic import medical_db
```

---

## Dependencias

```
# State Machine
threading
datetime
json

# Medical DB
sqlite3  # Módulo estándar
pathlib
typing
logging
```

---

**Estado:** 
- `state_machine.py` — ✅ Completado
- `medical_db.py` — ✅ Completado y probado
- `intent_classifier.py` — ❌ Pendiente (opcional)

**Última actualización:** 2026-03-02

