"""
Captura de audio desde micrófono usando PyAudio.
"""
import pyaudio
import numpy as np
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.capture')

_audio_interface = None
_stream = None


def initialize():
    global _audio_interface, _stream

    if _audio_interface is not None:
        logger.debug('Audio ya inicializado, omitiendo')
        return True

    try:
        _audio_interface = pyaudio.PyAudio()

        _stream = _audio_interface.open(
            format=pyaudio.paInt16,
            channels=settings.CHANNELS,
            rate=settings.SAMPLE_RATE,
            input=True,
            frames_per_buffer=settings.CHUNK_SIZE
        )

        logger.info(f'Audio inicializado: {settings.SAMPLE_RATE}Hz, {settings.CHANNELS}ch, chunk={settings.CHUNK_SIZE}')
        return True
    except Exception as e:
        logger.error(f'Error inicializando audio: {e}')
        if _audio_interface:
            _audio_interface.terminate()
            _audio_interface = None
        return False


def get_audio_frame():
    if _stream is None:
        logger.error('Stream no inicializado')
        return None

    try:
        raw_data = _stream.read(settings.CHUNK_SIZE, exception_on_overflow=False)
        audio_array = np.frombuffer(raw_data, dtype=np.int16)
        return audio_array
    except Exception as e:
        logger.error(f'Error capturando frame: {e}')
        return None


def is_running():
    return _stream is not None and _stream.is_active()


def shutdown():
    global _audio_interface, _stream

    if _stream is not None:
        try:
            _stream.stop_stream()
            _stream.close()
        except Exception as e:
            logger.warning(f'Error cerrando stream: {e}')
        finally:
            _stream = None
            logger.info('Stream cerrado')

    if _audio_interface is not None:
        try:
            _audio_interface.terminate()
        except Exception as e:
            logger.warning(f'Error terminando PyAudio: {e}')
        finally:
            _audio_interface = None
            logger.info('PyAudio terminado')

