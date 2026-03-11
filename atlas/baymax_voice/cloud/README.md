# ☁️ Módulo Cloud — Servicios de IA en la Nube

## Descripción

Este módulo gestiona todos los servicios cloud de IA del sistema conversacional Atlas:
- **Speech-to-Text (STT)** — Groq Whisper
- **Large Language Model (LLM)** — Groq Llama
- **Text-to-Speech (TTS)** — Azure Neural Voice

Todos los servicios tienen sistemas de fallback robustos y están optimizados para baja latencia.

---

## Arquitectura

```
Usuario habla
    ↓
[STT: Groq Whisper]  → Transcribe audio a texto
    ↓
[LLM: Groq Llama]    → Genera respuesta conversacional
    ↓
[TTS: Azure Salome]  → Sintetiza voz natural
    ↓
Robot responde
```

---

## Módulos

### `speech_to_text.py`
**Proveedor:** Groq Whisper  
**Función:** Transcripción de voz a texto

**API:**
```python
from baymax_voice.cloud import speech_to_text as stt

# Inicializar
stt.initialize()

# Transcribir audio
audio_bytes = buffer.get_buffer_as_bytes()
text, metadata = stt.transcribe(audio_bytes, language='es')

if text:
    print(f"Texto: {text}")
    print(f"Latencia: {metadata['latency']:.2f}s")
    print(f"Modelo: {metadata['model']}")

# Cerrar
stt.shutdown()
```

**Características:**
- ✅ 100+ idiomas soportados (default: español)
- ✅ Conversión automática PCM → WAV
- ✅ 2 modelos: `whisper-large-v3` (preciso) y `whisper-large-v3-turbo` (rápido)
- ✅ Fallback: 4 niveles (2 API keys + 2 modelos + Vosk local + error)
- ✅ Latencia promedio: ~900ms
- ✅ Tier gratuito

**Configuración:**
```python
# En llm_config.py
GROQ_API_KEY = 'gsk_...'
GROQ_API_KEY_BACKUP = 'gsk_...'  # Opcional
```

---

### `groq_llm.py`
**Proveedor:** Groq (Llama 3.3 70B)  
**Función:** Generación de respuestas conversacionales

**API:**
```python
from baymax_voice.cloud import groq_llm

# Inicializar
groq_llm.initialize()

# Generar respuesta
result = groq_llm.generate_response(
    user_text="¿Cuál es mi próxima dosis?",
    patient_context=None,  # Opcional: contexto del paciente
    remember=True          # Activar memoria conversacional
)

if result['success']:
    print(result['response'])
    print(f"Tokens: {result['tokens_input']} in, {result['tokens_output']} out")
    print(f"Latencia: {result['latency']:.2f}s")
    print(f"Turnos en memoria: {result['conversation_turns']}")

# Limpiar memoria
groq_llm.clear_conversation_history()

# Cerrar
groq_llm.shutdown()
```

**Características:**
- ✅ Memoria conversacional (ventana deslizante de 4 turnos)
- ✅ Contexto dinámico del paciente (integrado con medical_db)
- ✅ Fallback: 6 niveles (2 API keys × 3 modelos)
- ✅ Optimizado: MAX_TOKENS = 70 (ahorro 30%)
- ✅ Latencia promedio: ~400ms
- ✅ Tier gratuito
- ✅ Thread-safe

**Funciones adicionales:**
- `clear_conversation_history()` — Limpia la memoria
- `get_conversation_turns()` — Número de turnos en memoria
- `_build_messages_with_history()` — Construye mensajes con contexto

