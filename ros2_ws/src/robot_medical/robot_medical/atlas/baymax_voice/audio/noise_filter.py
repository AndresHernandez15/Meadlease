"""
Filtro de ruido adaptativo basado en calibración de ambiente.
"""
import numpy as np
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('audio.noise_filter')

_noise_profile = None


def calibrate_noise(capture_module, duration=None):
    global _noise_profile

    if duration is None:
        duration = settings.NOISE_CALIBRATION_DURATION

    logger.info(f'Calibrando ruido de fondo ({duration}s)...')
    logger.info('Mantén SILENCIO durante la calibración')

    frames_needed = int(duration * settings.SAMPLE_RATE / settings.CHUNK_SIZE)
    noise_samples = []

    for i in range(frames_needed):
        frame = capture_module.get_audio_frame()
        if frame is not None:
            noise_samples.append(frame.astype(np.float32))

    if len(noise_samples) == 0:
        logger.error('No se capturó audio para calibración')
        _noise_profile = None
        return False

    noise_array = np.concatenate(noise_samples)

    _noise_profile = {
        'mean': np.mean(noise_array),
        'std': np.std(noise_array),
        'rms': np.sqrt(np.mean(noise_array ** 2))
    }

    logger.info(f'Calibración completa (RMS ruido: {_noise_profile["rms"]:.2f})')
    return True


def apply_filter(audio_frame):
    if _noise_profile is None:
        return audio_frame

    if audio_frame is None or len(audio_frame) == 0:
        return audio_frame

    frame_float = audio_frame.astype(np.float32)

    noise_threshold = _noise_profile['rms'] * settings.NOISE_THRESHOLD_MULTIPLIER

    frame_rms = np.sqrt(np.mean(frame_float ** 2))

    if frame_rms < noise_threshold:
        reduction_factor = settings.NOISE_REDUCTION_FACTOR
    else:
        reduction_factor = 0.0

    filtered = frame_float - (_noise_profile['mean'] * reduction_factor)

    filtered = np.clip(filtered, -32768, 32767)

    return filtered.astype(np.int16)


def is_calibrated():
    return _noise_profile is not None


def get_noise_level():
    if _noise_profile is None:
        return None
    return _noise_profile['rms']