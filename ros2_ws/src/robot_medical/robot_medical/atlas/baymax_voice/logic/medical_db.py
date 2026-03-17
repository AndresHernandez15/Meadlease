"""
Base de datos médica SQLite (pacientes, medicamentos, signos vitales).
"""
import sqlite3
import logging
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger('medical_db')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(handler)

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'patient.db'


# ── CAPA 1 — Inicialización ──

def init_db() -> bool:
    """
    Inicializa la base de datos creando todas las tablas si no existen.
    Habilita foreign keys y crea el directorio data/ si no existe.

    Returns:
        bool: True si la inicialización fue exitosa, False en caso contrario
    """
    try:
        # Crear directorio data/ si no existe
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f'Directorio de datos: {DB_PATH.parent}')

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Habilitar foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')

            # Tabla pacientes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pacientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    ruta_encoding_facial TEXT,
                    notas TEXT,
                    activo INTEGER NOT NULL DEFAULT 1
                )
            ''')

            # Tabla medicamentos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medicamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    unidad TEXT NOT NULL,
                    id_compartimento INTEGER NOT NULL UNIQUE CHECK (id_compartimento BETWEEN 1 AND 6),
                    stock INTEGER NOT NULL DEFAULT 0,
                    ultima_recarga TEXT,
                    activo INTEGER NOT NULL DEFAULT 1
                )
            ''')

            # Tabla horarios_medicacion
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS horarios_medicacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_paciente INTEGER NOT NULL,
                    id_medicamento INTEGER NOT NULL,
                    hora_programada TEXT NOT NULL,
                    dias_semana TEXT NOT NULL,
                    dosis_unidades INTEGER NOT NULL DEFAULT 1,
                    activo INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (id_paciente) REFERENCES pacientes(id),
                    FOREIGN KEY (id_medicamento) REFERENCES medicamentos(id)
                )
            ''')

            # Tabla signos_vitales
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signos_vitales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_paciente INTEGER NOT NULL,
                    bpm INTEGER NOT NULL,
                    spo2 INTEGER NOT NULL,
                    temperatura REAL NOT NULL,
                    medido_en TEXT NOT NULL,
                    notas TEXT,
                    FOREIGN KEY (id_paciente) REFERENCES pacientes(id)
                )
            ''')

            # Tabla registros_dispensacion
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS registros_dispensacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_paciente INTEGER NOT NULL,
                    id_medicamento INTEGER NOT NULL,
                    id_horario INTEGER NOT NULL,
                    dispensado_en TEXT NOT NULL,
                    estado TEXT NOT NULL CHECK (estado IN ('exitoso', 'fallido', 'omitido', 'pendiente')),
                    notas TEXT,
                    FOREIGN KEY (id_paciente) REFERENCES pacientes(id),
                    FOREIGN KEY (id_medicamento) REFERENCES medicamentos(id),
                    FOREIGN KEY (id_horario) REFERENCES horarios_medicacion(id)
                )
            ''')

            conn.commit()
            logger.info('Base de datos inicializada correctamente')
            return True

    except Exception as e:
        logger.error(f'Error inicializando base de datos: {e}')
        return False


# ── CAPA 2 — CRUD por Entidad ──

# ── Pacientes ──
# PACIENTES

def crear_paciente(nombre: str, ruta_encoding_facial: Optional[str] = None, notas: Optional[str] = None) -> Optional[int]:
    """
    Crea un nuevo paciente en la base de datos.

    Args:
        nombre: Nombre completo del paciente
        ruta_encoding_facial: Ruta al archivo de encoding facial (opcional)
        notas: Notas adicionales sobre el paciente (opcional)

    Returns:
        int: ID del paciente creado, None si falla
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO pacientes (nombre, ruta_encoding_facial, notas) VALUES (?, ?, ?)',
                (nombre, ruta_encoding_facial, notas)
            )
            conn.commit()
            paciente_id = cursor.lastrowid
            logger.info(f'Paciente creado: {nombre} (ID: {paciente_id})')
            return paciente_id

    except Exception as e:
        logger.error(f'Error creando paciente: {e}')
        return None


def obtener_paciente(id_paciente: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un paciente por su ID.

    Args:
        id_paciente: ID del paciente

    Returns:
        dict: Datos del paciente o None si no existe
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pacientes WHERE id = ?', (id_paciente,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    except Exception as e:
        logger.error(f'Error obteniendo paciente {id_paciente}: {e}')
        return None


def obtener_pacientes_activos() -> List[Dict[str, Any]]:
    """
    Obtiene todos los pacientes activos.

    Returns:
        list: Lista de diccionarios con datos de pacientes activos
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pacientes WHERE activo = 1')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f'Error obteniendo pacientes activos: {e}')
        return []


def desactivar_paciente(id_paciente: int) -> bool:
    """
    Desactiva un paciente (soft delete).

    Args:
        id_paciente: ID del paciente a desactivar

    Returns:
        bool: True si se desactivó correctamente, False en caso contrario
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE pacientes SET activo = 0 WHERE id = ?', (id_paciente,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f'Paciente {id_paciente} desactivado')
                return True
            else:
                logger.warning(f'Paciente {id_paciente} no encontrado')
                return False

    except Exception as e:
        logger.error(f'Error desactivando paciente {id_paciente}: {e}')
        return False


# ── MEDICAMENTOS ──

def crear_medicamento(
    nombre: str,
    unidad: str,
    id_compartimento: int,
    descripcion: Optional[str] = None,
    stock: int = 0
) -> Optional[int]:
    """
    Crea un nuevo medicamento en la base de datos.

    Args:
        nombre: Nombre del medicamento
        unidad: Unidad de medida (ej: 'tabletas', 'ml', 'mg')
        id_compartimento: Número de compartimento (1-6)
        descripcion: Descripción del medicamento (opcional)
        stock: Cantidad inicial en stock (default: 0)

    Returns:
        int: ID del medicamento creado, None si falla
    """
    try:
        if not (1 <= id_compartimento <= 6):
            logger.error(f'id_compartimento debe estar entre 1 y 6, recibido: {id_compartimento}')
            return None

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO medicamentos 
                   (nombre, descripcion, unidad, id_compartimento, stock, ultima_recarga) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (nombre, descripcion, unidad, id_compartimento, stock, datetime.now().isoformat() if stock > 0 else None)
            )
            conn.commit()
            medicamento_id = cursor.lastrowid
            logger.info(f'Medicamento creado: {nombre} (ID: {medicamento_id}, Compartimento: {id_compartimento})')
            return medicamento_id

    except sqlite3.IntegrityError as e:
        logger.error(f'Error: compartimento {id_compartimento} ya está ocupado')
        return None
    except Exception as e:
        logger.error(f'Error creando medicamento: {e}')
        return None


def obtener_medicamento(id_medicamento: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un medicamento por su ID.

    Args:
        id_medicamento: ID del medicamento

    Returns:
        dict: Datos del medicamento o None si no existe
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM medicamentos WHERE id = ?', (id_medicamento,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    except Exception as e:
        logger.error(f'Error obteniendo medicamento {id_medicamento}: {e}')
        return None


def obtener_medicamentos_activos() -> List[Dict[str, Any]]:
    """
    Obtiene todos los medicamentos activos.

    Returns:
        list: Lista de diccionarios con datos de medicamentos activos
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM medicamentos WHERE activo = 1 ORDER BY id_compartimento')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f'Error obteniendo medicamentos activos: {e}')
        return []


def actualizar_stock_medicamento(id_medicamento: int, nuevo_stock: int) -> bool:
    """
    Actualiza el stock de un medicamento.

    Args:
        id_medicamento: ID del medicamento
        nuevo_stock: Nueva cantidad en stock

    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE medicamentos SET stock = ?, ultima_recarga = ? WHERE id = ?',
                (nuevo_stock, datetime.now().isoformat(), id_medicamento)
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f'Stock medicamento {id_medicamento} actualizado a {nuevo_stock}')
                return True
            else:
                logger.warning(f'Medicamento {id_medicamento} no encontrado')
                return False

    except Exception as e:
        logger.error(f'Error actualizando stock medicamento {id_medicamento}: {e}')
        return False


def desactivar_medicamento(id_medicamento: int) -> bool:
    """
    Desactiva un medicamento (soft delete).

    Args:
        id_medicamento: ID del medicamento a desactivar

    Returns:
        bool: True si se desactivó correctamente, False en caso contrario
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE medicamentos SET activo = 0 WHERE id = ?', (id_medicamento,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f'Medicamento {id_medicamento} desactivado')
                return True
            else:
                logger.warning(f'Medicamento {id_medicamento} no encontrado')
                return False

    except Exception as e:
        logger.error(f'Error desactivando medicamento {id_medicamento}: {e}')
        return False


# ── HORARIOS DE MEDICACIÓN ──

def crear_horario_medicacion(
    id_paciente: int,
    id_medicamento: int,
    hora_programada: str,
    dias_semana: str,
    dosis_unidades: int = 1
) -> Optional[int]:
    """
    Crea un nuevo horario de medicación.

    Args:
        id_paciente: ID del paciente
        id_medicamento: ID del medicamento
        hora_programada: Hora en formato "HH:MM" (ej: "08:00", "14:30")
        dias_semana: String de dígitos "1234567" donde 1=lunes, 7=domingo (ej: "135" = lun/mie/vie)
        dosis_unidades: Cantidad de unidades a dispensar (default: 1)

    Returns:
        int: ID del horario creado, None si falla
    """
    try:
        # Validar formato de hora
        time.fromisoformat(hora_programada)  # Lanza ValueError si formato inválido

        # Validar dias_semana
        if not all(c in '1234567' for c in dias_semana) or len(dias_semana) == 0:
            logger.error(f'dias_semana inválido: {dias_semana}. Debe ser string de dígitos 1-7')
            return None

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO horarios_medicacion 
                   (id_paciente, id_medicamento, hora_programada, dias_semana, dosis_unidades) 
                   VALUES (?, ?, ?, ?, ?)''',
                (id_paciente, id_medicamento, hora_programada, dias_semana, dosis_unidades)
            )
            conn.commit()
            horario_id = cursor.lastrowid
            logger.info(f'Horario creado: medicamento {id_medicamento} a las {hora_programada} (ID: {horario_id})')
            return horario_id

    except ValueError as e:
        logger.error(f'Formato de hora inválido: {hora_programada}. Use "HH:MM"')
        return None
    except Exception as e:
        logger.error(f'Error creando horario: {e}')
        return None


