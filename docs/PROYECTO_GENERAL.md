# ROBOT ASISTENTE MÉDICO DOMICILIARIO — MEADLESE
## Documentación Técnica General del Proyecto

> **Universidad Tecnológica de Bolívar** · Ingeniería Mecatrónica · Proyecto de Grado  
> **Última actualización:** 2026-03-17  
> **Deadline robot funcional:** 1 de mayo de 2026  
> **Entrega académica final:** Finales de mayo de 2026

---

## ÍNDICE

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Equipo](#2-equipo)
3. [Objetivos](#3-objetivos)
4. [Requerimientos del Sistema](#4-requerimientos-del-sistema)
5. [Arquitectura General](#5-arquitectura-general)
6. [Hardware del Sistema](#6-hardware-del-sistema)
7. [Módulos de Software](#7-módulos-de-software)
8. [Diseño Físico del Robot](#8-diseño-físico-del-robot)
9. [Estado Actual del Proyecto](#9-estado-actual-del-proyecto)
10. [Roadmap](#10-roadmap)
11. [Restricciones y Limitaciones](#11-restricciones-y-limitaciones)
12. [Consideraciones Éticas](#12-consideraciones-éticas)

---

## 1. DESCRIPCIÓN DEL PROYECTO

Meadlese es un robot asistente médico inteligente para uso domiciliario, diseñado para apoyar a personas con enfermedades crónicas (especialmente adultos mayores) en el seguimiento de sus tratamientos. Aborda el problema de que el ~60% de estos pacientes no adhieren correctamente a su medicación (OMS), lo que causa el 50% de los fracasos terapéuticos.

**Funciones principales del robot:**
1. Navegar autónomamente por el hogar para localizar al usuario
2. Dispensar medicamentos sólidos según horarios programados
3. Medir y registrar signos vitales (BPM, SpO₂, temperatura)
4. Interactuar con el usuario mediante conversación natural en español
5. Notificar a contactos de emergencia ante valores anómalos

**Nombre del sistema conversacional:** Atlas (wake word: "Atlas")  
**Plataforma de software:** ROS2 Humble sobre Ubuntu 22.04  
**Repositorio del proyecto:** `Meadlease` (GitHub) · Módulo conversacional en `atlas/`

---

## 2. EQUIPO

| Integrante | Perfil | Responsabilidades |
|------------|--------|-------------------|
| **Andrés** (líder) | Ing. Mecatrónico + Ing. Sistemas | Software, ROS2, sistema conversacional, Kinect, micro-ROS, impresión 3D |
| **Linda** | Ing. Biomédica + Mecatrónica | Diseño mecánico del robot y dispensador, calibración de sensores biomédicos |
| **Sergio** | Ing. Mecatrónico | Mecánica, pruebas de motores y dispensador |
| **Juan** | Ing. Mecatrónico | Visión artificial, firmware de microcontroladores (ESP32) |

---

## 3. OBJETIVOS

### Objetivo General
Desarrollar un robot asistente médico inteligente para monitoreo de signos vitales básicos y dispensación de medicamentos en entornos domésticos.

### Objetivos Específicos
1. Diseñar la arquitectura modular del sistema (hardware + software)
2. Seleccionar e integrar los componentes electrónicos, mecánicos y de comunicación
3. Implementar los sistemas de medición de signos vitales, dispensación, reconocimiento facial y navegación autónoma
4. Integrar la interfaz humano-máquina (HMI) para interacción por voz y pantalla
5. Validar el funcionamiento integral mediante pruebas en entorno controlado

### Entregables Académicos
- Prototipo físico completamente operativo con todos los módulos integrados
- Software de control (ROS2 + firmwares)
- Interfaz de usuario (HMI: pantalla + voz)
- Documentación técnica y académica

---

## 4. REQUERIMIENTOS DEL SISTEMA

### Funcionales
| ID | Requerimiento |
|----|--------------|
| RF-01 | Medir temperatura, BPM y SpO₂ con sensores biomédicos |
| RF-02 | Movilidad autónoma en interiores con detección y evasión de obstáculos |
| RF-03 | Dispensar medicamentos sólidos en horarios programados |
| RF-04 | Interacción conversacional en lenguaje natural (español) |
| RF-05 | Reconocimiento facial del usuario (mínimo 2 usuarios registrados) |
| RF-06 | Notificación automática a contactos de emergencia vía Wi-Fi |
| RF-07 | Registro y trazabilidad de mediciones y dispensaciones en BD local |
| RF-08 | Indicadores visuales y auditivos de estado del sistema |
| RF-09 | Control de acceso: el sistema no entrega medicación a no registrados |

### No Funcionales / Restricciones de Diseño
- Solo medicamentos sólidos (tabletas/cápsulas); máx. 6 tipos × ~14 unidades
- Operación exclusiva en interiores, una sola planta
- Velocidad máxima: 0.25 m/s
- Dispensador bloqueado mientras el robot está en movimiento
- La IA no emite diagnósticos ni prescripciones
- Datos de salud almacenados solo localmente (nunca en la nube)
- Requiere Wi-Fi para el sistema conversacional avanzado (con fallback offline)

---

## 5. ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────────────┐
│                     PC PRINCIPAL (ROS2)                     │
│              Dell Inspiron · Ubuntu 22.04 · i3-3227U        │
│                                                             │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │  Nav2 + SLAM │  │ Sistema Atlas  │  │ Visión Artificial│ │
│  │  (RTAB-Map)  │  │ (Conversacional│  │ (Reconoc. facial)│ │
│  └──────┬───────┘  └───────┬────────┘  └─────────┬────────┘ │
│         │                  │                     │          │
│  ┌──────▼──────────────────▼─────────────────────▼────────┐ │
│  │                  ROS2 Humble (topics / services)       │ │
│  └──────────────────────────┬─────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────┘
                              │ USB-CDC (micro-ROS)
                    ┌─────────▼──────────┐
                    │    STM32F411       │
                    │  (MCU Auxiliar)    │
                    │ Columna vertebral  │
                    │ de comunicaciones  │
                    └────┬──────────┬────┘
                         │ UART1    │ UART2
              ┌──────────▼──┐  ┌───▼──────────────┐
              │  ESP32 S3   │  │    ESP32 S3       │
              │  Movilidad  │  │    Médica         │
              │             │  │                   │
              │ Motores BLDC│  │ Dispensador       │
              │ Encoders    │  │ Signos vitales    │
              │ Ultrasonidos│  │ MAX30102+MAX30205  │
              └─────────────┘  └───────────────────┘
```

**Kinect V2** → USB al PC → ROS2 (kinect2_bridge)  
**Cámara portátil** → USB al PC → módulo visión artificial  
**Wi-Fi** → sistema conversacional cloud (Groq + Azure TTS) y alertas de emergencia

---

## 6. HARDWARE DEL SISTEMA

### Computador Principal

| Componente | Especificación |
|------------|----------------|
| Modelo | Dell Inspiron 3421 |
| CPU | Intel Core i3-3227U |
| RAM | 12 GB |
| SO | Ubuntu 22.04.5 LTS |
| Alimentación | 19.5V via step-down desde batería |

### Sensores y Percepción

| Componente | Función | Estado |
|----------|---------|--------|
| Kinect V2 (USB 3.0, 12V) | Mapeo SLAM 3D + detección de personas | ✅ Probado |
| Cámara portátil | Reconocimiento facial | ✅ Probado |
| JSN-SR04T × 2 (frontal/trasero) | Detección principal de obstáculos | ✅ Conseguidos |
| HC-SR04 × 2-4 (esquinas) | Cobertura lateral de obstáculos | ✅ Conseguidos |
| IR anticaída (posición TBD) | Detección de escalones/desniveles | ⏳ Pendiente selección |
| MAX30102 | BPM + SpO₂ | ⏳ Pendiente calibración |
| Sensor temperatura corporal | Temperatura corporal por contacto | ⏳ Pendiente calibración |

### Actuadores y Movilidad

| Componente | Especificación | Estado |
|------------|----------------|--------|
| Motores BLDC × 2 | 24V, hoverboard, con sensores Hall | ✅ Probados |
| Drivers ZS-X11H × 2 | Control PWM | ✅ Probados |
| Rueda frontal | Equilibrio (no motrices) | ✅ |
| Brazo robótico 2DOF | Dispensación de medicamentos | ⏳ En diseño |
| Bomba de vacío + manguera | Manipulación de pastillas sin daño | ⏳ En diseño |
| Sensor de presión | Confirma captura de pastilla | ⏳ En diseño |

### Microcontroladores

| MCU | Función | Estado |
|-----|---------|--------|
| **STM32F411 Blackpill** | Columna vertebral: micro-ROS (USB-CDC ↔ PC), UART1 ↔ ESP32 Movilidad, UART2 ↔ ESP32 Médica, GPIO botones HMI | ✅ micro-ROS validado |
| **ESP32 S3 — Movilidad** | PWM motores, encoders Hall, sensores obstáculos | ✅ Conectado y probado |
| **ESP32 S3 — Médica** | Control dispensador + sensores signos vitales | ⏳ Pendiente integración |

> STM32F411 elegido sobre ESP32 para MCU auxiliar por: 6 UARTs hardware, DMA por canal, latencia determinista en `/cmd_vel` (decisión tomada 2026-03-04).

### Sistema de Energía

| Componente | Detalle | Estado |
|------------|---------|--------|
| Pack baterías | 7S 4P litio, ~29.4V, ~6000mAh | ✅ Armado |
| Step-down 19.5V | Portátil | ✅ Probado |
| Step-down 12V | Kinect V2 | ✅ |
| Step-down 5V | MCUs y sensores | ✅ |
| Voltaje directo ~24-29V | Motores BLDC vía drivers | ✅ |

---

## 7. MÓDULOS DE SOFTWARE

### 7.1 Movilidad Autónoma

**Stack:** ROS2 Humble + RTAB-Map (SLAM 3D) + Nav2  
**Responsables:** Andrés (software), Sergio (firmware ESP32)

- Kinect V2 genera nube de puntos → RTAB-Map construye mapa 3D del entorno
- Nav2 planifica y ejecuta rutas con el mapa guardado
- Flujo de comando: `Nav2 → /cmd_vel → STM32 (micro-ROS) → UART → ESP32 → PWM → motores`
- Parada automática si ultrasonido frontal detecta obstáculo < 30 cm
- Velocidad máxima: **0.25 m/s**

**Estado:** SLAM funcionando en Ubuntu ✅ | Nav2 en robot físico ❌ (espera armado)

---

### 7.2 Visión Artificial

**Responsable:** Juan

- Detección de personas con Kinect V2 (skeleton tracking)
- Reconocimiento facial con cámara del portátil para verificar identidad
- Mínimo **2 usuarios registrados** (requerimiento académico)
- Usuario no reconocido → el robot no dispensa medicación

**Estado:** Funcionando en Windows ✅ | Port a ROS2 ❌ pendiente

---

### 7.3 Sistema Conversacional — Atlas

**Responsable:** Andrés  
**Documentación completa:** `DOCUMENTACION_CONVERSACIONAL.md`

**Arquitectura híbrida Edge-Cloud:**

| Escenario | Procesamiento | Latencia |
|-----------|--------------|----------|
| Sin internet / comando conocido | Local — Vosk offline | ~500 ms |
| Conversación avanzada | Cloud — Groq Whisper STT + Llama 3.3 70B + Azure TTS | ~1.6-1.9 s |

- **Wake word:** "Atlas" (Porcupine)
- **TTS:** Azure Neural Voice `es-PE-CamilaNeural`
- **Idioma:** Español latino
- **BD local:** SQLite — historial de salud, horarios de medicación, usuarios registrados
- **Principio ético:** Nunca diagnostica ni prescribe; siempre deriva al médico

**Estado:** Pipeline completo en Windows ✅ | Port a ROS2 🔄 (en progreso)

---

### 7.4 Dispensación de Medicamentos

**Responsables:** Linda + Sergio

- Carrusel de compartimentos (6 tipos de medicamento, ~14 unidades/tipo)
- Brazo robótico 2DOF + bomba de vacío para manipulación sin dañar pastillas
- Sensor de presión confirma captura antes de la entrega
- El dispensador se bloquea si el robot está en movimiento
- Cada dispensación se registra en BD local (timestamp + usuario + medicamento)

**Flujo:**
1. Scheduler detecta hora de medicación
2. Robot localiza y verifica identidad del usuario (visión artificial)
3. Brazo selecciona el medicamento del carrusel
4. Vacío agarra la pastilla → sensor confirma → entrega al usuario
5. Registro en BD

**Estado:** Diseño mecánico en progreso ⏳ | Construcción + firmware ❌

---

### 7.5 Monitoreo de Signos Vitales

**Responsables:** Linda (calibración), Juan (firmware ESP32)

- **Sensores:** MAX30102 (BPM + SpO₂) y sensor temperatura corporal (por contacto)
- Medición por comando de voz o por horario programado
- Resultados almacenados en BD local con timestamp
- Alerta automática vía Wi-Fi si valores fuera de rango normal

**Estado:** Sensores conseguidos ✅ | Calibración y firmware ⏳

---

### 7.6 HMI e Interfaz de Usuario

**Responsable:** Andrés
**Documentación completa:** `DOCUMENTACION_HMI.md`

- **Cara expresiva de Baymax:** Pantalla de estado permanente del robot, con animaciones que comunican visualmente qué está haciendo el robot en cada momento.
- **Dashboard médico:** Panel de datos del paciente, accesible por comando de voz o toque del trackpad.
- **Tecnología:** Aplicación web local (FastAPI + HTML/CSS/JS) corriendo en modo kiosko.

**Estado:** ❌ Pendiente (módulo separado)

---

### 7.7 Comunicación PC ↔ Microcontroladores

```
PC (ROS2)  ←── USB-CDC (micro-ROS) ──→  STM32F411
                                              ├── UART1 DMA ──→ ESP32 S3 Movilidad
                                              ├── UART2 DMA ──→ ESP32 S3 Médica
                                              └── GPIO PA0/PA1 ← Botones HMI
```

El STM32 corre como nodo ROS2 nativo vía **micro-ROS**: se suscribe a `/cmd_vel` y publica topics de sensores directamente en el grafo ROS2.

**Estado:** micro-ROS base validado ✅ | Integración con ESP32s ❌ (espera robot armado)

---

## 8. DISEÑO FÍSICO DEL ROBOT

### Dimensiones

| Dimensión | Valor                                                      |
|-----------|------------------------------------------------------------|
| Ancho base | 55 cm                                                      |
| Largo base | 60 cm                                                      |
| Alto total | ~120 cm                                                    |
| Configuración ruedas | 2 motrices traseras BLDC + 1 pequeña frontal |

### Posición de Componentes

| Componente | Altura desde el suelo | Justificación |
|------------|----------------------|---------------|
| Pantalla (HMI) | ~110 cm (parte superior) | A la altura visual del usuario de pie |
| Kinect V2 | ~88 cm | Campo de visión amplio; cubre usuario de pie y sentado |
| Sensores biomédicos | Lateral derecho accesible | Usuario apoya dedo/brazo para lectura |
| Dispensador | ~60 cm | A la altura de la mano de una persona sentada |
| Botón de emergencia | ~20 cm | Accionable con el pie |

### Estructura y Materiales
- **Estructura interna:** 4 varillas roscadas de soporte (distribuidas en el centro de masa)
- **Carcasa:** Impresión 3D en **PETG** (6 kg disponibles)
- **Uniones:** Sistema tipo cola de milano
- **Acabado:** Masilla automotriz + pintura
- **Puertas traseras de mantenimiento** para acceso al interior (recarga de pastillas + revisión electrónica)
- **Estabilidad:** Base triangular (3 puntos de apoyo); CoM diseñado para mantenerse dentro del polígono de soporte

---

## 9. ESTADO ACTUAL DEL PROYECTO

> **Última actualización:** 2026-03-17

| Módulo | Componente | Estado |
|--------|------------|--------|
| **Movilidad** | Control PWM motores + encoders Hall | ✅ Completado |
| **Movilidad** | SLAM Kinect + RTAB-Map en Ubuntu | ✅ Completado |
| **Movilidad** | Nav2 en robot físico | ❌ Pendiente — espera robot armado |
| **Movilidad** | Nodo `/cmd_vel` → STM32 → UART → ESP32 | ⏳ En desarrollo |
| **Visión** | Detección de personas + reconocimiento facial | ✅ Completado (Windows) — port ROS2 pendiente |
| **Conversacional** | Pipeline completo (Vosk + Groq + Azure) | ✅ Completado (Windows) |
| **Conversacional** | FSM + main.py — validación final | ✅ Completado |
| **Conversacional** | Port a ROS2 | ✅ Completado — `atlas_ros2_node` validado 2026-03-17 |
| **Dispensador** | Diseño mecánico | ⏳ En progreso (Linda + Sergio) |
| **Dispensador** | Construcción física + firmware | ❌ Pendiente |
| **Signos Vitales** | Sensores conseguidos | ⏳ Pendiente calibración y firmware |
| **HMI** | Interfaz desktop | ❌ Pendiente (última etapa) |
| **Comunicación** | micro-ROS STM32 base | ✅ Completado |
| **Comunicación** | Integración STM32 ↔ ESP32s | ❌ Pendiente — espera robot armado |
| **Estructura** | Diseño CAD + impresión 3D PETG | ⏳ En progreso |
| **Energía** | Pack 7S4P + step-downs | ✅ Completado |

---

## 10. ROADMAP

### Fase 1 — Integración Mecánica (Marzo 2026)
- [ ] Finalizar diseño CAD → iniciar impresión 3D en PETG
- [ ] Robot físicamente armado (estructura + electrónica montada)
- [ ] Movilidad básica funcional (teleop)
- [ ] TF tree completo en ROS2
- [ ] Mapa del entorno de prueba generado con Kinect + RTAB-Map

### Fase 2 — Navegación, Percepción y Conversacional (Abril — 1ª mitad)
- [ ] Nav2 funcionando en robot físico
- [ ] Port del sistema conversacional Atlas a ROS2
- [ ] Port del módulo de visión artificial a ROS2
- [ ] Reconocimiento facial de 2 usuarios en robot físico

### Fase 3 — Funciones Médicas e Integración (Abril — 2ª mitad)
- [ ] Dispensador construido y funcionando con firmware ESP32
- [ ] Signos vitales calibrados e integrados en ROS2
- [ ] BD local operativa con todos los módulos conectados
- [ ] Pruebas de integración completa end-to-end

### Entrega Final (Mayo 2026)
- [ ] Pruebas con usuarios reales
- [ ] Documentación académica completa
- [ ] Presentación del prototipo

---

## 11. RESTRICCIONES Y LIMITACIONES

| Categoría | Restricción |
|-----------|-------------|
| **Tiempo** | Deadline duro: 1 de mayo de 2026 |
| **Medicamentos** | Solo sólidos (tabletas/cápsulas); máx. 6 tipos × ~14 unidades |
| **Movilidad** | Solo una planta; no sube escaleras; velocidad máx. 0.25 m/s |
| **Hardware** | CPU i3 sin GPU; RAM 12 GB (RTAB-Map consume ~3-4 GB); sin LIDAR profesional |
| **Kinect V2** | Sensible a luz solar directa, superficies reflectivas y vidrios |
| **Energía** | ~6000mAh (suficiente para demos; escalable con packs adicionales) |
| **Conectividad** | Conversación avanzada requiere Wi-Fi; fallback offline solo para comandos predefinidos |

---

## 12. CONSIDERACIONES ÉTICAS

> Este sistema es un **prototipo académico** y NO es un dispositivo médico certificado.  
> Normas de referencia consideradas: **ISO 13482** (robots de cuidado personal) e **IEC 60601-1-11** (equipos médicos domiciliarios).

| El sistema PUEDE | El sistema NO PUEDE |
|-----------------|---------------------|
| Recordar y ejecutar horarios de medicación configurados | Diagnosticar enfermedades |
| Dispensar medicamentos previamente cargados | Prescribir o modificar tratamientos |
| Registrar y reportar mediciones de signos vitales | Reemplazar la supervisión médica profesional |
| Brindar información general de salud | Tomar decisiones médicas autónomas |
| Notificar a contactos de emergencia | Acceder a datos de salud sin identificación del usuario |

**Privacidad y seguridad física:**
- Datos de salud solo en BD local (nunca en la nube)
- Conversaciones no almacenadas de forma permanente
- Reconocimiento facial solo con consentimiento explícito del usuario registrado
- Velocidad limitada + múltiples sensores de obstáculos para proteger al usuario

---

*Para documentación técnica detallada por módulo, ver:*  
*→ `DOCUMENTACION_CONVERSACIONAL.md` (sistema Atlas)*  
*→ `DOCUMENTACION_ROS2.md` (ROS2, Nav2, Kinect, micro-ROS)*
