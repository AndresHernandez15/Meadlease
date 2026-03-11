"""
Máquina de estados finitos (FSM) del sistema conversacional.
Estados: IDLE → LISTENING → PROCESSING → SPEAKING → IDLE
"""
import time
import threading
from datetime import datetime
from typing import Optional
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger
from baymax_voice.utils.events import get_event, put_event, clear_events
import baymax_voice.audio.playback as playback
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.audio.vad as vad
import baymax_voice.local.commands as commands
import baymax_voice.cloud.speech_to_text as speech_to_text
import baymax_voice.cloud.groq_llm as groq_llm
import baymax_voice.cloud.text_to_speech as text_to_speech
from baymax_voice.cloud.llm_config import build_patient_context

TTS_SAMPLE_RATE = 24000  # Azure TTS retorna 24kHz
_cloud_processing = False  # Flag para evitar threads paralelos

logger = get_logger('logic.fsm') 

_current_state = 'IDLE'
_state_data = {}
_state_start_time: Optional[datetime] = None
_transition_count = 0

VALID_TRANSITIONS = {
    'IDLE': ['LISTENING', 'ERROR'],
    'LISTENING': ['PROCESSING_LOCAL', 'PROCESSING_CLOUD', 'IDLE', 'ERROR'],
    'PROCESSING_LOCAL': ['SPEAKING', 'IDLE', 'ERROR'],
    'PROCESSING_CLOUD': ['SPEAKING', 'ERROR'],
    'SPEAKING': ['IDLE', 'ERROR'],
    'ERROR': ['IDLE']
}


def initialize():
    global _current_state, _state_data, _state_start_time, _transition_count

    _current_state = 'IDLE'
    _state_data = {}
    _state_start_time = datetime.now()
    _transition_count = 0

    clear_events()

    logger.info('FSM inicializada')


def get_current_state():
    return _current_state


def get_state_duration():
    if _state_start_time is None:
        return 0.0
    return (datetime.now() - _state_start_time).total_seconds()


def get_transition_count():
    return _transition_count


def transition_to(new_state, data=None):
    global _current_state, _state_data, _state_start_time, _transition_count

    if new_state not in VALID_TRANSITIONS:
        logger.error(f'Estado inválido: {new_state}')
        return False

    if new_state not in VALID_TRANSITIONS[_current_state]:
        logger.error(f'Transición inválida: {_current_state} → {new_state}')
        return False

    old_state = _current_state
    old_duration = get_state_duration()

    exit_state(old_state)

    _current_state = new_state
    _state_data = data if data is not None else {}
    _state_start_time = datetime.now()
    _transition_count += 1

    logger.info(f'{old_state} → {new_state} ({old_duration:.2f}s)')

    enter_state(new_state)

    put_event('STATE_CHANGED', data={'from': old_state, 'to': new_state}, source='fsm')

    return True


def exit_state(state):
    if state == 'LISTENING':
        audio_buffer.stop_recording()
        vad.reset()

    elif state == 'SPEAKING':
        pass

    elif state == 'PROCESSING_LOCAL':
        commands.reset()

    elif state == 'PROCESSING_CLOUD':
        pass


def enter_state(state):
    if state == 'IDLE':
        logger.debug('Esperando wake word...')

    elif state == 'LISTENING':
        # Reset previo al beep para ignorar cualquier actividad residual
        vad.reset()

        # Reproducir beep en modo bloqueante
        try:
            playback.play_file(settings.CONFIRMATION_AUDIO_PATH, blocking=True)
        except Exception as e:
            logger.debug(f'Confirmation audio no disponible: {e}')

        # Pausa para que el eco del altavoz se disipe antes de abrir el micrófono
        time.sleep(settings.POST_BEEP_SILENCE)

        # Ahora sí, abrir grabación con estado limpio
        audio_buffer.start_recording()
        audio_buffer.clear_buffer()
        vad.reset()
        commands.reset()

        _state_data['start_time'] = time.time()
        _state_data['command_detected'] = False

        logger.info('Escuchando usuario...')

    elif state == 'PROCESSING_LOCAL':
        logger.info(f'Ejecutando comando local: {_state_data.get("command", {})}')

    elif state == 'PROCESSING_CLOUD':
        logger.info('Procesando con cloud (STT + LLM + TTS)...')

    elif state == 'SPEAKING':
        logger.info('Reproduciendo respuesta...')
        # Disparar evento interno para que el handler se ejecute en el próximo tick
        put_event('SPEAKING_START', source='fsm')

    elif state == 'ERROR':
        error_msg = _state_data.get('error', 'Error desconocido')
        logger.error(f'Estado ERROR: {error_msg}')