def obtener_horarios_activos_paciente(id_paciente: int) -> List[Dict[str, Any]]:
    """
    Obtiene todos los horarios activos de un paciente.

    Args:
        id_paciente: ID del paciente

    Returns:
        list: Lista de diccionarios con datos de horarios
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT h.*, m.nombre as nombre_medicamento, m.unidad
                   FROM horarios_medicacion h
                   JOIN medicamentos m ON h.id_medicamento = m.id
                   WHERE h.id_paciente = ? AND h.activo = 1
                   ORDER BY h.hora_programada''',
                (id_paciente,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f'Error obteniendo horarios del paciente {id_paciente}: {e}')
        return []


def desactivar_horario_medicacion(id_horario: int) -> bool:
    """
    Desactiva un horario de medicación (soft delete).

    Args:
        id_horario: ID del horario a desactivar

    Returns:
        bool: True si se desactivó correctamente, False en caso contrario
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE horarios_medicacion SET activo = 0 WHERE id = ?', (id_horario,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f'Horario {id_horario} desactivado')
                return True
            else:
                logger.warning(f'Horario {id_horario} no encontrado')
                return False

    except Exception as e:
        logger.error(f'Error desactivando horario {id_horario}: {e}')
        return False


# ── SIGNOS VITALES ──

def registrar_signos_vitales(
    id_paciente: int,
    bpm: int,
    spo2: int,
    temperatura: float,
    notas: Optional[str] = None
) -> Optional[int]:
    """
    Registra una medición de signos vitales.

    Args:
        id_paciente: ID del paciente
        bpm: Frecuencia cardíaca (latidos por minuto)
        spo2: Saturación de oxígeno (%)
        temperatura: Temperatura corporal (°C)
        notas: Notas adicionales sobre la medición (opcional)

    Returns:
        int: ID del registro creado, None si falla
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO signos_vitales 
                   (id_paciente, bpm, spo2, temperatura, medido_en, notas) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (id_paciente, bpm, spo2, temperatura, datetime.now().isoformat(), notas)
            )
            conn.commit()
            registro_id = cursor.lastrowid
            logger.info(f'Signos vitales registrados: BPM={bpm}, SpO2={spo2}%, T={temperatura}°C (ID: {registro_id})')
            return registro_id

    except Exception as e:
        logger.error(f'Error registrando signos vitales: {e}')
        return None


def obtener_ultimas_mediciones(id_paciente: int, n: int = 5) -> List[Dict[str, Any]]:
    """
    Obtiene las últimas N mediciones de signos vitales de un paciente.

    Args:
        id_paciente: ID del paciente
        n: Número de mediciones a recuperar (default: 5)

    Returns:
        list: Lista de diccionarios con las mediciones (más reciente primero)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM signos_vitales 
                   WHERE id_paciente = ? 
                   ORDER BY medido_en DESC 
                   LIMIT ?''',
                (id_paciente, n)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f'Error obteniendo mediciones del paciente {id_paciente}: {e}')
        return []


# ── REGISTROS DE DISPENSACIÓN ──

def crear_registro_dispensacion(
    id_paciente: int,
    id_medicamento: int,
    id_horario: int,
    estado: str = 'pendiente',
    notas: Optional[str] = None
) -> Optional[int]:
    """
    Crea un registro de dispensación de medicamento.

    Args:
        id_paciente: ID del paciente
        id_medicamento: ID del medicamento
        id_horario: ID del horario de medicación
        estado: Estado de la dispensación ('exitoso', 'fallido', 'omitido', 'pendiente')
        notas: Notas adicionales (opcional)

    Returns:
        int: ID del registro creado, None si falla
    """
    try:
        estados_validos = ['exitoso', 'fallido', 'omitido', 'pendiente']
        if estado not in estados_validos:
            logger.error(f'Estado inválido: {estado}. Debe ser uno de {estados_validos}')
            return None

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO registros_dispensacion 
                   (id_paciente, id_medicamento, id_horario, dispensado_en, estado, notas) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (id_paciente, id_medicamento, id_horario, datetime.now().isoformat(), estado, notas)
            )
            conn.commit()
            registro_id = cursor.lastrowid
            logger.info(f'Registro dispensación creado: medicamento {id_medicamento}, estado={estado} (ID: {registro_id})')
            return registro_id

    except Exception as e:
        logger.error(f'Error creando registro de dispensación: {e}')
        return None


def actualizar_estado_dispensacion(id_registro: int, nuevo_estado: str, notas: Optional[str] = None) -> bool:
    """
    Actualiza el estado de un registro de dispensación.

    Args:
        id_registro: ID del registro a actualizar
        nuevo_estado: Nuevo estado ('exitoso', 'fallido', 'omitido', 'pendiente')
        notas: Notas adicionales (opcional)

    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        estados_validos = ['exitoso', 'fallido', 'omitido', 'pendiente']
        if nuevo_estado not in estados_validos:
            logger.error(f'Estado inválido: {nuevo_estado}. Debe ser uno de {estados_validos}')
            return False

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if notas:
                cursor.execute(
                    'UPDATE registros_dispensacion SET estado = ?, notas = ? WHERE id = ?',
                    (nuevo_estado, notas, id_registro)
                )
            else:
                cursor.execute(
                    'UPDATE registros_dispensacion SET estado = ? WHERE id = ?',
                    (nuevo_estado, id_registro)
                )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f'Registro dispensación {id_registro} actualizado a estado={nuevo_estado}')
                return True
            else:
                logger.warning(f'Registro dispensación {id_registro} no encontrado')
                return False

    except Exception as e:
        logger.error(f'Error actualizando registro dispensación {id_registro}: {e}')
        return False


def obtener_historial_dispensacion(id_paciente: int, limite: int = 50) -> List[Dict[str, Any]]:
    """
    Obtiene el historial de dispensaciones de un paciente.

    Args:
        id_paciente: ID del paciente
        limite: Número máximo de registros a recuperar (default: 50)

    Returns:
        list: Lista de diccionarios con los registros (más reciente primero)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT r.*, m.nombre as nombre_medicamento, h.hora_programada
                   FROM registros_dispensacion r
                   JOIN medicamentos m ON r.id_medicamento = m.id
                   JOIN horarios_medicacion h ON r.id_horario = h.id
                   WHERE r.id_paciente = ?
                   ORDER BY r.dispensado_en DESC
                   LIMIT ?''',
                (id_paciente, limite)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f'Error obteniendo historial de dispensación del paciente {id_paciente}: {e}')
        return []


