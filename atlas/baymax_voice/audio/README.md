# 🎤 Módulo Audio — Pipeline de Captura y Procesamiento

## Descripción

Este módulo maneja toda la captura, procesamiento y reproducción de audio del sistema conversacional Atlas. Implementa un pipeline completo de audio con detección de voz, filtrado de ruido y buffering thread-safe.

---

## Módulos

### `capture.py`
**Captura de audio desde micrófono usando PyAudio**

- **Configuración:** 16kHz, mono, frames de 20ms
- **Formato:** PCM 16-bit
- **Funciones principales:**
  - `initialize()` — Inicializa PyAudio y abre stream
  - `get_audio_frame()` — Captura un frame de audio
  - `is_running()` — Verifica si el stream está activo
  - `shutdown()` — Cierra stream y libera recursos

---

### `vad.py`
**Voice Activity Detection usando WebRTC VAD**

Detecta automáticamente cuándo el usuario habla y cuándo hay silencio.

- **Motor:** WebRTC VAD (Google)
- **Agresividad:** Configurable 0-3 (default: 2)
- **Estados:** `speech_start`, `speech_ongoing`, `speech_end`, `silence`
- **Funciones principales:**
  - `initialize()` — Inicializa WebRTC VAD
  - `process_frame(audio_frame)` — Procesa frame y retorna estado
  - `is_speech_active()` — Indica si hay voz activa
  - `reset()` — Resetea contador de silencio

**Configuración:**
```python
VAD_AGGRESSIVENESS = 2        # 0-3 (mayor = más agresivo filtrando silencio)
VAD_SILENCE_DURATION = 1.5    # Segundos de silencio para detectar fin de voz
```

---

### `noise_filter.py`
**Filtro de ruido adaptativo basado en calibración del ambiente**

Reduce ruido de fondo constante (ventilador, AC, ruido eléctrico).

- **Método:** Calibración inicial + sustracción espectral
- **Funciones principales:**
  - `calibrate_noise(capture_module, duration)` — Calibra perfil de ruido
  - `apply_filter(audio_frame)` — Aplica filtro al frame
  - `is_calibrated()` — Verifica si está calibrado
  - `get_noise_level()` — Retorna nivel RMS de ruido

**Proceso de calibración:**
1. Se pide SILENCIO al usuario
2. Se captura audio durante N segundos
3. Se calcula perfil estadístico del ruido (mean, std, rms)
4. Se usa para filtrar frames posteriores

**Configuración:**
```python
NOISE_CALIBRATION_DURATION = 2.0      # Segundos de calibración
NOISE_THRESHOLD_MULTIPLIER = 1.5      # Multiplicador de threshold
NOISE_REDUCTION_FACTOR = 0.3          # Factor de reducción (0.0-1.0)
```

---

### `playback.py`
**Reproducción de audio usando sounddevice**

Reproduce respuestas de voz del robot y archivos de audio.

- **Funciones principales:**
  - `initialize()` — Inicializa sistema de audio de salida
  - `play_audio(audio_data, sample_rate, blocking)` — Reproduce audio raw
  - `play_file(filepath, blocking)` — Reproduce archivo WAV
  - `set_volume(level)` — Ajusta volumen (0.0-1.0)
  - `is_playing()` — Verifica si hay audio reproduciéndose
  - `wait_until_done()` — Espera a que termine la reproducción
  - `stop()` — Detiene reproducción actual
  - `shutdown()` — Cierra sistema de audio

**Características:**
- Soporta audio raw (bytes o numpy array)
- Soporta archivos WAV (mono/stereo)
- Control de volumen dinámico
- Modo blocking/non-blocking

---

### `audio_buffer.py`
**Buffer de audio thread-safe para almacenamiento temporal**

Almacena frames de audio mientras el usuario habla, para enviar al STT.

- **Características:**
  - Thread-safe (usa `Lock`)
  - Tamaño máximo configurable
  - Auto-descarte de audio antiguo si hay overflow
  
