# Atlas — Sistema Conversacional del Robot Baymax

Sistema conversacional híbrido (Edge + Cloud) para robot asistente médico domiciliario.

**Proyecto de Grado** — Ingeniería Mecatrónica
**Universidad Tecnológica de Bolívar**
**Líder de Software:** Andrés

---

## Estado del Módulo Conversacional

**Última actualización:** 2026-03-03
**Estado:** Completado y validado en Windows — Listo para migrar a ROS2

### Completado

**Audio (Edge):**
- Captura de micrófono (PyAudio, 16kHz mono)
- Voice Activity Detection (WebRTC VAD)
- Filtro de ruido adaptativo con calibración automática
- Buffer de audio thread-safe
- Reproducción (sounddevice) con modo bloqueante

**Procesamiento Local (Offline):**
- Wake word "Atlas" (Porcupine) — ~5-8% CPU en escucha continua
- Comandos locales (Vosk) — 9 comandos en 5 categorías

**Servicios Cloud:**
- STT: Groq Whisper large-v3-turbo (4 niveles de fallback, 2 API keys)
- LLM: Groq Llama 3.3 70B (6 niveles de fallback, memoria 4 turnos)
- TTS: Azure Neural Voice — Camila (Perú), es-PE-CamilaNeural

**Lógica:**
- FSM 6 estados completamente implementada y validada en conversación real
- Base de datos médica SQLite (5 tablas, 3 capas)
- Contexto dinámico del paciente integrado en el LLM (tiempos relativos)
- System prompt con restricciones médicas y comportamiento reactivo

**Infraestructura:**
- main.py orquestador funcional
- Suite de pruebas (15+ tests)
- Logging profesional por módulo
- Bus de eventos thread-safe

---

## Métricas de Rendimiento (Validadas 2026-03-03)

| Componente | Latencia medida |
|------------|-----------------|
| Wake word (Porcupine) | < 100ms |
| Confirmación "¿Sí?" (Camila) | ~1.24s |
| STT (Groq Whisper) | 0.67 – 0.99s |
| LLM (Groq Llama 3.3 70B) | 0.41 – 0.54s |
| TTS (Azure Camila, optimizado) | ~0.35 – 0.50s |
| **Pipeline completo cloud** | **1.62 – 1.90s** |
| Comando local (Vosk) | ~0.48s |

**TTS:** Reducción de 1586ms → 360ms promedio (77% mejora) gracias a
synthesizer persistente + caché de frases frecuentes.

---

## Voz del Sistema

**Camila (Perú) — es-PE-CamilaNeural**
Seleccionada en benchmark comparativo de 8 voces neurales (2026-03-03).
Características: alegre, simpática, dulce y cercana.
Configuración: rate=0.92 (8% más lenta), pitch y volumen naturales.

---

## Estructura del Proyecto

```
baymax_voice/
├── main.py              Orquestador principal
├── config/settings.py   Configuración centralizada
├── audio/               Captura, VAD, filtro, playback, buffer
├── local/               Wake word (Porcupine), comandos (Vosk)
├── cloud/               STT (Groq), LLM (Groq), TTS (Azure)
├── logic/               FSM, base de datos médica (SQLite)
├── utils/               Logger, bus de eventos
└── test/                Suite de pruebas y benchmarks

data/
├── patient.db           Base de datos SQLite
└── audio/confirmation.wav  "¿Sí?" voz de Camila

scripts/
├── populate_test_db.py         Datos de prueba
└── generate_confirmation_audio.py  Regenerar audio de confirmación

Documentacion/
├── DOCUMENTACION_CONVERSACIONAL_.md  Documentación técnica completa
├── DOCUMENTACION_ROS2.md             Plan de integración ROS2
└── PROYECTO_GENERAL.md               Contexto general del proyecto
```

---

## Inicio Rápido

### Requisitos

```bash
pip install -r requirements.txt
```

Variables de entorno necesarias (crear archivo `.env`):
```bash
GROQ_API_KEY=gsk_...
GROQ_API_KEY_BACKUP=gsk_...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
PORCUPINE_ACCESS_KEY=...
```

### Poblar base de datos de prueba

```bash
python scripts/populate_test_db.py
```

### Ejecutar el sistema

```bash
python baymax_voice/main.py
# Di "atlas" para activar, luego habla directamente
```

### Pruebas

```bash
# Verificación rápida sin hardware
python -m baymax_voice.test.test_quick_system

# Pipeline completo interactivo
python -m baymax_voice.test.test_integration_full
```

---

## Pendiente (Módulo Conversacional)

- Driver de comunicación con microcontrolador para medición real de signos vitales
- Scheduler de recordatorios automáticos de medicación
- Rate limiter para protección del tier gratuito de Groq

## Pendiente (Post Windows — ROS2)

- Port a Ubuntu 22.04 + ROS2 Humble
- Conversión a nodo ROS2 (AtlasNode)
- Topics para integración con navegación y hardware
- HMI dashboard de datos del paciente
- Reconocimiento facial para identificación automática del paciente

---

Ver `Documentacion/DOCUMENTACION_CONVERSACIONAL_.md` para la documentación técnica completa.

