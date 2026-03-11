"""
Test de Integración Completo - Sistema Baymax
Prueba todas las funciones implementadas hasta ahora:
- Captura de audio
- Filtro de ruido
- VAD (Voice Activity Detection)
- Wake Word Detection (Porcupine)
- Comandos locales (Vosk)
- Sistema de eventos
- Audio buffer
- Reproducción de audio
"""
import sys
import os
import time
import threading
from pathlib import Path

# Agregar ruta del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from baymax_voice.config import settings
from baymax_voice.utils.logger import setup_logger, get_logger
from baymax_voice.utils.events import get_event, clear_events, queue_size
import baymax_voice.audio.capture as capture
import baymax_voice.audio.vad as vad
import baymax_voice.audio.noise_filter as noise_filter
import baymax_voice.audio.audio_buffer as audio_buffer
import baymax_voice.audio.playback as playback
import baymax_voice.local.wake_word as wake_word
import baymax_voice.local.commands as commands

setup_logger(level='INFO')
logger = get_logger('test.integration')


class IntegrationTest:
    def __init__(self):
        self.modules_initialized = []
        self.test_results = {
            'passed': [],
            'failed': [],
            'skipped': []
        }
        self.running = False
        self.event_monitor_thread = None

    def log_test(self, test_name, status, message=''):
        """Registra resultado de test"""
        symbols = {
            'passed': '✓',
            'failed': '✗',
            'skipped': '⊘'
        }
        logger.info(f'{symbols[status]} {test_name}: {message}')
        self.test_results[status].append(test_name)

    def test_configuration_validation(self):
        """Test 1: Validación de configuración"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 1: VALIDACIÓN DE CONFIGURACIÓN')
        logger.info('=' * 60)

        try:
            errors = settings.validate_paths()

            if errors:
                self.log_test('Validación de paths', 'failed', f'{len(errors)} errores encontrados')
                for error in errors:
                    logger.error(f'  - {error}')
                return False
            else:
                self.log_test('Validación de paths', 'passed', 'Todos los archivos existen')

            # Verificar rangos de configuración
            assert 0 <= settings.VAD_AGGRESSIVENESS <= 3
            self.log_test('VAD aggressiveness', 'passed', f'Valor: {settings.VAD_AGGRESSIVENESS}')

            assert 0.0 <= settings.PORCUPINE_SENSITIVITY <= 1.0
            self.log_test('Porcupine sensitivity', 'passed', f'Valor: {settings.PORCUPINE_SENSITIVITY}')

            assert settings.SAMPLE_RATE > 0
            self.log_test('Sample rate', 'passed', f'{settings.SAMPLE_RATE} Hz')

            return True

        except Exception as e:
            self.log_test('Validación de configuración', 'failed', str(e))
            return False

    def test_audio_capture_init(self):
        """Test 2: Inicialización de captura de audio"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 2: CAPTURA DE AUDIO')
        logger.info('=' * 60)

        try:
            # Primera inicialización
            success = capture.initialize()
            if success:
                self.log_test('Inicialización de audio', 'passed', 'PyAudio inicializado')
                self.modules_initialized.append('capture')
            else:
                self.log_test('Inicialización de audio', 'failed', 'No se pudo inicializar')
                return False

            # Test de idempotencia
            success = capture.initialize()
            if success:
                self.log_test('Idempotencia de initialize()', 'passed', 'No falla al llamar 2 veces')

            # Verificar que está corriendo
            if capture.is_running():
                self.log_test('Stream activo', 'passed', 'Stream de audio corriendo')
            else:
                self.log_test('Stream activo', 'failed', 'Stream no está activo')
                return False

            # Capturar algunos frames
            frames_captured = 0
            for i in range(10):
                frame = capture.get_audio_frame()
                if frame is not None and len(frame) == settings.CHUNK_SIZE:
                    frames_captured += 1

            if frames_captured >= 8:  # Al menos 80% de éxito
                self.log_test('Captura de frames', 'passed', f'{frames_captured}/10 frames capturados')
            else:
                self.log_test('Captura de frames', 'failed', f'Solo {frames_captured}/10 frames')
                return False

            return True

        except Exception as e:
            self.log_test('Captura de audio', 'failed', str(e))
            return False

    def test_noise_filter(self):
        """Test 3: Filtro de ruido"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 3: FILTRO DE RUIDO')
        logger.info('=' * 60)

        try:
            logger.info('Calibrando ruido de fondo...')
            logger.info('MANTÉN SILENCIO durante 2 segundos')
            time.sleep(1)  # Dar tiempo al usuario

            success = noise_filter.calibrate_noise(capture, duration=2.0)

            if not success:
                self.log_test('Calibración de ruido', 'failed', 'No se pudo calibrar')
                return False

            self.log_test('Calibración de ruido', 'passed', 'Calibrado exitosamente')

            # Verificar que se calibró
            noise_level = noise_filter.get_noise_level()
            if noise_level is not None and noise_level > 0:
                self.log_test('Perfil de ruido', 'passed', f'RMS: {noise_level:.2f}')
            else:
                self.log_test('Perfil de ruido', 'failed', 'Perfil inválido')
                return False

            # Probar aplicar filtro
            frame = capture.get_audio_frame()
            if frame is not None:
                filtered = noise_filter.apply_filter(frame)
                if filtered is not None and len(filtered) == len(frame):
                    self.log_test('Aplicación de filtro', 'passed', 'Filtro aplicado correctamente')
                else:
                    self.log_test('Aplicación de filtro', 'failed', 'Filtro no funciona')
                    return False

            return True

        except Exception as e:
            self.log_test('Filtro de ruido', 'failed', str(e))
            return False

    def test_vad(self):
        """Test 4: Voice Activity Detection"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 4: VOICE ACTIVITY DETECTION (VAD)')
        logger.info('=' * 60)

        try:
            success = vad.initialize()
            if success:
                self.log_test('Inicialización VAD', 'passed', 'WebRTC VAD inicializado')
            else:
                self.log_test('Inicialización VAD', 'failed', 'No se pudo inicializar')
                return False

            # Test de idempotencia
            success = vad.initialize()
            if success:
                self.log_test('Idempotencia VAD', 'passed', 'No falla al llamar 2 veces')

            logger.info('')
            logger.info('Prueba de VAD:')
            logger.info('  1. Mantén SILENCIO por 2 segundos')
            logger.info('  2. Luego HABLA por 3 segundos')
            logger.info('  3. Luego SILENCIO nuevamente')
            input('Presiona ENTER cuando estés listo...')

            silence_detected = False
            speech_detected = False
            speech_end_detected = False

            start_time = time.time()
            while time.time() - start_time < 10:  # 10 segundos de prueba
                frame = capture.get_audio_frame()
                if frame is not None:
                    filtered = noise_filter.apply_filter(frame)
                    event = vad.process_frame(filtered)

                    if event == 'silence':
                        silence_detected = True
                    elif event == 'speech_start':
                        speech_detected = True
                        logger.info('  → Voz detectada')
                    elif event == 'speech_end':
                        speech_end_detected = True
                        logger.info('  → Fin de voz detectado')
                        break

                time.sleep(0.01)

            if silence_detected:
                self.log_test('Detección de silencio', 'passed', 'Silencio detectado')
            else:
                self.log_test('Detección de silencio', 'failed', 'No se detectó silencio')

            if speech_detected:
                self.log_test('Detección de voz', 'passed', 'Voz detectada')
            else:
                self.log_test('Detección de voz', 'failed', 'No se detectó voz')

            if speech_end_detected:
                self.log_test('Detección de fin de voz', 'passed', 'Fin detectado')
            else:
                self.log_test('Detección de fin de voz', 'skipped', 'No se completó en tiempo')

            # Test de reset
            vad.reset()
            if not vad.is_speech_active():
                self.log_test('Reset VAD', 'passed', 'Estado reseteado correctamente')

            return speech_detected  # Suficiente si detectó voz

        except Exception as e:
            self.log_test('VAD', 'failed', str(e))
            return False

    def test_audio_buffer(self):
        """Test 5: Buffer de audio thread-safe"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 5: BUFFER DE AUDIO')
        logger.info('=' * 60)

        try:
            # Test de grabación
            audio_buffer.start_recording()
            self.log_test('Inicio de grabación', 'passed', 'Buffer iniciado')

            # Agregar frames
            for i in range(50):
                frame = capture.get_audio_frame()
                if frame is not None:
                    audio_buffer.append_frame(frame)

            buffer_size = audio_buffer.get_buffer_size()
            duration = audio_buffer.get_duration_seconds()

            if buffer_size > 0:
                self.log_test('Almacenamiento en buffer', 'passed', f'{buffer_size} samples, {duration:.2f}s')
            else:
                self.log_test('Almacenamiento en buffer', 'failed', 'Buffer vacío')
                return False

            # Test de obtención de datos
            buffer_copy = audio_buffer.get_buffer_copy()
            if len(buffer_copy) == buffer_size:
                self.log_test('Copia de buffer', 'passed', 'Copia correcta')

            buffer_bytes = audio_buffer.get_buffer_as_bytes()
            if len(buffer_bytes) > 0:
                self.log_test('Buffer como bytes', 'passed', f'{len(buffer_bytes)} bytes')

            buffer_numpy = audio_buffer.get_buffer_as_numpy()
            if len(buffer_numpy) == buffer_size:
                self.log_test('Buffer como numpy', 'passed', 'Conversión correcta')

            # Test de detención
            audio_buffer.stop_recording()
            self.log_test('Detención de grabación', 'passed', 'Buffer detenido')

            # Test de limpieza
            audio_buffer.clear_buffer()
            if audio_buffer.get_buffer_size() == 0:
                self.log_test('Limpieza de buffer', 'passed', 'Buffer limpio')

            return True

        except Exception as e:
            self.log_test('Buffer de audio', 'failed', str(e))
            return False

    def test_playback(self):
        """Test 6: Reproducción de audio"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 6: REPRODUCCIÓN DE AUDIO')
        logger.info('=' * 60)

        try:
            success = playback.initialize()
            if success:
                self.log_test('Inicialización playback', 'passed', 'Sounddevice inicializado')
                self.modules_initialized.append('playback')
            else:
                self.log_test('Inicialización playback', 'failed', 'No se pudo inicializar')
                return False

            # Test de volumen
            playback.set_volume(0.5)
            if playback.get_volume() == 0.5:
                self.log_test('Control de volumen', 'passed', 'Volumen ajustado')

            # Generar tono de prueba (440 Hz - La)
            import numpy as np
            duration = 0.5  # segundos
            samples = int(settings.SAMPLE_RATE * duration)
            t = np.linspace(0, duration, samples)
            frequency = 440  # Hz
            test_tone = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)

            logger.info('Reproduciendo tono de prueba (440 Hz, 0.5s)...')
            success = playback.play_audio(test_tone, blocking=True)

            if success:
                self.log_test('Reproducción de audio', 'passed', 'Tono reproducido')
            else:
                self.log_test('Reproducción de audio', 'failed', 'No se pudo reproducir')
                return False

            return True

        except Exception as e:
            self.log_test('Reproducción de audio', 'failed', str(e))
            return False

    def test_wake_word(self):
        """Test 7: Detección de wake word"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 7: WAKE WORD DETECTION')
        logger.info('=' * 60)

        try:
            success = wake_word.initialize(
                access_key=settings.PORCUPINE_ACCESS_KEY,
                keyword_path=settings.PORCUPINE_KEYWORD_PATH,
                model_path=settings.PORCUPINE_MODEL_PATH,
                sensitivity=settings.PORCUPINE_SENSITIVITY
            )

            if success:
                self.log_test('Inicialización Porcupine', 'passed', 'Wake word inicializado')
                self.modules_initialized.append('wake_word')
            else:
                self.log_test('Inicialización Porcupine', 'failed', 'No se pudo inicializar')
                return False

            # Verificar frame length
            frame_length = wake_word.get_frame_length()
            sample_rate = wake_word.get_sample_rate()

            if frame_length and sample_rate == settings.SAMPLE_RATE:
                self.log_test('Configuración Porcupine', 'passed', f'Frame: {frame_length}, SR: {sample_rate}')

            logger.info('')
            logger.info(f'Ahora di "{settings.WAKE_WORD.upper()}" para probar detección')
            logger.info('Tienes 10 segundos...')

            detected = False
            start_time = time.time()

            while time.time() - start_time < 10:
                frame = capture.get_audio_frame()
                if frame is not None:
                    filtered = noise_filter.apply_filter(frame)
                    if wake_word.process_frame(filtered):
                        detected = True
                        break
                time.sleep(0.001)

            if detected:
                self.log_test('Detección de wake word', 'passed', f'"{settings.WAKE_WORD}" detectado')
                return True
            else:
                self.log_test('Detección de wake word', 'skipped', 'No se dijo la palabra o tiempo agotado')
                return True  # No fallar el test, es opcional

        except Exception as e:
            self.log_test('Wake word', 'failed', str(e))
            return False

    def test_commands(self):
        """Test 8: Detección de comandos"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 8: DETECCIÓN DE COMANDOS')
        logger.info('=' * 60)

        try:
            success = commands.initialize(settings.VOSK_MODEL_PATH)

            if success:
                self.log_test('Inicialización Vosk', 'passed', 'Comandos inicializados')
                self.modules_initialized.append('commands')
            else:
                self.log_test('Inicialización Vosk', 'failed', 'No se pudo inicializar')
                return False

            logger.info('')
            logger.info('Comandos disponibles:')
            logger.info('  MOVIMIENTO: "ven aquí", "detente", "sígueme"')
            logger.info('  MÉDICOS: "mide signos", "dispensa medicamento"')
            logger.info('  CONTROL: "cancela", "silencio"')
            logger.info('')
            logger.info('Di un COMANDO (tienes 10 segundos)...')

            command_detected = False
            listening = False
            start_time = time.time()

            clear_events()

            while time.time() - start_time < 10:
                frame = capture.get_audio_frame()
                if frame is not None:
                    filtered = noise_filter.apply_filter(frame)
                    event_vad = vad.process_frame(filtered)

                    if event_vad == 'speech_start':
                        listening = True
                        commands.reset()
                        logger.info('  → Escuchando...')

                    if listening:
                        result = commands.process_audio_streaming(filtered)
                        if result and result['type'] != 'UNKNOWN':
                            command_detected = True
                            logger.info(f'  → Comando: {result["type"]}/{result["action"]}')
                            break

                    if event_vad == 'speech_end' and listening:
                        break

                time.sleep(0.001)

            if command_detected:
                self.log_test('Detección de comandos', 'passed', 'Comando detectado')
                return True
            else:
                self.log_test('Detección de comandos', 'skipped', 'No se dijo comando o no se reconoció')
                return True  # No fallar, es opcional

        except Exception as e:
            self.log_test('Comandos', 'failed', str(e))
            return False

    def test_events_system(self):
        """Test 9: Sistema de eventos"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('TEST 9: SISTEMA DE EVENTOS')
        logger.info('=' * 60)

        try:
            from baymax_voice.utils.events import put_event, get_event, clear_events, queue_size

            # Limpiar cola
            clear_events()
            self.log_test('Limpieza de eventos', 'passed', 'Cola limpia')

            # Agregar eventos de prueba
            put_event('TEST_EVENT_1', data={'value': 1}, source='test')
            put_event('TEST_EVENT_2', data={'value': 2}, source='test')
            put_event('TEST_EVENT_3', data={'value': 3}, source='test')

            size = queue_size()
            if size == 3:
                self.log_test('Agregar eventos', 'passed', f'{size} eventos en cola')
            else:
                self.log_test('Agregar eventos', 'failed', f'Se esperaban 3, hay {size}')
                return False

            # Obtener eventos
            event1 = get_event(timeout=0.1)
            if event1 and event1.type == 'TEST_EVENT_1':
                self.log_test('Obtener evento', 'passed', 'Evento obtenido correctamente')
            else:
                self.log_test('Obtener evento', 'failed', 'Evento incorrecto')

            # Verificar orden FIFO
            event2 = get_event(timeout=0.1)
            if event2 and event2.type == 'TEST_EVENT_2':
                self.log_test('Orden FIFO', 'passed', 'Eventos en orden correcto')

            # Limpiar
            clear_events()
            if queue_size() == 0:
                self.log_test('Limpieza final', 'passed', 'Cola vacía')

            return True

        except Exception as e:
            self.log_test('Sistema de eventos', 'failed', str(e))
            return False

    def cleanup(self):
        """Limpia todos los módulos inicializados"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('LIMPIEZA DE RECURSOS')
        logger.info('=' * 60)

        if 'commands' in self.modules_initialized:
            commands.shutdown()
            logger.info('✓ Comandos cerrado')

        if 'wake_word' in self.modules_initialized:
            wake_word.shutdown()
            logger.info('✓ Wake word cerrado')

        if 'playback' in self.modules_initialized:
            playback.shutdown()
            logger.info('✓ Playback cerrado')

        if 'capture' in self.modules_initialized:
            capture.shutdown()
            logger.info('✓ Captura cerrada')

    def print_summary(self):
        """Imprime resumen de resultados"""
        logger.info('')
        logger.info('=' * 60)
        logger.info('RESUMEN DE RESULTADOS')
        logger.info('=' * 60)

        total = len(self.test_results['passed']) + len(self.test_results['failed']) + len(self.test_results['skipped'])
        passed = len(self.test_results['passed'])
        failed = len(self.test_results['failed'])
        skipped = len(self.test_results['skipped'])

        logger.info(f'Total de tests: {total}')
        logger.info(f'✓ Pasados: {passed}')
        logger.info(f'✗ Fallidos: {failed}')
        logger.info(f'⊘ Omitidos: {skipped}')

        if failed > 0:
            logger.info('')
            logger.info('Tests fallidos:')
            for test in self.test_results['failed']:
                logger.info(f'  ✗ {test}')

        logger.info('')
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f'Tasa de éxito: {success_rate:.1f}%')

        if failed == 0:
            logger.info('')
            logger.info('🎉 TODOS LOS TESTS PASARON 🎉')
        elif success_rate >= 80:
            logger.info('')
            logger.info('✓ Sistema mayormente funcional')
        else:
            logger.info('')
            logger.info('⚠ Sistema requiere atención')

        return failed == 0

    def run_all_tests(self):
        """Ejecuta todos los tests en secuencia"""
        logger.info('')
        logger.info('╔' + '═' * 58 + '╗')
        logger.info('║' + ' ' * 10 + 'TEST DE INTEGRACIÓN COMPLETO' + ' ' * 20 + '║')
        logger.info('║' + ' ' * 18 + 'Sistema Baymax' + ' ' * 26 + '║')
        logger.info('╚' + '═' * 58 + '╝')
        logger.info('')
        logger.info('Este test verificará TODAS las funciones del sistema:')
        logger.info('  • Configuración')
        logger.info('  • Captura de audio')
        logger.info('  • Filtro de ruido')
        logger.info('  • VAD (Voice Activity Detection)')
        logger.info('  • Buffer de audio')
        logger.info('  • Reproducción de audio')
        logger.info('  • Wake Word Detection')
        logger.info('  • Detección de comandos')
        logger.info('  • Sistema de eventos')
        logger.info('')
        logger.info('Algunos tests requerirán tu participación (hablar, silencio, etc.)')
        logger.info('')

        input('Presiona ENTER para comenzar...')

        try:
            # Ejecutar tests en secuencia
            self.test_configuration_validation()
            self.test_audio_capture_init()
            self.test_noise_filter()
            self.test_vad()
            self.test_audio_buffer()
            self.test_playback()
            self.test_wake_word()
            self.test_commands()
            self.test_events_system()

        except KeyboardInterrupt:
            logger.info('')
            logger.info('Test interrumpido por usuario')
        except Exception as e:
            logger.error(f'Error inesperado: {e}')
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
            success = self.print_summary()
            return success


def main():
    test = IntegrationTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