# ── CAPA 3 — QUERIES COMPUESTAS ──

def _calcular_tiempo_relativo(hora_programada_str: str) -> tuple[int, str]:
    """
    Calcula tiempo relativo hasta una hora programada.

    Args:
        hora_programada_str: Hora en formato "HH:MM"

    Returns:
        tuple: (minutos_restantes, texto_legible)
               ej: (150, "2 horas y 30 minutos")
    """
    ahora = datetime.now()
    hora_prog = time.fromisoformat(hora_programada_str)

    # Crear datetime para hoy con la hora programada
    dosis_datetime = datetime.combine(ahora.date(), hora_prog)

    # Si la hora ya pasó hoy, es para mañana
    if dosis_datetime < ahora:
        dosis_datetime += timedelta(days=1)

    delta = dosis_datetime - ahora
    minutos_totales = int(delta.total_seconds() / 60)

    # Formatear texto legible
    if minutos_totales < 60:
        if minutos_totales <= 1:
            texto = "1 minuto"
        else:
            texto = f"{minutos_totales} minutos"
    else:
        horas = minutos_totales // 60
        minutos = minutos_totales % 60

        if horas == 1:
            texto_horas = "1 hora"
        else:
            texto_horas = f"{horas} horas"

        if minutos == 0:
            texto = texto_horas
        elif minutos == 1:
            texto = f"{texto_horas} y 1 minuto"
        else:
            texto = f"{texto_horas} y {minutos} minutos"

    return minutos_totales, texto