- **Funciones principales:**
  - `start_recording()` — Inicia grabación (limpia buffer)
  - `stop_recording()` — Detiene grabación
  - `append_frame(audio_frame)` — Agrega frame al buffer
  - `get_buffer_as_bytes()` — Retorna buffer como bytes (para STT)
  - `get_buffer_as_numpy()` — Retorna buffer como numpy array
  - `get_duration_seconds()` — Duración del audio almacenado
  - `clear_buffer()` — Limpia buffer manualmente
  - `is_recording()` — Verifica si está grabando
  - `get_buffer_size()` — Número de samples en buffer

**Configuración:**
```python
MAX_BUFFER_DURATION = 30.0    # Máximo de segundos a almacenar
```

---

## Flujo de Audio en el Sistema

```
[Micrófono]
    ↓
[capture.get_audio_frame()]  ← Captura 20ms
    ↓
[noise_filter.apply_filter()] ← Reduce ruido de fondo
    ↓
[vad.process_frame()]         ← Detecta voz/silencio
    ↓
    ├─ speech_start → [audio_buffer.start_recording()]
    ├─ speech_ongoing → [audio_buffer.append_frame()]
    └─ speech_end → [audio_buffer.stop_recording()]
                       ↓
                [Enviar buffer al STT]
```

---

## Configuración Global

Todas las configuraciones están centralizadas en `config/settings.py`:

```python
# Audio básico
SAMPLE_RATE = 16000           # Hz (frecuencia de muestreo)
CHANNELS = 1                  # Mono
CHUNK_SIZE = 320              # Samples por frame (20ms @ 16kHz)

# VAD
VAD_AGGRESSIVENESS = 2        # 0-3
VAD_SILENCE_DURATION = 1.5    # Segundos

# Noise filter
NOISE_CALIBRATION_DURATION = 2.0
NOISE_THRESHOLD_MULTIPLIER = 1.5
NOISE_REDUCTION_FACTOR = 0.3

# Buffer
MAX_BUFFER_DURATION = 30.0    # Segundos
```

---

## Uso Típico

### Inicialización

```python
import baymax_voice.audio.capture as capture
import baymax_voice.audio.vad as vad
import baymax_voice.audio.noise_filter as noise_filter
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.audio.playback as playback

# Inicializar módulos
capture.initialize()
vad.initialize()
playback.initialize()

# Calibrar filtro de ruido
noise_filter.calibrate_noise(capture, duration=2.0)
```

### Loop de Captura con VAD

```python
while running:
    # Capturar frame
    frame = capture.get_audio_frame()
    
    # Filtrar ruido
    filtered = noise_filter.apply_filter(frame)
    
    # Detectar voz
    vad_state = vad.process_frame(filtered)
    
    if vad_state == 'speech_start':
        audio_buffer.start_recording()
    
    if vad.is_speech_active():
        audio_buffer.append_frame(filtered)
    
    if vad_state == 'speech_end':
        # Usuario terminó de hablar
        audio_bytes = audio_buffer.get_buffer_as_bytes()
        # Enviar a STT...
```

### Reproducción de Respuesta

```python
# Reproducir audio sintetizado
playback.play_audio(tts_audio_bytes, sample_rate=24000, blocking=True)

# Reproducir archivo de confirmación
playback.play_file('data/audio/confirmation.wav', blocking=False)
```

### Shutdown

```python
capture.shutdown()
playback.shutdown()
```

---

## Dependencias

- `pyaudio` — Captura de micrófono
- `webrtcvad` — Voice Activity Detection
- `sounddevice` — Reproducción de audio
- `numpy` — Procesamiento de arrays
- `wave` — Lectura de archivos WAV

---

## Notas de Implementación

### Thread Safety
- `audio_buffer.py` usa `Lock` para acceso thread-safe
- Diseñado para ser usado desde múltiples threads (audio thread, FSM thread)

### Manejo de Errores
- Todos los módulos tienen manejo robusto de excepciones
- Los errores se logean pero no crashean el sistema
- Funciones retornan `None` o `False` en caso de error

### Optimizaciones
- Frames pequeños (20ms) para baja latencia
- Filtro de ruido ligero (no afecta rendimiento)
- Buffer con límite de tamaño (previene memory leaks)

---

## Testing

Ver tests en `baymax_voice/test/`:
- `test_vad.py` — Prueba VAD interactivo
- `test_audio_conversion.py` — Prueba conversiones de formato

---

**Estado:** ✅ Módulos completados y probados  
**Última actualización:** 2026-03-02

