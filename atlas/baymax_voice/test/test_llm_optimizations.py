"""
Script de prueba para verificar las optimizaciones de memoria y tokens del LLM.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import groq_llm
from baymax_voice.cloud.llm_config import build_patient_context, CONVERSATION_MEMORY_TURNS, MAX_TOKENS
from baymax_voice.utils.logger import get_logger

logger = get_logger('test_llm_optimizations')

print('═' * 80)
print('TEST DE OPTIMIZACIONES LLM')
print('═' * 80)

# 1. Verificar configuración
print('\n1. Configuración optimizada:')
print(f'   MAX_TOKENS: {MAX_TOKENS} (antes: 100, ahorro ~30%)')
print(f'   CONVERSATION_MEMORY_TURNS: {CONVERSATION_MEMORY_TURNS} turnos')

# 2. Inicializar Groq
print('\n2. Inicializando Groq...')
if groq_llm.initialize():
    print('   ✓ Groq inicializado correctamente')
else:
    print('   ✗ Error inicializando Groq')
    sys.exit(1)

# 3. Probar memoria conversacional
print('\n3. Probando memoria conversacional (3 turnos):')
conversacion = [
    "Hola, soy Juan",
    "¿Cuál es mi presión arterial?",
    "¿Y mi nombre?"  # Esta pregunta DEBE usar el contexto del turno 1
]

for i, pregunta in enumerate(conversacion, 1):
    print(f'\n   Turno {i}: "{pregunta}"')
    result = groq_llm.generate_response(
        user_text=pregunta,
        patient_context=None,
        remember=True
    )

    if result['success']:
        print(f'   → "{result["response"]}"')
        print(f'   → Latencia: {result["latency"]:.2f}s')
        print(f'   → Tokens: in={result["tokens_input"]} out={result["tokens_output"]}')
        print(f'   → Turnos en memoria: {result["conversation_turns"]}/{CONVERSATION_MEMORY_TURNS}')
    else:
        print(f'   ✗ Error: {result}')

# 4. Verificar que recordó el contexto
print('\n4. Verificación de memoria:')
print('   Si la respuesta al turno 3 menciona "Juan", la memoria funciona ✓')

# 5. Limpiar historial
print('\n5. Limpiando historial conversacional...')
groq_llm.clear_conversation_history()
print(f'   Turnos después de limpiar: {groq_llm.get_conversation_turns()}')

# 6. Probar contexto del paciente (sin DB inicializada, debe devolver vacío)
print('\n6. Probando build_patient_context (sin DB):')
context = build_patient_context(patient_id=1)
print(f'   Contexto: "{context}" (esperado: vacío sin DB)')

print('\n' + '═' * 80)
print('TEST COMPLETADO')
print('═' * 80)

# Cerrar
groq_llm.shutdown()