def get_horarios_hoy(id_paciente: int) -> List[Dict[str, Any]]:
    """
    Obtiene todos los horarios activos del paciente para el día actual.

    Args:
        id_paciente: ID del paciente

    Returns:
        list: Lista de diccionarios con horarios del día, incluyendo:
              - id, hora_programada, dosis_unidades
              - nombre_medicamento, unidad
              - id_medicamento, id_compartimento
    """
    try:
        # Obtener día de la semana actual (1=lunes, 7=domingo)
        dia_actual = str(datetime.now().isoweekday())

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT h.id, h.hora_programada, h.dosis_unidades, h.id_medicamento,
                          m.nombre as nombre_medicamento, m.unidad, m.id_compartimento
                   FROM horarios_medicacion h
                   JOIN medicamentos m ON h.id_medicamento = m.id
                   WHERE h.id_paciente = ? 
                     AND h.activo = 1 
                     AND m.activo = 1
                     AND h.dias_semana LIKE ?
                   ORDER BY h.hora_programada''',
                (id_paciente, f'%{dia_actual}%')
            )
            rows = cursor.fetchall()
            horarios = [dict(row) for row in rows]

            logger.debug(f'Horarios hoy para paciente {id_paciente}: {len(horarios)} encontrados')
            return horarios

    except Exception as e:
        logger.error(f'Error obteniendo horarios de hoy para paciente {id_paciente}: {e}')
        return []


def get_proxima_dosis(id_paciente: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene el siguiente horario pendiente del día para un paciente.
    Incluye tiempo relativo calculado.

    Args:
        id_paciente: ID del paciente

    Returns:
        dict: Datos del próximo horario con campos adicionales:
              - tiempo_restante_minutos: int (minutos hasta la dosis)
              - tiempo_restante_texto: str (ej: "2 horas y 30 minutos")
              None si no hay más horarios hoy
    """
    try:
        horarios_hoy = get_horarios_hoy(id_paciente)
        hora_actual = datetime.now().time()

        for horario in horarios_hoy:
            hora_programada = time.fromisoformat(horario['hora_programada'])
            if hora_programada >= hora_actual:
                # Calcular tiempo relativo
                minutos, texto = _calcular_tiempo_relativo(horario['hora_programada'])
                horario['tiempo_restante_minutos'] = minutos
                horario['tiempo_restante_texto'] = texto

                logger.debug(f'Proxima dosis para paciente {id_paciente}: {horario["nombre_medicamento"]} en {texto}')
                return horario

        logger.debug(f'No hay mas dosis pendientes hoy para paciente {id_paciente}')
        return None

    except Exception as e:
        logger.error(f'Error obteniendo próxima dosis para paciente {id_paciente}: {e}')
        return None


def _calcular_tiempo_transcurrido(timestamp_iso: str) -> tuple[int, str]:
    """
    Calcula tiempo transcurrido desde un timestamp.

    Args:
        timestamp_iso: Timestamp en formato ISO 8601

    Returns:
        tuple: (minutos_transcurridos, texto_legible)
               ej: (45, "hace 45 minutos")
    """
    ahora = datetime.now()
    medicion_datetime = datetime.fromisoformat(timestamp_iso)

    delta = ahora - medicion_datetime
    minutos_totales = int(delta.total_seconds() / 60)

    # Formatear texto legible
    if minutos_totales < 1:
        texto = "hace menos de 1 minuto"
    elif minutos_totales == 1:
        texto = "hace 1 minuto"
    elif minutos_totales < 60:
        texto = f"hace {minutos_totales} minutos"
    elif minutos_totales < 120:
        texto = "hace 1 hora"
    elif minutos_totales < 1440:  # menos de 24 horas
        horas = minutos_totales // 60
        texto = f"hace {horas} horas"
    else:  # días
        dias = minutos_totales // 1440
        if dias == 1:
            texto = "hace 1 día"
        else:
            texto = f"hace {dias} días"

    return minutos_totales, texto


def get_ultimos_signos_vitales(id_paciente: int, n: int = 5) -> List[Dict[str, Any]]:
    """
    Obtiene las últimas N mediciones de signos vitales de un paciente.
    Alias de obtener_ultimas_mediciones() para consistencia de nomenclatura.

    Args:
        id_paciente: ID del paciente
        n: Número de mediciones a recuperar (default: 5)

    Returns:
        list: Lista de diccionarios con las mediciones (más reciente primero)
    """
    return obtener_ultimas_mediciones(id_paciente, n)


def get_resumen_paciente(id_paciente: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un resumen completo del paciente para contextualizar respuestas de Atlas.

    Args:
        id_paciente: ID del paciente

    Returns:
        dict: Resumen con:
              - nombre: nombre del paciente
              - medicamentos_activos: lista de medicamentos con horarios
              - ultima_medicion: última medición de signos vitales
              - proxima_dosis: próximo medicamento a tomar hoy (si existe)
              None si el paciente no existe
    """
    try:
        paciente = obtener_paciente(id_paciente)
        if not paciente:
            return None

        medicamentos = obtener_horarios_activos_paciente(id_paciente)
        ultimas_mediciones = get_ultimos_signos_vitales(id_paciente, n=1)
        ultima_medicion = ultimas_mediciones[0] if ultimas_mediciones else None

        # Agregar tiempo transcurrido a la última medición
        if ultima_medicion and 'medido_en' in ultima_medicion:
            minutos, texto = _calcular_tiempo_transcurrido(ultima_medicion['medido_en'])
            ultima_medicion['tiempo_transcurrido_minutos'] = minutos
            ultima_medicion['tiempo_transcurrido_texto'] = texto

        proxima_dosis = get_proxima_dosis(id_paciente)

        resumen = {
            'nombre': paciente['nombre'],
            'medicamentos_activos': medicamentos,
            'ultima_medicion': ultima_medicion,
            'proxima_dosis': proxima_dosis
        }

        logger.debug(f'Resumen generado para {paciente["nombre"]} (ID: {id_paciente})')
        return resumen

    except Exception as e:
        logger.error(f'Error generando resumen para paciente {id_paciente}: {e}')
        return None


def verificar_dosis_dispensada_hoy(id_paciente: int, id_horario: int) -> bool:
    """
    Verifica si ya se dispensó el medicamento para un horario específico hoy.
    Útil para evitar dispensaciones duplicadas si el robot reinicia.

    Args:
        id_paciente: ID del paciente
        id_horario: ID del horario de medicación

    Returns:
        bool: True si ya se dispensó hoy, False en caso contrario
    """
    try:
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT COUNT(*) FROM registros_dispensacion
                   WHERE id_paciente = ? 
                     AND id_horario = ?
                     AND dispensado_en >= ?
                     AND estado IN ('exitoso', 'pendiente')''',
                (id_paciente, id_horario, hoy_inicio)
            )
            count = cursor.fetchone()[0]

            dispensada = count > 0
            logger.debug(f'Dosis horario {id_horario} ya dispensada hoy: {dispensada}')
            return dispensada

    except Exception as e:
        logger.error(f'Error verificando dosis dispensada (paciente {id_paciente}, horario {id_horario}): {e}')
        return False


