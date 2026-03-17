"""
Reproducción de audio usando sounddevice.
"""
import sounddevice as sd
import numpy as np
import wave
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.playback')

_volume = 1.0
_is_playing = False
_initialized = False


def initialize():
    global _initialized

    if _initialized:
        logger.debug('Playback ya inicializado, omitiendo')
        return True

    try:
        devices = sd.query_devices()
        default_output = sd.default.device[1]
        logger.info(f'Playback inicializado (dispositivo: {devices[default_output]["name"]})')
        _initialized = True
        return True
    except Exception as e:
        logger.error(f'Error inicializando playback: {e}')
        return False


def play_audio(audio_data, sample_rate=None, blocking=False):
    global _is_playing

    if sample_rate is None:
        sample_rate = settings.SAMPLE_RATE

    if audio_data is None or len(audio_data) == 0:
        logger.warning('Audio vacío, no se reproduce')
        return False

    try:
        if isinstance(audio_data, bytes):
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
        else:
            audio_array = audio_data

        audio_float = audio_array.astype(np.float32) / 32768.0

        audio_float = audio_float * _volume

        _is_playing = True

        sd.play(audio_float, samplerate=sample_rate, blocking=blocking)

        if not blocking:
            logger.debug(f'Reproduciendo audio ({len(audio_array)} samples, {len(audio_array) / sample_rate:.2f}s)')

        return True

    except Exception as e:
        logger.error(f'Error reproduciendo audio: {e}')
        _is_playing = False
        return False


def play_file(filepath, blocking=False):
    global _is_playing

    try:
        with wave.open(filepath, 'rb') as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            audio_bytes = wf.readframes(wf.getnframes())

        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

        if channels == 2:
            audio_array = audio_array.reshape(-1, 2)

        logger.debug(f'Reproduciendo archivo: {filepath}')
        return play_audio(audio_array, sample_rate=sample_rate, blocking=blocking)

    except FileNotFoundError:
        logger.error(f'Archivo no encontrado: {filepath}')
        return False
    except Exception as e:
        logger.error(f'Error reproduciendo archivo {filepath}: {e}')
        return False


def set_volume(level):
    global _volume

    if level < 0.0 or level > 1.0:
        logger.warning(f'Volumen fuera de rango (0.0-1.0): {level}')
        level = max(0.0, min(1.0, level))

    _volume = level
    logger.debug(f'Volumen ajustado a {_volume:.2f}')


def get_volume():
    return _volume


def is_playing():
    try:
        return sd.get_stream().active if sd.get_stream() else False
    except:
        return False


def wait_until_done():
    global _is_playing
    try:
        sd.wait()
        _is_playing = False
        logger.debug('Reproducción finalizada')
    except Exception as e:
        logger.error(f'Error esperando reproducción: {e}')
        _is_playing = False


def stop():
    global _is_playing
    try:
        sd.stop()
        _is_playing = False
        logger.debug('Reproducción detenida')
    except Exception as e:
        logger.error(f'Error deteniendo reproducción: {e}')


def shutdown():
    global _initialized, _is_playing

    try:
        sd.stop()
    except Exception as e:
        logger.warning(f'Error deteniendo playback: {e}')
    finally:
        _initialized = False
        _is_playing = False
        logger.info('Playback cerrado')
