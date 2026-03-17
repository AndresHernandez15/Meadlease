# 🛠️ Módulo Utils — Utilidades del Sistema

## Descripción

Este módulo contiene utilidades generales del sistema conversacional:
- **Logger** — Sistema de logging centralizado
- **Events** — Bus de eventos thread-safe
- **Rate Limiter** — Control de límites de APIs (pendiente)

---

## Módulos

### `logger.py`
**Sistema de logging centralizado**

Proporciona logging consistente en todo el proyecto con soporte para consola y archivo.

**API:**
```python
from baymax_voice.utils.logger import setup_logger, get_logger

# Inicializar logger principal (llamar una vez al inicio)
setup_logger(level='DEBUG')  # DEBUG, INFO, WARN, ERROR

# Obtener logger para un módulo
logger = get_logger('audio.capture')

# Usar logger
logger.debug('Mensaje de debug')
logger.info('Información')
logger.warning('Advertencia')
logger.error('Error')
```

**Formato de salida:**
```
[INFO] [baymax.audio.capture] Audio inicializado: 16000Hz
[ERROR] [baymax.cloud.stt] Error transcribiendo: timeout
```

**Configuración:**
```python
# En config/settings.py
LOG_LEVEL = 'DEBUG'      # Nivel por defecto
LOG_TO_FILE = False      # Guardar logs en archivo
```

**Características:**
- Niveles estándar: DEBUG, INFO, WARNING, ERROR
- Formato consistente con módulo origen
- Opcional: guardado en archivo con timestamp
- Thread-safe (logging estándar de Python)

---

### `events.py`
**Sistema de eventos thread-safe**

Bus de eventos para comunicación entre threads (audio thread ↔ FSM thread).

**API:**
```python
from baymax_voice.utils.events import put_event, get_event, clear_events

# Publicar evento
put_event('WAKE_WORD_DETECTED', source='wake_word')
put_event('COMMAND_DETECTED', data={'type': 'MOVE', 'action': 'come'}, source='commands')

# Consumir evento (con timeout opcional)
event = get_event(timeout=0.1)  # None si no hay eventos
if event:
    print(f"Tipo: {event.type}")
    print(f"Datos: {event.data}")
    print(f"Origen: {event.source}")
    print(f"Timestamp: {event.timestamp}")

# Limpiar cola de eventos
clear_events()

# Obtener tamaño de la cola
size = queue_size()
```

**Clase Event:**
```python
@dataclass
class Event:
    type: str                    # Tipo de evento (ej: 'WAKE_WORD_DETECTED')
    data: Optional[Any] = None   # Datos asociados (opcional)
    timestamp: datetime          # Timestamp automático
    source: Optional[str] = None # Módulo origen (opcional)
```

**Eventos del Sistema:**
- `WAKE_WORD_DETECTED` — Wake word "Atlas" detectado
- `COMMAND_DETECTED` — Comando local reconocido (data = comando)
- `AUDIO_READY` — Audio completo listo para procesar
- Custom events según necesidad

**Características:**
- Thread-safe (usa Queue de Python)
- FIFO (First In, First Out)
- Timestamp automático
- Opcional: timeout en get_event()

---

### `rate_limiter.py`
**Control de límites de APIs** *(Pendiente de implementación)*

**Propósito futuro:**
Monitorear y limitar uso de APIs externas para evitar exceder tier gratuito.

**Funcionalidad propuesta:**
```python
from baymax_voice.utils.rate_limiter import check_limit, log_usage

# Verificar si se puede hacer llamada
if check_limit('groq_llm', tokens=150):
    # Hacer llamada
    result = groq_llm.generate_response(...)
    log_usage('groq_llm', tokens=150)
else:
    logger.warning('Límite de Groq alcanzado')
```

**Estado:** Placeholder (archivo vacío)

**Prioridad:** Baja (APIs tienen tier gratuito generoso)

---

## Flujo de Eventos Típico

```
[Audio Thread]
    ↓
wake_word detecta "Atlas"
    ↓
put_event('WAKE_WORD_DETECTED')
    ↓
[Event Queue] → FIFO
    ↓
[FSM Thread]
    ↓
event = get_event(timeout=0.01)
    ↓
if event.type == 'WAKE_WORD_DETECTED':
    state_machine.transition_to('LISTENING')
```

---

## Logging Best Practices

### Niveles Recomendados

**DEBUG:**
- Variables internas
- Flujo detallado
- Debugging temporal

```python
logger.debug(f'VAD state: {vad_state}')
```