**Modelos y Fallback:**
1. `llama-3.3-70b-versatile` (principal)
2. `llama-3.1-8b-instant` (fallback #1: 436ms, calidad 0.967)
3. `llama-4-scout-17b-16e-instruct` (fallback #2: 570ms, calidad 0.977)
4. `moonshotai/kimi-k2-instruct` (fallback #3: 979ms, calidad 1.000)

---

### `text_to_speech.py`
**Proveedor:** Azure Neural Voice  
**Voz:** es-CO-SalomeNeural (español colombiano, femenina)

**API:**
```python
from baymax_voice.cloud import text_to_speech as tts

# Inicializar
tts.initialize()

# Sintetizar voz
audio_bytes = tts.synthesize(
    text="Hola, soy Atlas",
    style='empatico'  # 'empatico', 'amigable', 'profesional'
)

if audio_bytes:
    # Reproducir audio
    playback.play_audio(audio_bytes, sample_rate=24000)

# Cerrar
tts.shutdown()
```

**Características:**
- ✅ Voz natural neural (Salome, español colombiano)
- ✅ Estilos emocionales: empático, amigable, profesional
- ✅ **OPTIMIZADO:** Conexión persistente (1586ms → 394ms, 75% mejora)
- ✅ Caché de frases frecuentes (opcional)
- ✅ Formato: PCM 24kHz mono
- ✅ Fallback: pyttsx3 local si Azure falla

**Configuración:**
```python
# En config/settings.py
AZURE_SPEECH_KEY = '...'
AZURE_SPEECH_REGION = 'eastus'
AZURE_TTS_VOICE = 'es-CO-SalomeNeural'
```

**Optimizaciones aplicadas (2026-03-02):**
- Synthesizer persistente (evita reconexión en cada llamada)
- Caché de frases frecuentes (hit = 0ms)
- Texto plano vs. SSML (ahorro marginal)

---

### `llm_config.py`
**Función:** Configuración centralizada del LLM

**Responsabilidades:**
- API keys de Groq
- Modelos principal y fallbacks
- Parámetros de generación (tokens, temperatura, memoria)
- System prompt médico
- Construcción de contexto del paciente

**Separación de responsabilidades:**
```
llm_config.py
    → Solo LLM (Groq, modelos, prompts, contexto paciente)

config/settings.py
    → Configuración general (audio, Azure Speech STT/TTS, paths, timeouts)
```

**Configuraciones principales:**
```python
# API Keys
GROQ_API_KEY = 'gsk_...'
GROQ_API_KEY_BACKUP = 'gsk_...'

# Modelos
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_FALLBACK_MODELS = [...]

# Generación
MAX_TOKENS = 70
TEMPERATURE = 0.7
CONVERSATION_MEMORY_TURNS = 4

# System Prompt
SYSTEM_PROMPT = """..."""
```

**Función especial:**
```python
def build_patient_context(patient_id: int = None) -> str:
    """Construye contexto del paciente desde medical_db"""
```

---

## Configuración de API Keys

### Groq (STT + LLM)

1. Crear cuenta en [Groq Console](https://console.groq.com/)
2. Generar API key desde el dashboard
3. Copiar y agregar a:
   - Variable de entorno: `GROQ_API_KEY`
   - O directamente en `llm_config.py`

**Opcional:** Segunda API key para fallback
- Variable: `GROQ_API_KEY_BACKUP`

### Azure Speech (TTS)

1. Crear recurso "Speech Services" en [Azure Portal](https://portal.azure.com/)
2. Copiar:
   - Key (de la sección "Keys and Endpoint")
   - Region (ej: eastus, westus, brazilsouth)
3. Agregar a `config/settings.py`:
   ```python
   AZURE_SPEECH_KEY = 'tu_key_aqui'
   AZURE_SPEECH_REGION = 'eastus'
   ```

---

## Sistema de Fallback

### STT (Speech-to-Text)

**4 niveles:**
1. Groq Whisper Large v3 (API key principal)
2. Groq Whisper Large v3 (API key backup)
3. Groq Whisper Turbo (más rápido, menos preciso)
4. Vosk local (offline, solo comandos predefinidos)

Si todos fallan → Error al usuario

### LLM (Conversacional)

**6 niveles (2 API keys × 3 modelos):**
1. Llama 3.3 70B (principal, API key 1)
2. Llama 3.3 70B (principal, API key 2)
3. Llama 3.1 8B instant (fallback #1, API key 1)
4. Llama 3.1 8B instant (fallback #1, API key 2)
5. Llama 4 Scout 17B (fallback #2, API key 1)
6. Llama 4 Scout 17B (fallback #2, API key 2)

Si todos fallan → Mensaje genérico de error

### TTS (Text-to-Speech)

**2 niveles:**
1. Azure Neural Voice (Salome)
2. pyttsx3 local (voz sintética de emergencia)

---

## Métricas de Rendimiento

| Servicio | Latencia Promedio | Optimización |
|----------|-------------------|--------------|
| STT (Groq Whisper) | ~900ms | Optimizado por API |
| LLM (Groq Llama) | ~400ms | MAX_TOKENS reducido |
| TTS (Azure Salome) | ~394ms | Conexión persistente |
| **Pipeline completo** | **~1.7s** | **Antes: ~4.5s (60% mejora)** |

---

## Costos Estimados

| Servicio | Tier | Costo/Mes |
|----------|------|-----------|
| Groq (STT + LLM) | Gratuito | $0 |
| Azure TTS | Pay-as-you-go | ~$5-10 |
| **Total** | | **~$5-10** |

**Notas:**
- Groq tiene límites de rate (6000 tokens/min en tier free)
- Azure cobra por caracteres sintetizados (~$16 por millón de caracteres)
- Con ~40 palabras por respuesta, alcanza para miles de conversaciones

---

## Optimizaciones Aplicadas (2026-03-02)

### LLM
- ✅ Memoria conversacional (ventana deslizante de 4 turnos)
- ✅ MAX_TOKENS: 100 → 70 (ahorro 30% sin pérdida de calidad)
- ✅ Contexto del paciente dinámico (solo info relevante)

### TTS
- ✅ Conexión persistente (1586ms → 394ms, mejora 75%)
- ✅ Caché de frases frecuentes (opcional)
- ✅ Texto plano vs SSML (ahorro marginal ~100ms)

### Pipeline Completo
- Latencia total: 4.5s → 1.7s (mejora 60%)

---

## Uso Típico

### Pipeline Completo

```python
from baymax_voice.cloud import speech_to_text as stt
from baymax_voice.cloud import groq_llm
from baymax_voice.cloud import text_to_speech as tts
from baymax_voice.cloud.llm_config import build_patient_context

# Inicializar módulos
stt.initialize()
groq_llm.initialize()
tts.initialize()

# 1. STT: Audio → Texto
audio_bytes = audio_buffer.get_buffer_as_bytes()
text, _ = stt.transcribe(audio_bytes)

# 2. LLM: Texto → Respuesta
context = build_patient_context(patient_id=1)
result = groq_llm.generate_response(text, patient_context=context)

# 3. TTS: Respuesta → Audio
audio_response = tts.synthesize(result['response'])

# 4. Reproducir
playback.play_audio(audio_response, sample_rate=24000)

# Cerrar
stt.shutdown()
groq_llm.shutdown()
tts.shutdown()
```

---

## Troubleshooting

### Errores de API Keys

**Problema:** `Authentication failed`

**Solución:**
1. Verificar que las API keys son correctas
2. Verificar que no han expirado
3. Verificar límites de rate del tier gratuito

### LLM lento

**Problema:** Latencia > 2s

**Solución:**
1. Verificar conexión a internet
2. El sistema de fallback se activa automáticamente
3. Revisar logs para ver qué modelo está usando
4. Modelo más rápido: `llama-3.1-8b-instant` (436ms)

### TTS sin audio

**Problema:** `synthesize()` retorna None

**Solución:**
1. Verificar `AZURE_SPEECH_KEY` en settings.py
2. Verificar `AZURE_SPEECH_REGION` (debe coincidir con la región del recurso)
3. Verificar que el texto no está vacío
4. El sistema usa pyttsx3 como fallback automáticamente

### Rate limit excedido

**Problema:** Error 429 de Groq

**Solución:**
- El sistema cambia automáticamente a la API key backup
- Si ambas fallan, usa modelo de fallback
- Esperar 1 minuto (límite: 6000 tokens/min)

---

## Testing

```bash
# Test individual de STT
python baymax_voice/test/test_groq_whisper.py

# Test individual de LLM
python baymax_voice/test/test_groq.py

# Test individual de TTS
python baymax_voice/test/test_tts_interactive.py

# Test de optimizaciones LLM
python baymax_voice/test/test_llm_optimizations.py

# Test completo de integración
python baymax_voice/test/test_integration_full.py
```

---

## Migración a ROS2

Los módulos cloud son 100% Python puro. La integración con ROS2 será simple:

```python
# En atlas_ros2_node.py
class AtlasNode(Node):
    def __init__(self):
        # Inicializar servicios cloud
        stt.initialize()
        groq_llm.initialize()
        tts.initialize()
    
    def process_audio(self, audio_msg):
        # STT
        text, _ = stt.transcribe(audio_msg.data)
        
        # LLM
        result = groq_llm.generate_response(text)
        
        # TTS
        audio = tts.synthesize(result['response'])
        
        # Publicar respuesta
        self.publish_audio(audio)
```

---

## Dependencias

```
groq>=0.4.0
azure-cognitiveservices-speech>=1.34.0
pyttsx3>=2.90  # Fallback TTS
numpy>=1.24.0
```

---

**Estado:** ✅ Módulos completados, optimizados y probados  
**Última actualización:** 2026-03-02

