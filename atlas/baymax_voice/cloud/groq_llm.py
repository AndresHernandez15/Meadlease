"""
Cliente LLM conversacional con Groq.
Incluye memoria conversacional (4 turnos) y sistema de fallback.
"""
import time
import threading
from collections import deque
from groq import Groq
from baymax_voice.cloud.llm_config import (
    GROQ_API_KEY,
    GROQ_API_KEY_BACKUP,
    GROQ_MODEL,
    GROQ_FALLBACK_MODELS,
    SYSTEM_PROMPT,
    MAX_TOKENS,
    TEMPERATURE,
    CONVERSATION_MEMORY_TURNS
)
from baymax_voice.utils.logger import get_logger

logger = get_logger('cloud.groq')

_client = None
_client_backup = None
_using_backup = False

# Memoria conversacional thread-safe
_conversation_history = deque(maxlen=CONVERSATION_MEMORY_TURNS * 2)
_history_lock = threading.Lock()


def initialize():
    global _client, _client_backup

    if _client is not None:
        logger.debug('Groq client ya inicializado')
        return True

    try:
        _client = Groq(api_key=GROQ_API_KEY)
        logger.info(f'Groq inicializado: {GROQ_MODEL} + {len(GROQ_FALLBACK_MODELS)} fallbacks')

        if GROQ_API_KEY_BACKUP:
            _client_backup = Groq(api_key=GROQ_API_KEY_BACKUP)
            logger.info('Backup API key configurada')
        else:
            logger.warning('Sin backup API key')

        logger.info(f'Memoria conversacional: {CONVERSATION_MEMORY_TURNS} turnos')
        return True
    except Exception as e:
        logger.error(f'Error inicializando Groq: {e}')
        return False


def clear_conversation_history():
    """
    Limpia el historial de conversación.
    Útil para empezar una nueva sesión conversacional.
    """
    global _conversation_history
    with _history_lock:
        _conversation_history.clear()
        logger.info('Historial conversacional limpiado')


def get_conversation_turns():
    """
    Obtiene el número de turnos (pares user+assistant) en memoria.

    Returns:
        int: Número de turnos conversacionales
    """
    with _history_lock:
        return len(_conversation_history) // 2


def _build_messages_with_history(user_text: str, context: str = None):
    """
    Construye la lista de mensajes incluyendo historial conversacional.

    Args:
        user_text: Texto actual del usuario
        context: Contexto adicional del paciente (opcional)

    Returns:
        list: Lista de mensajes para enviar a la API
    """
    messages = []

    # System prompt (siempre primero)
    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"\n\nCONTEXTO DEL PACIENTE:\n{context}"

    messages.append({"role": "system", "content": system_content})

    # Historial conversacional (si existe)
    with _history_lock:
        if _conversation_history:
            messages.extend(_conversation_history)
            logger.debug(f'Incluyendo {len(_conversation_history)} mensajes de historial')

    # Mensaje actual del usuario
    messages.append({"role": "user", "content": user_text})

    return messages


def _add_to_history(user_text: str, assistant_response: str):
    """
    Agrega un turno conversacional al historial.

    Args:
        user_text: Texto del usuario
        assistant_response: Respuesta del asistente
    """
    with _history_lock:
        _conversation_history.append({"role": "user", "content": user_text})
        _conversation_history.append({"role": "assistant", "content": assistant_response})

        current_turns = len(_conversation_history) // 2
        logger.debug(f'Historial actualizado: {current_turns}/{CONVERSATION_MEMORY_TURNS} turnos')