def update():
    event = get_event(timeout=0.01)

    if event is None:
        handle_timeout_check()
        return

    if _current_state == 'IDLE':
        handle_idle(event)
    elif _current_state == 'LISTENING':
        handle_listening(event)
    elif _current_state == 'PROCESSING_LOCAL':
        handle_processing_local(event)
    elif _current_state == 'PROCESSING_CLOUD':
        handle_processing_cloud(event)
    elif _current_state == 'SPEAKING':
        handle_speaking(event)
    elif _current_state == 'ERROR':
        handle_error(event)
    # Eventos de cambio de estado ya manejados internamente (STATE_CHANGED, etc.)


def handle_idle(event):
    if event.type == 'WAKE_WORD_DETECTED':
        transition_to('LISTENING')


def handle_listening(event):
    global _state_data

    if event.type == 'COMMAND_DETECTED':
        _state_data['command_detected'] = True
        _state_data['command'] = event.data
        transition_to('PROCESSING_LOCAL', data=_state_data)

    elif event.type == 'SPEECH_END':
        if not _state_data.get('command_detected', False):
            final_command = commands.finalize_audio()

            if final_command and final_command['type'] != 'UNKNOWN':
                _state_data['command'] = final_command
                transition_to('PROCESSING_LOCAL', data=_state_data)
            else:
                buffer_duration = audio_buffer.get_duration_seconds()

                if buffer_duration > settings.AUDIO_MIN_DURATION:
                    _state_data['audio_buffer'] = audio_buffer.get_buffer_as_bytes()
                    _state_data['text'] = final_command.get('raw_text', '') if final_command else ''
                    transition_to('PROCESSING_CLOUD', data=_state_data)
                else:
                    logger.warning('Audio muy corto, volviendo a IDLE')
                    transition_to('IDLE')


def handle_timeout_check():
    if _current_state == 'LISTENING':
        elapsed = time.time() - _state_data.get('start_time', 0)
        if elapsed > settings.MAX_LISTENING_TIME:
            logger.warning(f'Timeout en LISTENING ({elapsed:.1f}s)')
            transition_to('IDLE')

    elif _current_state == 'PROCESSING_CLOUD':
        elapsed = get_state_duration()
        if elapsed > 20.0:  # 20s máximo para todo el pipeline cloud
            logger.error(f'Timeout en PROCESSING_CLOUD ({elapsed:.1f}s), volviendo a IDLE')
            transition_to('ERROR', data={'error': 'cloud_pipeline_timeout'})

    elif _current_state == 'ERROR':
        if get_state_duration() > 2.0:
            logger.info('Recuperando de ERROR...')
            transition_to('IDLE')


def handle_processing_local(event):
    command = _state_data.get('command', {})
    command_type = command.get('type')
    action = command.get('action')

    logger.info(f'Comando local: {command_type}/{action}')

    response_text = execute_local_command(command_type, action)

    if not response_text:
        transition_to('IDLE')
        return

    # Sintetizar TTS en thread para no bloquear el loop
    def _run_local_tts():
        global _state_data
        audio_response = text_to_speech.synthesize(response_text, style='amigable')
        if audio_response:
            _state_data['tts_audio'] = audio_response
            _state_data['tts_sample_rate'] = TTS_SAMPLE_RATE
            _state_data['needs_tts'] = False
        else:
            _state_data['response_text'] = response_text
            _state_data['needs_tts'] = True
            _state_data['tts_audio'] = None
        transition_to('SPEAKING', data=_state_data)

    threading.Thread(target=_run_local_tts, name='local-tts', daemon=True).start()


