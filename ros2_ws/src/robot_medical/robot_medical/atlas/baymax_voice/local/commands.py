"""
Detección de comandos de voz offline usando Vosk.
Soporta detección en streaming y clasificación por patrones.
"""
import json
import vosk
from threading import Lock
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger
from baymax_voice.utils.events import put_event

logger = get_logger('local.commands')

_model = None
_recognizer = None
_last_partial = ""
_commands_lock = Lock()

COMMAND_PATTERNS = {
    'MOVE_COME':        ['ven aqui', 'ven aca', 'acercate', 'ven'],
    'MOVE_STOP':        ['detente', 'parate', 'alto', 'para', 'stop'],
    'MOVE_FOLLOW':      ['sigueme', 'sigues'],
    'MOVE_GO_KITCHEN':  ['ve a la cocina', 'ir a la cocina', 'cocina'],
    'MOVE_GO_ROOM':     ['ve al cuarto', 've a la habitacion', 'cuarto', 'habitacion'],
    'MEDICAL_MEASURE':  ['mide mis signos', 'mide los signos', 'signos vitales', 'toma mi presion', 'mide presion'],
    # Requieren verbo de acción explícito para evitar falsos positivos
    # con preguntas sobre medicamentos ("¿cuál es mi próximo medicamento?")
    'MEDICAL_DISPENSE': ['dame mi medicamento', 'dame la medicina', 'dame medicina',
                         'dispensa medicamento', 'necesito mi medicamento',
                         'quiero mi pastilla', 'dame mi pastilla'],
    'CONTROL_CANCEL':   ['cancela', 'olvidalo', 'olvida'],
    'CONTROL_SILENCE':  ['silencio', 'callate', 'calla']
}


def initialize(model_path):
    global _model, _recognizer

    if _model is not None:
        logger.debug('Comandos ya inicializados, omitiendo')
        return True

    try:
        vosk.SetLogLevel(-1)

        _model = vosk.Model(model_path)
        _recognizer = vosk.KaldiRecognizer(_model, settings.SAMPLE_RATE)
        _recognizer.SetWords(True)

        logger.info(f'Vosk inicializado ({len(COMMAND_PATTERNS)} comandos cargados)')
        return True

    except Exception as e:
        logger.error(f'Error inicializando Vosk: {e}')
        _model = None
        _recognizer = None
        return False


def process_audio_streaming(audio_data):
    global _last_partial

    if _recognizer is None:
        logger.error('Recognizer no inicializado')
        return None

    if audio_data is None or len(audio_data) == 0:
        return None

    try:
        if isinstance(audio_data, list):
            audio_bytes = bytes(audio_data)
        else:
            audio_bytes = audio_data.tobytes()

        with _commands_lock:
            if _recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(_recognizer.Result())
                text = result.get('text', '')

                if text:
                    command = classify_command(text)

                    if command and command['type'] != 'UNKNOWN':
                        put_event('COMMAND_DETECTED', data=command, source='commands')
                        logger.info(f'Comando: {command["type"]}/{command["action"]}')
                        return command

                    return command
            else:
                partial_result = json.loads(_recognizer.PartialResult())
                partial_text = partial_result.get('partial', '')

                if partial_text and partial_text != _last_partial:
                    _last_partial = partial_text
                    command = classify_command(partial_text)

                    if command and command['type'] != 'UNKNOWN':
                        put_event('COMMAND_DETECTED', data=command, source='commands')
                        logger.info(f'Comando: {command["type"]}/{command["action"]}')
                        return command

        return None

    except Exception as e:
        logger.error(f'Error procesando audio: {e}')
        return None


def finalize_audio():
    global _last_partial

    if _recognizer is None:
        return None

    try:
        with _commands_lock:
            result = json.loads(_recognizer.FinalResult())
            text = result.get('text', '')
            _last_partial = ""

        if text:
            command = classify_command(text)

            if command and command['type'] != 'UNKNOWN':
                put_event('COMMAND_DETECTED', data=command, source='commands')

            return command

        return None

    except Exception as e:
        logger.error(f'Error finalizando audio: {e}')
        return None


def classify_command(text: str):
    """Clasifica el texto en un comando conocido o UNKNOWN.

    Prioriza el patrón más largo (más específico) que aparezca en el texto.
    Requiere que el patrón esté rodeado de límites de palabra para evitar
    que 'ven' capture 'conveniente' o similares.
    """
    text_lower = text.lower().strip()

    if not text_lower:
        return None

    best_match = None
    best_score = 0

    for command_type, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                # Dar más peso a patrones que representan una fracción mayor del texto
                # para que frases largas no sean capturadas por palabras sueltas cortas
                coverage = len(pattern) / max(len(text_lower), 1)
                score = len(pattern) + (coverage * 10)
                if score > best_score:
                    best_score = score
                    best_match = command_type

    if best_match:
        command_category, command_action = best_match.split('_', 1)
        return {
            'type': command_category,
            'action': command_action.lower(),
            'raw_text': text,
            'matched_pattern': best_match,
            'confidence': min(0.95, 0.7 + (best_score / 30))
        }

    return {'type': 'UNKNOWN', 'raw_text': text}


def reset():
    global _recognizer, _last_partial

    if _model is None:
        return

    try:
        with _commands_lock:
            _recognizer = vosk.KaldiRecognizer(_model, settings.SAMPLE_RATE)
            _recognizer.SetWords(True)
            _last_partial = ""
        logger.debug('Recognizer reseteado')
    except Exception as e:
        logger.error(f'Error reseteando recognizer: {e}')


def shutdown():
    global _model, _recognizer, _last_partial

    with _commands_lock:
        _recognizer = None
        _model = None
        _last_partial = ""
    logger.info('Vosk cerrado')