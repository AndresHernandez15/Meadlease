"""
Test Interactivo de TTS - Escribe y Escucha
Permite escribir texto y reproducirlo mientras mide latencia.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import text_to_speech as tts
from baymax_voice.audio import playback
from baymax_voice.utils.logger import setup_logger
import time

setup_logger()


def main():
    print("\n" + "="*60)
    print("TEST INTERACTIVO: Text-to-Speech (Azure)")
    print("="*60)
    print("\nEscribe texto y escúchalo reproducido con análisis de latencia.")
    print("Escribe 'salir' para terminar.\n")

    # Inicializar TTS
    print("Inicializando TTS...")
    if not tts.initialize():
        print("✗ Error inicializando TTS")
        print("  Verifica que AZURE_SPEECH_KEY esté configurada")
        return False

    state = tts.get_state()
    print(f"✓ TTS inicializado")
    print(f"  - Voz: {state['voice']}")
    print(f"  - Región: {state['region']}")

    # Inicializar Playback
    print("\nInicializando reproducción...")
    if not playback.initialize():
        print("✗ Error inicializando playback")
        return False

    print("✓ Playback inicializado")

    print("\n" + "="*60)
    print("LISTO - Puedes empezar a escribir")
    print("="*60)

    # Loop interactivo
    iteration = 1
    total_synthesis_time = 0
    total_audio_duration = 0
    total_chars = 0

    while True:
        # Pedir texto
        print(f"\n[{iteration}] Escribe tu texto (o 'salir'):")
        user_text = input("> ").strip()

        if not user_text:
            print("⚠ Texto vacío, intenta de nuevo")
            continue

        if user_text.lower() in ['salir', 'exit', 'quit', 'q']:
            print("\n👋 Saliendo...")
            break

        # Estadísticas del texto
        char_count = len(user_text)
        word_count = len(user_text.split())
        estimated_duration = tts.estimate_duration(user_text)

        print(f"\n📝 Texto ingresado:")
        print(f"  - Caracteres: {char_count}")
        print(f"  - Palabras: {word_count}")
        print(f"  - Duración estimada: {estimated_duration:.1f}s")

        # Sintetizar
        print("\n⏱️  Sintetizando...")
        synthesis_start = time.time()

        audio_bytes = tts.synthesize(user_text)

        synthesis_time = time.time() - synthesis_start

        if not audio_bytes:
            print("✗ Error en síntesis")
            continue

        # Calcular duración real del audio
        audio_duration = len(audio_bytes) / (2 * 16000)  # PCM 16-bit 16kHz

        # Mostrar métricas de síntesis
        print(f"✓ Síntesis completada")
        print(f"\n📊 MÉTRICAS DE SÍNTESIS:")
        print(f"  - Tiempo de síntesis: {synthesis_time:.3f}s")
        print(f"  - Duración del audio: {audio_duration:.2f}s")
        print(f"  - Tamaño del audio: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
        print(f"  - Ratio (síntesis/audio): {synthesis_time/audio_duration:.2f}x")

        # Ratio interpretation
        ratio = synthesis_time / audio_duration
        if ratio < 0.5:
            speed_assessment = "⚡ Muy rápido"
        elif ratio < 1.0:
            speed_assessment = "✓ Rápido (síntesis más rápida que audio)"
        elif ratio < 1.5:
            speed_assessment = "⚠ Aceptable"
        else:
            speed_assessment = "❌ Lento"

        print(f"  - Evaluación: {speed_assessment}")

        # Reproducir
        print(f"\n▶ Reproduciendo...")
        playback_start = time.time()

        playback.play_audio(audio_bytes, sample_rate=24000)  # 24kHz para mejor calidad

        # Esperar a que termine
        while playback.is_playing():
            time.sleep(0.05)

        playback_time = time.time() - playback_start

        print(f"✓ Reproducción completada")
        print(f"\n📊 MÉTRICAS DE REPRODUCCIÓN:")
        print(f"  - Tiempo de reproducción: {playback_time:.2f}s")
        print(f"  - Diferencia vs duración esperada: {abs(playback_time - audio_duration):.2f}s")

        # Latencia total
        total_latency = synthesis_time + playback_time
        print(f"\n⏱️  LATENCIA TOTAL:")
        print(f"  - Síntesis + Reproducción: {total_latency:.2f}s")
        print(f"  - Para {word_count} palabras: {total_latency/word_count:.3f}s por palabra")

        # Actualizar estadísticas globales
        total_synthesis_time += synthesis_time
        total_audio_duration += audio_duration
        total_chars += char_count
        iteration += 1

        # Separador
        print("\n" + "-"*60)

    # Resumen final
    if iteration > 1:
        print("\n" + "="*60)
        print("📊 RESUMEN DE LA SESIÓN")
        print("="*60)
        print(f"\nTotal de pruebas: {iteration - 1}")
        print(f"Total de caracteres: {total_chars}")
        print(f"Total tiempo de síntesis: {total_synthesis_time:.2f}s")
        print(f"Total duración de audio: {total_audio_duration:.2f}s")
        print(f"\nPromedios:")
        print(f"  - Síntesis por prueba: {total_synthesis_time/(iteration-1):.2f}s")
        print(f"  - Audio por prueba: {total_audio_duration/(iteration-1):.2f}s")
        print(f"  - Chars por prueba: {total_chars/(iteration-1):.0f}")
        print(f"  - Ratio síntesis/audio: {total_synthesis_time/total_audio_duration:.2f}x")

    # Cleanup
    print("\n" + "="*60)
    print("CERRANDO")
    print("="*60)

    playback.shutdown()
    print("✓ Playback cerrado")

    tts.shutdown()
    print("✓ TTS cerrado")

    print("\n✓ Test completado exitosamente\n")
    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrumpido por el usuario")
        print("\nCerrando módulos...")
        try:
            playback.shutdown()
            tts.shutdown()
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