def execute_local_command(command_type, action):
    if command_type == 'MOVE':
        if action == 'come':
            logger.info('Robot: ejecutando movimiento "ven aquí"')
            return "Voy hacia ti"
        elif action == 'stop':
            logger.info('Robot: ejecutando "detente"')
            return "Me he detenido"
        elif action == 'follow':
            logger.info('Robot: ejecutando "sígueme"')
            return "Te sigo"

    elif command_type == 'MEDICAL':
        if action == 'measure':
            logger.info('Robot: midiendo signos vitales...')
            return "Midiendo tus signos vitales"
        elif action == 'dispense':
            logger.info('Robot: dispensando medicamento...')
            return "Dispensando tu medicamento"

    elif command_type == 'CONTROL':
        if action == 'cancel':
            logger.info('Robot: cancelando')
            return None
        elif action == 'silence':
            logger.info('Robot: modo silencio')
            return None

    return None


def handle_processing_cloud(event):
    global _cloud_processing

    # Solo lanzar el thread si no hay uno en curso ya
    if _cloud_processing:
        return

    _cloud_processing = True

    # Capturar una copia de los datos actuales para pasarla al thread
    data_snapshot = dict(_state_data)

    def _run_cloud_pipeline():
        global _cloud_processing, _state_data

        try:
            audio_bytes = data_snapshot.get('audio_buffer')
            vosk_text = data_snapshot.get('text', '')

            # --- PASO 1: STT (Groq Whisper) ---
            transcribed_text = None

            if audio_bytes and len(audio_bytes) > 0:
                duration_s = len(audio_bytes) / (settings.SAMPLE_RATE * 2)  # int16 = 2 bytes
                logger.info(f'STT: transcribiendo {duration_s:.2f}s de audio...')
                transcribed_text, stt_meta = speech_to_text.transcribe(audio_bytes)

                if transcribed_text:
                    logger.info(f'STT OK: "{transcribed_text}" ({stt_meta.get("latency", 0):.2f}s)')
                else:
                    logger.warning(f'STT falló ({stt_meta.get("error")}), usando texto de Vosk como fallback')
                    transcribed_text = vosk_text

            if not transcribed_text:
                logger.error('Sin texto para procesar (STT y Vosk vacíos), volviendo a IDLE')
                _cloud_processing = False
                transition_to('IDLE')
                return

            _state_data['transcribed_text'] = transcribed_text

            # --- PASO 2: LLM (Groq) con contexto del paciente ---
            logger.info(f'LLM: procesando "{transcribed_text[:60]}..."')

            # Construir contexto del paciente usando el ID configurado
            patient_context = build_patient_context(patient_id=settings.DEFAULT_PATIENT_ID)
            if patient_context:
                logger.debug(f'Contexto del paciente incluido: {patient_context[:80]}...')

            llm_result = groq_llm.generate_response(
                user_text=transcribed_text,
                patient_context=patient_context if patient_context else None,
                remember=True  # Mantener memoria conversacional
            )

            if llm_result.get('success') and llm_result.get('response'):
                response_text = llm_result['response']
                turns_in_memory = llm_result.get('conversation_turns', 0)
                logger.info(f'LLM OK: "{response_text[:60]}..." ({llm_result.get("latency", 0):.2f}s, {turns_in_memory} turnos en memoria)')
            else:
                logger.error('LLM falló con todos los fallbacks')
                response_text = "Lo siento, no pude procesar tu solicitud en este momento. Por favor intenta de nuevo."

            _state_data['response_text'] = response_text

            # --- PASO 3: TTS (Azure) ---
            logger.info('TTS: sintetizando respuesta...')
            audio_response = text_to_speech.synthesize(response_text, style='empatico')

            if audio_response:
                logger.info(f'TTS OK: {len(audio_response)} bytes')
                _state_data['tts_audio'] = audio_response
                _state_data['tts_sample_rate'] = TTS_SAMPLE_RATE
                _state_data['needs_tts'] = False
            else:
                logger.warning('TTS falló, marcando para reintento en SPEAKING')
                _state_data['tts_audio'] = None
                _state_data['needs_tts'] = True

            transition_to('SPEAKING', data=_state_data)

        except Exception as e:
            logger.error(f'Error en pipeline cloud: {e}')
            transition_to('ERROR', data={'error': str(e)})
        finally:
            _cloud_processing = False

    thread = threading.Thread(target=_run_cloud_pipeline, name='cloud-pipeline', daemon=True)
    thread.start()


