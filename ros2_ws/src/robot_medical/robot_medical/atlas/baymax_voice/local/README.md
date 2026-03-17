# 🎯 Módulo Local — Procesamiento Offline

## Descripción

Este módulo maneja el procesamiento de voz offline (sin conexión a internet) del sistema conversacional Atlas. Implementa la detección de palabra de activación ("Atlas") y el reconocimiento de comandos predefinidos usando modelos locales.

---

## Módulos

### `wake_word.py`
**Detección de palabra de activación usando Porcupine**

Detecta continuamente la palabra "Atlas" para activar el sistema conversacional.

- **Motor:** Porcupine (Picovoice)
- **Modo:** Offline, 100% local
- **CPU:** ~5-8% en background
- **Latencia:** < 100ms

**Funciones principales:**
- `initialize(access_key, keyword_path, model_path, sensitivity)` — Inicializa Porcupine
- `process_frame(audio_frame)` — Procesa frame y retorna True si detecta wake word
- `get_frame_length()` — Retorna tamaño de frame requerido
- `get_sample_rate()` — Retorna sample rate del motor
- `get_detection_count()` — Contador de detecciones
- `reset_detection_count()` — Resetea contador
- `reset_buffer()` — Limpia buffer interno
- `shutdown()` — Libera recursos

**Configuración:**
```python
WAKE_WORD = 'atlas'
PORCUPINE_SENSITIVITY = 0.5    # 0.0-1.0 (mayor = más sensible)
PORCUPINE_ACCESS_KEY = '...'   # Obtenida de Picovoice Console
PORCUPINE_KEYWORD_PATH = '...' # Ruta al archivo .ppn
PORCUPINE_MODEL_PATH = '...'   # Ruta al modelo español
```

**Características:**
- Buffer interno para manejar diferencias entre chunk size del sistema y frame length de Porcupine
- Auto-limpieza de buffer para prevenir memory leaks
- Contador de detecciones para métricas
- Compatible con SAMPLE_RATE = 16kHz

**Sensibilidad:**
- `0.0` — Muy conservador (menos falsos positivos, puede no detectar)
- `0.5` — Balance (recomendado)
- `1.0` — Muy sensible (más detecciones, más falsos positivos)

---

### `commands.py`
**Detección de comandos de voz offline usando Vosk**

Reconoce comandos predefinidos sin necesidad de conexión a internet.

- **Motor:** Vosk con modelo español
- **Modo:** Streaming + final
- **Latencia:** ~500ms
- **Vocabulario:** 9 categorías de comandos

**Funciones principales:**
- `initialize(model_path)` — Inicializa Vosk con modelo español
- `process_audio_streaming(audio_data)` — Procesa audio en streaming (parcial)
- `finalize_audio()` — Finaliza reconocimiento y obtiene resultado final
- `classify_command(text)` — Clasifica texto en comando
- `reset()` — Resetea recognizer para nueva sesión
- `shutdown()` — Libera recursos

**Categorías de Comandos:**

#### 1. Movimiento (`MOVE`)
- `come` — "ven", "acércate", "ven aquí", "ven acá"
- `stop` — "detente", "para", "alto", "párate", "stop"
- `follow` — "sígueme", "sigues"
- `go_kitchen` — "cocina", "ve a la cocina", "ir a la cocina"
- `go_room` — "cuarto", "ve al cuarto", "habitación"

#### 2. Médico (`MEDICAL`)
- `measure` — "mide signos", "signos vitales", "toma mi presión"
- `dispense` — "dispensa medicamento", "dame medicina", "pastilla"

#### 3. Control (`CONTROL`)
- `cancel` — "cancela", "olvídalo", "olvida"
- `silence` — "silencio", "cállate", "calla"

**Proceso de Clasificación:**

1. **Normalización:** Texto → minúsculas y strip
2. **Pattern matching:** Busca coincidencias en `COMMAND_PATTERNS`
3. **Scoring:** Selecciona el patrón más largo que coincida
4. **Resultado:** Retorna comando con tipo, acción, confianza

