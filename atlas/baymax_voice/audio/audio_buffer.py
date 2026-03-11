"""
Buffer de audio thread-safe para almacenamiento temporal de frames.
"""
import numpy as np
from threading import Lock
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.buffer')

_buffer = []
_buffer_lock = Lock()
_is_recording = False


def start_recording():
    global _is_recording, _buffer

    with _buffer_lock:
        _buffer = []
        _is_recording = True

    logger.debug('Buffer: iniciando grabación')


def stop_recording():
    global _is_recording

    with _buffer_lock:
        _is_recording = False

    logger.debug('Buffer: deteniendo grabación')


def append_frame(audio_frame):
    global _buffer

    if not _is_recording:
        return

    with _buffer_lock:
        if isinstance(audio_frame, np.ndarray):
            _buffer.extend(audio_frame.tolist())
        else:
            _buffer.extend(audio_frame)

        max_samples = int(settings.MAX_BUFFER_DURATION * settings.SAMPLE_RATE)

        if len(_buffer) > max_samples:
            overflow = len(_buffer) - max_samples
            _buffer = _buffer[overflow:]
            logger.warning(f'Buffer overflow: descartados {overflow} samples antiguos')


def get_buffer_copy():
    with _buffer_lock:
        return _buffer.copy()


def get_buffer_as_bytes():
    with _buffer_lock:
        if not _buffer:
            return b''
        array = np.array(_buffer, dtype=np.int16)
        return array.tobytes()


def get_buffer_as_numpy():
    with _buffer_lock:
        if not _buffer:
            return np.array([], dtype=np.int16)
        return np.array(_buffer, dtype=np.int16)


def get_duration_seconds():
    with _buffer_lock:
        if not _buffer:
            return 0.0
        return len(_buffer) / settings.SAMPLE_RATE


def clear_buffer():
    global _buffer

    with _buffer_lock:
        _buffer = []

    logger.debug('Buffer limpiado')


def is_recording():
    return _is_recording


def get_buffer_size():
    with _buffer_lock:
        return len(_buffer)