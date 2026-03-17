# Tests del Sistema Atlas

Suite de pruebas para validar el funcionamiento del sistema conversacional.
Última actualización: 2026-03-03

---

## Orden Recomendado de Ejecución

```bash
# 1. Verificación rápida sin hardware (~10s)
python -m baymax_voice.test.test_quick_system

# 2. Módulos de audio
python -m baymax_voice.test.test_vad
python -m baymax_voice.test.test_wake_word
python -m baymax_voice.test.test_commands

# 3. Servicios cloud
python -m baymax_voice.test.test_groq_whisper
python -m baymax_voice.test.test_groq
python -m baymax_voice.test.test_groq_fallback
python -m baymax_voice.test.test_tts
python -m baymax_voice.test.test_tts_interactive

# 4. Integración con base de datos
python -m baymax_voice.test.test_context_prompt

# 5. Validaciones específicas
python -m baymax_voice.test.test_camila_validation
python -m baymax_voice.test.test_confirmation_audio

# 6. Pipeline completo interactivo (~5-10 min)
python -m baymax_voice.test.test_integration_full
```

---

## Tests de Unidad

### test_quick_system.py
Verifica la inicialización correcta de todos los módulos sin intervención del usuario.
No requiere micrófono ni hablar. Duración ~10 segundos.

### test_vad.py
Prueba el Voice Activity Detection (WebRTC VAD).
Requiere micrófono. El usuario habla y el test verifica la detección de inicio/fin de voz.

### test_wake_word.py
Prueba la detección de la wake word "Atlas" con Porcupine.
Requiere micrófono. El usuario dice "Atlas" cuando se solicita.

### test_commands.py
Prueba el reconocimiento de comandos locales con Vosk.
Requiere micrófono. El usuario prueba los 9 comandos disponibles.

### test_groq_whisper.py
Prueba el módulo STT con Groq Whisper (transcripción desde archivo de audio).
No requiere micrófono. Requiere GROQ_API_KEY.

### test_groq.py
Prueba el LLM conversacional con Groq Llama 3.3 70B.
No requiere micrófono. Requiere GROQ_API_KEY.

### test_groq_fallback.py
Prueba el sistema de fallback con múltiples API keys y modelos.
Requiere GROQ_API_KEY y GROQ_API_KEY_BACKUP.

### test_tts.py
Prueba básica de síntesis de voz con Azure Neural TTS (Camila).
Requiere altavoces y AZURE_SPEECH_KEY.

### test_tts_simple.py
Prueba simplificada de TTS sin interacción. Sintetiza una frase y la guarda en disco.

### test_tts_interactive.py
Prueba interactiva de TTS — el usuario introduce texto y lo escucha sintetizado.
Útil para probar textos médicos y verificar la voz de Camila.

### test_context_prompt.py
Valida que el contexto de la base de datos (próxima dosis, signos vitales)
se genera correctamente y llega al LLM. Requiere patient.db poblado.

```bash
python scripts/populate_test_db.py  # poblar BD primero
```

### test_camila_validation.py
Valida que Camila (es-PE-CamilaNeural) está configurada y sintetiza
3 frases de prueba médicas. Requiere AZURE_SPEECH_KEY.

### test_confirmation_audio.py
Reproduce data/audio/confirmation.wav (Camila diciendo "¿Sí?") para
verificar que el audio de confirmación suena correcto.

### test_integration_full.py
Test exhaustivo del pipeline completo: wake word → escucha → STT → LLM → TTS.
Requiere micrófono, altavoces, internet y todas las API keys.
Duración: ~5-10 minutos.

### test_audio_conversion.py
Prueba de conversión de formatos de audio (PCM, WAV, sample rates).
No requiere hardware ni API keys.

### test_llm_optimizations.py
Prueba las optimizaciones del LLM: MAX_TOKENS, memoria conversacional,
contexto del paciente. No requiere micrófono.

---

## Benchmarks

### benchmark_latency.py
Mide latencias reales de cada componente del pipeline.
Genera benchmark_latency_results.json.

### benchmark_llm_models.py
Compara rendimiento entre modelos de Groq disponibles.
Genera benchmark_llm_models_results.json.

### benchmark_quality_llm.py
Evalúa calidad de respuestas del LLM con criterios médicos.
Genera benchmark_quality_results.json.

---

## Utilidades

### list_groq_models.py
Lista todos los modelos disponibles en la API de Groq.
Útil para actualizar la lista de fallbacks en groq_llm.py.

---

## Requisitos

**Hardware:** Micrófono + altavoces (solo tests interactivos)

**API keys en settings.py:**
```
GROQ_API_KEY, GROQ_API_KEY_BACKUP
AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
PORCUPINE_ACCESS_KEY
```