**Formato de Comando:**
```python
{
    'type': 'MOVE',                # Categoría
    'action': 'come',              # Acción específica
    'raw_text': 'ven aquí',        # Texto original
    'matched_pattern': 'MOVE_COME',# Patrón que coincidió
    'confidence': 0.85             # Confianza (0.7-0.95)
}
```

Si no reconoce el comando:
```python
{
    'type': 'UNKNOWN',
    'raw_text': 'texto no reconocido'
}
```

**Características:**
- **Streaming:** Detecta comandos mientras el usuario habla
- **Thread-safe:** Usa `Lock` para proteger el recognizer
- **Eventos:** Publica `COMMAND_DETECTED` al bus de eventos
- **Fallback:** Si falla Vosk, retorna texto transcrito para enviar al LLM

---

## Flujo de Procesamiento Local

```
[Audio Frame]
    ↓
[wake_word.process_frame()]
    ├─ False → Continuar escuchando
    └─ True → Wake word detectado!
         ↓
    [Evento: WAKE_WORD_DETECTED]
         ↓
    [FSM → LISTENING]
         ↓
    [Acumular audio mientras usuario habla]
         ↓
    [commands.process_audio_streaming()]
         ├─ Comando reconocido → [PROCESSING_LOCAL]
         └─ No reconocido → [PROCESSING_CLOUD]
```

---

## Integración con FSM

### Wake Word
```python
# En el audio thread
if wake_word.process_frame(audio_frame):
    put_event('WAKE_WORD_DETECTED', source='wake_word')
    # FSM transiciona: IDLE → LISTENING
```

### Comandos Locales
```python
# En el audio thread (durante LISTENING)
command = commands.process_audio_streaming(audio_frame)
if command and command['type'] != 'UNKNOWN':
    # Evento publicado automáticamente por commands.py
    # FSM transiciona: LISTENING → PROCESSING_LOCAL
```

### Finalización
```python
# Cuando VAD detecta fin de voz
command = commands.finalize_audio()
if command and command['type'] != 'UNKNOWN':
    # Ejecutar comando local
else:
    # Enviar al pipeline cloud (STT → LLM → TTS)
```

---

## Ventajas del Procesamiento Local

### 1. Funciona Sin Internet
- Comandos críticos siempre disponibles
- Emergencias: "detente", "ayuda" funcionan offline

### 2. Baja Latencia
- Wake word: < 100ms
- Comandos: ~500ms (vs. ~4s del pipeline cloud)

### 3. Privacidad
- Ningún audio sale del dispositivo
- No se envían datos a servidores

### 4. Confiabilidad
- Sin dependencia de APIs externas
- Sin límites de uso
- Sin costos recurrentes

---

## Configuración de Modelos

### Porcupine (Wake Word)

