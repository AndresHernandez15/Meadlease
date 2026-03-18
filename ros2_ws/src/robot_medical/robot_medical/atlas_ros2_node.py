#!/usr/bin/env python3
"""
atlas_ros2_node.py — Nodo ROS2 wrapper del sistema conversacional Atlas.
Estrategia: Wrapper (Atlas corre en thread interno, ROS2 es el bridge externo).
"""

import os
import sys
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Int32, Float32
from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_ATLAS_DIR  = os.path.join(_THIS_DIR, 'atlas')
_LEGACY_ATLAS_DIR = os.path.abspath(
    os.path.join(_THIS_DIR, '..', '..', '..', '..', 'atlas')
)
_DOTENV_CANDIDATES = [
    os.path.join(_ATLAS_DIR, '.env'),
    os.path.join(_LEGACY_ATLAS_DIR, '.env'),
]

# Añadir atlas/ al path ANTES de importar cualquier módulo de baymax_voice
sys.path.insert(0, _ATLAS_DIR)

# Cargar API keys (.env) desde ubicación integrada o legacy
_LOADED_DOTENV = None
for _dotenv_path in _DOTENV_CANDIDATES:
    if os.path.isfile(_dotenv_path):
        load_dotenv(_dotenv_path)
        _LOADED_DOTENV = _dotenv_path
        break

# ── Imports de Atlas (después de ajustar sys.path) ───────────────────────────
from baymax_voice.utils.events import put_event, register_callback  # noqa: E402


class AtlasNode(Node):
    """Nodo ROS2 que encapsula el sistema conversacional Atlas."""

    # Eventos internos de Atlas que se exponen como topics ROS2
    SPEAKING_START   = 'SPEAKING_START'
    STATE_CHANGED    = 'STATE_CHANGED'
    COMMAND_DETECTED = 'COMMAND_DETECTED'
    PLAYBACK_DONE    = 'PLAYBACK_DONE'

    def __init__(self):
        super().__init__('atlas_ros2_node')
        self.get_logger().info('Iniciando AtlasNode...')
        if _LOADED_DOTENV:
            self.get_logger().info(f'Archivo .env cargado: {_LOADED_DOTENV}')
        else:
            self.get_logger().warning(
                'No se encontró .env en atlas integrado ni en atlas legacy; '
                'se usarán solo variables ya exportadas en el entorno.'
            )

        # Estado compartido — actualizado por subscribers ROS2, leído por Atlas
        self._shared_state = {
            'bpm':         None,
            'spo2':        None,
            'temperature': None,
            'patient_id':  None,
        }
        self._state_lock = threading.Lock()

        # ── Publishers ───────────────────────────────────────────────────────
        self._pub_listening = self.create_publisher(
            Bool, '/atlas/listening', 10)
        self._pub_command = self.create_publisher(
            String, '/atlas/detected_command', 10)
        self._pub_speak = self.create_publisher(
            String, '/robot/speak', 10)

        # ── Subscribers ──────────────────────────────────────────────────────
        self.create_subscription(
            Int32, '/health/bpm', self._on_bpm, 10)
        self.create_subscription(
            Int32, '/health/spo2', self._on_spo2, 10)
        self.create_subscription(
            Float32, '/health/temperature', self._on_temperature, 10)
        self.create_subscription(
            String, '/patient/identified', self._on_patient_identified, 10)

        # ── Conectar al EventBus de Atlas ─────────────────────────────────────
        register_callback(self._on_atlas_event)

        # ── Lanzar Atlas en thread daemon ─────────────────────────────────────
        self._atlas_thread = threading.Thread(
            target=self._run_atlas,
            name='atlas_main',
            daemon=True
        )
        self._atlas_thread.start()
        self.get_logger().info('AtlasNode listo — thread Atlas iniciado.')

    # ── Callbacks ROS2 (Robot → Atlas) ───────────────────────────────────────

    def _on_bpm(self, msg: Int32) -> None:
        with self._state_lock:
            self._shared_state['bpm'] = msg.data

    def _on_spo2(self, msg: Int32) -> None:
        with self._state_lock:
            self._shared_state['spo2'] = msg.data

    def _on_temperature(self, msg: Float32) -> None:
        with self._state_lock:
            self._shared_state['temperature'] = msg.data

    def _on_patient_identified(self, msg: String) -> None:
        with self._state_lock:
            self._shared_state['patient_id'] = msg.data
        # Notificar a la FSM de Atlas
        put_event('PATIENT_IDENTIFIED', msg.data)
        self.get_logger().info(f'Paciente identificado: {msg.data}')

    # ── Callback EventBus (Atlas → ROS2) ─────────────────────────────────────

    def _on_atlas_event(self, event_type: str, data=None) -> None:
        """Recibe eventos internos de Atlas y los publica como topics ROS2."""
        if event_type == self.SPEAKING_START:
            msg = String()
            msg.data = str(data) if data else ''
            self._pub_speak.publish(msg)

        elif event_type == self.STATE_CHANGED:
            listening = (data == 'LISTENING')
            msg = Bool()
            msg.data = listening
            self._pub_listening.publish(msg)

        elif event_type == self.COMMAND_DETECTED:
            msg = String()
            msg.data = str(data) if data else ''
            self._pub_command.publish(msg)

    # ── Thread Atlas ──────────────────────────────────────────────────────────

    def _run_atlas(self) -> None:
        """Lanza Atlas directamente sin registrar signal handlers — rclpy los maneja."""
        try:
            from baymax_voice.main import initialize_all, start, shutdown, _shutdown_event

            if not initialize_all():
                self.get_logger().error('Atlas: inicialización falló — módulo crítico no disponible')
                return

            start()
            self.get_logger().info('Atlas: sistema conversacional activo 🎙️')

            while not _shutdown_event.is_set():
                _shutdown_event.wait(timeout=1.0)

        except Exception as e:
            self.get_logger().error(f'Atlas thread terminó con error: {e}')

    def get_shared_state(self) -> dict:
        """Acceso thread-safe al estado compartido (para uso de medical_db)."""
        with self._state_lock:
            return dict(self._shared_state)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = AtlasNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

