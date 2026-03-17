"""
Voice Activity Detection usando WebRTC VAD.
"""
import webrtcvad
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.vad')

_vad = None
_silence_counter = 0
_is_speaking = False


def initialize():
    global _vad

    if _vad is not None:
        logger.debug('VAD ya inicializado, omitiendo')
        return True

    try:
        _vad = webrtcvad.Vad(settings.VAD_AGGRESSIVENESS)
        logger.info(f'WebRTC VAD inicializado (agresividad: {settings.VAD_AGGRESSIVENESS})')
        return True
    except Exception as e:
        logger.error(f'Error inicializando VAD: {e}')
        _vad = None
        return False


def process_frame(audio_frame):
    global _silence_counter, _is_speaking

    if _vad is None:
        logger.error('VAD no inicializado')
        return 'silence'

    if audio_frame is None or len(audio_frame) == 0:
        return 'silence'

    audio_bytes = audio_frame.tobytes()

    try:
        is_speech = _vad.is_speech(audio_bytes, settings.SAMPLE_RATE)
    except Exception as e:
        logger.error(f'Error en VAD: {e}')
        return 'silence'

    if is_speech:
        _silence_counter = 0

        if not _is_speaking:
            _is_speaking = True
            logger.debug('Voz detectada')
            return 'speech_start'

        return 'speech_ongoing'

    else:
        if _is_speaking:
            _silence_counter += 1
            frames_needed = int(settings.VAD_SILENCE_DURATION * settings.SAMPLE_RATE / settings.CHUNK_SIZE)

            if _silence_counter >= frames_needed:
                _is_speaking = False
                _silence_counter = 0
                logger.debug(f'Voz finalizada (silencio: {settings.VAD_SILENCE_DURATION}s)')
                return 'speech_end'

            return 'speech_ongoing'

        return 'silence'


def is_speech_active():
    return _is_speaking


def reset():
    global _silence_counter, _is_speaking
    _silence_counter = 0
    _is_speaking = False
    logger.debug('VAD reseteado')
