import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.config import settings
from baymax_voice.utils.logger import setup_logger, get_logger
import baymax_voice.audio.capture as capture
import baymax_voice.audio.vad as vad
import baymax_voice.audio.noise_filter as noise_filter

setup_logger(level='DEBUG')
logger = get_logger('test')

logger.info('=== Test de Captura de Audio con Filtro de Ruido y VAD ===')
logger.info(f'Sample Rate: {settings.SAMPLE_RATE} Hz')
logger.info(f'Chunk Size: {settings.CHUNK_SIZE} samples ({settings.CHUNK_SIZE / settings.SAMPLE_RATE * 1000:.1f} ms)')
logger.info(f'VAD Aggressiveness: {settings.VAD_AGGRESSIVENESS}')
logger.info(f'Silencio para finalizar: {settings.VAD_SILENCE_DURATION}s')
logger.info('')

capture.initialize()
vad.initialize()

logger.info('=== PASO 1: Calibración de ruido ===')
input('Presiona ENTER cuando estés listo (luego mantén SILENCIO)...')

success = noise_filter.calibrate_noise(capture, duration=2.0)

if not success:
    logger.error('Calibración falló')
    capture.shutdown()
    sys.exit(1)

noise_level = noise_filter.get_noise_level()
logger.info(f'Nivel de ruido ambiente: {noise_level:.2f}')
logger.info('')

logger.info('=== PASO 2: Test de detección de voz ===')
logger.info('Ahora HABLA para probar el VAD con filtro activo')
logger.info('Presiona Ctrl+C para terminar')
logger.info('')

try:
    frame_count = 0
    speech_frames = 0

    while True:
        frame = capture.get_audio_frame()

        if frame is None:
            continue

        filtered_frame = noise_filter.apply_filter(frame)

        event = vad.process_frame(filtered_frame)
        frame_count += 1

        if event == 'speech_start':
            logger.info('>>> VOZ DETECTADA <<<')
            speech_frames = 0

        elif event == 'speech_ongoing':
            speech_frames += 1
            if speech_frames % 10 == 0:
                duration = speech_frames * settings.CHUNK_SIZE / settings.SAMPLE_RATE
                print(f'  Hablando... {duration:.1f}s', end='\r')

        elif event == 'speech_end':
            total_duration = speech_frames * settings.CHUNK_SIZE / settings.SAMPLE_RATE
            logger.info(f'>>> VOZ FINALIZADA (duración: {total_duration:.1f}s) <<<')
            logger.info('')

        time.sleep(0.01)

except KeyboardInterrupt:
    logger.info('')
    logger.info('=== Test finalizado ===')
    total_time = frame_count * settings.CHUNK_SIZE / settings.SAMPLE_RATE
    logger.info(f'Frames procesados: {frame_count}')
    logger.info(f'Tiempo total: {total_time:.1f}s')

finally:
    capture.shutdown()
    logger.info('Audio cerrado correctamente')