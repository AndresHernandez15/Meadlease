"""
Test del nuevo audio de confirmación con la voz de Camila.
Reproduce el archivo confirmation.wav para validarlo.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from baymax_voice.audio import playback
from baymax_voice.config import settings

print('=' * 80)
print('🎧 TEST DEL NUEVO AUDIO DE CONFIRMACIÓN')
print('=' * 80)

# Verificar que el archivo existe
confirmation_path = settings.CONFIRMATION_AUDIO_PATH
print(f'\n📂 Verificando archivo: {confirmation_path}')

if not Path(confirmation_path).exists():
    print(f'✗ ERROR: Archivo no encontrado')
    sys.exit(1)

print(f'✓ Archivo encontrado')

# Obtener información del archivo
import wave
with wave.open(confirmation_path, 'rb') as wf:
    channels = wf.getnchannels()
    sample_width = wf.getsampwidth()
    framerate = wf.getframerate()
    frames = wf.getnframes()
    duration = frames / framerate

print(f'\n📊 Información del audio:')
print(f'  • Duración: {duration:.2f}s')
print(f'  • Sample rate: {framerate} Hz')
print(f'  • Canales: {channels} ({"mono" if channels == 1 else "estéreo"})')
print(f'  • Formato: {sample_width * 8}-bit')
print(f'  • Frames: {frames}')

# Inicializar playback
if not playback.initialize():
    print('\n✗ ERROR: No se pudo inicializar playback')
    sys.exit(1)

print(f'\n✓ Playback inicializado')

# Reproducir
print('\n' + '─' * 80)
print('🎙️  REPRODUCIENDO: Camila diciendo "¿Sí?"')
print('─' * 80)
print('\nEscucharás el nuevo audio de confirmación que se reproducirá')
print('cuando el sistema detecte la wake word "atlas".')
print()

try:
    print('► Reproduciendo...')
    playback.play_file(confirmation_path, blocking=True)
    print('✓ Reproducción completada')
except Exception as e:
    print(f'✗ Error: {e}')

# Reproducir 2 veces más para validar bien
print('\n¿Quieres escucharlo de nuevo? (S/N): ', end='')
respuesta = input().strip().upper()

if respuesta == 'S':
    for i in range(2):
        print(f'\n► Reproducción {i+2}/3...')
        playback.play_file(confirmation_path, blocking=True)
        print('✓ Completado')

print('\n' + '=' * 80)
print('✅ TEST COMPLETADO')
print('=' * 80)

print('\n📝 RESUMEN:')
print('  • Voz: Camila (Perú)')
print('  • Texto: "¿Sí?"')
print('  • Tono: +5% (sonido de pregunta)')
print('  • Duración: ~1.24s')
print('  • Estado: Listo para usar en el sistema')

print('\n💡 El nuevo audio se usará automáticamente cuando ejecutes main.py')
print('   y digas "atlas". El robot responderá con "¿Sí?" antes de escucharte.')

print('\n' + '=' * 80)

# Cleanup
playback.shutdown()

