# DOCUMENTACION SISTEMA CONVERSACIONAL — ATLAS
## Robot Asistente Inteligente para el Cuidado de la Salud en el Hogar

> **Audiencia:** Andres (lider software)
> **Estado general:** Modulo conversacional completo y validado en Windows
> **Plataforma actual:** Windows 11 + Python 3.10
> **Plataforma destino:** Ubuntu 22.04 + ROS2 Humble
> **Ultima actualizacion:** 2026-03-03

---

## INDICE

1. [Vision General](#1-vision-general)
2. [Arquitectura Hibrida Edge-Cloud](#2-arquitectura-hibrida-edge-cloud)
3. [Tecnologias Utilizadas](#3-tecnologias-utilizadas)
4. [Estructura del Proyecto](#4-estructura-del-proyecto)
5. [Modulos en Detalle](#5-modulos-en-detalle)
6. [Maquina de Estados FSM](#6-maquina-de-estados-fsm)
7. [Base de Datos Medica](#7-base-de-datos-medica)
8. [Voz del Sistema](#8-voz-del-sistema)
9. [Consideraciones Eticas](#9-consideraciones-eticas)
10. [Metricas y Rendimiento](#10-metricas-y-rendimiento)
11. [Estado Actual y Pendientes](#11-estado-actual-y-pendientes)
12. [Plan de Migracion a ROS2](#12-plan-de-migracion-a-ros2)
13. [Guia de Pruebas](#13-guia-de-pruebas)
14. [Solucion de Problemas](#14-solucion-de-problemas)

---

## 1. VISION GENERAL

### Proposito

Atlas es el sistema conversacional del robot Baymax. Permite al usuario interactuar de
forma natural mediante voz en espanol para:

- Activar funciones del robot mediante comandos de voz
- Consultar historial de salud y proximas dosis con datos reales de la base de datos
- Recibir informacion general sobre salud
- Recibir confirmaciones y respuestas empaticas del robot

### Nombre y Activacion

- **Wake word:** "Atlas"
- **Idioma de reconocimiento:** Espanol Colombia (es-CO)
- **Voz del sistema:** Azure Neural Voice — Camila (Peru), es-PE-CamilaNeural
- **Confirmacion de escucha:** Camila dice "Si?" al detectar la wake word

### Principios de Diseno

- **Hibrido:** Funciona sin internet (comandos criticos) y con internet (conversacion avanzada)
- **Etico:** Nunca diagnostica, nunca prescribe, siempre deriva al medico
- **Reactivo:** Responde solo lo que se pregunta, nunca da informacion no solicitada
- **Rapido:** Pipeline completo ~1.6-1.9s promedio (post-optimizaciones)
- **Confiable:** Multiples niveles de fallback en cada servicio cloud
- **Privado:** Conversaciones no almacenadas, datos de salud solo locales (SQLite)

---

## 2. ARQUITECTURA HIBRIDA EDGE-CLOUD

```
+-------------------------------------------------------------+
|                  PROCESAMIENTO LOCAL (EDGE)                 |
|                                                             |
|  [Microfono] -> [Noise Filter] -> [VAD]                    |
|                                    |                        |
|                    [Wake Word: "Atlas"]  <- Porcupine       |
|                                    |                        |
|                          [Comando local?] <- Vosk           |
|                           SI |         | NO                 |
|                [Respuesta inmediata]  [Buffer audio]        |
|                                              |              |
+----------------------------------------------|--------------+
                                               | (requiere internet)
+----------------------------------------------v--------------+
|                    PROCESAMIENTO CLOUD                      |
|                                                             |
|  [Audio PCM] -> [Groq Whisper STT] -> [Texto]             |
|                                          |                  |
|                              [Groq LLM Llama 3.3 70B]      |
|                              + Contexto paciente (BD)       |
|                              + Memoria 4 turnos             |
|                                          |                  |
|                         [Azure Neural TTS Camila (Peru)]    |
|                         + SSML prosody (rate=0.92)          |
|                         + Mejora de numeros a texto         |
|                                          |                  |
+------------------------------------------|-----------------+
                                           |
                              [Reproduccion de audio]
```

### Cuando usa cada modo

| Situacion | Modo | Latencia |
|-----------|------|----------|
| Sin internet | Local (Vosk) solo comandos predefinidos | ~500ms |
| Comando reconocible ("ven aqui", "mide signos") | Local (prioridad) | ~500ms |
| Pregunta libre en lenguaje natural | Cloud completo | ~1.6-2.5s |
| Emergencia / "detente" | Siempre local | < 500ms |

---

## 3. TECNOLOGIAS UTILIZADAS

### Procesamiento Local

| Componente | Tecnologia | Proposito |
|------------|------------|-----------|
| Wake Word | Porcupine (Picovoice) | Detecta "Atlas" 24/7 sin conexion |
| STT local | Vosk (modelo espanol) | Reconoce 9 comandos predefinidos offline |
| Deteccion de voz | WebRTC VAD | Detecta inicio/fin de habla |
| Captura de audio | PyAudio | Captura del microfono (16kHz mono) |
| Reproduccion | sounddevice | Reproduce respuestas de voz |
| Base de datos | SQLite (sqlite3) | Datos medicos del paciente (local) |

### Servicios Cloud

| Componente | Tecnologia | Latencia promedio | Tier |
|------------|------------|-------------------|------|
| STT | Groq Whisper large-v3-turbo | ~0.7-1.3s | Gratuito |
| LLM | Groq Llama 3.3 70B Versatile | ~0.4-0.6s | Gratuito |
| TTS | Azure Neural Camila (Peru) | ~0.35-0.50s | ~$5-10/mes |

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
robot_project/
├── README.md
├── requirements.txt
├── Documentacion/
│   ├── DOCUMENTACION_CONVERSACIONAL_.md  <- Este archivo
│   ├── DOCUMENTACION_ROS2.md
│   └── PROYECTO_GENERAL.md
├── data/
│   ├── patient.db                        <- Base de datos SQLite
│   └── audio/
│       └── confirmation.wav              <- "Si?" voz de Camila
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
    │   ├── text_to_speech.py             <- Azure TTS + cache + SSML
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
        ├── test_tts_simple.py
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

## 5. MODULOS EN DETALLE

### audio/capture.py
Captura audio a 16kHz mono en chunks de 20ms (320 samples). Thread-safe.

### audio/vad.py
Detecta inicio/fin de habla con WebRTC VAD. Al detectar silencio prolongado
publica SPEECH_END en el bus de eventos. Agresividad: 2 (configurable 0-3).

### audio/noise_filter.py
Calibra ruido ambiente durante 2s al arrancar. Aplica sustraccion del nivel base.

### audio/playback.py
Reproduce audio PCM via sounddevice. El beep de confirmacion se reproduce en
modo bloqueante para que el microfono no lo capture antes de grabar al usuario.

### audio/audio_buffer.py
Acumula frames mientras el usuario habla. stop_recording() entrega bytes listos para STT.

### local/wake_word.py
Corre Porcupine en thread dedicado. Publica WAKE_WORD_DETECTED al detectar "Atlas".
Consume ~5-8% CPU. Buffer interno adapta chunk de captura (320) a Porcupine (512).

### local/commands.py
Reconoce 9 comandos con Vosk en paralelo con el VAD durante LISTENING.
Prioriza el comando local sobre el pipeline cloud cuando lo detecta.

Comandos disponibles:
```
NAVIGATION  : ven aqui, sigueme, detente, regresa
MEDICAL     : mide mis signos vitales
MEDICATION  : dame mi medicamento
EMERGENCY   : emergencia, llama al medico
INFO        : cual es mi proxima dosis
```

### cloud/speech_to_text.py
Transcribe audio con Groq Whisper large-v3-turbo.
Fallback 4 niveles: key principal -> key backup -> Vosk local -> error notificado.

### cloud/groq_llm.py
Respuestas conversacionales con Groq Llama 3.3 70B.

- Memoria conversacional deslizante de 4 turnos (~280 tokens)
- MAX_TOKENS = 70 (optimizado desde 100, -30% latencia)
- Temperatura = 0.7
- Contexto del paciente inyectado desde medical_db en cada peticion
- Fallback de 6 niveles entre modelos de Groq

### cloud/text_to_speech.py
Sintesis Azure Neural TTS voz Camila.

- Synthesizer persistente (1586ms -> 286ms baseline, ahorro 82%)
- Cache de 7 frases frecuentes pre-sintetizadas al iniciar (~0ms hits)
- SSML con prosody: rate=0.92, pitch=0%, volume=0%
- improve_medical_text_naturalness(): "78 BPM" -> "setenta y ocho pulsaciones por minuto"

### cloud/llm_config.py
System prompt + build_patient_context(patient_id).

Contexto generado dinamicamente:
```
Paciente: Juan Perez
Hora actual: 09:30
Proxima dosis: Metformina en 2 horas y 30 minutos (12:00, 2 tabletas)
Ultimos signos vitales: 78 BPM, 98% SpO2, 36.7C (hace 12 minutos)
```

Los tiempos relativos se calculan en codigo, no por el LLM.

### logic/state_machine.py
FSM de 6 estados. Usa el bus de eventos para comunicarse sin acoplamiento directo
entre threads de audio y modulos cloud.

### logic/medical_db.py
SQLite con 5 tablas, 3 capas (init, CRUD, queries compuestas).
get_proxima_dosis() incluye tiempo_restante_texto calculado.
get_resumen_paciente() incluye tiempo_transcurrido_texto.

### utils/events.py
Bus de eventos con queue.Queue. Eventos: WAKE_WORD_DETECTED, SPEECH_END,
COMMAND_DETECTED, STATE_CHANGED, SPEAKING_START, PLAYBACK_DONE.

---

## 6. MAQUINA DE ESTADOS FSM

```
              IDLE
          (Porcupine activo)
                |
      WAKE_WORD_DETECTED
                |
           LISTENING
      Camila dice "Si?" (bloqueante)
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

| Estado | Timeout | Accion |
|--------|---------|--------|
| LISTENING | 10s | Volver a IDLE |
| LISTENING | 5s sin voz | Volver a IDLE |
| PROCESSING_CLOUD | 15s | Fallback / error |
| PROCESSING_LOCAL | 2s | Error y IDLE |

---

## 7. BASE DE DATOS MEDICA

### Esquema (SQLite — data/patient.db)

```
pacientes               medicamentos            horarios_medicacion
─────────────           ────────────────        ───────────────────
id PK                   id PK                   id PK
nombre                  nombre                  id_paciente FK
ruta_encoding_facial    descripcion             id_medicamento FK
notas                   unidad                  hora_programada HH:MM
activo                  id_compartimento 1-6    dias_semana "1234567"
                        stock                   dosis_unidades
                        ultima_recarga          activo
                        activo

signos_vitales              registros_dispensacion
──────────────              ──────────────────────
id PK                       id PK
id_paciente FK              id_paciente FK
bpm                         id_medicamento FK
spo2                        id_horario FK NOT NULL
temperatura                 dispensado_en ISO 8601
medido_en ISO 8601          estado (exitoso/fallido/omitido/pendiente)
notas                       notas
```

### Integracion con el LLM

Contexto dinamico calculado en cada peticion. Los tiempos relativos
("en 2 horas", "hace 12 minutos") se calculan en codigo via
_calcular_tiempo_relativo() y _calcular_tiempo_transcurrido().

### Poblar datos de prueba

```bash
python scripts/populate_test_db.py
```

---

## 8. VOZ DEL SISTEMA

### Voz Seleccionada: Camila (Peru) — es-PE-CamilaNeural

Seleccionada en benchmark de 8 voces neurales (2026-03-03).
Caracteristicas: alegre, simpatica, dulce y cercana.

### Configuracion

```python
# settings.py
AZURE_TTS_VOICE = 'es-PE-CamilaNeural'

# text_to_speech.py preset 'empatico'
rate    = '0.92'   # 8% mas lenta (Camila habla rapido de base)
pitch   = '0%'     # Sin modificacion (mantener su alegria natural)
volume  = '+0%'    # Sin modificacion
```

### Audio de Confirmacion

data/audio/confirmation.wav — Camila diciendo "Si?" (pitch +5%, rate 0.95).
Regenerar con: python scripts/generate_confirmation_audio.py

### Voces Evaluadas en Benchmark

| Posicion | Voz | Pais |
|----------|-----|------|
| 1 | es-PE-CamilaNeural | Peru (ELEGIDA) |
| 2 | es-MX-LarissaNeural | Mexico |
| 3 | es-CR-MariaNeural | Costa Rica |
| — | es-CO-SalomeNeural | Colombia (anterior) |

---

## 9. CONSIDERACIONES ETICAS

### System Prompt (llm_config.py)

Comportamiento del LLM:
- Respuestas maximo 40 palabras (optimizado para TTS)
- Responde SOLO lo que se pregunta — no da informacion no solicitada
- No menciona dosis o signos vitales a menos que se pregunte
- Solo reporta datos medicos, nunca interpreta ni diagnostica
- Ante valores anormales: informa y recomienda consultar medico
- Nunca prescribe, nunca diagnostica, siempre deriva al medico
- No inventa datos que no tiene

### Privacidad

- Conversaciones NO almacenadas (RAM de 4 turnos, se borra al cerrar)
- Datos medicos solo en SQLite local, nunca enviados a la nube
- Al cloud solo va el texto transcrito (no audio crudo)
- Reconocimiento facial (futuro) operara con consentimiento previo

---

## 10. METRICAS Y RENDIMIENTO

### Latencias del Pipeline (Conversacion real, 2026-03-03)

| Componente | Latencia medida |
|------------|-----------------|
| Wake word Porcupine | < 100ms |
| Beep confirmacion bloqueante | ~1.24s |
| STT Groq Whisper | 0.67 – 0.99s |
| LLM Groq Llama 3.3 70B | 0.41 – 0.54s |
| TTS Azure Camila optimizado | ~0.35 – 0.50s |
| **Pipeline completo cloud** | **1.62 – 1.90s** |
| Comando local Vosk | ~0.48s |

### Optimizaciones TTS (Benchmark 2026-03-02)

| Variante | Promedio | vs Baseline |
|----------|----------|-------------|
| Baseline sin optimizar | 1586ms | — |
| Synthesizer persistente | 394ms | -1193ms |
| Synthesizer + cache + sin SSML | 286ms | -1300ms |
| Config actual (+ SSML naturalidad) | ~360ms | -1226ms |

### Optimizaciones LLM

| Parametro | Antes | Ahora |
|-----------|-------|-------|
| MAX_TOKENS | 100 | 70 (-30%) |
| Tokens output promedio | ~60 | ~15 (-75%) |
| Memoria conversacional | No | 4 turnos |
| Contexto del paciente | No | Dinamico (BD) |

---

## 11. ESTADO ACTUAL Y PENDIENTES

### Completado (2026-03-03)

Audio:
- Capture, VAD, noise_filter, playback, audio_buffer
- Wake word Porcupine ("Atlas")
- Comandos locales Vosk (9 comandos, 5 categorias)
- Beep bloqueante (evita captura por microfono)

Cloud:
- STT Groq Whisper + fallback 4 niveles + 2 API keys
- LLM Groq Llama 3.3 70B + fallback 6 niveles + memoria 4 turnos
- TTS Azure Camila + synthesizer persistente + cache + SSML
- Contexto dinamico paciente integrado (tiempos relativos)
- System prompt con restricciones medicas y comportamiento reactivo

Logica:
- FSM 6 estados implementada y validada en conversacion real
- medical_db.py — 5 tablas, 3 capas, queries con tiempos relativos
- Integracion BD -> LLM funcionando (validado en prueba real 2026-03-03)

Infraestructura:
- main.py homogeneizado y funcional
- Logging profesional por modulo
- Bus de eventos thread-safe
- settings.py (config general) + llm_config.py (config LLM) separados

Voz:
- Benchmark 8 voces neurales completado
- Camila (es-PE-CamilaNeural) seleccionada e implementada
- Audio confirmacion "Si?" regenerado con voz de Camila
- improve_medical_text_naturalness() activo en todos los textos medicos

### Pendiente — Modulo Conversacional Windows

- Driver de comunicacion con microcontrolador para medicion real de signos vitales
  (cuando Vosk detecte el comando: enviar al micro, recibir datos, guardar en BD, reportar)
- Scheduler de recordatorios automaticos de medicacion
- Rate limiter para proteccion del tier gratuito de Groq
- intent_classifier.py para mejorar enrutamiento local/cloud

### Pendiente — Post Windows (ROS2)

- Port a Ubuntu 22.04 + validar todas las dependencias
- Convertir main.py en nodo ROS2 (AtlasNode)
- Topics ROS2 para integracion con navegacion y hardware
- HMI dashboard para visualizacion de datos del paciente
- Reconocimiento facial para patient_id automatico

---

## 12. PLAN DE MIGRACION A ROS2

### Interfaz del Nodo ROS2 (atlas_ros2_node.py)

```python
# Topics que publica (Atlas -> Robot)
/atlas/detected_command    # std_msgs/String  Comando local
/atlas/intent              # std_msgs/String  Intent JSON
/robot/speak               # std_msgs/String  TTS proactivo
/atlas/listening           # std_msgs/Bool    Estado escucha
/atlas/active              # std_msgs/Bool    Estado sistema

# Topics a los que se suscribe (Robot -> Atlas)
/health/bpm                # std_msgs/Int32
/health/spo2               # std_msgs/Int32
/health/temperature        # std_msgs/Float32
/patient/identified        # std_msgs/String  De reconocimiento facial

# Services
/atlas/say                 # texto -> OK/error (TTS sincrono)
/atlas/ask                 # pregunta -> respuesta LLM
```

### Pasos de Migracion

1. Instalar Ubuntu 22.04 + ROS2 Humble + virtualenv Python
2. Verificar compatibilidad de cada dependencia Python en Ubuntu
3. Convertir main.py en clase AtlasNode(Node) de ROS2
4. Reemplazar bus de eventos interno por topics ROS2
5. Conectar medical_db con datos reales de sensores
6. Agregar al launch file del robot
7. Pruebas de integracion con hardware real

---

## 13. GUIA DE PRUEBAS

### Arrancar el sistema completo

```bash
cd robot_project
python baymax_voice/main.py
# Di "atlas" para activar, luego habla directamente
```

### Pruebas individuales

```bash
python -m baymax_voice.test.test_quick_system       # Verificacion rapida
python -m baymax_voice.test.test_integration_full   # Pipeline completo
python -m baymax_voice.test.test_vad                # Audio y VAD
python -m baymax_voice.test.test_wake_word          # Wake word
python -m baymax_voice.test.test_commands           # Comandos Vosk
python -m baymax_voice.test.test_groq               # LLM
python -m baymax_voice.test.test_tts_interactive    # TTS Camila
python -m baymax_voice.test.test_context_prompt     # Contexto BD -> LLM
python -m baymax_voice.test.test_camila_validation  # Validar voz Camila
python -m baymax_voice.test.test_confirmation_audio # Validar audio "Si?"
```

### Poblar base de datos

```bash
python scripts/populate_test_db.py
```

---

## 14. SOLUCION DE PROBLEMAS

### Wake word no se detecta
- Subir PORCUPINE_SENSITIVITY a 0.7 en settings.py si hay ruido
- Verificar que PORCUPINE_ACCESS_KEY es valida
- Hablar a menos de 2 metros del microfono a volumen normal

### STT transcribe el beep de confirmacion
- Ya corregido: el beep se reproduce en modo bloqueante
- El microfono graba solo despues de que Camila termine de decir "Si?"

### Latencia alta
- Verificar conexion a internet (LLM es el mas sensible)
- Region eastus es la mas cercana a Latinoamerica para Azure
- Los comandos locales no dependen de internet (~480ms)

### Error de API (STT/LLM)
- Sistema activa fallback automaticamente — revisar logs
- Verificar GROQ_API_KEY y GROQ_API_KEY_BACKUP en settings.py
- Groq tier gratuito: ~1000 requests/dia por key

### Error de TTS (Azure)
- Verificar AZURE_SPEECH_KEY y AZURE_SPEECH_REGION en settings.py
- Deben coincidir con el recurso en Azure Portal
- El synthesizer persistente se reconecta automaticamente

---

*Ver PROYECTO_GENERAL.md para contexto completo del robot Baymax.*
*Ver DOCUMENTACION_ROS2.md para arquitectura de integracion con ROS2.*