**Obtener Access Key:**
1. Crear cuenta en [Picovoice Console](https://console.picovoice.ai/)
2. Copiar Access Key desde el dashboard
3. Agregar a `settings.py` o variable de entorno

**Entrenar Keyword Personalizado:**
1. Ir a [Picovoice Console](https://console.picovoice.ai/)
2. Sección "Wake Word" → "Create Custom Wake Word"
3. Entrenar con palabra "Atlas" (español)
4. Descargar archivo `.ppn` para Windows/Linux
5. Colocar en `baymax_voice/data/models/`

### Vosk (Comandos)

**Descargar Modelo:**
1. Ir a [Vosk Models](https://alphacephei.com/vosk/models)
2. Descargar `vosk-model-small-es-0.42` (español, 40MB)
3. Extraer en `baymax_voice/data/models/`

**Modelo recomendado para producción:**
- `vosk-model-es-0.42` (1.4GB) — Mayor precisión
- Trade-off: Más espacio en disco, mejor reconocimiento

---

## Agregar Nuevos Comandos

### Paso 1: Agregar Patrones
```python
# En commands.py, actualizar COMMAND_PATTERNS:
COMMAND_PATTERNS = {
    # ... comandos existentes ...
    'MEDICAL_PILL_COUNT': ['cuantas pastillas', 'contar pastillas', 'inventario'],
    'MOVE_GO_BATHROOM': ['baño', 've al baño', 'ir al baño'],
}
```

### Paso 2: Implementar Acción
```python
# En state_machine.py, función execute_local_command():
elif command_type == 'MEDICAL':
    if action == 'pill_count':
        logger.info('Robot: contando pastillas...')
        return "Tengo registradas 30 pastillas de Losartán"
```

### Paso 3: Probar
```bash
python baymax_voice/test/test_commands.py
# Hablar: "Atlas, cuántas pastillas tengo"
```

---

## Testing

### Wake Word
```bash
python baymax_voice/test/test_wake_word.py
# Hablar "Atlas" varias veces
# Verificar detección en logs
```

### Comandos
```bash
python baymax_voice/test/test_commands.py
# Hablar comandos de la lista
# Verificar clasificación correcta
```

---

## Troubleshooting

### Wake word no detecta

**Problema:** Porcupine no detecta "Atlas"

**Soluciones:**
1. Subir `PORCUPINE_SENSITIVITY` de 0.5 → 0.7
2. Verificar que `PORCUPINE_ACCESS_KEY` es válida
3. Verificar que el archivo `.ppn` existe
4. Hablar más claro y a volumen normal
5. Reducir ruido de fondo

### Comandos no se reconocen

**Problema:** Vosk no reconoce comandos

**Soluciones:**
1. Verificar que el modelo español está instalado
2. Hablar más lento y claro
3. Usar variaciones de los comandos (ver `COMMAND_PATTERNS`)
4. Revisar logs para ver qué texto transcribió Vosk
5. Considerar usar modelo más grande (1.4GB)

### Falsos positivos del wake word

**Problema:** Detecta "Atlas" cuando no se dijo

**Solución:**
- Bajar `PORCUPINE_SENSITIVITY` de 0.5 → 0.3

---

## Dependencias

- `pvporcupine` — Wake word detection (Picovoice)
- `vosk` — Speech recognition offline
- `json` — Parsing de resultados de Vosk

---

## Archivos Necesarios

```
baymax_voice/data/models/
├── Atlas_es_windows_v4_0_0.ppn          # Wake word keyword (Windows)
├── porcupine_params_es.pv               # Modelo de idioma español
└── vosk-model-small-es-0.42/            # Modelo Vosk español
    ├── am/
    ├── conf/
    ├── graph/
    └── ...
```

**Tamaño total:** ~100MB

---

## Notas de Implementación

### Thread Safety
- `commands.py` usa `Lock` para proteger el recognizer
- `wake_word.py` es thread-safe por diseño (solo lectura)

### Manejo de Errores
- Todos los errores se logean
- Las funciones retornan `None`/`False` en caso de error
- El sistema continúa funcionando en modo degradado

### Buffer Management
- `wake_word.py` usa buffer interno para manejar diferencias de frame size
- Auto-limpieza del buffer para prevenir crecimiento infinito

### Eventos
- `commands.py` publica `COMMAND_DETECTED` automáticamente
- `wake_word.py` NO publica eventos (se hace en el audio thread)

---

## Migración a ROS2

Estos módulos son 100% Python puro, no dependen de ROS2. La integración será simple:

```python
# En atlas_ros2_node.py
if wake_word.process_frame(audio_frame):
    self.publish_wake_word_detected()  # Topic ROS2

command = commands.process_audio_streaming(audio_frame)
if command and command['type'] != 'UNKNOWN':
    self.publish_command(command)  # Topic ROS2
```

---

**Estado:** ✅ Módulos completados y probados  
**Última actualización:** 2026-03-02

