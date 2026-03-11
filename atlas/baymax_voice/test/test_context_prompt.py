"""
Test rápido del nuevo contexto y system prompt.
Valida que el LLM no dé información no solicitada.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import groq_llm
from baymax_voice.cloud.llm_config import build_patient_context

print('=' * 70)
print('TEST — Nuevo Contexto del Paciente + System Prompt')
print('=' * 70)

# Inicializar
if not groq_llm.initialize():
    print('[ERROR] No se pudo inicializar Groq LLM')
    sys.exit(1)

print('\n[OK] LLM inicializado')

# Construir contexto
patient_context = build_patient_context(patient_id=1)
print('\n[CONTEXTO DEL PACIENTE]')
print(patient_context)

# Casos de prueba
test_cases = [
    {
        'name': 'Saludo simple (NO debe mencionar dosis)',
        'input': 'hola',
        'should_not_contain': ['metformina', 'dosis', '12:00', 'medicamento']
    },
    {
        'name': 'Pregunta general (NO debe mencionar datos médicos)',
        'input': '¿cómo estás?',
        'should_not_contain': ['metformina', 'dosis', 'signos vitales', 'BPM']
    },
    {
        'name': 'Pregunta por próxima dosis (SÍ debe mencionar)',
        'input': '¿cuál es mi próxima dosis?',
        'should_contain': ['metformina']
    },
    {
        'name': 'Pregunta por signos vitales (SÍ debe mencionar)',
        'input': '¿cuáles fueron mis últimos signos vitales?',
        'should_contain': ['78', 'BPM']
    },
    {
        'name': 'Pregunta por cuánto falta para dosis',
        'input': '¿en cuánto tiempo es mi próxima dosis?',
        'should_contain': ['hora']
    }
]

print('\n' + '=' * 70)
print('EJECUTANDO CASOS DE PRUEBA')
print('=' * 70)

for i, test in enumerate(test_cases, 1):
    print(f'\n[TEST {i}] {test["name"]}')
    print(f'  Usuario: "{test["input"]}"')

    result = groq_llm.generate_response(
        user_text=test['input'],
        patient_context=patient_context,
        remember=False  # Sin memoria para tests independientes
    )

    if not result.get('success'):
        print(f'  [ERROR] Falló: {result.get("error")}')
        continue

    response = result['response']
    print(f'  Atlas: "{response}"')

    # Validaciones
    if 'should_contain' in test:
        for keyword in test['should_contain']:
            if keyword.lower() in response.lower():
                print(f'  [OK] Contiene "{keyword}" (esperado)')
            else:
                print(f'  [!] NO contiene "{keyword}" (se esperaba)')

    if 'should_not_contain' in test:
        found_unwanted = []
        for keyword in test['should_not_contain']:
            if keyword.lower() in response.lower():
                found_unwanted.append(keyword)

        if found_unwanted:
            print(f'  [!] FALLO: Menciona info no solicitada: {", ".join(found_unwanted)}')
        else:
            print(f'  [OK] No menciona info no solicitada')

print('\n' + '=' * 70)
print('TEST COMPLETADO')
print('=' * 70)

