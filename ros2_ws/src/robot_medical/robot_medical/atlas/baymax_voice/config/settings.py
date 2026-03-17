"""
Configuración centralizada del proyecto Baymax.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carga el archivo .env desde la raíz del proyecto (atlas/) de forma explícita
_current_file = Path(__file__).resolve()
_config_dir = _current_file.parent
_baymax_voice_dir = _config_dir.parent
_atlas_dir = _baymax_voice_dir.parent
load_dotenv(dotenv_path=_atlas_dir / '.env')

PROJECT_ROOT = str(_atlas_dir)

# Logging
LOG_LEVEL = 'DEBUG'
LOG_TO_FILE = False

# Idioma
LANGUAGE = 'es-ES'
WAKE_WORD = 'atlas'

# Porcupine
PORCUPINE_ACCESS_KEY = os.getenv('PORCUPINE_ACCESS_KEY', '')
PORCUPINE_KEYWORD_PATH = os.path.join(PROJECT_ROOT, 'baymax_voice', 'data', 'models', 'Atlas_es_windows_v4_0_0.ppn')
PORCUPINE_MODEL_PATH = os.path.join(PROJECT_ROOT, 'baymax_voice', 'data', 'models', 'porcupine_params_es.pv')
PORCUPINE_SENSITIVITY = 0.5

# Vosk
VOSK_MODEL_PATH = os.path.join(PROJECT_ROOT, 'baymax_voice', 'data', 'models', 'vosk-model-small-es-0.42')

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 320

# VAD
VAD_AGGRESSIVENESS = 2
VAD_SILENCE_DURATION = 1.5

# Filtro de ruido
NOISE_CALIBRATION_DURATION = 2.0
NOISE_THRESHOLD_MULTIPLIER = 1.5
NOISE_REDUCTION_FACTOR = 0.3

# Audio paths
CONFIRMATION_AUDIO_PATH = os.path.join(PROJECT_ROOT, 'data', 'audio', 'confirmation.wav')

# Timeouts
MAX_LISTENING_TIME = 10.0
AUDIO_MIN_DURATION = 0.5
MAX_BUFFER_DURATION = 30.0
POST_BEEP_SILENCE = 0.15   # Pausa tras el beep para que el eco del altavoz se disipe

# Privacidad
PRIVACY_MODE = True

# Azure Speech Service (STT + TTS)
AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY', '')
AZURE_SPEECH_REGION = 'eastus'
AZURE_STT_LANGUAGE = 'es-CO'
AZURE_STT_MIN_CONFIDENCE = 0.6
AZURE_TTS_VOICE = 'es-PE-CamilaNeural'  # Camila (Perú) - Ganadora benchmark 2026-03-03
AZURE_MAX_REQUESTS_PER_MINUTE = 20

# ── Configuración de Paciente ──
DEFAULT_PATIENT_ID = 1  # Juan Pérez (datos de prueba)


def validate_paths():
    """
    Valida que todos los recursos necesarios existan y estén configurados.

    Returns:
        list: Lista de errores encontrados (vacía si todo OK)
    """
    errors = []

    # Validar rutas de modelos locales
    if not os.path.exists(PORCUPINE_KEYWORD_PATH):
        errors.append(f'Porcupine keyword no encontrado: {PORCUPINE_KEYWORD_PATH}')

    if not os.path.exists(PORCUPINE_MODEL_PATH):
        errors.append(f'Porcupine model no encontrado: {PORCUPINE_MODEL_PATH}')

    if not os.path.exists(VOSK_MODEL_PATH):
        errors.append(f'Vosk model no encontrado: {VOSK_MODEL_PATH}')

    # Validar parámetros de audio
    if not 0 <= VAD_AGGRESSIVENESS <= 3:
        errors.append(f'VAD aggressiveness debe estar en [0, 3]: {VAD_AGGRESSIVENESS}')

    if not 0.0 <= PORCUPINE_SENSITIVITY <= 1.0:
        errors.append(f'Porcupine sensitivity debe estar en [0.0, 1.0]: {PORCUPINE_SENSITIVITY}')

    if CHUNK_SIZE <= 0 or CHUNK_SIZE > SAMPLE_RATE:
        errors.append(f'CHUNK_SIZE inválido: {CHUNK_SIZE}')

    if SAMPLE_RATE <= 0:
        errors.append(f'SAMPLE_RATE inválido: {SAMPLE_RATE}')

    # Validar configuración de Azure (warning, no error crítico)
    if not AZURE_SPEECH_KEY:
        errors.append('WARNING: AZURE_SPEECH_KEY no configurada (necesaria para cloud)')

    if AZURE_SPEECH_REGION not in ['brazilsouth', 'eastus', 'westus', 'westeurope']:
        errors.append(f'WARNING: Región Azure inusual: {AZURE_SPEECH_REGION}')

    return errors

