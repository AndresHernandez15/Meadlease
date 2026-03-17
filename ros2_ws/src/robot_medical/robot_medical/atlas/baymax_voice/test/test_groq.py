"""
Test simple para probar Groq LLM
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from baymax_voice.utils.logger import setup_logger
from baymax_voice.cloud import groq_llm

TEST_QUERIES = [
    "¿Cómo te llamas?",
    "¿Cuál es mi próxima dosis?",
    "¿Cómo me siento hoy?",
]

def test_groq():
    print("=" * 60)
    print("TEST: GROQ LLM")
    print("=" * 60)

    setup_logger()

    print("\n1. Inicializando Groq...")
    if groq_llm.initialize():
        print("   ✓ Groq inicializado correctamente")
    else:
        print("   ✗ Error inicializando Groq")
        return

    print(f"\n2. Probando {len(TEST_QUERIES)} consultas...\n")

    results = []

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n--- Query {i}/{len(TEST_QUERIES)} ---")
        print(f"Usuario: {query}")

        result = groq_llm.generate_response(query)
        results.append(result)

        if result['success']:
            print(f"Baymax: {result['response']}")
            print(f"  • Latencia: {result['latency']:.2f}s")
            print(f"  • Tokens: {result['tokens_input']} in / {result['tokens_output']} out")
            print(f"  • Modelo: {result['model']}")
        else:
            print("  ✗ Error en la respuesta")

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)

    successful = [r for r in results if r['success']]

    if successful:
        avg_latency = sum(r['latency'] for r in successful) / len(successful)
        total_tokens_in = sum(r['tokens_input'] for r in successful)
        total_tokens_out = sum(r['tokens_output'] for r in successful)

        print(f"Consultas exitosas: {len(successful)}/{len(results)}")
        print(f"Latencia promedio: {avg_latency:.2f}s")
        print(f"Total tokens input: {total_tokens_in}")
        print(f"Total tokens output: {total_tokens_out}")
        print(f"Total tokens: {total_tokens_in + total_tokens_out}")
    else:
        print("No hubo respuestas exitosas")

    groq_llm.shutdown()
    print("\n✓ Test completado")


if __name__ == '__main__':
    test_groq()


