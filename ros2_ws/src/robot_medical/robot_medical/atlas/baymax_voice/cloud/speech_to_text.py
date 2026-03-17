"""
Transcripción de audio a texto usando Groq Whisper.
"""
from groq import Groq
from baymax_voice.cloud import llm_config
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger
import time
import io
import wave

logger = get_logger('cloud.stt')

_client_primary = None
_client_backup = None
_initialized = False

WHISPER_MODELS = [
    'whisper-large-v3-turbo',  # Más rápido
    'whisper-large-v3',        # Más preciso
]


def initialize():
    """
    Inicializa clientes de Groq para Whisper.
    Idempotente: puede llamarse múltiples veces sin error.

    Returns:
        bool: True si al menos un cliente fue inicializado
    """
    global _client_primary, _client_backup, _initialized

    if _initialized:
        logger.debug('Groq Whisper ya inicializado, omitiendo')
        return True

    success_count = 0

    # Inicializar cliente principal
    try:
        if llm_config.GROQ_API_KEY:
            _client_primary = Groq(api_key=llm_config.GROQ_API_KEY)
            logger.info('Groq Whisper (principal) inicializado')
            success_count += 1
        else:
            logger.warning('GROQ_API_KEY no configurada')
    except Exception as e:
        logger.error(f'Error inicializando cliente principal: {e}')
        _client_primary = None

    # Inicializar cliente backup
    try:
        if llm_config.GROQ_API_KEY_BACKUP:
            _client_backup = Groq(api_key=llm_config.GROQ_API_KEY_BACKUP)
            logger.info('Groq Whisper (backup) inicializado')
            success_count += 1
        else:
            logger.debug('GROQ_API_KEY_BACKUP no configurada (opcional)')
    except Exception as e:
        logger.error(f'Error inicializando cliente backup: {e}')
        _client_backup = None

    if success_count == 0:
        logger.error('No se pudo inicializar ningún cliente de Groq Whisper')
        return False

    _initialized = True
    logger.info(f'Groq Whisper inicializado ({success_count} cliente(s))')
    return True


def transcribe(audio_bytes, language='es'):
    """
    Transcribe audio a texto usando Groq Whisper con fallback.

    Args:
        audio_bytes: bytes, audio en cualquier formato (preferible WAV/MP3)
        language: str, código de idioma (default: 'es' para español)

    Returns:
        tuple: (texto, metadata)
            - texto: str, transcripción o None si error
            - metadata: dict con información adicional

    Ejemplo:
        text, meta = transcribe(audio_data)
        if text:
            print(f"Usuario: {text}")
            print(f"Modelo: {meta['model']}")
            print(f"Latencia: {meta['latency']:.2f}s")
    """
    if not _initialized:
        logger.error('Groq Whisper no inicializado, llamar initialize() primero')
        return None, {'success': False, 'error': 'not_initialized'}

    if audio_bytes is None or len(audio_bytes) == 0:
        logger.error('audio_bytes vacío o None')
        return None, {'success': False, 'error': 'empty_audio'}

    # Intentar transcripción con fallback
    return _transcribe_with_fallback(audio_bytes, language)


def _transcribe_with_fallback(audio_bytes, language):
    """
    Intenta transcribir con sistema de fallback completo.

    Niveles de fallback (ordenado por velocidad):
    1. whisper-large-v3 + API Key Principal       (~0.9s)
    2. whisper-large-v3 + API Key Backup          (~0.9s)
    3. whisper-large-v3-turbo + API Key Principal (~2.3s)
    4. whisper-large-v3-turbo + API Key Backup    (~2.3s)

    Nota: Contrario a lo esperado, v3 es más rápido que turbo en Groq.
    """
    attempts = []

    for model in WHISPER_MODELS:
        # Intentar con cliente principal
        if _client_primary:
            result = _try_transcribe(_client_primary, audio_bytes, model, language, 'principal')
            attempts.append(result)

            if result['success']:
                _log_success(result, len(attempts))
                return result['text'], result

        # Intentar con cliente backup
        if _client_backup:
            result = _try_transcribe(_client_backup, audio_bytes, model, language, 'backup')
            attempts.append(result)

            if result['success']:
                _log_success(result, len(attempts))
                return result['text'], result

    # Todos los intentos fallaron
    logger.error(f'Groq Whisper: Todos los intentos fallaron ({len(attempts)} intentos)')
    return None, {
        'success': False,
        'error': 'all_attempts_failed',
        'attempts': attempts
    }


