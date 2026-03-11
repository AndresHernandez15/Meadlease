"""
Genera el nuevo audio de confirmación con la voz de Camila.
Crea: confirmation.wav - Camila diciendo "¿Sí?" como pregunta
"""
import sys
from pathlib import Path
import wave
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import azure.cognitiveservices.speech as speechsdk
from baymax_voice.config import settings

print('=' * 80)
print('🎙️  GENERANDO NUEVO AUDIO DE CONFIRMACIÓN - CAMILA')
print('=' * 80)

# Configurar Azure Speech
speech_config = speechsdk.SpeechConfig(
    subscription=settings.AZURE_SPEECH_KEY,
    region=settings.AZURE_SPEECH_REGION
)

# Usar la voz de Camila
speech_config.speech_synthesis_voice_name = 'es-PE-CamilaNeural'

# Formato de audio: 24kHz mono PCM (mismo que el sistema)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
)

# Crear synthesizer
synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config,
    audio_config=None
)

print('\n📝 Generando audio: Camila diciendo "¿Sí?" como pregunta')
print('─' * 80)

# SSML para que suene como pregunta (tono ascendente al final)
ssml_text = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-PE">
    <voice name="es-PE-CamilaNeural">
        <prosody pitch="+5%" rate="0.95">
            ¿Sí?
        </prosody>
    </voice>
</speak>'''

print('Configuración:')
print('  • Voz: Camila (Perú)')
print('  • Texto: "¿Sí?"')
print('  • Pitch: +5% (tono de pregunta)')
print('  • Rate: 0.95 (ligeramente más lenta)')
print()

try:
    print('Sintetizando...')
    result = synthesizer.speak_ssml_async(ssml_text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = result.audio_data
        print(f'✓ Síntesis exitosa: {len(audio_data)} bytes')

        # Guardar como WAV
        output_path = PROJECT_ROOT / 'data' / 'audio' / 'confirmation.wav'

        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convertir bytes a array numpy
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Guardar como WAV
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(24000)  # 24kHz
            wav_file.writeframes(audio_array.tobytes())

        print(f'\n✓ Archivo guardado: {output_path}')

        # Información del archivo
        duration = len(audio_array) / 24000
        print(f'\n📊 Información del archivo:')
        print(f'  • Duración: {duration:.2f}s')
        print(f'  • Sample rate: 24000 Hz')
        print(f'  • Canales: 1 (mono)')
        print(f'  • Formato: PCM 16-bit')
        print(f'  • Tamaño: {len(audio_data)} bytes')

        print('\n' + '=' * 80)
        print('✅ AUDIO DE CONFIRMACIÓN GENERADO EXITOSAMENTE')
        print('=' * 80)
        print('\nCamila ahora dirá "¿Sí?" cuando detecte la wake word "atlas".')
        print('El nuevo archivo reemplazó al anterior en data/audio/confirmation.wav')

    else:
        print(f'✗ Error en síntesis: {result.reason}')
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f'  Razón: {cancellation.reason}')
            if cancellation.error_details:
                print(f'  Detalles: {cancellation.error_details}')

except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)

print('\n' + '=' * 80)

