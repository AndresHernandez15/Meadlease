"""
Test del módulo Text-to-Speech (Azure).
Prueba la síntesis de texto a audio con Azure TTS.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import text_to_speech as tts
from baymax_voice.audio import playback
from baymax_voice.utils.logger import setup_logger
import wave
import time

setup_logger()


def test_tts_initialization():
    """Test 1: Inicialización del módulo TTS"""
    print("\n" + "="*60)
    print("TEST 1: Inicialización de TTS")
    print("="*60)

    success = tts.initialize()

    if success:
        print("✓ TTS inicializado correctamente")

        state = tts.get_state()
        print(f"  - Región: {state['region']}")
        print(f"  - Voz: {state['voice']}")
        print(f"  - Formato: {state['format']}")
        print(f"  - Inicializado: {state['initialized']}")

        voice_info = tts.get_voice_info()
        print(f"\nInformación de la voz:")
        print(f"  - Nombre: {voice_info['voice']}")
        print(f"  - Idioma: {voice_info['language']}")
        print(f"  - Género: {voice_info['gender']}")
        print(f"  - Estilo: {voice_info['style']}")

        return True
    else:
        print("✗ Error inicializando TTS")
        print("  NOTA: Verifica que AZURE_SPEECH_KEY esté configurada en settings.py")
        return False


def test_tts_idempotence():
    """Test 2: Idempotencia de initialize()"""
    print("\n" + "="*60)
    print("TEST 2: Idempotencia de initialize()")
    print("="*60)

    for i in range(3):
        success = tts.initialize()
        if success:
            print(f"  ✓ Llamada {i+1}: OK")
        else:
            print(f"  ✗ Llamada {i+1}: FALLÓ")
            return False

    print("✓ Idempotencia verificada")
    return True


def test_tts_simple_synthesis():
    """Test 3: Síntesis simple de texto"""
    print("\n" + "="*60)
    print("TEST 3: Síntesis simple de texto")
    print("="*60)

    test_text = "Hola, soy Baymax, tu asistente médico personal."

    print(f"\nTexto a sintetizar: \"{test_text}\"")
    print(f"Longitud: {len(test_text)} caracteres")

    # Estimar duración
    estimated_duration = tts.estimate_duration(test_text)
    print(f"Duración estimada: {estimated_duration:.1f}s")

    print("\nSintetizando...")
    start_time = time.time()

    audio_bytes = tts.synthesize(test_text)

    synthesis_time = time.time() - start_time

    if audio_bytes:
        print(f"✓ Síntesis exitosa")
        print(f"  - Audio generado: {len(audio_bytes)} bytes")
        print(f"  - Tiempo de síntesis: {synthesis_time:.2f}s")

        # Calcular duración real del audio
        # PCM 16-bit mono 16kHz = 2 bytes por muestra, 16000 muestras/segundo
        audio_duration = len(audio_bytes) / (2 * 16000)
        print(f"  - Duración del audio: {audio_duration:.2f}s")

        # Guardar audio para inspección
        save_audio_wav(audio_bytes, 'test_tts_simple.wav')
        print(f"  - Audio guardado: test_tts_simple.wav")

        return audio_bytes
    else:
        print("✗ Síntesis falló")
        return None


def test_tts_medical_phrases():
    """Test 4: Frases médicas comunes"""
    print("\n" + "="*60)
    print("TEST 4: Frases médicas comunes")
    print("="*60)

    phrases = [
        "Por favor, consulta con un médico profesional.",
        "Es importante que monitorees tu presión arterial regularmente.",
        "¿Tienes algún otro síntoma que debamos revisar?",
        "Recuerda tomar tus medicamentos según la prescripción médica.",
    ]

    for i, phrase in enumerate(phrases, 1):
        print(f"\n{i}. \"{phrase}\"")

        audio_bytes = tts.synthesize(phrase)

        if audio_bytes:
            print(f"   ✓ {len(audio_bytes)} bytes")
        else:
            print(f"   ✗ Falló")
            return False

    print("\n✓ Todas las frases sintetizadas exitosamente")
    return True


def test_tts_error_handling():
    """Test 5: Manejo de errores"""
    print("\n" + "="*60)
    print("TEST 5: Manejo de errores")
    print("="*60)

    # Texto None
    print("\n1. Probando texto None...")
    result = tts.synthesize(None)
    if result is None:
        print("   ✓ Maneja None correctamente")
    else:
        print("   ✗ No manejó None correctamente")
        return False

    # Texto vacío
    print("\n2. Probando texto vacío...")
    result = tts.synthesize("")
    if result is None:
        print("   ✓ Maneja texto vacío correctamente")
    else:
        print("   ✗ No manejó texto vacío correctamente")
        return False

    # Texto muy largo
    print("\n3. Probando texto muy largo (>1000 chars)...")
    long_text = "Hola. " * 200  # ~1200 caracteres
    result = tts.synthesize(long_text)
    if result is not None:
        print(f"   ✓ Truncó y sintetizó correctamente ({len(result)} bytes)")
    else:
        print("   ✗ No manejó texto largo correctamente")
        return False

    print("\n✓ Manejo de errores verificado")
    return True


def test_tts_playback():
    """Test 6: Reproducción de audio (opcional, si tienes bocinas)"""
    print("\n" + "="*60)
    print("TEST 6: Reproducción de audio")
    print("="*60)

    test_text = "Este es un test de reproducción de audio."

    print(f"Texto: \"{test_text}\"")
    print("\nSintetizando...")

    audio_bytes = tts.synthesize(test_text)

    if not audio_bytes:
        print("✗ No se pudo sintetizar")
        return False

    print(f"✓ Audio sintetizado: {len(audio_bytes)} bytes")

    # Preguntar si quiere reproducir
    print("\n¿Deseas reproducir el audio? (s/n): ", end='')
    choice = input().lower().strip()

    if choice == 's':
        print("\nInicializando reproducción...")

        if not playback.initialize():
            print("✗ Error inicializando playback")
            return False

        print("▶ Reproduciendo...")
        playback.play_audio(audio_bytes)

        # Esperar a que termine
        while playback.is_playing():
            time.sleep(0.1)

        print("✓ Reproducción completada")
        playback.shutdown()

        return True
    else:
        print("⊘ Reproducción omitida")
        return True


def test_tts_available_voices():
    """Test 7: Voces disponibles"""
    print("\n" + "="*60)
    print("TEST 7: Voces disponibles")
    print("="*60)

    voices = tts.get_available_voices()

    print(f"\nVoces disponibles: {len(voices)}")
    for i, voice in enumerate(voices, 1):
        print(f"  {i}. {voice}")

    print("\n✓ Voces listadas correctamente")
    return True


def save_audio_wav(pcm_bytes, filename):
    """
    Guarda audio PCM raw como archivo WAV.
    """
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)          # Mono
        wf.setsampwidth(2)          # 16-bit = 2 bytes
        wf.setframerate(16000)      # 16kHz
        wf.writeframes(pcm_bytes)


def main():
    print("\n" + "="*60)
    print("TEST COMPLETO: Text-to-Speech (Azure)")
    print("="*60)

    # Test 1: Inicialización
    if not test_tts_initialization():
        return False

    # Test 2: Idempotencia
    if not test_tts_idempotence():
        return False

    # Test 3: Síntesis simple
    if not test_tts_simple_synthesis():
        return False

    # Test 4: Frases médicas
    if not test_tts_medical_phrases():
        return False

    # Test 5: Manejo de errores
    if not test_tts_error_handling():
        return False

    # Test 6: Reproducción (opcional)
    test_tts_playback()

    # Test 7: Voces disponibles
    if not test_tts_available_voices():
        return False

    # Shutdown
    print("\n" + "="*60)
    print("SHUTDOWN")
    print("="*60)
    tts.shutdown()
    print("✓ TTS cerrado correctamente")

    # Resumen
    print("\n" + "="*60)
    print("✓ TODOS LOS TESTS PASARON")
    print("="*60)
    print("\nArchivos generados:")
    print("  - test_tts_simple.wav")
    print("\nPuedes reproducirlos con cualquier reproductor de audio.")
    print("\n")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

