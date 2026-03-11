#!/usr/bin/env python3
"""
Test interactivo del micrófono del Kinect V2
Prueba la captura de audio con la configuración exacta que usará el módulo Atlas.

Uso:
    python3 kinect_mic_test.py [--record 5] [--playback] [--vosk]

Requisitos:
    pip install pyaudio webrtcvad
"""

import argparse
import wave
import sys
import os
import struct
import numpy as np
import threading
import time

# ─── Configuración del dispositivo ──────────────────────────────────────────
# Micrófono Kinect V2 - detectado en el sistema como:
#   ALSA:       hw:0,0  (card 0, device 0)
#   PulseAudio: alsa_input.usb-Microsoft_Xbox_NUI_Sensor_204763633847-02
KINECT_SAMPLE_RATE = 16000      # Hz nativo del hardware
KINECT_CHANNELS    = 4          # Array de 4 micrófonos
KINECT_FORMAT_ALSA = "S32_LE"   # 32-bit little-endian
FRAME_DURATION_MS  = 20         # ms por frame (requerido por webrtcvad)

# Ganancia de amplificación digital (el Kinect tiene salida baja ~-44dB)
# Factor 16 = +24.3 dB → niveles conversacionales normales
DIGITAL_GAIN = 16.0

# ─── Indices de canal PulseAudio ─────────────────────────────────────────────
# [0] front-left  [1] front-right  [2] rear-left  [3] rear-right
# rear-right mostró mejor SNR en pruebas → usar como canal principal
BEST_CHANNEL = 3  # rear-right (puede cambiar con posición del Kinect)


def find_kinect_device_index():
    """
    Busca el índice PyAudio del micrófono del Kinect V2.
    Retorna el índice o None si no se encuentra.
    """
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        kinect_index = None
        
        print("🔍  Buscando dispositivo Kinect V2...")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name = info.get('name', '').lower()
            max_input = info.get('maxInputChannels', 0)
            
            if 'xbox' in name or 'kinect' in name or 'nui' in name:
                print(f"   ✅ Encontrado: [{i}] {info['name']}")
                print(f"      Canales entrada:  {max_input}")
                print(f"      Sample rate:      {info['defaultSampleRate']} Hz")
                kinect_index = i
        
        if kinect_index is None:
            print("   ⚠️  No encontrado por nombre. Listando todos los dispositivos:")
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    print(f"   [{i}] {info['name']} ({info['maxInputChannels']}ch)")
        
        p.terminate()
        return kinect_index
    except ImportError:
        print("❌  PyAudio no instalado. Instalar con: pip install pyaudio")
        return None


def record_with_pyaudio(duration_sec: int, output_file: str, device_index: int = None):
    """
    Graba audio desde el Kinect usando PyAudio.
    Aplica ganancia digital y mezcla a mono.
    
    Args:
        duration_sec: Segundos a grabar
        output_file: Ruta del archivo WAV de salida
        device_index: Índice del dispositivo (None = buscar automáticamente)
    """
    try:
        import pyaudio
    except ImportError:
        print("❌  PyAudio no instalado. Instalar con: pip install pyaudio")
        return False
    
    p = pyaudio.PyAudio()
    
    if device_index is None:
        device_index = find_kinect_device_index()
    
    if device_index is None:
        print("❌  No se pudo encontrar el Kinect, usando dispositivo por defecto")
    
    # Frames por chunk de 20ms (requerido por webrtcvad)
    frames_per_chunk = int(KINECT_SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    
    print(f"\n⏺  Grabando {duration_sec} segundos desde el Kinect...")
    print(f"   Sample rate: {KINECT_SAMPLE_RATE} Hz | Canales: {KINECT_CHANNELS} | Gain: +{20*np.log10(DIGITAL_GAIN):.0f} dB")
    
    all_frames: list[bytes] = []
    
    # Indicador de progreso en otra thread
    stop_event = threading.Event()
    
    def progress():
        for i in range(duration_sec):
            if stop_event.is_set():
                break
            bar = '█' * (i + 1) + '░' * (duration_sec - i - 1)
            print(f"\r   [{bar}] {i+1}/{duration_sec}s", end='', flush=True)
            time.sleep(1)
        print()
    
    progress_thread = threading.Thread(target=progress)
    progress_thread.start()
    
    try:
        # PyAudio no soporta S32_LE directamente → usar paInt32
        stream = p.open(
            format=pyaudio.paInt32,
            channels=KINECT_CHANNELS,
            rate=KINECT_SAMPLE_RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=frames_per_chunk
        )
        
        total_chunks = int(duration_sec * KINECT_SAMPLE_RATE / frames_per_chunk)
        
        for _ in range(total_chunks):
            data = stream.read(frames_per_chunk, exception_on_overflow=False)
            all_frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"\n❌  Error en grabación: {e}")
        stop_event.set()
        progress_thread.join()
        p.terminate()
        return False
    
    stop_event.set()
    progress_thread.join()
    
    p.terminate()
    
    # ── Procesar audio capturado ──────────────────────────────────────────────
    raw = b''.join(all_frames)
    samples = np.frombuffer(raw, dtype=np.int32).reshape(-1, KINECT_CHANNELS)
    samples_f = samples.astype(np.float32) / (2**31)
    
    # Mezclar a mono (promedio de todos los canales para omnidireccional)
    mono = np.mean(samples_f, axis=1)
    
    # Aplicar ganancia digital
    mono_amplified = np.clip(mono * DIGITAL_GAIN, -0.99, 0.99)
    
    # Métricas
    rms = np.sqrt(np.mean(mono_amplified**2))
    rms_db = 20 * np.log10(rms + 1e-10)
    print(f"   RMS tras ganancia: {rms_db:.1f} dB")
    
    # Guardar como WAV 16-bit mono (formato ideal para Vosk/Whisper)
    samples_16 = (mono_amplified * 32767).astype(np.int16)
    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(KINECT_SAMPLE_RATE)
        wf.writeframes(samples_16.tobytes())
    
    size_kb = os.path.getsize(output_file) / 1024
    print(f"   ✅ Guardado: {output_file} ({size_kb:.0f} KB)")
    return True


