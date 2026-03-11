"""
Test simple de TTS - Sin reproducción
Verifica la inicialización y funciones básicas.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import text_to_speech as tts
from baymax_voice.utils.logger import setup_logger

setup_logger()


def main():
    print("\n" + "="*60)
    print("TEST SIMPLE: Text-to-Speech (Azure)")
    print("="*60)

    # Test 1: Inicialización
    print("\n1. Probando inicialización...")
    success = tts.initialize()

    if success:
        print("✓ TTS inicializado correctamente")
        state = tts.get_state()
        print(f"  - Región: {state['region']}")
        print(f"  - Voz: {state['voice']}")
        print(f"  - Formato: {state['format']}")
        print(f"  - Inicializado: {state['initialized']}")
    else:
        print("✗ Error inicializando TTS")
        print("  NOTA: Verifica que AZURE_SPEECH_KEY esté configurada en settings.py")
        return False

    # Test 2: Idempotencia
    print("\n2. Probando idempotencia (llamar initialize() 3 veces)...")
    for i in range(3):
        success = tts.initialize()
        if success:
            print(f"  ✓ Llamada {i+1}: OK")
        else:
            print(f"  ✗ Llamada {i+1}: FALLÓ")
            return False

    # Test 3: Estado del módulo
    print("\n3. Verificando estado del módulo...")
    is_init = tts.is_initialized()
    print(f"  - is_initialized(): {is_init}")

    # Test 4: Información de voz
    print("\n4. Información de la voz...")
    voice_info = tts.get_voice_info()
    print(f"  - Nombre: {voice_info['voice']}")
    print(f"  - Idioma: {voice_info['language']}")
    print(f"  - Género: {voice_info['gender']}")
    print(f"  - Estilo: {voice_info['style']}")

    # Test 5: Voces disponibles
    print("\n5. Voces disponibles...")
    voices = tts.get_available_voices()
    print(f"  - Total voces: {len(voices)}")
    for voice in voices:
        print(f"    • {voice}")

    # Test 6: Síntesis simple
    print("\n6. Probando síntesis simple...")
    test_text = "Hola, soy Baymax, tu asistente médico."
    print(f"  - Texto: \"{test_text}\"")

    audio_bytes = tts.synthesize(test_text)

    if audio_bytes:
        print(f"  ✓ Síntesis exitosa: {len(audio_bytes)} bytes")

        # Calcular duración
        audio_duration = len(audio_bytes) / (2 * 16000)
        print(f"  - Duración del audio: {audio_duration:.2f}s")
    else:
        print("  ✗ Síntesis falló")
        return False

    # Test 7: Estimación de duración
    print("\n7. Probando estimación de duración...")
    test_phrases = [
        "Hola.",
        "¿Cómo estás hoy?",
        "Recuerda tomar tus medicamentos según la prescripción médica.",
    ]

    for phrase in test_phrases:
        estimated = tts.estimate_duration(phrase)
        print(f"  - \"{phrase}\" → ~{estimated:.1f}s")

    # Test 8: Manejo de errores
    print("\n8. Probando manejo de errores...")

    print("  - Texto None:")
    result = tts.synthesize(None)
    if result is None:
        print("    ✓ Maneja correctamente")
    else:
        print("    ✗ No manejó correctamente")
        return False

    print("  - Texto vacío:")
    result = tts.synthesize("")
    if result is None:
        print("    ✓ Maneja correctamente")
    else:
        print("    ✗ No manejó correctamente")
        return False

    print("  - Texto largo (>1000 chars):")
    long_text = "Hola. " * 200
    result = tts.synthesize(long_text)
    if result is not None:
        print(f"    ✓ Trunca y sintetiza correctamente")
    else:
        print("    ✗ No manejó correctamente")
        return False

    # Test 9: Shutdown
    print("\n9. Probando shutdown...")
    tts.shutdown()
    print("  ✓ Shutdown completado")

    # Resumen
    print("\n" + "="*60)
    print("✓ TODOS LOS TESTS PASARON")
    print("="*60)
    print("\nPara test completo con reproducción:")
    print("  python baymax_voice\\test\\test_tts.py")
    print("\n")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrumpido")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

