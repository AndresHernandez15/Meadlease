"""
Síntesis de texto a voz usando Azure Neural TTS.

Optimizaciones activas:
  ✓ Synthesizer persistente (ahorro ~1193ms)
  ✓ Caché de frases frecuentes (hits en ~0ms)
  ✓ SSML con prosody por defecto (más natural, +73ms aceptable)

Voz actual: Camila (Perú) - es-PE-CamilaNeural
  - Seleccionada por equipo en benchmark 2026-03-03
  - Características: Alegre, simpática, dulce y cercana
  - Configuración: rate=0.92 (8% más lenta), sin modificaciones de pitch/volumen
"""
import azure.cognitiveservices.speech as speechsdk
from baymax_voice.config import settings
from baymax_voice.utils.logger import get_logger

logger = get_logger('cloud.tts')

_speech_config = None
_synthesizer: speechsdk.SpeechSynthesizer | None = None
_audio_cache: dict[str, bytes] = {}
_initialized = False

# Frases frecuentes que se pre-sintetizan al inicializar
CACHEABLE_PHRASES = [
    "Voy hacia donde estás.",
    "De acuerdo.",
    "Entendido.",
    "¿En qué puedo ayudarte?",
    "Lo siento, no entendí eso. ¿Puedes repetirlo?",
    "Un momento, por favor.",
    "Listo.",
]


def initialize():
    """
    Inicializa Azure Speech SDK para TTS.
    Idempotente: puede llamarse múltiples veces sin error.

    Aplica:
      - OPT-1: crea el SpeechSynthesizer persistente
      - OPT-2: pre-sintetiza frases frecuentes en caché

    Returns:
        bool: True si exitoso, False si error
    """
    global _speech_config, _synthesizer, _audio_cache, _initialized

    if _initialized:
        logger.debug('TTS ya inicializado, omitiendo')
        return True

    try:
        if not settings.AZURE_SPEECH_KEY:
            logger.error('AZURE_SPEECH_KEY no configurada')
            return False

        _speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        _speech_config.speech_synthesis_voice_name = settings.AZURE_TTS_VOICE
        # Raw24Khz16BitMonoPcm → mejor calidad para voces neurales
        _speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
        )

        # OPT-1: synthesizer persistente (evita re-handshake TLS en cada llamada)
        _synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=_speech_config,
            audio_config=None
        )

        _initialized = True
        logger.info(
            f'TTS inicializado (región: {settings.AZURE_SPEECH_REGION}, '
            f'voz: {settings.AZURE_TTS_VOICE}, formato: 24kHz, synthesizer: persistente)'
        )

        # OPT-2: pre-calentar caché con frases frecuentes
        _warmup_cache()

        return True

    except Exception as e:
        logger.error(f'Error inicializando TTS: {e}')
        _speech_config  = None
        _synthesizer    = None
        _audio_cache    = {}
        _initialized    = False
        return False


def _warmup_cache():
    """
    Pre-sintetiza CACHEABLE_PHRASES y las almacena en _audio_cache.
    Se llama una sola vez desde initialize(). Los errores no son fatales.
    """
    global _audio_cache

    logger.debug(f'Precalentando caché TTS ({len(CACHEABLE_PHRASES)} frases)...')
    ok = 0
    for phrase in CACHEABLE_PHRASES:
        try:
            result = _synthesizer.speak_text_async(phrase).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                _audio_cache[phrase] = result.audio_data
                ok += 1
        except Exception as e:
            logger.warning(f'No se pudo pre-sintetizar "{phrase[:30]}": {e}')

    logger.info(f'Caché TTS listo: {ok}/{len(CACHEABLE_PHRASES)} frases precalentadas')


# Presets de estilos SSML para diferentes contextos
# Optimizados para máxima naturalidad (basado en análisis 2026-03-03)
SSML_STYLES = {
    'normal': {
        'rate': '1.0',
        'pitch': '0%',
        'volume': '+0%',
        'description': 'Voz neutral sin modificaciones'
    },
    'amigable': {
        'rate': '0.92',
        'pitch': '+2%',
        'volume': '+3%',
        'description': 'Voz cálida y cercana'
    },
    'profesional': {
        'rate': '0.95',
        'pitch': '0%',
        'volume': '+0%',
        'description': 'Voz formal y clara'
    },
    'empatico': {
        'rate': '0.92',       # Reducción leve de velocidad (8% más lenta) para Camila
        'pitch': '0%',        # Sin modificación - voz natural
        'volume': '+0%',      # Sin modificación - voz natural
        'description': 'Voz natural con velocidad ligeramente reducida (Camila - Perú)'
    },
    'energico': {
        'rate': '1.05',
        'pitch': '+5%',
        'volume': '+8%',
        'description': 'Voz dinámica y entusiasta'
    },
    'calmado': {
        'rate': '0.85',
        'pitch': '-2%',
        'volume': '+0%',
        'description': 'Voz tranquila y relajada'
    }
}