**INFO:**
- Inicialización de módulos
- Eventos importantes
- Métricas

```python
logger.info('Groq inicializado: llama-3.3-70b-versatile')
logger.info(f'LLM OK: {latency:.2f}s')
```

**WARNING:**
- Situaciones anormales pero recuperables
- Fallbacks activados
- Configuración faltante

```python
logger.warning('Rate limit alcanzado, usando backup key')
```

**ERROR:**
- Errores que impiden funcionalidad
- Excepciones capturadas
- Fallos de inicialización

```python
logger.error(f'Error transcribiendo audio: {e}')
```

---

## Ejemplos de Uso

### Setup Inicial (main.py)

```python
from baymax_voice.utils.logger import setup_logger, get_logger

# Inicializar sistema de logging
setup_logger(level='DEBUG')

# Obtener logger para main
logger = get_logger('main')
logger.info('Sistema Atlas iniciando...')
```

### Uso en Módulos

```python
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.capture')

def initialize():
    logger.debug('Inicializando captura de audio...')
    try:
        # código
        logger.info('Audio inicializado: 16000Hz')
    except Exception as e:
        logger.error(f'Error inicializando audio: {e}')
```

### Comunicación entre Threads

```python
# Audio thread
from baymax_voice.utils.events import put_event

if wake_word.process_frame(audio_frame):
    put_event('WAKE_WORD_DETECTED', source='wake_word')

# FSM thread
from baymax_voice.utils.events import get_event

while running:
    event = get_event(timeout=0.01)
    if event and event.type == 'WAKE_WORD_DETECTED':
        logger.info('Wake word detectada')
        transition_to('LISTENING')
```

---

## Testing

### Logger
```python
# Test manual
from baymax_voice.utils.logger import setup_logger, get_logger

setup_logger('DEBUG')
logger = get_logger('test')

logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
```

### Events
```python
from baymax_voice.utils.events import put_event, get_event, clear_events

# Publicar eventos
put_event('TEST_EVENT', data={'value': 42}, source='test')

# Consumir
event = get_event()
print(f"{event.type}: {event.data}")

# Limpiar
clear_events()
```

---

## Configuración

### Logger
```python
# En config/settings.py
LOG_LEVEL = 'DEBUG'      # DEBUG, INFO, WARN, ERROR
LOG_TO_FILE = False      # True para guardar en logs/baymax_*.log
```

---

## Migración a ROS2

### Logger
```python
# Continúa usando el mismo sistema
# ROS2 tiene su propio logging, pero este es compatible
from baymax_voice.utils.logger import get_logger
logger = get_logger('atlas_node')
```

### Events
```python
# Reemplazar con ROS2 topics
# En atlas_ros2_node.py:

# Antes (standalone):
put_event('WAKE_WORD_DETECTED')

# Después (ROS2):
self.wake_word_pub.publish(String(data='detected'))
```

---

## Dependencias

```python
# Logger
import logging         # Módulo estándar
from datetime import datetime
from pathlib import Path

# Events
from queue import Queue, Empty  # Módulos estándar
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime
```

---

## Notas de Implementación

### Thread Safety

**Logger:**
- Thread-safe por diseño (logging estándar de Python)
- Múltiples threads pueden escribir simultáneamente

**Events:**
- Thread-safe (usa Queue.Queue)
- put_event() y get_event() son atómicos

### Performance

**Logger:**
- Overhead mínimo (~1-5µs por llamada)
- Solo escribe a archivo si LOG_TO_FILE=True

**Events:**
- Queue.Queue es muy eficiente
- get_event() con timeout=0 no bloquea

### Límites

**Events:**
- Queue sin límite de tamaño (puede crecer indefinidamente)
- clear_events() si se acumulan eventos no procesados
- En producción: monitorear queue_size()

---

## Troubleshooting

### Logger no imprime nada

**Problema:** No se ven logs

**Solución:**
1. Verificar que se llamó `setup_logger()`
2. Verificar LOG_LEVEL en settings.py
3. Usar `get_logger()` no `logging.getLogger()`

### Eventos no llegan

**Problema:** get_event() siempre retorna None

**Solución:**
1. Verificar que put_event() se llama desde otro thread
2. Revisar timeout (muy bajo puede perder eventos)
3. Verificar que no se llama clear_events() accidentalmente

---

**Estado:**
- `logger.py` — ✅ Completado y en uso
- `events.py` — ✅ Completado y en uso
- `rate_limiter.py` — ❌ Pendiente (opcional)

**Última actualización:** 2026-03-02