def handle_speaking(event):
    # SPEAKING_START: lanzar reproducción en thread separado (no bloquear la FSM)
    if event.type == 'SPEAKING_START':
        tts_audio = _state_data.get('tts_audio')
        response_text = _state_data.get('response_text', '')

        def _play_and_notify():
            try:
                if tts_audio:
                    sample_rate = _state_data.get('tts_sample_rate', TTS_SAMPLE_RATE)
                    playback.play_audio(tts_audio, sample_rate=sample_rate, blocking=True)
                elif response_text and _state_data.get('needs_tts', False):
                    # Fallback: sintetizar en el momento (solo si TTS no estaba listo)
                    logger.info(f'TTS tardío: "{response_text}"')
                    audio_response = text_to_speech.synthesize(response_text, style='amigable')
                    if audio_response:
                        playback.play_audio(audio_response, sample_rate=TTS_SAMPLE_RATE, blocking=True)
                    else:
                        dummy = generate_dummy_audio(response_text)
                        playback.play_audio(dummy, sample_rate=settings.SAMPLE_RATE, blocking=True)
            except Exception as e:
                logger.error(f'Error en reproducción: {e}')
            finally:
                put_event('PLAYBACK_DONE', source='speaking_thread')

        threading.Thread(target=_play_and_notify, name='speaking', daemon=True).start()
        return

    # PLAYBACK_DONE: la reproducción terminó → volver a IDLE
    if event.type == 'PLAYBACK_DONE':
        _state_data['tts_audio'] = None
        _state_data['needs_tts'] = False
        transition_to('IDLE')
        return



def handle_error(event):
    pass


def generate_dummy_audio(text):
    """Genera silencio como audio de emergencia cuando TTS falla completamente."""
    import numpy as np
    duration = min(len(text) * 0.05, 3.0)
    samples = int(settings.SAMPLE_RATE * duration)
    return np.zeros(samples, dtype=np.int16)


def initialize_cloud_modules():
    """
    Inicializa los módulos cloud (STT, LLM, TTS).
    Llamar antes de iniciar el loop principal.

    Returns:
        dict: {'stt': bool, 'llm': bool, 'tts': bool, 'all_ok': bool}
    """
    results = {}

    logger.info('Inicializando módulos cloud...')

    results['stt'] = speech_to_text.initialize()
    if results['stt']:
        logger.info('  [OK] STT (Groq Whisper) listo')
    else:
        logger.warning('  [X] STT fallo -- pipeline cloud usara fallback Vosk')

    results['llm'] = groq_llm.initialize()
    if results['llm']:
        logger.info('  [OK] LLM (Groq) listo')
    else:
        logger.warning('  [X] LLM fallo -- respuestas cloud no disponibles')

    results['tts'] = text_to_speech.initialize()
    if results['tts']:
        logger.info('  [OK] TTS (Azure Camila) listo')
    else:
        logger.warning('  [X] TTS fallo -- se usara audio sintetico de emergencia')

    results['all_ok'] = all(results.values())

    if results['all_ok']:
        logger.info('Modulos cloud: todos operativos [OK]')
    else:
        failed = [k for k, v in results.items() if k != 'all_ok' and not v]
        logger.warning(f'Modulos cloud: {failed} con problemas -- sistema continua en modo degradado')

    return results


def shutdown():
    global _current_state

    logger.info(f'FSM cerrando (estado actual: {_current_state})')
    logger.info(f'Total de transiciones: {_transition_count}')

    # Cerrar módulos cloud
    speech_to_text.shutdown()
    groq_llm.shutdown()
    text_to_speech.shutdown()

    _current_state = 'IDLE'