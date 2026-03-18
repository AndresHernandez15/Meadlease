# Módulo de Visión Artificial - Robot Asistente Médico

Sistema de visión artificial para Meadlese.

## Características

- **Detección Humana** (`Identificacion_Corporal_Lejos.py`) - Identificador de personas usando MediaPipe
- **Reconocimiento Facial** (`Reconocimiento.py`) - Identifica al usuario mediante algoritmo LBPH
- **Registro de Usuario** (`captura_rostros_compatible.py`) - Captura y entrena modelo facial

## Instalación
```bash
pip install -r requirements.txt
```

## Uso

### 1. Registrar nuevo usuario
```bash
python captura_rostros_compatible.py
```

### 2. Reconocimiento facial
```bash
python Reconocimiento.py
```

### 3. Detección humana
```bash
python Identificacion_Corporal_Lejos.py
```

## Librerias

- Python 3.10
- OpenCV 4.8+
- MediaPipe 0.10.9
- NumPy

