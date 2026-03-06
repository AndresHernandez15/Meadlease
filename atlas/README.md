# Atlas — Sistema Conversacional

> **Plataforma actual:** Windows 11 · Python 3.10  
> **Plataforma destino:** Ubuntu 22.04 + ROS2 Humble  
> **Responsable:** Andrés

## Variables de entorno requeridas

Crear un archivo `.env` en esta carpeta (está en `.gitignore`, nunca se sube al repo):

```env
GROQ_API_KEY=gsk_...
GROQ_API_KEY_BACKUP=gsk_...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
PORCUPINE_ACCESS_KEY=...
```

## Instalación

```bash
pip install -r requirements.txt
```

## Arrancar el sistema

```bash
python main.py
# Di "Atlas" para activar
```

## Pruebas individuales

```bash
python -m test.test_quick_system
python -m test.test_integration_full
python -m test.test_tts_interactive
python -m test.test_context_prompt
```

## Poblar base de datos de prueba

```bash
python ../database/scripts/populate_test_db.py
```

## Estructura

```
atlas/
├── main.py               # Orquestador principal
├── config/
│   ├── settings.py       # Configuración general
│   └── llm_config.py     # System prompt + contexto paciente
├── audio/                # Captura, VAD, filtro ruido, reproducción
├── local/                # Wake word (Porcupine) + comandos (Vosk)
├── cloud/                # STT (Groq Whisper) + LLM + TTS (Azure)
├── logic/                # FSM + medical_db
├── utils/                # Logger + bus de eventos
├── test/                 # Suite de pruebas y benchmarks
├── models/               # Modelos Vosk (no versionados — pesados)
└── data/
    └── audio/            # Audio de confirmación "¿Sí?" de Camila
```

Ver [DOCUMENTACION_CONVERSACIONAL.md](../docs/DOCUMENTACION_CONVERSACIONAL.md) para referencia completa.
