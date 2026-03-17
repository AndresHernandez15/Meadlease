"""
Sistema de eventos thread-safe para comunicación entre módulos.
"""
from queue import Queue, Empty
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime
from baymax_voice.utils.logger import get_logger

logger = get_logger('utils.events')


@dataclass
class Event:
    type: str
    data: Optional[Any] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


_event_queue = Queue()


def put_event(event_type, data=None, source=None):
    event = Event(type=event_type, data=data, source=source)
    _event_queue.put(event)
    logger.debug(f'Evento: {event_type} (origen: {source})')

    for cb in _callbacks:
        try:
            cb(event_type, data)
        except Exception:
            pass


def get_event(timeout=None):
    try:
        return _event_queue.get(timeout=timeout)
    except Empty:
        return None



def clear_events():
    while not _event_queue.empty():
        try:
            _event_queue.get_nowait()
        except Empty:
            break
    logger.debug('Cola de eventos limpiada')


def queue_size():
    return _event_queue.qsize()


# ── ROS2 Bridge hook (no modifica comportamiento existente) ──────────────
_callbacks: list = []

def register_callback(cb) -> None:
    """Registra una función que recibe (event_type, data) sin consumir el evento."""
    _callbacks.append(cb)

def unregister_all_callbacks() -> None:
    """Limpia callbacks — útil en tests."""
    _callbacks.clear()

