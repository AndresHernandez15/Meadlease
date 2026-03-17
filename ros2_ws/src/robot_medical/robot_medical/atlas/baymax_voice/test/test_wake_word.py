import sys
import time
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from baymax_voice.config import settings
from baymax_voice.utils.logger import setup_logger, get_logger
import baymax_voice.audio.capture as capture
import baymax_voice.audio.noise_filter as noise_filter
import baymax_voice.local.wake_word as wake_word

setup_logger(level='INFO')
logger = get_logger('test')

logger.info('=== Test de Wake Word Detection ===')
logger.info(f'Wake word: "{settings.WAKE_WORD}"')
logger.info(f'Archivo keyword: {settings.PORCUPINE_KEYWORD_PATH}')
logger.info(f'Archivo modelo: {settings.PORCUPINE_MODEL_PATH}')
logger.info(f'Sensibilidad: {settings.PORCUPINE_SENSITIVITY}')
logger.info('')

capture.initialize()

logger.info('=== Calibración de ruido ===')
input('Presiona ENTER y mantén SILENCIO...')
success = noise_filter.calibrate_noise(capture, duration=2.0)

if not success:
    logger.error('Calibración falló')
    capture.shutdown()
    sys.exit(1)

logger.info(f'Nivel de ruido: {noise_filter.get_noise_level():.2f}')
logger.info('')

success = wake_word.initialize(
    access_key=settings.PORCUPINE_ACCESS_KEY,
    keyword_path=settings.PORCUPINE_KEYWORD_PATH,
    model_path=settings.PORCUPINE_MODEL_PATH,
    sensitivity=settings.PORCUPINE_SENSITIVITY
)

if not success:
    logger.error('Wake word no se pudo inicializar')
    capture.shutdown()
    sys.exit(1)

logger.info('')
logger.info('=== Escuchando wake word ===')
logger.info(f'Di "{settings.WAKE_WORD.upper()}" para probar')
logger.info('Presiona Ctrl+C para terminar')
logger.info('')

try:
    frame_count = 0

    while True:
        frame = capture.get_audio_frame()

        if frame is None:
            continue

        filtered_frame = noise_filter.apply_filter(frame)

        detected = wake_word.process_frame(filtered_frame)

        frame_count += 1

        if detected:
            logger.info('¡Detección confirmada!')
            logger.info('')

        time.sleep(0.001)

except KeyboardInterrupt:
    logger.info('')
    logger.info('=== Test finalizado ===')
    total_time = frame_count * settings.CHUNK_SIZE / settings.SAMPLE_RATE
    detections = wake_word.get_detection_count()
    logger.info(f'Tiempo total: {total_time:.1f}s')
    logger.info(f'Detecciones totales: {detections}')

finally:
    wake_word.shutdown()
    capture.shutdown()
    logger.info('Sistema cerrado correctamente')