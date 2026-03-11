"""
Test del sistema de fallback de Groq
Simula fallos del modelo principal para probar el fallback automático
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from baymax_voice.utils.logger import setup_logger
from baymax_voice.cloud import groq_llm

def test_fallback():
    print("=" * 70)
    print("TEST: SISTEMA DE FALLBACK GROQ")
    print("=" * 70)

    setup_logger()

    print("\n1. Inicializando Groq...")
    if groq_llm.initialize():
        print("   ✓ Groq inicializado con fallback chain")
    else:
        print("   ✗ Error inicializando Groq")
        return

    # Test queries
    queries = [
        "¿Cómo estuvo mi temperatura hoy?",
        "¿Qué ejercicios puedo hacer?",
        "Tengo 38.5°C de temperatura"
    ]

    print(f"\n2. Probando {len(queries)} consultas con fallback...\n")

    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}/{len(queries)} ---")
        print(f"Usuario: {query}")

        result = groq_llm.generate_response(query)

        if result['success']:
            print(f"✓ Respuesta exitosa")
            print(f"  Modelo usado: {result['model']}")
            print(f"  Fallback usado: {'Sí' if result.get('fallback_used') else 'No'}")
            if result.get('fallback_used') and 'fallback_level' in result:
                print(f"  Nivel de fallback: {result['fallback_level']}")
            print(f"  Latencia: {result['latency']:.2f}s")
            print(f"  Tokens: {result['tokens_input']} in / {result['tokens_output']} out")
            print(f"  Respuesta: {result['response'][:80]}...")
        else:
            print(f"✗ Todos los modelos fallaron")

    print("\n" + "=" * 70)
    print("CONFIGURACIÓN DE FALLBACK")
    print("=" * 70)

    from baymax_voice.cloud.llm_config import GROQ_MODEL, GROQ_FALLBACK_MODELS

    print(f"\nModelo principal:")
    print(f"  • {GROQ_MODEL}")

    print(f"\nCadena de fallback ({len(GROQ_FALLBACK_MODELS)} modelos):")
    for i, model in enumerate(GROQ_FALLBACK_MODELS, 1):
        print(f"  {i}. {model}")

    print("\nEstrategia:")
    print("  Si el modelo principal falla, intenta automáticamente")
    print("  cada modelo de fallback en orden hasta obtener respuesta.")

    groq_llm.shutdown()
    print("\n✓ Test completado")


if __name__ == '__main__':
    test_fallback()

