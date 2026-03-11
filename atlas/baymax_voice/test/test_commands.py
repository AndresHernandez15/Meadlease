import sys
import time
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.config import settings
from baymax_voice.utils.logger import setup_logger, get_logger
from baymax_voice.utils.events import get_event, clear_events
import baymax_voice.audio.capture as capture
import baymax_voice.audio.vad as vad
import baymax_voice.audio.noise_filter as noise_filter
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.local.commands as commands

setup_logger(level='INFO')
logger = get_logger('test')

logger.info('=== Test de Comandos en Streaming (Tiempo Real) ===')
logger.info('Este test demuestra detección de comandos MIENTRAS hablas')
logger.info('')

capture.initialize()
vad.initialize()

logger.info('=== Calibración de ruido ===')
input('Presiona ENTER y mantén SILENCIO...')
success = noise_filter.calibrate_noise(capture, duration=2.0)

if not success:
    logger.error('Calibración falló')
    capture.shutdown()
    sys.exit(1)

logger.info(f'Nivel de ruido: {noise_filter.get_noise_level():.2f}')
logger.info('')

success = commands.initialize(settings.VOSK_MODEL_PATH)

if not success:
    logger.error('Comandos no se pudieron inicializar')
    capture.shutdown()
    sys.exit(1)

logger.info('')
logger.info('=== Comandos disponibles ===')
logger.info('MOVIMIENTO: "ven aquí", "detente", "sígueme", "ve a la cocina"')
logger.info('MÉDICOS: "mide signos", "dispensa medicamento"')
logger.info('CONTROL: "cancela", "silencio"')
logger.info('')
logger.info('=== Modo Streaming ===')
logger.info('Los comandos se detectan EN TIEMPO REAL mientras hablas')
logger.info('No es necesario terminar de hablar para que se detecte')
logger.info('')
logger.info('Presiona Ctrl+C para terminar')
logger.info('')

running = True
listening = False
command_detected_flag = False


def event_monitor():
    while running:
        event = get_event(timeout=0.1)
        if event and event.type == 'COMMAND_DETECTED':
            logger.info('')
            logger.info('=' * 50)
            logger.info('⚡ COMANDO DETECTADO EN TIEMPO REAL ⚡')
            logger.info(f'  Tipo: {event.data["type"]}')
            logger.info(f'  Acción: {event.data["action"]}')
            logger.info(f'  Texto: "{event.data["raw_text"]}"')
            logger.info(f'  Confianza: {event.data.get("confidence", 0):.2f}')
            logger.info('=' * 50)
            logger.info('')


event_thread = threading.Thread(target=event_monitor, daemon=True)
event_thread.start()

try:
    while True:
        frame = capture.get_audio_frame()

        if frame is None:
            continue

        filtered_frame = noise_filter.apply_filter(frame)

        event_vad = vad.process_frame(filtered_frame)

        if event_vad == 'speech_start':
            logger.info('>>> ESCUCHANDO (procesamiento en tiempo real) >>>')
            listening = True
            command_detected_flag = False
            audio_buffer.start_recording()
            commands.reset()
            clear_events()

        if listening:
            audio_buffer.append_frame(filtered_frame)

            result = commands.process_audio_streaming(filtered_frame)

            if result and result['type'] != 'UNKNOWN' and not command_detected_flag:
                command_detected_flag = True

        if event_vad == 'speech_end' and listening:
            logger.info('Finalizando...')

            audio_buffer.stop_recording()

            if not command_detected_flag:
                final_result = commands.finalize_audio()

                if final_result and final_result['type'] == 'UNKNOWN':
                    logger.info(f'No es comando → enviaría a STT cloud: "{final_result["raw_text"]}"')
                    logger.info(f'Audio capturado: {audio_buffer.get_duration_seconds():.2f}s')

            listening = False
            logger.info('')

        time.sleep(0.001)

except KeyboardInterrupt:
    logger.info('')
    logger.info('=== Test finalizado ===')
    running = False

finally:
    commands.shutdown()
    capture.shutdown()
    logger.info('Sistema cerrado correctamente')