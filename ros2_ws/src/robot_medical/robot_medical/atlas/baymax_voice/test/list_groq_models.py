"""
Listar todos los modelos LLM activos disponibles en Groq.
Filtra modelos de tipo STT/TTS/Whisper y muestra solo candidatos LLM.

Uso:
    python baymax_voice/test/list_groq_models.py
"""

import sys
import os
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud.llm_config import GROQ_API_KEY

# ── Colores ANSI ──────────────────────────────────────────────────────────
GREEN  = '\033[92m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

# Palabras clave para excluir modelos no-LLM
EXCLUDE_KEYWORDS = ['whisper', 'tts', 'stt', 'speech', 'audio', 'vision', 'guard']

def list_groq_models():
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  MODELOS DISPONIBLES EN GROQ API{RESET}")
    print(f"{'═'*60}\n")

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error al consultar la API: {response.status_code}")
        print(response.text)
        return []

    data = response.json()
    all_models = data.get('data', [])

    print(f"  Total modelos en API: {len(all_models)}\n")

    # Separar LLM de no-LLM
    llm_models = []
    excluded_models = []

    for model in sorted(all_models, key=lambda x: x.get('id', '')):
        model_id = model.get('id', '').lower()
        is_excluded = any(kw in model_id for kw in EXCLUDE_KEYWORDS)

        if is_excluded:
            excluded_models.append(model.get('id', ''))
        else:
            llm_models.append(model.get('id', ''))

    # Mostrar modelos LLM
    print(f"{BOLD}{GREEN}  ✅ MODELOS LLM CANDIDATOS ({len(llm_models)}):{RESET}")
    print(f"  {'─'*50}")
    for i, model_id in enumerate(llm_models, 1):
        print(f"  {i:2}. {CYAN}{model_id}{RESET}")

    # Mostrar excluidos
    print(f"\n{BOLD}{YELLOW}  ⚠️  MODELOS EXCLUIDOS (no-LLM) ({len(excluded_models)}):{RESET}")
    print(f"  {'─'*50}")
    for model_id in excluded_models:
        print(f"      - {model_id}")

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"  Modelos LLM disponibles para benchmark: {len(llm_models)}")
    print(f"{'═'*60}\n")

    return llm_models


if __name__ == '__main__':
    models = list_groq_models()
    print("\nCopia esta lista para usarla en benchmark_llm_models.py:")
    print("MODELS_TO_TEST = [")
    for m in models:
        print(f"    '{m}',")
    print("]")