def synthesize(text, style='empatico', use_ssml=True, improve_naturalness=True):
    """
    Sintetiza texto a audio usando Azure TTS.

    Optimizaciones activas:
      - OPT-2: si el texto está en caché devuelve bytes en ~0ms
      - OPT-1: usa el synthesizer persistente (sin re-handshake TLS)
      - use_ssml=True por defecto (más natural, +73ms aceptable)
      - improve_naturalness=True: convierte números/abreviaciones a texto

    Args:
        text:     str,  texto a sintetizar (máximo ~1000 caracteres)
        style:    str,  estilo SSML — solo aplicable si use_ssml=True
                        (normal, amigable, profesional, empatico, energico, calmado)
        use_ssml: bool, True  = SSML con prosody (más natural, +73ms) ← DEFAULT
                        False = texto plano (más rápido pero robótico)
        improve_naturalness: bool, True = mejora texto médico (números → palabras)

    Returns:
        bytes: audio PCM 16-bit mono 24kHz, o None si error
    """
    if not _initialized:
        logger.error('TTS no inicializado, llamar initialize() primero')
        return None

    if not text or not text.strip():
        logger.error('Texto vacío o None')
        return None

    text = text.strip()

    # Mejorar naturalidad de números y abreviaciones médicas
    if improve_naturalness:
        text_original = text
        text = improve_medical_text_naturalness(text)
        if text != text_original:
            logger.debug(f'Texto mejorado: "{text_original[:40]}" → "{text[:40]}"')

    if len(text) > 1000:
        logger.warning(f'Texto muy largo ({len(text)} chars), truncando a 1000')
        text = text[:997] + '...'

    # OPT-2: revisar caché antes de ir a la red
    if text in _audio_cache:
        logger.debug(f'TTS caché HIT: "{text[:40]}"')
        return bytes(_audio_cache[text])

    if style not in SSML_STYLES:
        logger.warning(f'Estilo "{style}" no reconocido, usando "empatico"')
        style = 'empatico'

    try:
        logger.debug(f'Sintetizando: "{text[:50]}..." ({len(text)} chars, ssml={use_ssml}, estilo={style})')

        # OPT-1 + OPT-3: synthesizer persistente + texto plano por defecto
        if use_ssml:
            sc = SSML_STYLES[style]
            ssml_text = (
                f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-CO">'
                f'<voice name="{settings.AZURE_TTS_VOICE}">'
                f'<prosody rate="{sc["rate"]}" pitch="{sc["pitch"]}" volume="{sc["volume"]}">'
                f'{text}'
                f'</prosody></voice></speak>'
            )
            result = _synthesizer.speak_ssml_async(ssml_text).get()
        else:
            result = _synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            logger.info(f'TTS éxito: {len(audio_data)} bytes ({len(text)} chars, 24kHz)')
            return audio_data

        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.error(f'TTS cancelado: {cancellation.reason}')
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f'Error TTS: {cancellation.error_details}')

            return None

        else:
            logger.error(f'TTS resultado inesperado: {result.reason}')
            return None

    except Exception as e:
        logger.error(f'Error en síntesis: {e}')
        return None


