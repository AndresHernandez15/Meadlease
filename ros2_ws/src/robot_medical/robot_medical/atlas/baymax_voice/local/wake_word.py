"""
Detección de palabra de activación usando Porcupine.
"""
import pvporcupine

from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('local.wake_word')

_porcupine = None
_detection_count = 0
_buffer = []


def initialize(access_key, keyword_path, model_path=None, sensitivity=0.5):
    global _porcupine, _buffer

    if _porcupine is not None:
        logger.debug('Wake word ya inicializado, omitiendo')
        return True

    try:
        if model_path:
            _porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[keyword_path],
                model_path=model_path,
                sensitivities=[sensitivity]
            )
        else:
            _porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[keyword_path],
                sensitivities=[sensitivity]
            )

        _buffer = []

        logger.info(f'Porcupine inicializado (sensitivity: {sensitivity})')

        if _porcupine.sample_rate != settings.SAMPLE_RATE:
            logger.error(
                f'Sample rate no coincide: Porcupine={_porcupine.sample_rate}, Settings={settings.SAMPLE_RATE}')
            _porcupine.delete()
            _porcupine = None
            return False

        if settings.CHUNK_SIZE != _porcupine.frame_length:
            logger.info(f'Usando buffer interno ({settings.CHUNK_SIZE} -> {_porcupine.frame_length} samples)')

        return True

    except Exception as e:
        logger.error(f'Error inicializando Porcupine: {e}')
        _porcupine = None
        return False


def process_frame(audio_frame):
    global _detection_count, _buffer

    if _porcupine is None:
        logger.error('Porcupine no inicializado')
        return False

    if audio_frame is None or len(audio_frame) == 0:
        return False

    _buffer.extend(audio_frame.tolist())

    detected = False

    while len(_buffer) >= _porcupine.frame_length:
        porcupine_frame = _buffer[:_porcupine.frame_length]

        try:
            keyword_index = _porcupine.process(porcupine_frame)

            if keyword_index >= 0:
                _detection_count += 1
                logger.info(f'Wake word detectada: "{settings.WAKE_WORD}" (#{_detection_count})')
                detected = True

        except Exception as e:
            logger.error(f'Error procesando frame: {e}')

        _buffer = _buffer[_porcupine.frame_length:]

    if len(_buffer) > _porcupine.frame_length * 10:
        logger.warning(f'Buffer interno demasiado grande ({len(_buffer)} samples), limpiando')
        _buffer = _buffer[-_porcupine.frame_length:]

    return detected


def get_frame_length():
    if _porcupine is None:
        return None
    return _porcupine.frame_length


def get_sample_rate():
    if _porcupine is None:
        return None
    return _porcupine.sample_rate


def get_detection_count():
    return _detection_count


def reset_detection_count():
    global _detection_count
    _detection_count = 0


def reset_buffer():
    global _buffer
    _buffer = []
    logger.debug('Buffer interno reseteado')


def shutdown():
    global _porcupine, _buffer

    if _porcupine is not None:
        try:
            _porcupine.delete()
        except Exception as e:
            logger.warning(f'Error cerrando Porcupine: {e}')
        finally:
            _porcupine = None
            _buffer = []
            logger.info('Porcupine cerrado')

