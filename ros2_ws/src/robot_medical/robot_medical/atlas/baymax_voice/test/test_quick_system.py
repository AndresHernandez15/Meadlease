"""
Test Rápido de Sistema - Baymax
Prueba automática de módulos sin intervención del usuario
"""
import sys
from pathlib import Path

# Agregar ruta del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from baymax_voice.config import settings
from baymax_voice.utils.logger import setup_logger, get_logger
from baymax_voice.utils.events import put_event, get_event, clear_events, queue_size
import baymax_voice.audio.capture as capture
import baymax_voice.audio.vad as vad
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.audio.playback as playback
import baymax_voice.local.wake_word as wake_word
import baymax_voice.local.commands as commands

setup_logger(level='INFO')
logger = get_logger('test.quick')


def test_module(name, test_func):
    """Ejecuta un test y reporta resultado"""
    try:
        logger.info(f'Testing {name}...')
        result = test_func()
        if result:
            logger.info(f'  ✓ {name} OK')
            return True
        else:
            logger.error(f'  ✗ {name} FAILED')
            return False
    except Exception as e:
        logger.error(f'  ✗ {name} ERROR: {e}')
        return False


def main():
    logger.info('=' * 60)
    logger.info('TEST RÁPIDO DE SISTEMA BAYMAX')
    logger.info('=' * 60)
    logger.info('')

    results = {}

    # Test 1: Validación de configuración
    def test_config():
        errors = settings.validate_paths()
        return len(errors) == 0

    results['Configuración'] = test_module('Configuración', test_config)

    # Test 2: Sistema de eventos
    def test_events():
        clear_events()
        put_event('TEST', data={'test': True}, source='test')
        event = get_event(timeout=0.1)
        return event is not None and event.type == 'TEST'

    results['Sistema de eventos'] = test_module('Sistema de eventos', test_events)

    # Test 3: Captura de audio
    def test_capture():
        success = capture.initialize()
        if not success:
            return False
        frame = capture.get_audio_frame()
        return frame is not None and len(frame) == settings.CHUNK_SIZE

    results['Captura de audio'] = test_module('Captura de audio', test_capture)

    # Test 4: VAD
    def test_vad_init():
        return vad.initialize()

    results['VAD'] = test_module('VAD', test_vad_init)

    # Test 5: Buffer de audio
    def test_buffer():
        audio_buffer.start_recording()
        frame = capture.get_audio_frame()
        if frame is not None:
            audio_buffer.append_frame(frame)
        size = audio_buffer.get_buffer_size()
        audio_buffer.stop_recording()
        audio_buffer.clear_buffer()
        return size > 0

    results['Buffer de audio'] = test_module('Buffer de audio', test_buffer)

    # Test 6: Playback
    def test_playback_init():
        success = playback.initialize()
        if success:
            playback.set_volume(0.5)
            return playback.get_volume() == 0.5
        return False

    results['Playback'] = test_module('Playback', test_playback_init)

    # Test 7: Wake word
    def test_wake_word_init():
        return wake_word.initialize(
            access_key=settings.PORCUPINE_ACCESS_KEY,
            keyword_path=settings.PORCUPINE_KEYWORD_PATH,
            model_path=settings.PORCUPINE_MODEL_PATH,
            sensitivity=settings.PORCUPINE_SENSITIVITY
        )

    results['Wake word'] = test_module('Wake word', test_wake_word_init)

    # Test 8: Comandos
    def test_commands_init():
        return commands.initialize(settings.VOSK_MODEL_PATH)

    results['Comandos'] = test_module('Comandos', test_commands_init)

    # Cleanup
    logger.info('')
    logger.info('Limpiando recursos...')
    commands.shutdown()
    wake_word.shutdown()
    playback.shutdown()
    capture.shutdown()

    # Resumen
    logger.info('')
    logger.info('=' * 60)
    logger.info('RESUMEN')
    logger.info('=' * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        symbol = '✓' if result else '✗'
        logger.info(f'{symbol} {name}')

    logger.info('')
    logger.info(f'Pasados: {passed}/{total}')

    if passed == total:
        logger.info('🎉 TODOS LOS TESTS PASARON 🎉')
        return True
    else:
        logger.error(f'⚠ {total - passed} tests fallaron')
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f'Error crítico: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

