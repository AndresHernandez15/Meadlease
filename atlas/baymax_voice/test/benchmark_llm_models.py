"""
Benchmark Multi-Modelo LLM — Groq
===================================
Mide latencia real de cada modelo candidato para reemplazar
'llama-4-maverick-17b-128e-instruct' (deprecado 9 marzo 2026).

Uso:
    python baymax_voice/test/benchmark_llm_models.py

Genera: baymax_voice/test/benchmark_llm_models_results.json
"""

import sys
import os
import time
import json
import statistics
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud.llm_config import (
    GROQ_API_KEY, SYSTEM_PROMPT, MAX_TOKENS, TEMPERATURE
)

# ── Colores ANSI ──────────────────────────────────────────────────────────
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
CYAN   = '\033[96m'
MAGENTA = '\033[95m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

# ── Frases de prueba (mismas que benchmark_latency.py) ────────────────────
TEST_PHRASES = [
    "¿Cuándo es mi próxima dosis de medicamento?",
    "Me duele la cabeza, ¿qué hago?",
    "¿Cómo han estado mis signos vitales esta semana?",
    "Necesito que vengas aquí por favor.",
    "¿Cuál es mi temperatura de hoy?",
]

N_RUNS = 2   # repeticiones por frase (menor para evitar rate limits)
SLEEP_BETWEEN = 1.5  # segundos entre llamadas para evitar rate limit 429

# ── Modelos candidatos (excluye llama-3.3-70b que ya es principal,
#    orpheus (TTS), allam-2-7b (árabe), maverick (deprecado)) ─────────────
MODELS_TO_TEST = [
    'llama-3.1-8b-instant',                          # Rápido, pequeño
    'meta-llama/llama-4-scout-17b-16e-instruct',     # Sucesor de maverick
    'openai/gpt-oss-20b',                             # Versión ligera OSS
    'openai/gpt-oss-120b',                            # Ya en fallback actual
    'qwen/qwen3-32b',                                 # Alternativa potente
    'groq/compound-mini',                             # Compuesto optimizado
    'moonshotai/kimi-k2-instruct',                   # Alternativa emergente
    'meta-llama/llama-4-maverick-17b-128e-instruct', # DEPRECADO — referencia
]

RESULTS_FILE = Path(__file__).parent / 'benchmark_llm_models_results.json'


def color_latency(ms: float) -> str:
    if ms < 600:
        return f"{GREEN}{ms:.0f}ms{RESET}"
    elif ms < 1200:
        return f"{YELLOW}{ms:.0f}ms{RESET}"
    else:
        return f"{RED}{ms:.0f}ms{RESET}"


