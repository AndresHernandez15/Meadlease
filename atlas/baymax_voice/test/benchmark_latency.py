"""
Benchmark de Latencia del Pipeline Conversacional
===================================================
Mide con precisión las latencias de cada componente por separado
y del pipeline completo STT → LLM → TTS.

Uso:
    python baymax_voice/test/benchmark_latency.py

No requiere micrófono — usa audio de prueba pregrabado.
"""

import sys
import os
import time
import wave
import json
import statistics
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.utils.logger import setup_logger, get_logger
from baymax_voice.config import settings
import baymax_voice.cloud.speech_to_text as stt_module
import baymax_voice.cloud.groq_llm       as llm_module
import baymax_voice.cloud.text_to_speech as tts_module

setup_logger('WARNING')  # silenciar logs internos durante el benchmark
logger = get_logger('benchmark')

# ── Frases de prueba (representativas de uso real) ────────────────────────
TEST_PHRASES = [
    "¿Cuándo es mi próxima dosis de medicamento?",
    "Me duele la cabeza, ¿qué hago?",
    "¿Cómo han estado mis signos vitales esta semana?",
    "Necesito que vengas aquí por favor.",
    "¿Cuál es mi temperatura de hoy?",
]

# Respuestas cortas simuladas para el benchmark de TTS
# (representan lo que devolvería el LLM con MAX_TOKENS=60)
TTS_TEST_RESPONSES = [
    "No tengo acceso a tu horario ahora. Consulta tu aplicación.",
    "Lamento que te duela. Te recomiendo consultar a tu médico.",
    "No tengo tus datos de signos vitales en este momento.",
    "Voy hacia donde estás.",
    "No tengo tu temperatura registrada hoy.",
]

# ── Colores ANSI para la consola ──────────────────────────────────────────
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

N_RUNS = 3  # repeticiones por frase para promediar


def color_latency(ms: float) -> str:
    """Colorea la latencia según umbrales de UX."""
    if ms < 1000:
        return f"{GREEN}{ms:.0f}ms{RESET}"
    elif ms < 2000:
        return f"{YELLOW}{ms:.0f}ms{RESET}"
    else:
        return f"{RED}{ms:.0f}ms{RESET}"


def make_test_wav(text_seconds: float = 2.5) -> bytes:
    """
    Genera audio PCM de prueba (tono 440Hz) simulando voz,
    del mismo formato que captura el micrófono (16kHz, mono, int16).
    """
    sample_rate = settings.SAMPLE_RATE
    samples = int(sample_rate * text_seconds)
    t = np.linspace(0, text_seconds, samples, False)
    # Mezcla de tonos para simular habla con algo más complejo que un seno puro
    audio = (
        np.sin(2 * np.pi * 220 * t) * 8000 +
        np.sin(2 * np.pi * 440 * t) * 4000 +
        np.sin(2 * np.pi * 880 * t) * 2000 +
        np.random.normal(0, 200, samples)  # ruido pequeño
    ).astype(np.int16)
    return audio.tobytes()


def load_real_audio() -> bytes | None:
    """Intenta cargar el audio de prueba real si existe."""
    candidates = [
        PROJECT_ROOT / 'baymax_voice' / 'audio' / 'speech_only.wav',
        PROJECT_ROOT / 'baymax_voice' / 'audio' / 'test_audio.wav',
        PROJECT_ROOT / 'test_audio_groq.wav',
    ]
    for path in candidates:
        if path.exists():
            try:
                with wave.open(str(path), 'rb') as wf:
                    audio = wf.readframes(wf.getnframes())
                print(f"  Usando audio real: {path.name} ({len(audio)//2000:.1f}s)")
                return audio
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  BENCHMARK STT
# ═══════════════════════════════════════════════════════════════════════════