def synthesize_ssml(ssml_text):
    """
    Sintetiza texto usando SSML (Speech Synthesis Markup Language).
    Permite mayor control sobre prosodia, velocidad, tono, pausas, etc.
    Usa el synthesizer persistente (OPT-1).

    Args:
        ssml_text: str, texto en formato SSML

    Returns:
        bytes: audio PCM 16-bit mono 24kHz, o None si error
    """
    if not _initialized:
        logger.error('TTS no inicializado')
        return None

    if not ssml_text or not ssml_text.strip():
        logger.error('SSML vacío o None')
        return None

    try:
        logger.debug(f'Sintetizando SSML ({len(ssml_text)} chars)')
        result = _synthesizer.speak_ssml_async(ssml_text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(f'TTS SSML éxito: {len(result.audio_data)} bytes')
            return result.audio_data
        else:
            logger.error(f'TTS SSML falló: {result.reason}')
            return None

    except Exception as e:
        logger.error(f'Error en síntesis SSML: {e}')
        return None


def create_ssml_with_pauses(text, pause_after_sentences='300ms', pause_after_commas='200ms'):
    """
    Crea SSML automáticamente agregando pausas después de puntos y comas.

    Args:
        text: str, texto a sintetizar
        pause_after_sentences: str, pausa después de punto (ej: '300ms', '500ms')
        pause_after_commas: str, pausa después de coma (ej: '200ms', '300ms')

    Returns:
        str: texto en formato SSML con pausas

    Ejemplo:
        ssml = create_ssml_with_pauses("Hola. ¿Cómo estás?")
        audio = synthesize_ssml(ssml)
    """
    # Reemplazar puntos y comas con pausas SSML
    text_with_pauses = text.replace('. ', f'. <break time="{pause_after_sentences}"/> ')
    text_with_pauses = text_with_pauses.replace(', ', f', <break time="{pause_after_commas}"/> ')

    ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-CO">
        <voice name="{settings.AZURE_TTS_VOICE}">
            <prosody rate="0.90" pitch="+2%">
                {text_with_pauses}
            </prosody>
        </voice>
    </speak>'''

    return ssml


def get_available_styles():
    """
    Obtiene lista de estilos SSML disponibles.

    Returns:
        dict: Diccionario con estilos y sus descripciones
    """
    return {k: v['description'] for k, v in SSML_STYLES.items()}


def get_style_config(style='empatico'):
    """
    Obtiene configuración de un estilo específico.

    Args:
        style: str, nombre del estilo

    Returns:
        dict: Configuración del estilo (rate, pitch, volume)
    """
    return SSML_STYLES.get(style, SSML_STYLES['empatico'])


def get_available_voices():
    """
    Obtiene lista de voces disponibles para español colombiano.

    Returns:
        list: Lista de nombres de voces
    """
    return [
        'es-CO-SalomeNeural',   # Femenina (empática, cálida)
        'es-CO-GonzaloNeural',  # Masculina (profesional)
    ]


def get_voice_info():
    """
    Obtiene información de la voz configurada actualmente.

    Returns:
        dict: Información de la voz
    """
    return {
        'voice': settings.AZURE_TTS_VOICE,
        'language': 'es-CO',
        'gender': 'Female' if 'Salome' in settings.AZURE_TTS_VOICE else 'Male',
        'style': 'Neural (empática)' if 'Salome' in settings.AZURE_TTS_VOICE else 'Neural (profesional)',
    }


def estimate_duration(text):
    """
    Estima la duración del audio en segundos.
    Aproximación: ~150 palabras por minuto en español.

    Args:
        text: str, texto a sintetizar

    Returns:
        float: Duración estimada en segundos
    """
    words = len(text.split())
    return (words / 150) * 60


def improve_medical_text_naturalness(text: str) -> str:
    """
    Mejora la naturalidad del texto médico para TTS.

    Convierte:
    - Números a texto escrito
    - Abreviaciones médicas a texto completo
    - Símbolos a palabras

    Args:
        text: Texto original con números y abreviaciones

    Returns:
        str: Texto optimizado para síntesis natural

    Ejemplos:
        "78 BPM" → "setenta y ocho pulsaciones por minuto"
        "98% SpO2" → "noventa y ocho por ciento de saturación de oxígeno"
        "36.5°C" → "treinta y seis punto cinco grados centígrados"
    """
    import re

    # Diccionario de números (0-100)
    numeros = {
        '0': 'cero', '1': 'uno', '2': 'dos', '3': 'tres', '4': 'cuatro',
        '5': 'cinco', '6': 'seis', '7': 'siete', '8': 'ocho', '9': 'nueve',
        '10': 'diez', '11': 'once', '12': 'doce', '13': 'trece', '14': 'catorce',
        '15': 'quince', '16': 'dieciséis', '17': 'diecisiete', '18': 'dieciocho',
        '19': 'diecinueve', '20': 'veinte', '21': 'veintiuno', '22': 'veintidós',
        '23': 'veintitrés', '24': 'veinticuatro', '25': 'veinticinco',
        '26': 'veintiséis', '27': 'veintisiete', '28': 'veintiocho',
        '29': 'veintinueve', '30': 'treinta', '40': 'cuarenta', '50': 'cincuenta',
        '60': 'sesenta', '70': 'setenta', '80': 'ochenta', '90': 'noventa',
        '100': 'cien'
    }

    def numero_a_texto(n: int) -> str:
        """Convierte número entero a texto."""
        if str(n) in numeros:
            return numeros[str(n)]
        elif 30 <= n < 100:
            decena = (n // 10) * 10
            unidad = n % 10
            return f"{numeros[str(decena)]} y {numeros[str(unidad)]}"
        return str(n)

    # Patrones de reemplazo para términos médicos
    replacements = [
        # BPM (pulsaciones)
        (r'(\d+)\s*BPM', lambda m: f"{numero_a_texto(int(m.group(1)))} pulsaciones por minuto"),
        (r'(\d+)\s*bpm', lambda m: f"{numero_a_texto(int(m.group(1)))} pulsaciones por minuto"),

        # SpO2 (saturación de oxígeno)
        (r'(\d+)%?\s*SpO2', lambda m: f"{numero_a_texto(int(m.group(1)))} por ciento de saturación de oxígeno"),
        (r'(\d+)%?\s*spo2', lambda m: f"{numero_a_texto(int(m.group(1)))} por ciento de saturación de oxígeno"),

        # Temperatura
        (r'(\d+)\.(\d+)\s*°?C', lambda m: f"{numero_a_texto(int(m.group(1)))} punto {m.group(2)} grados centígrados"),
        (r'(\d+)\.(\d+)\s*grados', lambda m: f"{numero_a_texto(int(m.group(1)))} punto {m.group(2)} grados"),

        # Porcentajes generales
        (r'(\d+)%', lambda m: f"{numero_a_texto(int(m.group(1)))} por ciento"),

        # Horas
        (r'(\d{1,2}):(\d{2})', lambda m: f"{numero_a_texto(int(m.group(1)))} y {m.group(2)} minutos" if m.group(2) != '00' else f"{numero_a_texto(int(m.group(1)))} en punto"),
    ]

    # Aplicar reemplazos
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)

    return result


def is_initialized():
    """
    Verifica si TTS está inicializado.

    Returns:
        bool: True si inicializado
    """
    return _initialized


def get_state():
    """
    Obtiene estado actual del módulo TTS.

    Returns:
        dict: Estado del módulo
    """
    return {
        'initialized':       _initialized,
        'region':            settings.AZURE_SPEECH_REGION if _initialized else None,
        'voice':             settings.AZURE_TTS_VOICE if _initialized else None,
        'format':            'PCM 24kHz 16-bit mono (Neural optimizado)' if _initialized else None,
        'synthesizer':       'persistente (OPT-1)' if _synthesizer else None,
        'cache_entries':     len(_audio_cache),
        'cached_phrases':    list(_audio_cache.keys()) if _audio_cache else [],
    }


def add_to_cache(text: str) -> bool:
    """
    Añade una frase al caché en tiempo de ejecución (sin reiniciar).
    Útil para pre-sintetizar respuestas frecuentes descubiertas en runtime.

    Args:
        text: str, frase a añadir al caché

    Returns:
        bool: True si se añadió correctamente
    """
    if not _initialized:
        logger.error('TTS no inicializado')
        return False

    if text in _audio_cache:
        logger.debug(f'"{text[:40]}" ya está en caché')
        return True

    try:
        result = _synthesizer.speak_text_async(text.strip()).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            _audio_cache[text.strip()] = result.audio_data
            logger.info(f'Añadido al caché: "{text[:40]}"')
            return True
        return False
    except Exception as e:
        logger.error(f'Error añadiendo al caché: {e}')
        return False


def shutdown():
    """
    Libera recursos de Azure TTS.
    """
    global _speech_config, _synthesizer, _audio_cache, _initialized

    try:
        _synthesizer    = None
        _speech_config  = None
        _audio_cache    = {}
        _initialized    = False
        logger.info('TTS cerrado')
    except Exception as e:
        logger.warning(f'Error cerrando TTS: {e}')
    finally:
        _synthesizer    = None
        _speech_config  = None
        _audio_cache    = {}
        _initialized    = False

