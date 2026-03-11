"""
Sistema de logging centralizado para el proyecto.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from baymax_voice.config import settings

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR
}


def setup_logger(level=None):
    logger = logging.getLogger('baymax')
    effective_level = LOG_LEVELS.get(level or settings.LOG_LEVEL, logging.INFO)
    logger.setLevel(effective_level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if settings.LOG_TO_FILE:
        log_dir = 'logs'
        Path(log_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_handler = logging.FileHandler(f'{log_dir}/baymax_{timestamp}.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(module_name):
    return logging.getLogger(f'baymax.{module_name}')