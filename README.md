# 🤖 Meadlease — Robot Asistente Inteligente para el Cuidado de la Salud en el Hogar

> **Universidad Tecnológica de Bolívar** · Ingeniería Mecatrónica · Proyecto de Grado 2026

Meadlease es un robot asistente domiciliario, diseñado para apoyar el cuidado autónomo de personas en casa. Integra navegación autónoma, dispensación de medicamentos, monitoreo de signos vitales e interacción conversacional en español.

---

## 👥 Equipo

| Integrante | Rol |
|------------|-----|
| **Andrés** | Líder software — ROS2, navegación, sistema conversacional |
| **Linda** | Diseño mecánico, sensores biomédicos |
| **Sergio** | Mecánica, pruebas de motores y dispensador |
| **Juan** | Visión artificial, firmware microcontroladores |

---

## 🗂️ Estructura del Repositorio

```
Meadlease/
├── docs/                        # Documentación técnica
│   ├── DOCUMENTACION_ROS2.md
│   ├── DOCUMENTACION_CONVERSACIONAL.md
│   └── PROYECTO_GENERAL.md
├── ros2_ws/                     # Workspace ROS2 (Ubuntu — Andrés)
│   └── src/
│       └── robot_medical/       # Paquete principal ROS2
├── atlas/                       # Sistema conversacional (Windows — Andrés)
├── vision/                      # Visión artificial (Juan)
├── database/                    # Base de datos SQLite + scripts
└── .github/                     # Plantillas de issues y PRs
```

---

## 🚀 Módulos Principales

| Módulo | Estado | Responsable |
|--------|--------|-------------|
| Navegación autónoma (ROS2 + Nav2) | ⏳ En progreso | Andrés |
| Sistema conversacional Atlas | ✅ Validado en Windows | Andrés |
| Visión artificial (detección + reconocimiento) | ❌ Pendiente | Juan |
| Dispensador de medicamentos | ⏳ Diseño en curso | Linda / Sergio |
| Monitoreo de signos vitales | ⏳ Pendiente calibración | Linda |
| HMI / Interfaz de usuario | ❌ Pendiente | Andrés |

---

## ⚙️ Stack Tecnológico

- **Framework:** ROS2 Humble Hawksbill (Ubuntu 22.04)
- **SLAM:** RTAB-Map con Kinect V2
- **Navegación:** Nav2
- **Conversacional:** Porcupine + Vosk + Groq Whisper + Groq LLM + Azure TTS
- **MCUs:** ESP32 S3 (×2), STM32F411 Blackpill
- **Base de datos:** SQLite

---

## 📦 Requisitos por Módulo

Ver instrucciones detalladas de instalación en cada subcarpeta:

- [`ros2_ws/`](ros2_ws/) → ROS2 Humble en Ubuntu 22.04
- [`atlas/`](atlas/) → Python 3.10 en Windows/Ubuntu + variables de entorno
- [`vision/`](vision/) → Por definir (Juan)

---

## 📄 Documentación

Toda la documentación técnica está en [`docs/`](docs/):

- [Proyecto General](docs/PROYECTO_GENERAL.md)
- [Documentación ROS2](docs/DOCUMENTACION_ROS2.md)
- [Sistema Conversacional Atlas](docs/DOCUMENTACION_CONVERSACIONAL.md)

---

## 📅 Deadline

- **Robot funcional:** 1 de mayo de 2026
- **Entrega académica:** Finales de mayo de 2026
