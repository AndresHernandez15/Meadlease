"""
Atlas — Sistema Conversacional del Robot

Orquestador principal que coordina:
  - audio_thread: captura y procesamiento de audio
  - fsm_thread: máquina de estados (loop principal)
  - cloud pipeline: procesamiento STT → LLM → TTS

Comunicación: eventos thread-safe (utils/events.py)
"""
import sys
import time
import signal
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.utils.logger import setup_logger, get_logger
from baymax_voice.utils.events import put_event
from baymax_voice.config import settings
import baymax_voice.audio.capture as capture
import baymax_voice.audio.noise_filter as noise_filter
import baymax_voice.audio.vad as vad
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.audio.playback as playback
import baymax_voice.local.wake_word as wake_word
import baymax_voice.local.commands as commands
from baymax_voice.logic import state_machine

setup_logger()
logger = get_logger('main')

_running = False
_shutdown_event = threading.Event()


# ═══════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════

def initialize_all() -> bool:
    """
    Inicializa todos los módulos en orden.
    Retorna False si algún módulo crítico falla (el sistema no puede arrancar).
    """
    logger.info('=' * 60)
    logger.info('  ATLAS — Sistema Conversacional')
    logger.info('=' * 60)

    errors = []

    # Audio capture
    logger.info('[1/7] Audio capture...')
    if not capture.initialize():
        errors.append('capture')
        logger.error('  [X] Audio capture FALLO')
    else:
        logger.info('  [OK] Audio capture OK')

    # VAD
    logger.info('[2/7] VAD (WebRTC)...')
    if not vad.initialize():
        errors.append('vad')
        logger.error('  [X] VAD FALLO')
    else:
        logger.info('  [OK] VAD OK')

    # Playback
    logger.info('[3/7] Playback...')
    if not playback.initialize():
        errors.append('playback')
        logger.error('  [X] Playback FALLO -- sin dispositivo de audio de salida')
    else:
        logger.info('  [OK] Playback OK')

    # Calibración de ruido
    logger.info('[4/7] Calibracion de ruido de fondo...')
    logger.info('      Manten SILENCIO durante 2 segundos...')
    if not noise_filter.calibrate_noise(capture, duration=settings.NOISE_CALIBRATION_DURATION):
        logger.warning('  [!] Calibracion de ruido fallo -- continuando sin filtro')
    else:
        logger.info(f'  [OK] Ruido ambiente calibrado: {noise_filter.get_noise_level():.1f} RMS')

    # Wake word (Porcupine)
    logger.info('[5/7] Wake word (Porcupine)...')
    if not wake_word.initialize(
        access_key=settings.PORCUPINE_ACCESS_KEY,
        keyword_path=settings.PORCUPINE_KEYWORD_PATH,
        model_path=settings.PORCUPINE_MODEL_PATH,
        sensitivity=settings.PORCUPINE_SENSITIVITY,
    ):
        errors.append('wake_word')
        logger.error('  [X] Wake word FALLO')
    else:
        logger.info(f'  [OK] Wake word OK -- escuchando "{settings.WAKE_WORD}"')

    # Comandos locales (Vosk)
    logger.info('[6/7] Comandos locales (Vosk)...')
    if not commands.initialize(settings.VOSK_MODEL_PATH):
        logger.warning('  [!] Vosk FALLO -- comandos offline no disponibles')
    else:
        logger.info('  [OK] Vosk OK')

    # Módulos cloud (STT + LLM + TTS)
    logger.info('[7/7] Modulos cloud (STT + LLM + TTS)...')
    cloud_results = state_machine.initialize_cloud_modules()
    if not cloud_results['all_ok']:
        logger.warning('  [!] Algunos modulos cloud no disponibles -- modo degradado')
    else:
        logger.info('  [OK] STT + LLM + TTS OK')

    # FSM
    state_machine.initialize()

    # Resultado final
    critical = [e for e in errors if e in ('capture', 'vad', 'playback', 'wake_word')]
    if critical:
        logger.error(f'Modulos criticos fallaron: {critical}. El sistema no puede arrancar.')
        return False

    logger.info('')
    logger.info('Sistema listo [OK]')
    logger.info(f'Di "{settings.WAKE_WORD}" para activar a Atlas')
    logger.info('Ctrl+C para apagar')
    logger.info('=' * 60)
    return True


