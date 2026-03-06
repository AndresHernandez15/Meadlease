# 🤖 ROBOT ASISTENTE INTELIGENTE PARA EL CUIDADO DE LA SALUD EN EL HOGAR
## Documentación General del Proyecto

> **Universidad Tecnológica de Bolívar**  
> **Programa:** Ingeniería Mecatrónica  
> **Tipo:** Proyecto de Grado  
> **Fecha de creación:** 2026-02-26  
> **Última actualización:** 2026-02-26  
> **Deadline interno:** 1 de mayo de 2026 (robot armado y funcional)  
> **Entrega final:** Finales de mayo de 2026  

---

## 📋 ÍNDICE

1. [Visión General](#visión-general)
2. [Equipo de Trabajo](#equipo-de-trabajo)
3. [Hardware del Sistema](#hardware-del-sistema)
4. [Módulos del Proyecto](#módulos-del-proyecto)
5. [Estado Actual del Proyecto](#estado-actual-del-proyecto)
6. [Roadmap y Cronograma](#roadmap-y-cronograma)
7. [Restricciones y Limitaciones](#restricciones-y-limitaciones)
8. [Consideraciones Éticas](#consideraciones-éticas)

---

## VISIÓN GENERAL

### Descripción del Proyecto

Robot asistente inteligente de uso domiciliario inspirado en el personaje ficticio "Baymax", diseñado para apoyar el cuidado autónomo de personas en casa. El sistema integra navegación autónoma, dispensación automatizada de medicamentos, monitoreo de signos vitales y conversación natural con el usuario.

**Nombre provisional del sistema conversacional:** Atlas  
**Nombre definitivo del robot:** Pendiente de definición (se evita usar "Baymax" por derechos de autor)

### Objetivos Principales

- Navegar de forma autónoma por un apartamento pequeño para localizar al usuario
- Dispensar medicamentos al usuario en los horarios programados
- Medir y registrar signos vitales básicos (BPM, SpO2, temperatura corporal)
- Interactuar con el usuario mediante conversación natural en español
- Proporcionar una interfaz de usuario intuitiva para gestión y consulta

### Filosofía de Diseño

- **Seguridad ante todo:** Movimiento lento, múltiples sensores de obstáculos, lógica de emergencia offline
- **MVP sobre completitud:** Funcionalidad demostrable > sistema perfecto
- **Modularidad:** Cada módulo puede desarrollarse y probarse independientemente
- **Escalabilidad:** Estructura preparada para mejoras futuras (más batería, más sensores, más usuarios)

---

## EQUIPO DE TRABAJO

| Integrante | Perfil | Rol en el Proyecto |
|------------|--------|--------------------|
| **Andrés** (Líder) | Ing. Mecatrónico e Ing. de Sistemas | Software, ROS2, Kinect V2, mapeo, IA conversacional, impresión 3D |
| **Linda** | Ing. Biomédica y Mecatrónica | Diseño mecánico del robot, diseño del dispensador, calibración y prueba de sensores biomédicos |
| **Sergio** | Ing. Mecatrónico | Mecánica, prueba de motores, prueba del sistema de dispensación, apoyo a Linda |
| **Juan** | Ing. Mecatrónico | Visión artificial, programación de microcontroladores, apoyo a Andrés |

---

## HARDWARE DEL SISTEMA

### Computador Principal (Cerebro del Robot)

| Componente | Especificación |
|------------|----------------|
| Modelo | Dell Inspiron 3421 |
| CPU | Intel Core i3-3227U |
| RAM | 12 GB |
| Almacenamiento | 500 GB HDD |
| Sistema Operativo | Ubuntu Desktop 22.04.5 LTS |
| Alimentación | Via jack DC desde batería (sin batería interna) |
| Voltaje requerido | 19.5V (step-down desde batería) |

> **Nota:** Hardware moderado. Todo el diseño de software prioriza optimización sobre features.

### Sensor Principal de Percepción

| Componente | Especificación |
|------------|----------------|
| Modelo | Microsoft Kinect V2 |
| RGB | 1920x1080 @ 30fps |
| Depth | 512x424 @ 30fps |
| Rango útil | 0.5m - 4.5m |
| Conexión | USB 3.0 + adaptador de corriente |
| Alimentación | 12V (step-down desde batería) |
| Serial | 204763633847 |
| Uso | Mapeo SLAM 3D + detección de personas (TBD) |

### Actuadores de Movilidad

| Componente | Especificación |
|------------|----------------|
| Motores | 2x BLDC (Brushless DC) de 24V extraídos de Hoverboard |
| Sensores Hall | Sí, incluidos (lectura de RPM validada ✅) |
| Drivers | 2x ZS-X11H |
| Configuración | Tracción diferencial (2 ruedas motrices + 1 rueda loca delantera) |
| Control PWM | Validado desde ESP32 S3 ✅ |

### Microcontroladores

| MCU | Función | Estado |
|-----|---------|--------|
| ESP32 S3 (Movilidad) | Control de motores vía PWM, lectura encoders Hall, sensores de obstáculos | ✅ Conectado a motores, probado |
| ESP32 S3 (Médica) | Control del dispensador de medicamentos, lectura de sensores de signos vitales | ⏳ Pendiente integración |
| STM32F411 Blackpill o ESP32 auxiliar | Comunicación con PC, recepción de botones HMI (si aplica) | ❌ Pendiente evaluación |

> **Decisión pendiente:** STM32F411 (mejor control de interrupciones, comunicación UART) vs ESP32 adicional (ESP-NOW u otro protocolo inalámbrico). Requiere pruebas comparativas.

### Sensores de Obstáculos y Seguridad

| Sensor | Cantidad | Posición | Función |
|--------|----------|----------|---------|
| JSN-SR04T (ultrasónico impermeable) | 2 | Frontal y trasero | Detección principal de obstáculos |
| HC-SR04 (ultrasónico) | 2-4 | Esquinas (distribución TBD) | Cobertura lateral adicional |
| Infrarrojo anticaída | TBD | Bordes delanteros | Detección de escalones/desniveles |

> **Nota:** Distribución exacta de HC-SR04 y selección definitiva del sensor anticaída están pendientes de pruebas.

### Sensores Biomédicos

| Sensor | Magnitudes | Estado |
|--------|-----------|--------|
| MAX30102 (o similar) x2 | BPM (ritmo cardíaco), SpO2 (saturación de oxígeno) | ⏳ Conseguidos, pendiente prueba y calibración |
| Sensor temperatura corporal | Temperatura corporal | ⏳ Conseguido, pendiente prueba y calibración |

### Sistema de Energía

| Componente | Detalle | Estado |
|------------|---------|--------|
| Pack de baterías | 7S 4P litio, ~29.4V nominal, ~6000mAh | ✅ Armado |
| Step-Down 19.5V | Alimentación portátil (jack DC) | ✅ Conseguido, probado |
| Step-Down 12V | Alimentación Kinect V2 | ✅ Conseguido |
| Step-Down 5V | MCUs, sensores, actuadores menores | ✅ Conseguido |
| Voltaje directo (~24-29V) | Motores BLDC via drivers ZS-X11H | ✅ |

> **Nota de capacidad:** 6000mAh es suficiente para demostración. La estructura interna permite añadir packs adicionales para mayor autonomía en versiones futuras.

---

## MÓDULOS DEL PROYECTO

### Módulo 1: Movilidad Autónoma

**Objetivo:** El robot debe ser capaz de moverse de forma segura y autónoma por un apartamento pequeño para localizar al usuario.

**Componentes clave:**
- Kinect V2 como sensor principal para mapeo (RTAB-Map en ROS2)
- Nav2 para navegación autónoma con el mapa generado
- ESP32 S3 como puente entre los comandos de ROS2 (`/cmd_vel`) y los motores físicos
- Sensores de obstáculos como capa de seguridad adicional

**Lógica de operación:**
1. En primera ejecución o por comando, el robot mapea el apartamento con Kinect
2. Una vez con mapa guardado, usa Nav2 + localización para navegar
3. Recibe objetivo de navegación (ej: posición del usuario detectada por visión)
4. Se desplaza de forma segura evitando obstáculos

**Parámetros de seguridad:**
- Velocidad máxima: 0.25 m/s
- Detención automática si ultrasonido detecta obstáculo < 30cm
- Sensores anticaída activos en todo momento

**Responsables:** Andrés (software/ROS2), Juan (firmware ESP32), Sergio (mecánica/pruebas)

---

### Módulo 2: Visión Artificial

**Objetivo:** Detectar personas en el entorno del robot e identificar al usuario mediante reconocimiento facial para personalizar la interacción.

**Componentes:**
- Cámara del portátil (ubicada en la parte superior de la pantalla) como sensor principal para reconocimiento facial
- Kinect V2 como posible apoyo para detección de personas a mayor rango

**Flujo de operación:**
1. El robot detecta presencia de una persona (detección de silueta/skeleton)
2. Se aproxima para tener un rango adecuado de visión del rostro
3. Realiza reconocimiento facial para verificar si es un usuario registrado
4. Si es usuario reconocido → activa flujo de interacción personalizado
5. Si no es reconocido → comportamiento por defecto

**Usuarios soportados:** Mínimo 2 usuarios registrados (requerimiento del profesor)

**Responsable:** Juan

---

### Módulo 3: Dispensación de Medicamentos

**Objetivo:** Dispensar automáticamente el medicamento correcto al usuario en el horario programado.

**Componentes mecánicos:**
- Carrusel de pastillas (compartimentos identificados por medicamento)
- Brazo robótico de 2DOF para manipulación
- Manguera conectada a bomba de vacío (para agarrar pastillas sin dañarlas)
- Sensor de presión (confirma cuando la pastilla es capturada en la manguera)

**Control:** ESP32 S3 (compartida con módulo de signos vitales)

**Flujo de operación:**
1. Sistema detecta que es hora de tomar un medicamento (scheduler)
2. Robot localiza al usuario (movilidad + visión)
3. Sistema verifica identidad del usuario (reconocimiento facial)
4. Brazo selecciona el medicamento correcto del carrusel
5. Vacío agarra la pastilla, sensor confirma captura
6. Robot entrega el medicamento al usuario
7. Sistema registra la entrega en base de datos

**Estado:** ❌ Diseño mecánico en curso (Linda + Sergio)

**Responsables:** Linda (diseño mecánico), Sergio (pruebas mecánicas), Juan (firmware ESP32)

---

### Módulo 4: Monitoreo de Signos Vitales

**Objetivo:** Medir y registrar periódicamente los signos vitales del usuario para llevar un historial de salud.

**Magnitudes medidas:**
- Ritmo cardíaco (BPM)
- Saturación de oxígeno en sangre (SpO2)
- Temperatura corporal

**Control:** ESP32 S3 (compartida con módulo dispensador)

**Flujo de operación:**
1. Por comando del usuario o por horario programado
2. Robot solicita al usuario colocar el dedo/mano en el sensor
3. Realiza medición (MAX30102 + sensor temperatura)
4. Almacena resultado en base de datos local con timestamp
5. El usuario puede consultar su historial desde el HMI o preguntando a Atlas

**Estado:** ⏳ Sensores conseguidos, pendiente pruebas y calibración (Linda)

**Responsables:** Linda (calibración y pruebas), Juan (firmware ESP32)

---

### Módulo 5: HMI e Interfaz de Usuario

**Objetivo:** Proveer al usuario una interfaz visual intuitiva en la pantalla del portátil para gestionar todas las funciones del robot, y un sistema conversacional para interacción natural.

**Interfaz gráfica:**
- Tipo: Aplicación desktop (modo kiosco) — tecnología TBD (PyQt, Electron, u otro)
- Pantalla: Pantalla del portátil Dell (no táctil)
- Interacción: Por evaluar entre trackpad o botones físicos
- Si se usan botones: MCU auxiliar recibe señales y las envía al portátil

**Sistema conversacional (Atlas):**
- Activación por wake word: "Atlas"
- Procesamiento local para comandos predefinidos (sin internet, Vosk)
- Procesamiento cloud para conversación avanzada (Groq LLM + Groq Whisper + Azure TTS)
- Idioma: Español colombiano
- Voz: Azure Neural Voice (Salome, femenina, empática)
- Ver documentación detallada en `DOCUMENTACION_CONVERSACIONAL.md`

**Base de datos local:**
- Almacena: usuarios registrados, horarios de medicamentos, historial de signos vitales, registros de dispensación
- Motor: TBD (SQLite probable por ligereza)

**Estado:** ❌ Pendiente (se desarrolla al final, cuando los demás módulos estén en ROS2)

**Responsable:** Andrés

---

### Módulo 6: Comunicación PC ↔ Microcontroladores

**Objetivo:** Canal de comunicación confiable entre el portátil (ROS2) y los microcontroladores.

**Opción A - STM32F411 Blackpill:**
- Ventaja: Mejor control de interrupciones, comunicación física UART
- Integración ROS2: ros2serial o protocolo personalizado
- Ideal para: Control de botones HMI con alta responsividad

**Opción B - ESP32 adicional:**
- Ventaja: Protocolo ESP-NOW u otro inalámbrico, sin cables extra
- Integración ROS2: Vía WiFi o serial USB

**Estado:** ❌ Pendiente pruebas comparativas para tomar decisión

---

### Extra: ROS2 como Framework de Integración

ROS2 Humble Hawksbill se utiliza en el portátil como framework principal de integración entre todos los módulos de software. Facilita:
- Drivers para Kinect V2 (kinect2_bridge)
- SLAM 3D con RTAB-Map
- Navegación autónoma con Nav2
- Comunicación entre nodos mediante topics y servicios
- Visualización con RViz2

Ver documentación técnica detallada en `DOCUMENTACION_ROS2.md`.

---

## ESTRUCTURA FÍSICA DEL ROBOT

### Dimensiones

| Dimensión | Valor |
|-----------|-------|
| Ancho base | 40 cm |
| Largo base | 50 cm |
| Alto total | ~110 cm |
| Configuración ruedas | 2 ruedas motrices traseras + 1 rueda loca delantera |

### Estructura y Carcasa

- **Estructura interna:** Reforzada con 4 varillas roscadas ubicadas estratégicamente en el centro de masa
- **Carcasa:** Impresión 3D en PET-G (6 kg disponibles)
- **Uniones:** Sistema tipo cola de milano
- **Acabado:** Masilla automotriz + pintura para acabado profesional
- **Diseño:** Modular para facilitar mantenimiento y escalabilidad

### Posición de Componentes (TBD al finalizar diseño mecánico)
- Kinect V2: Altura y offset frontal por definir en diseño CAD
- Cámara portátil: Parte superior del robot (encima de la pantalla)
- Sensores ultrasonidos: Perímetro (posiciones exactas TBD)
- Sensores biomédicos: Posición accesible para el usuario (TBD)
- Pantalla portátil: Parte frontal, orientada hacia el usuario

---

## ESTADO ACTUAL DEL PROYECTO

> **Fecha:** 2026-02-26

| Módulo | Componente | Estado | Notas |
|--------|------------|--------|-------|
| **Movilidad** | Motores instalados + control PWM | ✅ Completado | Probado con ESP32, lectura encoders Hall validada |
| **Movilidad** | SLAM con Kinect + RTAB-Map | ⏳ En progreso | Optimización realizada, funcionando en Ubuntu |
| **Movilidad** | Nav2 navegación autónoma | ❌ Pendiente | Se inicia cuando robot esté armado |
| **Movilidad** | Nodo puente ESP32 ↔ ROS2 | ⏳ En desarrollo | Próximo paso crítico |
| **Visión** | Detección de personas | ❌ Pendiente | Por iniciar (Juan) |
| **Visión** | Reconocimiento facial | ❌ Pendiente | Por iniciar (Juan) |
| **Dispensador** | Diseño mecánico | ⏳ En progreso | Linda + Sergio trabajando en ello |
| **Dispensador** | Construcción física | ❌ Pendiente | Esperando diseño |
| **Dispensador** | Firmware ESP32 | ❌ Pendiente | Esperando diseño mecánico |
| **Signos Vitales** | Sensores | ⏳ Conseguidos | Pendiente pruebas y calibración (Linda) |
| **Signos Vitales** | Firmware ESP32 | ❌ Pendiente | |
| **Conversacional** | Módulos audio + local (Vosk) | ✅ Completado | Funcionando en Windows |
| **Conversacional** | Módulos cloud (Groq + Azure) | ✅ Completado | Funcionando en Windows |
| **Conversacional** | FSM + main.py | ⏳ En pruebas | Validación final en Windows |
| **Conversacional** | Port a ROS2 | ❌ Pendiente | |
| **HMI** | Interfaz desktop | ❌ Pendiente | Se hace al final |
| **Energía** | Pack baterías 7S4P | ✅ Completado | Armado y probado |
| **Energía** | Step-downs (19.5V, 12V, 5V) | ✅ Completado | Conseguidos, alimentación portátil probada |
| **Estructura** | Diseño CAD carcasa 3D | ⏳ En progreso | Finaliza en 1-2 días |
| **Estructura** | Impresión 3D PET-G | ❌ Pendiente | Inicia al terminar diseño |
| **Comunicación** | Selección MCU auxiliar | ❌ Pendiente | Pruebas STM32 vs ESP32 |

---

## ROADMAP Y CRONOGRAMA

### Meta: Robot funcional listo para pruebas finales → 1 de mayo 2026

### Prioridades Inmediatas (Próximas 2 semanas)
1. Finalizar diseño CAD e iniciar impresión 3D
2. Implementar nodo puente ESP32 ↔ ROS2 (`/cmd_vel` → Serial → Motores)
3. Validar FSM + main.py del sistema conversacional en Windows
4. Iniciar diseño del módulo dispensador
5. Pruebas y calibración de sensores biomédicos

### Fase 1: Integración Mecánica (Marzo)
- Robot físicamente armado (estructura + electrónica)
- Movilidad básica funcional (teleop físico)
- TF tree completo en ROS2
- Mapa del apartamento de prueba generado

### Fase 2: Navegación y Percepción (Abril - primera mitad)
- Nav2 funcionando en robot físico
- Detección de personas con cámara
- Reconocimiento facial (2 usuarios)
- Sistema conversacional portado a ROS2

### Fase 3: Funciones Médicas (Abril - segunda mitad)
- Dispensador construido y funcionando
- Signos vitales integrados en ROS2
- Base de datos local operativa
- Integración completa de todos los módulos

### Entrega Final (Mayo)
- Pruebas end-to-end con usuarios reales
- Documentación académica
- Presentación del prototipo

---

## RESTRICCIONES Y LIMITACIONES

### Tiempo
- Deadline: 1 mayo 2026 (robot funcional) + finales mayo (entrega académica)
- ~280 horas de trabajo restantes estimadas

### Presupuesto
- Hardware principal: ✅ Ya adquirido
- APIs conversación: ~$10-15/mes (Groq gratuito, Azure TTS ~$5-10/mes)
- Material impresión 3D: ✅ 6 kg PET-G disponibles
- Sensores adicionales: Ya conseguidos

### Hardware
- Sin GPU dedicada (solo CPU Intel i3)
- RAM limitada: 12GB (RTAB-Map consume ~3-4GB)
- Sin LIDAR profesional (se usa Kinect como sustituto)
- Autonomía de batería limitada (~6000mAh, suficiente para demos)

### Operacionales
- Uso exclusivo en interiores
- Velocidad máxima 0.25 m/s (seguridad)
- Dependencia de internet para conversación avanzada (con fallback local)
- Robot conectado a la red del apartamento para APIs cloud

---

## CONSIDERACIONES ÉTICAS

### Sobre el módulo médico

> **IMPORTANTE:** Este sistema es un prototipo académico de investigación y **NO es un dispositivo médico certificado**.

**El sistema SÍ puede:**
- Recordar horarios de medicamentos registrados por el usuario o cuidador
- Dispensar medicamentos previamente cargados y configurados
- Reportar mediciones de signos vitales almacenadas
- Brindar información general de salud

**El sistema NO puede:**
- Diagnosticar enfermedades o condiciones médicas
- Prescribir medicamentos o modificar tratamientos
- Reemplazar la supervisión de un profesional de la salud
- Tomar decisiones médicas autónomas

### Privacidad
- Los datos de salud se almacenan localmente (no en la nube)
- Las conversaciones no se almacenan permanentemente
- El reconocimiento facial opera con consentimiento explícito del usuario

### Seguridad física
- Velocidad limitada para proteger a usuarios, especialmente adultos mayores
- Múltiples capas de detección de obstáculos
- Comandos de emergencia siempre disponibles offline

---

## ENTORNO DE OPERACIÓN

- **Tipo:** Apartamento residencial pequeño (50-80 m² estimado)
- **Suelos:** Indoor (madera, baldosa o similar)
- **Iluminación:** Natural y artificial
- **Obstáculos típicos:** Muebles, personas, mascotas

**Limitaciones del Kinect a considerar:**
- Luz solar directa directa degrada la lectura de profundidad
- Vidrios y espejos pueden generar lecturas falsas
- Superficies muy oscuras o muy brillantes pueden afectar la precisión

---

*Este documento se actualiza con cada hito importante del proyecto.*  
*Para detalles técnicos: ver `DOCUMENTACION_ROS2.md` y `DOCUMENTACION_CONVERSACIONAL.md`*