def _try_transcribe(client, audio_bytes, model, language, api_key_name):
    """
    Intenta transcribir con un cliente y modelo específico.
    """
    start_time = time.time()

    try:
        # Convertir PCM raw a WAV
        wav_buffer = _convert_pcm_to_wav(
            audio_bytes,
            sample_rate=settings.SAMPLE_RATE,
            channels=settings.CHANNELS,
            sample_width=2  # 16-bit = 2 bytes
        )

        # Crear un nuevo BytesIO con el contenido completo del WAV
        # Esto es necesario porque Groq necesita el tamaño total del archivo
        wav_bytes = wav_buffer.getvalue()
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "audio.wav"  # Groq necesita un nombre de archivo

        logger.debug(f'Intentando: {model} (key: {api_key_name})')

        # Transcribir
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            language=language,
            response_format="verbose_json"  # Incluye más metadata
        )

        latency = time.time() - start_time

        text = transcription.text.strip()

        if not text:
            logger.warning(f'{model} ({api_key_name}): Transcripción vacía')
            return {
                'success': False,
                'error': 'empty_transcription',
                'model': model,
                'api_key_used': api_key_name,
                'latency': latency
            }

        # Éxito
        return {
            'success': True,
            'text': text,
            'model': model,
            'api_key_used': api_key_name,
            'latency': latency,
            'language': transcription.language if hasattr(transcription, 'language') else language,
            'duration': transcription.duration if hasattr(transcription, 'duration') else None,
        }

    except Exception as e:
        latency = time.time() - start_time
        error_msg = str(e)

        # Detectar rate limit
        if _is_rate_limit_error(error_msg):
            logger.warning(f'{model} ({api_key_name}): Rate limit alcanzado')
            return {
                'success': False,
                'error': 'rate_limit',
                'model': model,
                'api_key_used': api_key_name,
                'latency': latency
            }
        else:
            logger.error(f'{model} ({api_key_name}): Error - {error_msg}')
            return {
                'success': False,
                'error': error_msg,
                'model': model,
                'api_key_used': api_key_name,
                'latency': latency
            }


def _is_rate_limit_error(error_msg):
    """
    Detecta si el error es por rate limit.
    """
    rate_limit_indicators = [
        'rate_limit',
        '429',
        'too many requests',
        'resource exhausted',
        'quota'
    ]

    error_lower = error_msg.lower()
    return any(indicator in error_lower for indicator in rate_limit_indicators)


def _convert_pcm_to_wav(pcm_bytes, sample_rate=16000, channels=1, sample_width=2):
    """
    Convierte bytes PCM raw a formato WAV.

    Args:
        pcm_bytes: bytes, audio PCM raw
        sample_rate: int, frecuencia de muestreo (default 16000)
        channels: int, número de canales (default 1 = mono)
        sample_width: int, bytes por muestra (default 2 = 16-bit)

    Returns:
        io.BytesIO: Archivo WAV en memoria
    """
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)

    wav_buffer.seek(0)
    return wav_buffer



def _log_success(result, attempt_number):
    """
    Log de transcripción exitosa.
    """
    if attempt_number == 1:
        logger.info(
            f'Groq Whisper: "{result["text"][:50]}..." '
            f'({result["model"]}, {result["api_key_used"]}, {result["latency"]:.2f}s)'
        )
    else:
        logger.info(
            f'Groq Whisper: Éxito con fallback (intento {attempt_number}) - '
            f'{result["model"]} ({result["api_key_used"]}, {result["latency"]:.2f}s)'
        )


def get_supported_languages():
    """
    Obtiene lista de idiomas soportados por Whisper.

    Returns:
        list: Lista de códigos de idioma ISO-639-1
    """
    # Whisper soporta 99 idiomas
    # Aquí listamos los más comunes
    return [
        'es',  # Español
        'en',  # Inglés
        'pt',  # Portugués
        'fr',  # Francés
        'de',  # Alemán
        'it',  # Italiano
        'ja',  # Japonés
        'ko',  # Coreano
        'zh',  # Chino
        'ru',  # Ruso
    ]


def get_available_models():
    """
    Obtiene lista de modelos Whisper disponibles en Groq.

    Returns:
        list: Lista de modelos
    """
    return WHISPER_MODELS.copy()


def is_initialized():
    """
    Verifica si Groq Whisper está inicializado.

    Returns:
        bool: True si inicializado
    """
    return _initialized


def get_state():
    """
    Obtiene estado actual del módulo.

    Returns:
        dict: Estado del módulo
    """
    return {
        'initialized': _initialized,
        'primary_client': _client_primary is not None,
        'backup_client': _client_backup is not None,
        'models': WHISPER_MODELS,
        'default_language': 'es'
    }


def shutdown():
    """
    Libera recursos de STT.
    """
    global _client_primary, _client_backup, _initialized

    try:
        _client_primary = None
        _client_backup = None
        _initialized = False
        logger.info('STT cerrado')
    except Exception as e:
        logger.warning(f'Error cerrando STT: {e}')
    finally:
        _client_primary = None
        _client_backup = None
        _initialized = False