def test_with_vosk(audio_file: str):
    """
    Intenta reconocer el audio grabado con Vosk (si está instalado).
    """
    try:
        from vosk import Model, KaldiRecognizer
    except ImportError:
        print("⚠️  Vosk no instalado. Para instalarlo: pip install vosk")
        print("    También necesitas el modelo: vosk-model-small-es-0.42")
        return
    
    model_path = os.path.expanduser("~/vosk_models/vosk-model-small-es-0.42")
    if not os.path.exists(model_path):
        print(f"⚠️  Modelo Vosk no encontrado en: {model_path}")
        print("    Descarga: https://alphacephei.com/vosk/models")
        return
    
    print("\n🧠  Probando reconocimiento de voz con Vosk...")
    model = Model(model_path)
    rec = KaldiRecognizer(model, KINECT_SAMPLE_RATE)
    
    with wave.open(audio_file, 'rb') as wf:
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            rec.AcceptWaveform(data)
    
    result = rec.FinalResult()
    print(f"   Texto reconocido: {result}")


def print_pyaudio_config():
    """Imprime la configuración PyAudio para usar en el módulo Atlas."""
    device_index = find_kinect_device_index()
    
    print("\n" + "=" * 60)
    print("   📋  CONFIGURACIÓN PARA MÓDULO ATLAS (PyAudio)")
    print("=" * 60)
    print(f"""
# En baymax_voice/config/settings.py o atlas_ros2_node.py:

# Micrófono Kinect V2
AUDIO_DEVICE_INDEX  = {device_index}    # Xbox NUI Sensor
AUDIO_SAMPLE_RATE   = {KINECT_SAMPLE_RATE}      # Hz (nativo, ideal para Vosk/Whisper)
AUDIO_CHANNELS_RAW  = {KINETIC_CHANNELS}         # Canales del hardware
AUDIO_CHANNELS_OUT  = 1         # Mono tras mezcla
AUDIO_FORMAT        = pyaudio.paInt32  # 32-bit signed
DIGITAL_GAIN        = {DIGITAL_GAIN}       # Amplificación x{DIGITAL_GAIN:.0f} para nivel normal

# En capture.py — ajustar para Kinect:
stream = p.open(
    format=pyaudio.paInt32,
    channels={KINECT_CHANNELS},           # 4 canales del Kinect
    rate={KINECT_SAMPLE_RATE},
    input=True,
    input_device_index={device_index},
    frames_per_buffer=320        # 20ms @ 16kHz
)
# Luego mezclar los 4 canales a 1 y amplificar x{DIGITAL_GAIN:.0f}
""")


if __name__ == '__main__':
    KINETIC_CHANNELS = KINECT_CHANNELS  # alias para el f-string

    parser = argparse.ArgumentParser(description='Test micrófono Kinect V2')
    parser.add_argument('--record', type=int, default=5, metavar='SEGUNDOS',
                        help='Grabar N segundos (default: 5)')
    parser.add_argument('--output', default='/tmp/kinect_pyaudio_test.wav',
                        help='Archivo de salida')
    parser.add_argument('--vosk', action='store_true',
                        help='Probar reconocimiento con Vosk')
    parser.add_argument('--config', action='store_true',
                        help='Solo mostrar configuración para Atlas')
    parser.add_argument('--device', type=int, default=None,
                        help='Índice dispositivo PyAudio (auto-detectar si no se especifica)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("    🎙️  TEST MICRÓFONO KINECT V2 — Atlas Module")
    print("=" * 60)
    
    if args.config:
        print_pyaudio_config()
        sys.exit(0)
    
    # Mostrar dispositivo detectado
    device_index = find_kinket_device_index() if args.device is None else args.device
    
    # Grabar
    success = record_with_pyaudio(args.record, args.output, device_index)
    
    if success:
        print("\n🔊  Para reproducir:")
        print(f"    aplay {args.output}")
        
        if args.vosk:
            test_with_vosk(args.output)
        
        print_pyaudio_config()
    
    print()
