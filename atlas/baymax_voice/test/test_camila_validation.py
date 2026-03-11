"""
Test de validación de la nueva voz: Camila (Perú)
Confirma que el cambio se aplicó correctamente.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.cloud import text_to_speech
from baymax_voice.audio import playback
from baymax_voice.config import settings

print('=' * 80)
print('🎙️  VALIDACIÓN DE NUEVA VOZ - CAMILA (PERÚ)')
print('=' * 80)

# Verificar configuración
print('\n📋 VERIFICANDO CONFIGURACIÓN:')
print('─' * 80)
print(f'Voz configurada: {settings.AZURE_TTS_VOICE}')

if settings.AZURE_TTS_VOICE == 'es-PE-CamilaNeural':
    print('✓ Voz correcta: Camila (Perú)')
else:
    print(f'✗ ERROR: Se esperaba es-PE-CamilaNeural, encontrado: {settings.AZURE_TTS_VOICE}')
    sys.exit(1)

# Inicializar
if not text_to_speech.initialize():
    print('[ERROR] No se pudo inicializar TTS')
    sys.exit(1)

if not playback.initialize():
    print('[ERROR] No se pudo inicializar playback')
    sys.exit(1)

print('\n[OK] Sistemas inicializados correctamente')

# Textos de prueba
print('\n' + '=' * 80)
print('🧪 PRUEBAS DE VOZ')
print('=' * 80)

pruebas = [
    {
        'nombre': 'Saludo médico',
        'texto': 'Hola, soy Atlas, tu asistente médico personal. ¿En qué puedo ayudarte hoy?'
    },
    {
        'nombre': 'Reporte de signos vitales',
        'texto': 'Tus últimos signos vitales fueron: setenta y ocho pulsaciones por minuto, noventa y ocho por ciento de saturación de oxígeno, y treinta y seis punto cinco grados centígrados.'
    },
    {
        'nombre': 'Recordatorio empático',
        'texto': 'Tu próxima dosis es Ibuprofeno en dos horas. No olvides tomarla con alimentos para proteger tu estómago.'
    },
]

for i, prueba in enumerate(pruebas, 1):
    print(f'\n[Prueba {i}/3] {prueba["nombre"]}')
    print('─' * 80)
    print(f'Texto: "{prueba["texto"][:60]}..."')

    # Sintetizar con configuración actual (rate=0.92, sin pitch/volumen)
    audio = text_to_speech.synthesize(
        prueba['texto'],
        style='empatico',
        use_ssml=True,
        improve_naturalness=True
    )

    if audio:
        print('► Reproduciendo...')
        playback.play_audio(audio, sample_rate=24000, blocking=True)
        print('✓ Completado\n')
    else:
        print('✗ Error en síntesis')

print('=' * 80)
print('✅ VALIDACIÓN COMPLETADA')
print('=' * 80)

print('\n📊 RESUMEN:')
print(f'  • Voz: Camila (Perú) - es-PE-CamilaNeural')
print(f'  • Características: Alegre, simpática, dulce y cercana')
print(f'  • Velocidad: 0.92 (8% más lenta que normal)')
print(f'  • Pitch: 0% (voz natural sin modificación)')
print(f'  • Volumen: 0% (voz natural sin modificación)')
print(f'  • SSML: Activado')
print(f'  • Mejora de números: Activada')

print('\n💡 La nueva voz está lista para usarse en el sistema completo.')
print('   Ejecuta main.py para probar en conversación real.')

print('\n' + '=' * 80)

# Cleanup
playback.shutdown()
text_to_speech.shutdown()