def benchmark_stt(audio_bytes: bytes) -> dict:
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  STT — Groq Whisper  (whisper-large-v3-turbo){RESET}")
    print(f"{'─'*55}")
    print(f"  Audio de entrada: {len(audio_bytes)//2/settings.SAMPLE_RATE:.2f}s de audio")
    print(f"  Repeticiones: {N_RUNS}\n")

    latencies = []
    results   = []

    for i in range(N_RUNS):
        t0 = time.perf_counter()
        text, meta = stt_module.transcribe(audio_bytes)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        ok = meta.get('success', False)
        latencies.append(elapsed_ms)
        results.append({'text': text, 'meta': meta, 'latency_ms': elapsed_ms})

        status = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        transcript = f'"{text[:55]}..."' if text and len(text) > 55 else f'"{text}"' if text else "[fallo]"
        print(f"  [{i+1}] {status} {color_latency(elapsed_ms)}  →  {transcript}")

    avg = statistics.mean(latencies)
    p50 = statistics.median(latencies)
    mx  = max(latencies)
    mn  = min(latencies)

    print(f"\n  {CYAN}Promedio: {avg:.0f}ms | Min: {mn:.0f}ms | Max: {mx:.0f}ms | P50: {p50:.0f}ms{RESET}")

    return {
        'component': 'STT (Groq Whisper)',
        'runs': N_RUNS,
        'latencies_ms': latencies,
        'avg_ms': avg,
        'min_ms': mn,
        'max_ms': mx,
        'p50_ms': p50,
        'last_transcript': results[-1]['text'],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BENCHMARK LLM
# ═══════════════════════════════════════════════════════════════════════════

def benchmark_llm() -> dict:
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  LLM — Groq Llama 3.3 70B{RESET}")
    print(f"{'─'*55}")
    print(f"  Frases de prueba: {len(TEST_PHRASES)}")
    print(f"  Repeticiones por frase: {N_RUNS}\n")

    all_latencies = []
    all_tokens    = []

    for phrase in TEST_PHRASES:
        phrase_latencies = []
        for i in range(N_RUNS):
            t0 = time.perf_counter()
            result = llm_module.generate_response(phrase)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            phrase_latencies.append(elapsed_ms)
            all_latencies.append(elapsed_ms)
            if result.get('tokens_output'):
                all_tokens.append(result['tokens_output'])

        avg_phrase = statistics.mean(phrase_latencies)
        response   = result.get('response', '[fallo]') or '[fallo]'
        response_short = response[:50] + '...' if len(response) > 50 else response
        tokens_out = result.get('tokens_output', 0)

        print(f"  [{color_latency(avg_phrase)}] \"{phrase[:42]}...\"")
        print(f"           → \"{response_short}\" ({tokens_out} tokens)")

    avg = statistics.mean(all_latencies)
    p50 = statistics.median(all_latencies)
    mx  = max(all_latencies)
    mn  = min(all_latencies)
    avg_tok = statistics.mean(all_tokens) if all_tokens else 0

    print(f"\n  {CYAN}Promedio: {avg:.0f}ms | Min: {mn:.0f}ms | Max: {mx:.0f}ms | P50: {p50:.0f}ms{RESET}")
    print(f"  {CYAN}Tokens de salida promedio: {avg_tok:.1f}{RESET}")

    return {
        'component': 'LLM (Groq Llama 3.3 70B)',
        'runs': len(TEST_PHRASES) * N_RUNS,
        'latencies_ms': all_latencies,
        'avg_ms': avg,
        'min_ms': mn,
        'max_ms': mx,
        'p50_ms': p50,
        'avg_tokens_output': avg_tok,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BENCHMARK TTS
# ═══════════════════════════════════════════════════════════════════════════

def benchmark_tts() -> dict:
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  TTS — Azure Neural (es-CO-SalomeNeural @ 24kHz){RESET}")
    print(f"{'─'*55}")
    print(f"  Frases de prueba: {len(TTS_TEST_RESPONSES)}")
    print(f"  Repeticiones por frase: {N_RUNS}\n")

    all_latencies  = []
    all_bytes      = []
    all_durations  = []

    for text in TTS_TEST_RESPONSES:
        phrase_latencies = []
        for i in range(N_RUNS):
            t0 = time.perf_counter()
            audio = tts_module.synthesize(text, style='empatico')
            elapsed_ms = (time.perf_counter() - t0) * 1000

            phrase_latencies.append(elapsed_ms)
            all_latencies.append(elapsed_ms)

            if audio:
                all_bytes.append(len(audio))
                # Duración del audio generado (PCM 24kHz 16-bit mono = 2 bytes/sample)
                duration_s = len(audio) / (24000 * 2)
                all_durations.append(duration_s)

        avg_phrase = statistics.mean(phrase_latencies)
        duration_s = (len(audio) / (24000 * 2)) if audio else 0
        n_chars    = len(text)

        print(f"  [{color_latency(avg_phrase)}] \"{text[:48]}...\"")
        print(f"           → {n_chars} chars | audio: {duration_s:.1f}s | {len(audio)//1024 if audio else 0}KB")

    avg = statistics.mean(all_latencies)
    p50 = statistics.median(all_latencies)
    mx  = max(all_latencies)
    mn  = min(all_latencies)
    avg_dur  = statistics.mean(all_durations) if all_durations else 0
    avg_size = statistics.mean(all_bytes) / 1024 if all_bytes else 0

    # Ratio clave: tiempo de síntesis vs duración del audio generado
    # Un ratio < 1.0 significa que el TTS es más rápido que el audio que genera (ideal)
    rtf = (avg / 1000) / avg_dur if avg_dur > 0 else 0

    print(f"\n  {CYAN}Promedio: {avg:.0f}ms | Min: {mn:.0f}ms | Max: {mx:.0f}ms | P50: {p50:.0f}ms{RESET}")
    print(f"  {CYAN}Audio generado promedio: {avg_dur:.1f}s ({avg_size:.0f}KB){RESET}")
    print(f"  {CYAN}Real-Time Factor (RTF): {rtf:.2f}x  {'✓ más rápido que tiempo real' if rtf < 1 else '⚠ más lento que tiempo real'}{RESET}")

    return {
        'component': 'TTS (Azure Salome 24kHz)',
        'runs': len(TTS_TEST_RESPONSES) * N_RUNS,
        'latencies_ms': all_latencies,
        'avg_ms': avg,
        'min_ms': mn,
        'max_ms': mx,
        'p50_ms': p50,
        'avg_audio_duration_s': avg_dur,
        'avg_audio_size_kb': avg_size,
        'real_time_factor': rtf,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BENCHMARK PIPELINE COMPLETO
# ═══════════════════════════════════════════════════════════════════════════

def benchmark_pipeline(audio_bytes: bytes) -> dict:
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  PIPELINE COMPLETO: STT → LLM → TTS{RESET}")
    print(f"{'─'*55}")
    print(f"  Simulando {N_RUNS} conversaciones completas...\n")

    pipeline_latencies = []
    step_latencies = {'stt': [], 'llm': [], 'tts': []}

    for i in range(N_RUNS):
        t_total = time.perf_counter()

        # STT
        t0 = time.perf_counter()
        text, _ = stt_module.transcribe(audio_bytes)
        stt_ms = (time.perf_counter() - t0) * 1000
        step_latencies['stt'].append(stt_ms)

        if not text:
            text = "¿Cuándo es mi próxima medicina?"  # fallback si falla STT

        # LLM
        t0 = time.perf_counter()
        result = llm_module.generate_response(text)
        llm_ms = (time.perf_counter() - t0) * 1000
        step_latencies['llm'].append(llm_ms)

        response = result.get('response') or "Lo siento, no pude procesar tu solicitud."

        # TTS
        t0 = time.perf_counter()
        audio_out = tts_module.synthesize(response, style='empatico')
        tts_ms = (time.perf_counter() - t0) * 1000
        step_latencies['tts'].append(tts_ms)

        total_ms = (time.perf_counter() - t_total) * 1000
        pipeline_latencies.append(total_ms)

        audio_dur = (len(audio_out) / (24000 * 2)) if audio_out else 0
        print(f"  [{i+1}] STT:{color_latency(stt_ms)} + LLM:{color_latency(llm_ms)} + TTS:{color_latency(tts_ms)}"
              f" = {BOLD}{color_latency(total_ms)}{RESET}  →  audio:{audio_dur:.1f}s")
        print(f"       \"{text[:40]}...\"")
        print(f"       \"{response[:55]}...\"" if len(response) > 55 else f"       \"{response}\"")
        print()

    avg_total = statistics.mean(pipeline_latencies)
    avg_stt   = statistics.mean(step_latencies['stt'])
    avg_llm   = statistics.mean(step_latencies['llm'])
    avg_tts   = statistics.mean(step_latencies['tts'])

    pct_stt = (avg_stt / avg_total) * 100
    pct_llm = (avg_llm / avg_total) * 100
    pct_tts = (avg_tts / avg_total) * 100

    print(f"  {'─'*50}")
    print(f"  {BOLD}Desglose del tiempo total promedio ({avg_total:.0f}ms):{RESET}")
    print(f"  STT : {color_latency(avg_stt):>18}  ({pct_stt:.0f}%)")
    print(f"  LLM : {color_latency(avg_llm):>18}  ({pct_llm:.0f}%)")
    print(f"  TTS : {color_latency(avg_tts):>18}  ({pct_tts:.0f}%)")
    print(f"  {'─'*50}")
    print(f"  {BOLD}TOTAL: {color_latency(avg_total)}  (hasta audio listo para reproducir){RESET}")

    return {
        'component': 'Pipeline completo (STT+LLM+TTS)',
        'runs': N_RUNS,
        'pipeline_latencies_ms': pipeline_latencies,
        'avg_total_ms': avg_total,
        'avg_stt_ms': avg_stt,
        'avg_llm_ms': avg_llm,
        'avg_tts_ms': avg_tts,
        'pct_stt': pct_stt,
        'pct_llm': pct_llm,
        'pct_tts': pct_tts,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  BENCHMARK DE LATENCIA — ATLAS CONVERSACIONAL{RESET}")
    print(f"{BOLD}{'═'*55}{RESET}")
    print(f"  Fecha : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  N runs: {N_RUNS} por prueba")

    # ── Inicializar módulos ───────────────────────────────────────────────
    print(f"\n  Inicializando módulos cloud...")
    ok_stt = stt_module.initialize()
    ok_llm = llm_module.initialize()
    ok_tts = tts_module.initialize()

    if not all([ok_stt, ok_llm, ok_tts]):
        print(f"  {RED}✗ Error inicializando módulos. Abortando.{RESET}")
        sys.exit(1)
    print(f"  {GREEN}✓ STT | ✓ LLM | ✓ TTS{RESET}")

    # ── Preparar audio de prueba ──────────────────────────────────────────
    print(f"\n  Preparando audio de prueba...")
    audio_bytes = load_real_audio()
    if audio_bytes is None:
        print(f"  Audio real no encontrado — usando audio sintético (2.5s)")
        audio_bytes = make_test_wav(2.5)

    # ── Ejecutar benchmarks ───────────────────────────────────────────────
    results = {}

    results['stt']      = benchmark_stt(audio_bytes)
    results['llm']      = benchmark_llm()
    results['tts']      = benchmark_tts()
    results['pipeline'] = benchmark_pipeline(audio_bytes)

    # ── Resumen final ─────────────────────────────────────────────────────
    p = results['pipeline']

    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  RESUMEN FINAL{RESET}")
    print(f"{'═'*55}")
    print(f"  {'Componente':<30} {'Promedio':>10} {'Min':>8} {'Max':>8}")
    print(f"  {'─'*54}")
    for key in ['stt', 'llm', 'tts']:
        r = results[key]
        print(f"  {r['component']:<30} {r['avg_ms']:>8.0f}ms {r['min_ms']:>6.0f}ms {r['max_ms']:>6.0f}ms")
    print(f"  {'─'*54}")
    print(f"  {'Pipeline completo':<30} {p['avg_total_ms']:>8.0f}ms")
    print(f"{'═'*55}")

    # Veredicto del cuello de botella
    bottleneck = max(['stt', 'llm', 'tts'], key=lambda k: results[k]['avg_ms'])
    bottleneck_pct = p[f'pct_{bottleneck}']
    print(f"\n  {BOLD}Cuello de botella: {bottleneck.upper()} ({bottleneck_pct:.0f}% del tiempo total){RESET}")

    # Guardar resultados en JSON
    output_path = PROJECT_ROOT / 'baymax_voice' / 'test' / 'benchmark_latency_results.json'
    summary = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'n_runs': N_RUNS,
        'stt': {k: v for k, v in results['stt'].items() if k != 'latencies_ms'},
        'llm': {k: v for k, v in results['llm'].items() if k != 'latencies_ms'},
        'tts': {k: v for k, v in results['tts'].items() if k != 'latencies_ms'},
        'pipeline': results['pipeline'],
        'bottleneck': bottleneck,
        'bottleneck_pct': bottleneck_pct,
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Resultados guardados en: {output_path.name}")
    print(f"{'═'*55}\n")

    # Shutdown
    stt_module.shutdown()
    llm_module.shutdown()
    tts_module.shutdown()


if __name__ == '__main__':
    main()

