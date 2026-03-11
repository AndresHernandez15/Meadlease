# SISTEMA CONVERSACIONAL — ATLAS
## Robot Asistente Médico Domiciliario Meadlese

> **Audiencia:** Andrés (líder software)  
> **Estado:** Módulo completo y validado en Windows · Port a ROS2 pendiente  
> **Plataforma actual:** Windows 11 + Python 3.10  
> **Plataforma destino:** Ubuntu 22.04 + ROS2 Humble  
> **Última actualización:** 2026-03-09

---

## ÍNDICE

1. [Visión General](#1-visión-general)
2. [Arquitectura Híbrida Edge-Cloud](#2-arquitectura-híbrida-edge-cloud)
3. [Tecnologías Utilizadas](#3-tecnologías-utilizadas)
4. [Estructura del Proyecto](#4-estructura-del-proyecto)
5. [Módulos en Detalle](#5-módulos-en-detalle)
6. [Máquina de Estados FSM](#6-máquina-de-estados-fsm)
7. [Base de Datos Médica](#7-base-de-datos-médica)
8. [Voz del Sistema](#8-voz-del-sistema)
9. [Métricas y Rendimiento](#9-métricas-y-rendimiento)
10. [Estado Actual y Pendientes](#10-estado-actual-y-pendientes)
11. [Plan de Migración a ROS2](#11-plan-de-migración-a-ros2)
12. [Guía de Pruebas](#12-guía-de-pruebas)
13. [Solución de Problemas](#13-solución-de-problemas)

---

## 1. VISIÓN GENERAL

Atlas es el sistema conversacional del robot Meadlese. Permite al usuario interactuar de forma natural mediante voz en español para:

- Activar funciones del robot mediante comandos de voz
- Consultar historial de salud y próximas dosis con datos reales de la base de datos
- Recibir información general sobre salud
- Recibir confirmaciones y respuestas empáticas del robot

### Nombre y Activación

- **Wake word:** "Atlas"
- **Idioma de reconocimiento:** Español latino
- **Voz del sistema:** Azure Neural Voice — Camila (Perú), `es-PE-CamilaNeural`
- **Confirmación de escucha:** Camila dice "¿Sí?" al detectar la wake word

### Principios de Diseño

| Principio | Descripción |
|-----------|-------------|
| **Híbrido** | Funciona sin internet (comandos críticos) y con internet (conversación avanzada) |
| **Ético** | Nunca diagnostica, nunca prescribe, siempre deriva al médico |
| **Reactivo** | Responde solo lo que se pregunta; no da información no solicitada |
| **Rápido** | Pipeline completo ~1.6–1.9s promedio (post-optimizaciones) |
| **Confiable** | Múltiples niveles de fallback en cada servicio cloud |
| **Privado** | Conversaciones no almacenadas; datos de salud solo en SQLite local |

---

## 2. ARQUITECTURA HÍBRIDA EDGE-CLOUD

```
+-------------------------------------------------------------+
|                  PROCESAMIENTO LOCAL (EDGE)                 |
|                                                             |
|  [Micrófono] -> [Noise Filter] -> [VAD]                     |
|                                    |                        |
|                    [Wake Word: "Atlas"]  <- Porcupine       |
|                                    |                        |
|                          [¿Comando local?] <- Vosk          |
|                           SÍ |          | NO                |
|                [Respuesta inmediata]  [Buffer audio]        |
|                                              |              |
+----------------------------------------------|--------------+
                                               | (requiere internet)
+----------------------------------------------v--------------+
|                    PROCESAMIENTO CLOUD                      |
|                                                             |
|  [Audio PCM] -> [Groq Whisper STT] -> [Texto]               |
|                                          |                  |
|                              [Groq LLM Llama 3.3 70B]       |
|                              + Contexto paciente (BD)       |
|                              + Memoria 4 turnos             |
|                                          |                  |
|                         [Azure Neural TTS Camila (Perú)]    |
|                         + SSML prosody (rate=0.92)          |
|                         + Mejora de números a texto         |
|                                          |                  |
+------------------------------------------|------------------+
                                           |
                              [Reproducción de audio]
```

### Cuándo usa cada modo

| Situación | Modo | Latencia |
|-----------|------|----------|
| Sin internet | Local (Vosk) — solo comandos predefinidos | ~500ms |
| Comando reconocible ("ven aquí", "mide signos") | Local (prioridad) | ~500ms |
| Pregunta libre en lenguaje natural | Cloud completo | ~1.6–2.5s |
| Emergencia / "detente" | Siempre local | < 500ms |

---

## 3. TECNOLOGÍAS UTILIZADAS

### Procesamiento Local

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| Wake word | Porcupine (Picovoice) | Detecta "Atlas" 24/7 sin conexión |
| STT local | Vosk (modelo español) | Reconoce 9 comandos predefinidos offline |
| Detección de voz | WebRTC VAD | Detecta inicio/fin de habla |
| Captura de audio | PyAudio | Captura del micrófono (16kHz mono) |
| Reproducción | sounddevice | Reproduce respuestas de voz |
| Base de datos | SQLite (sqlite3) | Datos médicos del paciente (local) |

### Servicios Cloud

| Componente | Tecnología | Latencia promedio | Tier |
|------------|------------|-------------------|------|
| STT | Groq Whisper large-v3-turbo | ~0.7–1.3s | Gratuito |
| LLM | Groq Llama 3.3 70B Versatile | ~0.4–0.6s | Gratuito |
| TTS | Azure Neural Camila (Perú) | ~0.35–0.50s | ~$5–10/mes |

### Variables de Entorno Necesarias

```bash
GROQ_API_KEY=gsk_...
GROQ_API_KEY_BACKUP=gsk_...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
PORCUPINE_ACCESS_KEY=...
```

---

## 4. ESTRUCTURA DEL PROYECTO

```
atlas/                                    # Módulo conversacional (Meadlease/atlas/)
├── README.md
├── requirements.txt
├── .env                                  <- API keys (local, nunca al repo)
├── .env.example                          <- Plantilla pública
├── data/
│   ├── patient.db                        <- Base de datos SQLite
│   └── audio/
│       └── confirmation.wav              <- "¿Sí?" voz de Camila
├── scripts/
│   ├── populate_test_db.py
│   └── generate_confirmation_audio.py
└── baymax_voice/
    ├── main.py                           <- Orquestador principal
    ├── config/
    │   └── settings.py
    ├── audio/
    │   ├── capture.py
    │   ├── vad.py
    │   ├── noise_filter.py
    │   ├── playback.py
    │   └── audio_buffer.py
    ├── local/
    │   ├── wake_word.py                  <- Porcupine ("Atlas")
    │   └── commands.py                   <- Vosk (9 comandos)
    ├── cloud/
    │   ├── speech_to_text.py             <- Groq Whisper + fallback 4 niveles
    │   ├── groq_llm.py                   <- Groq LLM + fallback 6 niveles
    │   ├── text_to_speech.py             <- Azure TTS + caché + SSML
    │   └── llm_config.py                 <- System prompt + build_patient_context()
    ├── logic/
    │   ├── state_machine.py              <- FSM 6 estados
    │   └── medical_db.py                 <- CRUD SQLite + queries compuestas
    ├── utils/
    │   ├── logger.py
    │   └── events.py                     <- Bus de eventos thread-safe
    └── test/
        ├── README_TESTS.md
        ├── test_quick_system.py
        ├── test_integration_full.py
        ├── test_vad.py
        ├── test_wake_word.py
        ├── test_commands.py
        ├── test_groq.py
        ├── test_tts.py
        ├── test_tts_interactive.py
        ├── test_groq_fallback.py
        ├── test_groq_whisper.py
        ├── test_context_prompt.py
        ├── test_camila_validation.py
        ├── test_confirmation_audio.py
        ├── benchmark_latency.py
        ├── benchmark_llm_models.py
        └── benchmark_quality_llm.py
```

---

## 5. MÓDULOS EN DETALLE

### audio/capture.py
Captura audio a 16kHz mono en chunks de 20ms (320 samples). Thread-safe.

### audio/vad.py
Detecta inicio/fin de habla con WebRTC VAD. Al detectar silencio prolongado publica `SPEECH_END` en el bus de eventos. Agresividad: 2 (configurable 0–3).

### audio/noise_filter.py
Calibra ruido ambiente durante 2s al arrancar. Aplica sustracción del nivel base.

### audio/playback.py
Reproduce audio PCM vía sounddevice. El beep de confirmación se reproduce en modo bloqueante para que el micrófono no lo capture antes de grabar al usuario.

### audio/audio_buffer.py
Acumula frames mientras el usuario habla. `stop_recording()` entrega bytes listos para STT.

### local/wake_word.py
Corre Porcupine en thread dedicado. Publica `WAKE_WORD_DETECTED` al detectar "Atlas". Consume ~5–8% CPU. Buffer interno adapta chunk de captura (320) a Porcupine (512).

### local/commands.py
Reconoce 9 comandos con Vosk en paralelo con el VAD durante el estado LISTENING. Prioriza el comando local sobre el pipeline cloud cuando lo detecta.

Comandos disponibles:
```
NAVIGATION  : ven aquí, sígueme, detente, regresa
MEDICAL     : mide mis signos vitales
MEDICATION  : dame mi medicamento
EMERGENCY   : emergencia, llama al médico
INFO        : cuál es mi próxima dosis
```

### cloud/speech_to_text.py
Transcribe audio con Groq Whisper large-v3-turbo. Fallback 4 niveles: key principal → key backup → Vosk local → error notificado.

### cloud/groq_llm.py
Respuestas conversacionales con Groq Llama 3.3 70B.
- Memoria conversacional deslizante de 4 turnos (~280 tokens)
- `MAX_TOKENS = 70` (optimizado desde 100, −30% latencia)
- Temperatura = 0.7
- Contexto del paciente inyectado desde `medical_db` en cada petición
- Fallback de 6 niveles entre modelos de Groq

### cloud/text_to_speech.py
Síntesis Azure Neural TTS voz Camila.
- Synthesizer persistente (1586ms → 286ms baseline, ahorro 82%)
- Caché de 7 frases frecuentes pre-sintetizadas al iniciar (~0ms en hits)
- SSML con prosody: `rate=0.92`, `pitch=0%`, `volume=+0%`
- `improve_medical_text_naturalness()`: "78 BPM" → "setenta y ocho pulsaciones por minuto"

### cloud/llm_config.py
System prompt + `build_patient_context(patient_id)`.

Contexto generado dinámicamente en cada petición:
```
Paciente: Juan Pérez
Hora actual: 09:30
Próxima dosis: Metformina en 2 horas y 30 minutos (12:00, 2 tabletas)
Últimos signos vitales: 78 BPM, 98% SpO₂, 36.7°C (hace 12 minutos)
```
Los tiempos relativos se calculan en código, no por el LLM.

### logic/state_machine.py
FSM de 6 estados. Usa el bus de eventos para comunicarse sin acoplamiento directo entre threads de audio y módulos cloud.

### logic/medical_db.py
SQLite con 5 tablas, 3 capas (init, CRUD, queries compuestas). `get_proxima_dosis()` incluye `tiempo_restante_texto` calculado. `get_resumen_paciente()` incluye `tiempo_transcurrido_texto`.

### utils/events.py
Bus de eventos con `queue.Queue`. Eventos: `WAKE_WORD_DETECTED`, `SPEECH_END`, `COMMAND_DETECTED`, `STATE_CHANGED`, `SPEAKING_START`, `PLAYBACK_DONE`.

---

## 6. MÁQUINA DE ESTADOS FSM

```
              IDLE
          (Porcupine activo)
                |
      WAKE_WORD_DETECTED
                |
           LISTENING
      Camila dice "¿Sí?" (bloqueante)
      Luego: VAD + Vosk en paralelo
                |
     +----------+----------+
 COMMAND_DETECTED      SPEECH_END
     |                     |
PROCESSING_LOCAL   PROCESSING_CLOUD
Vosk -> comando    STT -> LLM -> TTS
Respuesta fija     (+ contexto BD)
     |                     |
     +----------+----------+
                |
            SPEAKING
       Reproduciendo respuesta
                |
           PLAYBACK_DONE
                |
              IDLE
```

### Timeouts

| Estado | Timeout | Acción |
|--------|---------|--------|
| LISTENING | 10s sin habla | Volver a IDLE |
| LISTENING | 5s sin voz detectada | Volver a IDLE |
| PROCESSING_CLOUD | 15s | Fallback / error → IDLE |
| PROCESSING_LOCAL | 2s | Error → IDLE |

---

## 7. BASE DE DATOS MÉDICA

### Esquema (SQLite — `data/patient.db`)

```
pacientes                   medicamentos                horarios_medicacion
─────────────               ────────────────            ───────────────────
id PK                       id PK                       id PK
nombre                      nombre                      id_paciente FK
ruta_encoding_facial        descripcion                 id_medicamento FK
notas                       unidad                      hora_programada  HH:MM
activo                      id_compartimento  1-6       dias_semana  "1234567"
                            stock                       dosis_unidades
                            ultima_recarga              activo
                            activo

signos_vitales              registros_dispensacion
──────────────              ──────────────────────
id PK                       id PK
id_paciente FK              id_paciente FK
bpm                         id_medicamento FK
spo2                        id_horario FK NOT NULL
temperatura                 dispensado_en  ISO 8601
medido_en  ISO 8601         estado  (exitoso/fallido/omitido/pendiente)
notas                       notas
```

### Integración con el LLM

El contexto dinámico se calcula en cada petición vía `_calcular_tiempo_relativo()` y `_calcular_tiempo_transcurrido()`. Los tiempos relativos ("en 2 horas", "hace 12 minutos") los resuelve el código, no el LLM.

### Poblar datos de prueba

```bash
python scripts/populate_test_db.py
```

---

## 8. VOZ DEL SISTEMA

### Voz seleccionada: Camila (Perú) — `es-PE-CamilaNeural`

Seleccionada en benchmark de 8 voces neurales (2026-03-03). Características: alegre, simpática, dulce y cercana.

### Configuración

```python
# settings.py
AZURE_TTS_VOICE = 'es-PE-CamilaNeural'

# text_to_speech.py — preset 'empático'
rate   = '0.92'   # 8% más lenta (Camila habla rápido de base)
pitch  = '0%'     # Sin modificación (mantener su alegría natural)
volume = '+0%'    # Sin modificación
```

### Audio de confirmación

`data/audio/confirmation.wav` — Camila diciendo "¿Sí?" (pitch +5%, rate 0.95).  
Regenerar con: `python scripts/generate_confirmation_audio.py`

### Voces evaluadas en benchmark

| Posición | Voz | País |
|----------|-----|------|
| 1 ✅ | es-PE-CamilaNeural | Perú (ELEGIDA) |
| 2 | es-MX-LarissaNeural | México |
| 3 | es-CR-MariaNeural | Costa Rica |
| — | es-CO-SalomeNeural | Colombia (anterior) |

---

## 9. MÉTRICAS Y RENDIMIENTO

### Latencias del pipeline (conversación real, 2026-03-03)

| Componente | Latencia medida |
|------------|-----------------|
| Wake word Porcupine | < 100ms |
| Beep de confirmación (bloqueante) | ~1.24s |
| STT Groq Whisper | 0.67 – 0.99s |
| LLM Groq Llama 3.3 70B | 0.41 – 0.54s |
| TTS Azure Camila optimizado | 0.35 – 0.50s |
| **Pipeline completo cloud** | **1.62 – 1.90s** |
| Comando local Vosk | ~0.48s |

### Optimizaciones TTS (benchmark 2026-03-02)

| Variante | Promedio | vs Baseline |
|----------|----------|-------------|
| Baseline sin optimizar | 1586ms | — |
| Synthesizer persistente | 394ms | −1193ms |
| Synthesizer + caché + sin SSML | 286ms | −1300ms |
| Config actual (+ SSML naturalidad) | ~360ms | −1226ms |

### Optimizaciones LLM

| Parámetro | Antes | Ahora |
|-----------|-------|-------|
| MAX_TOKENS | 100 | 70 (−30%) |
| Tokens output promedio | ~60 | ~15 (−75%) |
| Memoria conversacional | No | 4 turnos |
| Contexto del paciente | No | Dinámico (BD) |

---

## 10. ESTADO ACTUAL Y PENDIENTES

### Completado ✅ (2026-03-09)

**Audio:** capture, VAD, noise_filter, playback, audio_buffer, wake word Porcupine, comandos Vosk (9 comandos / 5 categorías), beep bloqueante.

**Cloud:** STT Groq Whisper + fallback 4 niveles + 2 API keys · LLM Groq Llama 3.3 70B + fallback 6 niveles + memoria 4 turnos · TTS Azure Camila + synthesizer persistente + caché + SSML · contexto dinámico del paciente · system prompt con restricciones médicas.

**Lógica:** FSM 6 estados validada · `medical_db.py` (5 tablas, queries con tiempos relativos) · integración BD → LLM validada en conversación real.

**Infraestructura:** `main.py` funcional · logging por módulo · bus de eventos thread-safe · `settings.py` y `llm_config.py` separados.

**Voz:** Benchmark 8 voces completado · Camila seleccionada e implementada · audio de confirmación "¿Sí?" generado.

### Pendientes — aún en Windows ⏳

- Driver de comunicación con microcontrolador para recibir mediciones reales de signos vitales (cuando Vosk detecte el comando: enviar al micro → recibir datos → guardar en BD → reportar)
- Scheduler de recordatorios automáticos de medicación
- Rate limiter para protección del tier gratuito de Groq
- `intent_classifier.py` para mejorar enrutamiento local/cloud

### Pendientes — post Windows (ROS2) ❌

- Port a Ubuntu 22.04 y validación de dependencias
- Convertir `main.py` en nodo ROS2 (`AtlasNode`)
- Topics ROS2 para integración con navegación y hardware
- HMI dashboard para visualización de datos del paciente
- Reconocimiento facial para `patient_id` automático

---

## 11. PLAN DE MIGRACIÓN A ROS2

### Interfaz del nodo ROS2 (`atlas_ros2_node.py`)

```python
# Topics que publica (Atlas → Robot)
/atlas/detected_command    # std_msgs/String   Comando local detectado
/atlas/intent              # std_msgs/String   Intent JSON
/robot/speak               # std_msgs/String   TTS proactivo del robot
/atlas/listening           # std_msgs/Bool     Estado de escucha
/atlas/active              # std_msgs/Bool     Estado general del sistema

# Topics a los que se suscribe (Robot → Atlas)
/health/bpm                # std_msgs/Int32
/health/spo2               # std_msgs/Int32
/health/temperature        # std_msgs/Float32
/patient/identified        # std_msgs/String   patient_id de reconocimiento facial

# Services
/atlas/say                 # texto → OK/error  (TTS síncrono)
/atlas/ask                 # pregunta → respuesta LLM
```

### Pasos de migración

1. Instalar Ubuntu 22.04 + ROS2 Humble + virtualenv Python 3.10
2. Verificar compatibilidad de cada dependencia Python en Ubuntu (especialmente Porcupine y PyAudio)
3. Convertir `main.py` en clase `AtlasNode(Node)` de ROS2
4. Reemplazar bus de eventos interno por topics ROS2
5. Conectar `medical_db` con datos reales de sensores (vía topics `/health/*`)
6. Agregar al launch file del robot
7. Pruebas de integración con hardware real

---

## 12. GUÍA DE PRUEBAS

### Arrancar el sistema completo

```bash
cd Meadlease/atlas
python baymax_voice/main.py
# Di "atlas" para activar, luego habla directamente
```

### Pruebas individuales

```bash
python -m baymax_voice.test.test_quick_system       # Verificación rápida
python -m baymax_voice.test.test_integration_full   # Pipeline completo
python -m baymax_voice.test.test_vad                # Audio y VAD
python -m baymax_voice.test.test_wake_word          # Wake word
python -m baymax_voice.test.test_commands           # Comandos Vosk
python -m baymax_voice.test.test_groq               # LLM
python -m baymax_voice.test.test_tts_interactive    # TTS Camila
python -m baymax_voice.test.test_context_prompt     # Contexto BD → LLM
python -m baymax_voice.test.test_camila_validation  # Validar voz Camila
python -m baymax_voice.test.test_confirmation_audio # Validar audio "¿Sí?"
```

### Poblar base de datos de prueba

```bash
python scripts/populate_test_db.py
```

---

## 13. SOLUCIÓN DE PROBLEMAS

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| Wake word no se detecta | Ruido ambiente alto o key inválida | Subir `PORCUPINE_SENSITIVITY` a 0.7 en `settings.py`; verificar `PORCUPINE_ACCESS_KEY`; hablar a < 2m |
| STT transcribe el beep | Bug antiguo (ya corregido) | El beep corre en modo bloqueante; el micrófono solo graba después de que Camila termine "¿Sí?" |
| Latencia alta | Conexión a internet lenta | Verificar conexión; los comandos locales no dependen de internet (~480ms) |
| Error STT/LLM de API | Keys inválidas o límite alcanzado | Sistema activa fallback automático; verificar `GROQ_API_KEY` y `GROQ_API_KEY_BACKUP`; límite gratuito ~1000 req/día por key |
| Error TTS Azure | Key o región incorrecta | Verificar `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` (debe coincidir con el recurso en Azure Portal); el synthesizer se reconecta automáticamente |

---

*Para contexto general del proyecto: ver `PROYECTO_GENERAL.md`*  
*Para arquitectura ROS2, Nav2, Kinect y micro-ROS: ver `DOCUMENTACION_ROS2.md`*

