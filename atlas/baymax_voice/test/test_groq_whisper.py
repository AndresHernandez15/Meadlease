"""
Test simple de Groq Whisper - Sin micrófono
Verifica la inicialización y funciones básicas.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import speech_to_text as stt
from baymax_voice.utils.logger import setup_logger

setup_logger()


def main():
    print("\n" + "="*60)
    print("TEST SIMPLE: Speech-to-Text (Groq Whisper)")
    print("="*60)

    # Test 1: Inicialización
    print("\n1. Probando inicialización...")
    success = stt.initialize()

    if success:
        print("✓ STT inicializado correctamente")
        state = stt.get_state()
        print(f"  - Cliente principal: {state['primary_client']}")
        print(f"  - Cliente backup: {state['backup_client']}")
        print(f"  - Modelos: {state['models']}")
        print(f"  - Idioma default: {state['default_language']}")
    else:
        print("✗ Error inicializando STT")
        print("  NOTA: Verifica que GROQ_API_KEY esté configurada")
        return False

    # Test 2: Idempotencia
    print("\n2. Probando idempotencia (llamar initialize() 3 veces)...")
    for i in range(3):
        success = stt.initialize()
        if success:
            print(f"  ✓ Llamada {i+1}: OK")
        else:
            print(f"  ✗ Llamada {i+1}: FALLÓ")
            return False

    # Test 3: Estado del módulo
    print("\n3. Verificando estado del módulo...")
    is_init = stt.is_initialized()
    print(f"  - is_initialized(): {is_init}")

    # Test 4: Modelos disponibles
    print("\n4. Modelos disponibles...")
    models = stt.get_available_models()
    print(f"  - Total modelos: {len(models)}")
    for model in models:
        print(f"    • {model}")

    # Test 5: Idiomas soportados
    print("\n5. Idiomas soportados...")
    languages = stt.get_supported_languages()
    print(f"  - Total idiomas principales: {len(languages)}")
    print(f"  - Idioma español (es): {'✓' if 'es' in languages else '✗'}")

    # Test 6: Manejo de errores
    print("\n6. Probando manejo de errores...")

    print("  - Audio None:")
    text, meta = stt.transcribe(None)
    if text is None and not meta.get('success'):
        print("    ✓ Maneja correctamente")
    else:
        print("    ✗ No manejó correctamente")
        return False

    print("  - Audio vacío:")
    text, meta = stt.transcribe(b'')
    if text is None and not meta.get('success'):
        print("    ✓ Maneja correctamente")
    else:
        print("    ✗ No manejó correctamente")
        return False

    # Test 7: Shutdown
    print("\n7. Probando shutdown...")
    stt.shutdown()
    print("  ✓ Shutdown completado")

    # Resumen
    print("\n" + "="*60)
    print("✓ TODOS LOS TESTS PASARON")
    print("="*60)
    print("\n")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