# ═══════════════════════════════════════════════════════════════════════════
#  THREAD DE AUDIO
# ═══════════════════════════════════════════════════════════════════════════

def audio_loop():
    """
    Captura frames del micrófono y los distribuye a los módulos correctos
    según el estado actual de la FSM.

    Enrutamiento por estado:
      IDLE         → wake_word.process_frame()
      LISTENING    → vad + audio_buffer + commands (streaming)
      SPEAKING / PROCESSING_* → silencio (Atlas no se "escucha a sí mismo")
    """
    logger.info('Thread de audio iniciado')

    while not _shutdown_event.is_set():
        frame = capture.get_audio_frame()
        if frame is None:
            time.sleep(0.005)
            continue

        # Filtro de ruido adaptativo
        frame = noise_filter.apply_filter(frame)

        current_state = state_machine.get_current_state()

        if current_state == 'IDLE':
            # Solo buscar wake word
            if wake_word.process_frame(frame):
                put_event('WAKE_WORD_DETECTED', source='audio_loop')

        elif current_state == 'LISTENING':
            # Grabar en buffer
            audio_buffer.append_frame(frame)

            # VAD — detectar fin de voz del usuario
            vad_result = vad.process_frame(frame)
            if vad_result == 'speech_end':
                put_event('SPEECH_END', source='audio_loop')

            # Comandos en streaming (Vosk detecta keywords mientras el usuario habla)
            # Solo si aún no se detectó un comando en este ciclo de escucha
            if not state_machine._state_data.get('command_detected', False):
                commands.process_audio_streaming(frame)

        # SPEAKING / PROCESSING_LOCAL / PROCESSING_CLOUD / ERROR:
        # No capturar — evita eco y procesamiento innecesario

    logger.info('Thread de audio detenido')


# ═══════════════════════════════════════════════════════════════════════════
#  THREAD DE LA FSM
# ═══════════════════════════════════════════════════════════════════════════

def fsm_loop():
    """
    Loop principal de la máquina de estados.
    Llama a state_machine.update() en cada tick para consumir
    eventos y ejecutar el handler del estado actual.
    """
    logger.info('Thread FSM iniciado')

    while not _shutdown_event.is_set():
        try:
            state_machine.update()
        except Exception as e:
            logger.error(f'Error inesperado en FSM: {e}', exc_info=True)
            time.sleep(0.1)

    logger.info('Thread FSM detenido')


# ═══════════════════════════════════════════════════════════════════════════
#  ARRANQUE Y SHUTDOWN
# ═══════════════════════════════════════════════════════════════════════════

def start():
    global _running

    _running = True
    _shutdown_event.clear()

    t_audio = threading.Thread(target=audio_loop, name='audio-loop', daemon=True)
    t_fsm   = threading.Thread(target=fsm_loop,   name='fsm-loop',   daemon=True)

    t_audio.start()
    t_fsm.start()

    logger.info('Threads arrancados: audio-loop, fsm-loop')
    return t_audio, t_fsm


def shutdown(reason: str = 'señal de apagado'):
    global _running

    if not _running:
        return

    logger.info(f'Apagando sistema ({reason})...')
    _running = False
    _shutdown_event.set()

    time.sleep(0.3)  # dar tiempo a los threads daemon para terminar limpiamente

    try:
        playback.stop()
    except Exception:
        pass

    state_machine.shutdown()   # cierra STT + LLM + TTS
    commands.shutdown()
    wake_word.shutdown()
    capture.shutdown()
    playback.shutdown()

    logger.info('Sistema apagado.')


# ═══════════════════════════════════════════════════════════════════════════
#  SEÑALES DEL SO
# ═══════════════════════════════════════════════════════════════════════════

def _signal_handler(sig, frame):
    print()  # nueva línea tras el ^C en consola
    shutdown('Ctrl+C / SIGTERM')
    sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if not initialize_all():
        sys.exit(1)

    start()

    # Mantener el proceso principal vivo mientras los threads daemon corren
    try:
        while not _shutdown_event.is_set():
            _shutdown_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown('loop principal terminado')


if __name__ == '__main__':
    main()

