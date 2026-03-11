"""
Configuración del modelo LLM (Large Language Model).

Este archivo contiene exclusivamente configuración del LLM:
- API keys de Groq
- Modelos y fallbacks
- Parámetros de generación
- System prompt y contexto del paciente

Para otras configuraciones: ver baymax_voice/config/settings.py
"""
import os

# ────────────────────────────────────────────────────────────────────────────
# API Keys
# ────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_API_KEY_BACKUP = os.getenv('GROQ_API_KEY_BACKUP', '')

# ────────────────────────────────────────────────────────────────────────────
# Modelos
# ────────────────────────────────────────────────────────────────────────────

GROQ_MODEL = 'llama-3.3-70b-versatile'

# Fallbacks ordenados por calidad/velocidad (benchmark 2026-03-02)
# Ranking: llama-3.1-8b (436ms), llama-4-scout (570ms), kimi-k2 (979ms)
GROQ_FALLBACK_MODELS = [
    'llama-3.1-8b-instant',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'moonshotai/kimi-k2-instruct',
]

# ────────────────────────────────────────────────────────────────────────────
# Parámetros de Generación
# ────────────────────────────────────────────────────────────────────────────

MAX_TOKENS = 70                      # Optimizado: 100 → 70 (ahorro ~30%)
TEMPERATURE = 0.7                    # 0.0 = determinista, 1.0 = creativo
CONVERSATION_MEMORY_TURNS = 4       # Turnos a recordar (~280 tokens)

# ────────────────────────────────────────────────────────────────────────────
# System Prompt
# ────────────────────────────────────────────────────────────────────────────

# IMPORTANTE: Núcleo ético del sistema.
# Mantener restricciones médicas y límite de 40 palabras.
# Evitar información no solicitada.

SYSTEM_PROMPT = """Eres Atlas, un asistente médico robótico personal empático y profesional.

REGLAS DE COMUNICACIÓN:
- Respuestas MUY cortas: máximo 40 palabras
- Usa "tú" para cercanía con el paciente
- Responde SOLO lo que el usuario pregunta, NO des información extra no solicitada
- NO menciones dosis, horarios o signos vitales a menos que te lo pidan explícitamente
- Solo REPORTA datos médicos, NUNCA interpretes ni diagnostiques
- Si detectas valores anormales: informa + recomienda consultar médico
- Ante dudas médicas: deriva siempre a profesional de salud
- Si no tienes acceso a un dato médico, NO lo inventes

PROHIBIDO:
- Diagnosticar o analizar síntomas
- Recomendar medicamentos o tratamientos
- Dar recordatorios de medicación no solicitados
- Frases como "Es probable que...", "Parece que...", "Podría ser..."

CONTEXTO:
Tienes acceso a datos del paciente (nombre, próxima dosis, signos vitales).
Úsalos SOLO cuando el usuario pregunte por ellos directamente.

Sé empático, claro, conciso y honesto sobre tus limitaciones."""

# ────────────────────────────────────────────────────────────────────────────
# Contexto del Paciente
# ────────────────────────────────────────────────────────────────────────────

def build_patient_context(patient_id: int = None) -> str:
    """
    Construye contexto del paciente para el LLM con tiempos relativos.

    Consulta medical_db y formatea información relevante:
    - Nombre del paciente
    - Hora actual
    - Próxima dosis con tiempo restante calculado
    - Últimos signos vitales con tiempo transcurrido

    Args:
        patient_id: ID del paciente (None = sin contexto)

    Returns:
        str: Contexto formateado o "" si no hay paciente/error

    Ejemplo:
        "Paciente: Juan Pérez
         Hora actual: 09:30
         Próxima dosis: Metformina en 2 horas y 30 minutos (12:00, 2 tabletas)
         Últimos signos vitales: 78 BPM, 98% SpO2, 36.5°C (hace 1 hora)"

    Nota:
        - Import lazy para evitar dependencia circular
        - Retorna "" silenciosamente si hay error
        - Tiempos relativos calculados en medical_db
    """
    if patient_id is None:
        return ""

    try:
        from datetime import datetime
        from baymax_voice.logic import medical_db

        resumen = medical_db.get_resumen_paciente(patient_id)
        if not resumen:
            return ""

        context_parts = []

        # Nombre
        context_parts.append(f"Paciente: {resumen['nombre']}")

        # Hora actual
        ahora = datetime.now()
        context_parts.append(f"Hora actual: {ahora.strftime('%H:%M')}")

        # Próxima dosis con tiempo relativo
        if resumen.get('proxima_dosis'):
            prox = resumen['proxima_dosis']
            tiempo_texto = prox.get('tiempo_restante_texto', '')
            context_parts.append(
                f"Proxima dosis: {prox['nombre_medicamento']} en {tiempo_texto} "
                f"({prox['hora_programada']}, {prox['dosis_unidades']} {prox['unidad']})"
            )

        # Últimos signos vitales con tiempo transcurrido
        if resumen.get('ultima_medicion'):
            ult = resumen['ultima_medicion']
            tiempo_texto = ult.get('tiempo_transcurrido_texto', '')
            context_parts.append(
                f"Ultimos signos vitales: {ult['bpm']} BPM, {ult['spo2']}% SpO2, "
                f"{ult['temperatura']}°C ({tiempo_texto})"
            )

        return "\n".join(context_parts)

    except Exception:
        # Si falla, el LLM funciona sin contexto
        return ""