# ── BLOQUE DE PRUEBA ──

if __name__ == '__main__':
    print('═' * 80)
    print('PRUEBA RÁPIDA DE medical_db.py')
    print('═' * 80)

    # Inicializar base de datos
    print('\n1. Inicializando base de datos...')
    if init_db():
        print('   ✓ Base de datos inicializada correctamente')
    else:
        print('   ✗ Error inicializando base de datos')
        exit(1)

    # Crear paciente
    print('\n2. Creando paciente...')
    id_paciente = crear_paciente(
        nombre='Juan Pérez',
        notas='Paciente con hipertensión controlada'
    )
    if id_paciente:
        print(f'   ✓ Paciente creado con ID: {id_paciente}')
    else:
        print('   ✗ Error creando paciente')
        exit(1)

    # Crear medicamento
    print('\n3. Creando medicamento...')
    id_medicamento = crear_medicamento(
        nombre='Losartán',
        unidad='tabletas',
        id_compartimento=1,
        descripcion='Antihipertensivo',
        stock=30
    )
    if id_medicamento:
        print(f'   ✓ Medicamento creado con ID: {id_medicamento}')
    else:
        print('   ✗ Error creando medicamento')
        exit(1)

    # Crear horario de medicación
    print('\n4. Creando horario de medicación...')
    id_horario = crear_horario_medicacion(
        id_paciente=id_paciente,
        id_medicamento=id_medicamento,
        hora_programada='08:00',
        dias_semana='1234567',  # Todos los días
        dosis_unidades=1
    )
    if id_horario:
        print(f'   ✓ Horario creado con ID: {id_horario}')
    else:
        print('   ✗ Error creando horario')
        exit(1)

    # Registrar signos vitales
    print('\n5. Registrando signos vitales...')
    id_medicion = registrar_signos_vitales(
        id_paciente=id_paciente,
        bpm=72,
        spo2=98,
        temperatura=36.5,
        notas='Medición matutina'
    )
    if id_medicion:
        print(f'   ✓ Signos vitales registrados con ID: {id_medicion}')
    else:
        print('   ✗ Error registrando signos vitales')
        exit(1)

    # Crear registro de dispensación
    print('\n6. Creando registro de dispensación...')
    id_dispensacion = crear_registro_dispensacion(
        id_paciente=id_paciente,
        id_medicamento=id_medicamento,
        id_horario=id_horario,
        estado='exitoso',
        notas='Dispensación sin incidentes'
    )
    if id_dispensacion:
        print(f'   ✓ Registro de dispensación creado con ID: {id_dispensacion}')
    else:
        print('   ✗ Error creando registro de dispensación')
        exit(1)

    # Probar queries compuestas
    print('\n' + '─' * 80)
    print('PROBANDO QUERIES COMPUESTAS (Capa 3)')
    print('─' * 80)

    print('\n7. get_horarios_hoy()')
    horarios = get_horarios_hoy(id_paciente)
    print(f'   → {len(horarios)} horarios encontrados para hoy')
    for h in horarios:
        print(f'      • {h["nombre_medicamento"]}: {h["hora_programada"]} ({h["dosis_unidades"]} {h["unidad"]})')

    print('\n8. get_proxima_dosis()')
    proxima = get_proxima_dosis(id_paciente)
    if proxima:
        print(f'   → Próxima dosis: {proxima["nombre_medicamento"]} a las {proxima["hora_programada"]}')
    else:
        print('   → No hay más dosis pendientes hoy')

    print('\n9. get_ultimos_signos_vitales()')
    mediciones = get_ultimos_signos_vitales(id_paciente, n=5)
    print(f'   → {len(mediciones)} mediciones encontradas')
    for m in mediciones:
        print(f'      • BPM: {m["bpm"]}, SpO2: {m["spo2"]}%, T: {m["temperatura"]}°C ({m["medido_en"][:19]})')

    print('\n10. get_resumen_paciente()')
    resumen = get_resumen_paciente(id_paciente)
    if resumen:
        print(f'   → Paciente: {resumen["nombre"]}')
        print(f'   → Medicamentos activos: {len(resumen["medicamentos_activos"])}')
        if resumen['ultima_medicion']:
            ult = resumen['ultima_medicion']
            print(f'   → Última medición: BPM={ult["bpm"]}, SpO2={ult["spo2"]}%, T={ult["temperatura"]}°C')
        if resumen['proxima_dosis']:
            print(f'   → Próxima dosis: {resumen["proxima_dosis"]["nombre_medicamento"]} a las {resumen["proxima_dosis"]["hora_programada"]}')

    print('\n11. verificar_dosis_dispensada_hoy()')
    dispensada = verificar_dosis_dispensada_hoy(id_paciente, id_horario)
    print(f'   → ¿Dosis ya dispensada hoy? {dispensada}')

    print('\n' + '═' * 80)
    print('TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE ✓')
    print('═' * 80)
    print(f'\nBase de datos creada en: {DB_PATH}')
    print('Puedes inspeccionar el archivo con cualquier cliente SQLite.')