def _try_model(model_name, messages, use_backup_key=False):
    """
    Intenta generar respuesta con un modelo específico.

    Args:
        model_name: Nombre del modelo
        messages: Lista de mensajes (incluye system, historial y user actual)
        use_backup_key: Si True, usa la segunda API key

    Returns:
        dict con resultado o None si falla
    """
    global _using_backup

    client = _client_backup if (use_backup_key and _client_backup) else _client
    key_label = "backup" if use_backup_key else "principal"

    if not client:
        logger.warning(f'Cliente {key_label} no disponible')
        return None

    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )

        latency = time.time() - start_time

        answer = response.choices[0].message.content.strip()
        tokens_input = response.usage.prompt_tokens
        tokens_output = response.usage.completion_tokens

        logger.info(f'Groq ({model_name}, key: {key_label}): "{answer[:50]}..." ({latency:.2f}s, in:{tokens_input} out:{tokens_output})')
        _using_backup = use_backup_key

        return {
            'response': answer,
            'latency': latency,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'model': model_name,
            'api_key_used': key_label,
            'success': True
        }

    except Exception as e:
        latency = time.time() - start_time
        error_msg = str(e)

        is_rate_limit = 'rate_limit' in error_msg.lower() or '429' in error_msg

        if is_rate_limit:
            logger.warning(f'Rate limit alcanzado en {model_name} (key: {key_label})')
        else:
            logger.warning(f'Modelo {model_name} (key: {key_label}) falló: {error_msg[:60]}')

        return None


def generate_response(user_text: str, patient_context: str = None, remember: bool = True):
    """
    Genera respuesta usando Groq con fallback automático inteligente y memoria conversacional.

    Estrategia de fallback (solo Groq con 2 API keys):
    1. Modelo principal (70B) con API key principal
    2. Si falla por rate limit → Modelo principal con API key backup
    3. Si falla → Fallback 1 con API key principal
    4. Si falla por rate limit → Fallback 1 con API key backup
    5. Si falla → Fallback 2 con API key principal
    6. Si falla por rate limit → Fallback 2 con API key backup
    7. Si todo falla → Error

    Args:
        user_text: str, consulta del usuario
        patient_context: str, contexto adicional del paciente (opcional)
                        Ejemplo: "Paciente: Juan, Próxima dosis: Losartán 08:00"
        remember: bool, si True agrega este turno al historial conversacional (default: True)

    Returns:
        dict: {
            'response': str,
            'latency': float (segundos),
            'tokens_input': int,
            'tokens_output': int,
            'model': str,
            'api_key_used': str ('principal' o 'backup'),
            'success': bool,
            'fallback_used': bool,
            'conversation_turns': int (número de turnos en memoria)
        }
    """
    if _client is None:
        if not initialize():
            return {
                'response': None,
                'latency': 0.0,
                'tokens_input': 0,
                'tokens_output': 0,
                'model': GROQ_MODEL,
                'api_key_used': 'principal',
                'success': False,
                'fallback_used': False,
                'conversation_turns': 0
            }

    # Construir mensajes con historial y contexto
    messages = _build_messages_with_history(user_text, patient_context)

    # Lista de modelos a probar
    models_to_try = [GROQ_MODEL] + GROQ_FALLBACK_MODELS

    # Intentar cada modelo con ambas API keys
    for model_idx, model_name in enumerate(models_to_try):
        # Intentar con API key principal
        result = _try_model(model_name, messages, use_backup_key=False)
        if result:
            result['fallback_used'] = (model_idx > 0)
            result['fallback_level'] = model_idx
            result['conversation_turns'] = get_conversation_turns()

            # Agregar al historial si se solicita
            if remember and result['response']:
                _add_to_history(user_text, result['response'])
                result['conversation_turns'] = get_conversation_turns()

            return result

        # Si falla y hay backup key, intentar con backup
        if _client_backup:
            logger.info(f'Intentando {model_name} con API key backup...')
            result = _try_model(model_name, messages, use_backup_key=True)
            if result:
                result['fallback_used'] = True
                result['fallback_level'] = model_idx
                result['conversation_turns'] = get_conversation_turns()
                logger.info(f'Éxito con backup key en {model_name}')

                # Agregar al historial si se solicita
                if remember and result['response']:
                    _add_to_history(user_text, result['response'])
                    result['conversation_turns'] = get_conversation_turns()

                return result

    # Todo falló
    logger.error('Todos los modelos Groq con ambas API keys fallaron')
    return {
        'response': None,
        'latency': 0.0,
        'tokens_input': 0,
        'tokens_output': 0,
        'model': GROQ_MODEL,
        'api_key_used': 'none',
        'success': False,
        'fallback_used': True,
        'fallback_level': len(models_to_try),
        'conversation_turns': get_conversation_turns()
    }


def shutdown():
    global _client
    if _client is not None:
        logger.info('Groq client cerrado')
        _client = None

    # Limpiar historial conversacional
    clear_conversation_history()

