"""
Test de conversión de audio para Groq Whisper.
Verifica que el audio se convierte correctamente a WAV.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import speech_to_text as stt
from baymax_voice.audio import capture, audio_buffer
from baymax_voice.utils.logger import setup_logger
import wave
import time

setup_logger()


def test_audio_conversion():
    """Prueba la conversión de PCM a WAV"""
    print("\n" + "="*60)
    print("TEST: Conversión PCM → WAV para STT")
    print("="*60)

    # Capturar 3 segundos de audio
    print("\n📢 Por favor habla durante 3 segundos...")
    print("   Di algo como: 'Hola Baymax, esto es una prueba'")

    if not capture.initialize():
        print("✗ Error inicializando captura")
        return False

    audio_buffer.start_recording()

    start_time = time.time()
    duration = 3.0

    try:
        while time.time() - start_time < duration:
            frame = capture.get_audio_frame()
            if frame is not None:
                audio_buffer.append_frame(frame)

            remaining = duration - (time.time() - start_time)
            print(f"\rCapturando... {remaining:.1f}s", end='', flush=True)

        print("\n✓ Captura completada\n")

    except KeyboardInterrupt:
        print("\n⚠ Interrumpido")
        return False
    finally:
        audio_buffer.stop_recording()
        capture.shutdown()

    # Obtener audio capturado
    pcm_bytes = audio_buffer.get_buffer_as_bytes()
    print(f"Audio PCM: {len(pcm_bytes)} bytes")

    # Convertir a WAV y guardar para inspección
    print("\n1. Convirtiendo PCM a WAV...")
    wav_buffer = stt._convert_pcm_to_wav(pcm_bytes, sample_rate=16000, channels=1, sample_width=2)

    # Guardar WAV a disco para verificar
    with open('test_audio_groq.wav', 'wb') as f:
        f.write(wav_buffer.getvalue())

    print(f"✓ WAV guardado: test_audio_groq.wav")
    print(f"  Tamaño: {len(wav_buffer.getvalue())} bytes")

    # Verificar el WAV
    print("\n2. Verificando formato WAV...")
    with wave.open('test_audio_groq.wav', 'rb') as wf:
        print(f"  - Canales: {wf.getnchannels()}")
        print(f"  - Sample width: {wf.getsampwidth()} bytes")
        print(f"  - Frame rate: {wf.getframerate()} Hz")
        print(f"  - Frames: {wf.getnframes()}")
        print(f"  - Duración: {wf.getnframes() / wf.getframerate():.2f}s")

    print("✓ WAV válido")

    # Intentar transcribir con Groq
    print("\n3. Intentando transcribir con STT...")

    if not stt.initialize():
        print("✗ Error inicializando STT")
        return False

    # Leer el WAV que guardamos
    with open('test_audio_groq.wav', 'rb') as f:
        wav_bytes = f.read()

    print(f"WAV leído: {len(wav_bytes)} bytes")

    # Transcribir
    text, metadata = stt.transcribe(wav_bytes, language='es')

    if text:
        print(f"\n✓ ÉXITO!")
        print(f"  📝 Texto: \"{text}\"")
        print(f"  🔧 Modelo: {metadata['model']}")
        print(f"  ⚡ Latencia: {metadata['latency']:.3f}s")
        print(f"  🔑 API Key: {metadata['api_key_used']}")
        return True
    else:
        print(f"\n✗ Falló: {metadata.get('error')}")
        return False


if __name__ == '__main__':
    try:
        success = test_audio_conversion()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