def call_groq(model: str, message: str) -> dict:
    """Llama directamente a la API de Groq con el modelo especificado."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": message}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code == 200:
            data = resp.json()
            content = data['choices'][0]['message']['content'].strip()
            tokens_out = data.get('usage', {}).get('completion_tokens', 0)
            return {
                'success': True,
                'response': content,
                'latency_ms': elapsed_ms,
                'tokens_output': tokens_out,
                'status_code': 200
            }
        else:
            return {
                'success': False,
                'response': None,
                'latency_ms': elapsed_ms,
                'tokens_output': 0,
                'status_code': resp.status_code,
                'error': resp.text[:200]
            }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            'success': False,
            'response': None,
            'latency_ms': elapsed_ms,
            'tokens_output': 0,
            'status_code': 0,
            'error': str(e)
        }


def benchmark_model(model_id: str) -> dict:
    """Ejecuta el benchmark completo para un modelo."""
    deprecated_flag = '(⚠️ DEPRECADO)' if 'maverick' in model_id else ''
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  Modelo: {CYAN}{model_id}{RESET} {YELLOW}{deprecated_flag}{RESET}")
    print(f"{'─'*60}")

    all_latencies = []
    all_tokens    = []
    successes     = 0
    total_calls   = 0
    sample_responses = []

    for phrase in TEST_PHRASES:
        phrase_latencies = []
        for run in range(N_RUNS):
            result = call_groq(model_id, phrase)
            total_calls += 1

            if result['success']:
                successes += 1
                phrase_latencies.append(result['latency_ms'])
                all_latencies.append(result['latency_ms'])
                if result['tokens_output'] > 0:
                    all_tokens.append(result['tokens_output'])
                if run == 0 and len(sample_responses) < 2:
                    sample_responses.append({
                        'phrase': phrase,
                        'response': result['response']
                    })
            else:
                status = result.get('status_code', 0)
                error_short = result.get('error', '')[:80]
                print(f"    {RED}✗ Error {status}: {error_short}{RESET}")

            time.sleep(SLEEP_BETWEEN)

        if phrase_latencies:
            avg_phrase = statistics.mean(phrase_latencies)
            short_phrase = phrase[:40] + '...' if len(phrase) > 40 else phrase
            resp_text = result.get('response', '') or ''
            short_resp = resp_text[:50] + '...' if len(resp_text) > 50 else resp_text
            print(f"  [{color_latency(avg_phrase)}] \"{short_phrase}\"")
            print(f"           → \"{short_resp}\"")

    # Métricas finales
    if all_latencies:
        avg_ms = statistics.mean(all_latencies)
        min_ms = min(all_latencies)
        max_ms = max(all_latencies)
        p50_ms = statistics.median(all_latencies)
    else:
        avg_ms = min_ms = max_ms = p50_ms = 9999.0

    success_rate = (successes / total_calls * 100) if total_calls > 0 else 0
    avg_tokens   = statistics.mean(all_tokens) if all_tokens else 0

    print(f"\n  {CYAN}Promedio: {avg_ms:.0f}ms | Min: {min_ms:.0f}ms | "
          f"Max: {max_ms:.0f}ms | P50: {p50_ms:.0f}ms{RESET}")
    print(f"  {CYAN}Tasa de éxito: {success_rate:.0f}% | "
          f"Tokens output (avg): {avg_tokens:.1f}{RESET}")

    return {
        'model': model_id,
        'avg_ms': round(avg_ms, 1),
        'min_ms': round(min_ms, 1),
        'max_ms': round(max_ms, 1),
        'p50_ms': round(p50_ms, 1),
        'success_rate_pct': round(success_rate, 1),
        'avg_tokens_output': round(avg_tokens, 1),
        'total_calls': total_calls,
        'successes': successes,
        'deprecated': 'maverick' in model_id,
        'sample_responses': sample_responses,
    }


def print_ranking(results: list):
    """Imprime el ranking final de modelos ordenado por latencia."""
    # Filtrar deprecados y fallidos del ranking
    valid = [r for r in results if not r['deprecated'] and r['success_rate_pct'] >= 50]
    ranked = sorted(valid, key=lambda x: (x['avg_ms']))

    print(f"\n\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  🏆 RANKING FINAL — CANDIDATOS PARA FALLBACK{RESET}")
    print(f"{'═'*70}")
    print(f"\n  {'#':<4} {'Modelo':<45} {'Avg':>7} {'P50':>7} {'Éxito':>7}")
    print(f"  {'─'*4} {'─'*45} {'─'*7} {'─'*7} {'─'*7}")

    medals = ['🥇', '🥈', '🥉']
    for i, r in enumerate(ranked):
        medal = medals[i] if i < 3 else f"  {i+1}."
        avg_colored = f"{r['avg_ms']:.0f}ms"
        if r['avg_ms'] < 600:
            avg_colored = f"{GREEN}{avg_colored}{RESET}"
        elif r['avg_ms'] < 1200:
            avg_colored = f"{YELLOW}{avg_colored}{RESET}"
        else:
            avg_colored = f"{RED}{avg_colored}{RESET}"

        print(f"  {medal}  {r['model']:<45} {r['avg_ms']:>6.0f}ms {r['p50_ms']:>6.0f}ms {r['success_rate_pct']:>6.0f}%")

    # Mostrar los deprecados al final
    deprecated = [r for r in results if r['deprecated']]
    if deprecated:
        print(f"\n  {YELLOW}━ MODELOS DEPRECADOS (referencia) ━{RESET}")
        for r in deprecated:
            print(f"  ⚠️   {r['model']:<45} {r['avg_ms']:>6.0f}ms {r['p50_ms']:>6.0f}ms {r['success_rate_pct']:>6.0f}%")

    # Recomendación top 3
    top3 = ranked[:3]
    print(f"\n{BOLD}{'─'*70}{RESET}")
    print(f"{BOLD}  📋 RECOMENDACIÓN — NUEVA CADENA DE FALLBACK:{RESET}")
    print(f"{'─'*70}")
    print(f"  GROQ_MODEL = 'llama-3.3-70b-versatile'  (sin cambios)")
    print(f"  GROQ_FALLBACK_MODELS = [")
    for r in top3:
        print(f"      '{r['model']}',   # avg {r['avg_ms']:.0f}ms, éxito {r['success_rate_pct']:.0f}%")
    print(f"  ]")
    print(f"{'═'*70}\n")

    return top3


def main():
    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  BENCHMARK MULTI-MODELO LLM — GROQ{RESET}")
    print(f"{BOLD}  Motivo: Deprecación de llama-4-maverick (9 mar 2026){RESET}")
    print(f"{'═'*70}")
    print(f"  Modelos a probar: {len(MODELS_TO_TEST)}")
    print(f"  Frases de prueba: {len(TEST_PHRASES)}")
    print(f"  Repeticiones por frase: {N_RUNS}")
    print(f"  Total llamadas API: ~{len(MODELS_TO_TEST) * len(TEST_PHRASES) * N_RUNS}")
    print(f"  Tiempo estimado: ~{len(MODELS_TO_TEST) * len(TEST_PHRASES) * N_RUNS * (SLEEP_BETWEEN + 0.8):.0f}s")
    print(f"{'─'*70}")

    all_results = []

    for model_id in MODELS_TO_TEST:
        result = benchmark_model(model_id)
        all_results.append(result)
        # Pausa extra entre modelos para evitar rate limits globales
        print(f"  {YELLOW}Pausa entre modelos...{RESET}")
        time.sleep(3)

    top3 = print_ranking(all_results)

    # Guardar resultados en JSON
    output = {
        'benchmark_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'reason': 'Deprecacion llama-4-maverick-17b-128e-instruct (9 marzo 2026)',
        'n_runs_per_phrase': N_RUNS,
        'sleep_between_s': SLEEP_BETWEEN,
        'models_tested': len(MODELS_TO_TEST),
        'results': all_results,
        'recommended_top3': [r['model'] for r in top3],
        'recommended_config': {
            'GROQ_MODEL': 'llama-3.3-70b-versatile',
            'GROQ_FALLBACK_MODELS': [r['model'] for r in top3]
        }
    }

    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  {GREEN}✅ Resultados guardados en:{RESET}")
    print(f"  {RESULTS_FILE}\n")


if __name__ == '__main__':
    main()

