# INTERFAZ HUMANO-MÁQUINA (HMI) — ATLAS FACE
## Robot Asistente Médico Domiciliario Meadlese

> **Audiencia:** Andrés (líder software)  
> **Estado:** Diseño completo definido · Implementación pendiente  
> **Tecnología:** FastAPI + Chromium Kiosk + HTML/CSS/JS (Canvas 2D)  
> **Plataforma destino:** Ubuntu 22.04 + ROS2 Humble  
> **Última actualización:** 2026-03-16

---

## ÍNDICE

1. [Visión General](#1-visión-general)
2. [Decisión Tecnológica](#2-decisión-tecnológica)
3. [Arquitectura del Módulo HMI](#3-arquitectura-del-módulo-hmi)
4. [Estados del Sistema — Definición Completa](#4-estados-del-sistema--definición-completa)
5. [Mapa de Transiciones](#5-mapa-de-transiciones)
6. [Flujos Principales de Uso](#6-flujos-principales-de-uso)
7. [Diseño Visual — Cara Baymax](#7-diseño-visual--cara-baymax)
8. [Integración con ROS2 y Sistemas Backend](#8-integración-con-ros2-y-sistemas-backend)
9. [Interacción Física — Trackpad](#9-interacción-física--trackpad)
10. [Estado Actual y Pendientes](#10-estado-actual-y-pendientes)
11. [Comandos de Referencia Rápida](#11-comandos-de-referencia-rápida)

---

## 1. VISIÓN GENERAL

El módulo HMI es la capa de presentación del robot Meadlese. Tiene dos responsabilidades principales:

1. **Cara expresiva de Baymax** — pantalla de estado permanente del robot, con animaciones que comunican visualmente qué está haciendo el robot en cada momento.
2. **Dashboard médico** — panel de datos del paciente, accesible por comando de voz o toque del trackpad, con visualización de signos vitales, próximas dosis e historial.

### Principios de Diseño

| Principio | Descripción |
|-----------|-------------|
| **Expresivo** | La cara comunica el estado del robot sin que el usuario tenga que leer texto |
| **No intrusivo** | En IDLE la pantalla es casi completamente negra — no molesta en un entorno doméstico nocturno |
| **Reactivo** | Animaciones sincronizadas con audio real (amplitud de micrófono y TTS) |
| **Seguro** | El dashboard con datos de salud se cierra automáticamente si no hay persona presente |
| **Robusto** | Si el frontend falla, el robot sigue funcionando — HMI es una capa de presentación, no de control |

### Hardware de Pantalla

- **Dispositivo:** Samsung laptop (trackpad integrado como superficie táctil)
- **Montaje:** En el pecho del robot, cable de pantalla y USB ruteados por el cuello hacia el Dell
- **Modo:** Chromium en pantalla completa (kiosk mode)
- **Resolución objetivo:** 1366×768 o superior
- **Nota para Linda/Sergio:** El diseño CAD debe incluir recorte para trackpad en la carcasa frontal

---

## 2. DECISIÓN TECNOLÓGICA

### Stack Seleccionado: FastAPI + Chromium Kiosk

**Decisión tomada:** 2026-03-16  
**Alternativa descartada:** PyQt5/6

### Tabla Comparativa

| Criterio | PyQt5/6 | **Web App Local** ✅ |
|----------|---------|---------------------|
| Cara Baymax animada | Posible pero verboso (QGraphicsScene) | Canvas 2D + CSS — estándar de industria |
| Integración ROS2 | Directo (mismo proceso Python) | FastAPI + rclpy, separación limpia |
| Velocidad de desarrollo | Media — reinicio ROS2 por cada cambio UI | Alta — frontend hot-reload independiente |
| Uso de RAM | ~50–100 MB | ~200–400 MB (Chromium overhead) |
| Modo kiosko | Manual (showFullScreen + suprimir atajos SO) | `chromium --kiosk` — un comando, battle-tested |
| Debugging | Acoplado — crash UI puede afectar ROS2 | Desacoplado — Chrome DevTools + logs FastAPI independientes |
| Experiencia previa del equipo | Algo de PyQt | HTML/CSS/JS + FastAPI — todo conocido |

**Argumento definitivo:** La cara Baymax animada es la feature más visible del robot. HTML Canvas con `requestAnimationFrame` permite ojos con pupila dinámica, parpadeo suave, onda de voz en tiempo real y expresiones transicionales con ciclos de iteración de segundos. El overhead de ~200–400 MB de Chromium es manejable con los 12 GB de RAM disponibles.

> **Nota de recursos:** Con RTAB-Map consumiendo ~3–4 GB, queda margen suficiente. Verificar en pruebas cuando todos los nodos corran simultáneamente.

### Arquitectura de Capas

```
ROS2 graph ──→ FastAPI (Python, proceso separado, mismo PC)
                  │  suscribe a /health/*, /atlas/*, /robot/speak
                  │  publica a /hmi/state, /hmi/action
                  │
                  ├── REST endpoints (datos dashboard, BD)
                  ├── WebSocket /ws/state    (cambios de estado → cara)
                  └── WebSocket /ws/audio    (nivel de amplitud → boca)
                              │
                    Chromium (kiosk mode, localhost:8000)
                              │
                    HTML + Canvas 2D + CSS animations
                    (cara Baymax + dashboard)
```

---

## 3. ARQUITECTURA DEL MÓDULO HMI

### Estructura de Archivos (Target)

```
hmi/                                     # Módulo HMI (Meadlease/hmi/)
├── server.py                            # FastAPI app — entrypoint
├── ros2_bridge.py                       # rclpy subscriber/publisher thread
├── audio_level.py                       # Captura nivel de amplitud sounddevice → WS
├── routers/
│   ├── state.py                         # WebSocket /ws/state
│   ├── audio.py                         # WebSocket /ws/audio
│   └── dashboard.py                     # REST endpoints datos BD
├── static/
│   ├── index.html                       # App HTML única
│   ├── baymax_face.js                   # Renderizado Canvas — cara Baymax
│   ├── dashboard.js                     # Panel de datos del paciente
│   ├── state_machine.js                 # FSM del frontend (16 estados)
│   └── style.css                        # Variables CSS + layout kiosk
└── templates/                           # Jinja2 si se necesita SSR
```

### Lanzar el HMI

```bash
# Terminal 1 — servidor FastAPI
cd ~/Meadlease/hmi
uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Chromium en modo kiosko
chromium-browser --kiosk \
  --app=http://localhost:8000 \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0

# Salir del kiosko (durante desarrollo)
# Alt+F4 o Ctrl+Alt+T para terminal
```

### Integrar en el Launch del Robot

```python
# En bringup.launch.py
Node(
    package='robot_medical',
    executable='hmi_launcher.py',
    name='hmi_node',
    output='screen'
)
```

---

## 4. ESTADOS DEL SISTEMA — DEFINICIÓN COMPLETA

El HMI tiene **16 estados**, cada uno con visual específico, entradas, salidas y nodos ROS2 conectados. Se organizan en cuatro grupos funcionales.

> **Criterio de estado propio:** visual diferente + lógica HMI diferente + transiciones propias.  
> Los estados con 🔒 bloquean subsistemas durante su ejecución.

---

### Grupo A — Núcleo Conversacional

#### Estado 1: IDLE

**Descripción:** Cara Baymax pura en reposo. Modo screensaver. Porcupine corre en background 24/7. Se activa tras timeout de inactividad o ausencia de persona detectada por ultrasonidos.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos blancos (elipses) / fondo `#000000` / parpadeo aleatorio cada 3–6 s / micro-animación de "respiración" (escala `1.0 → 1.02 → 1.0` en loop de 4 s) |
| **Texto en pantalla** | Ninguno |
| **Audio** | Silencio — Porcupine escucha en background |
| **Timeout** | No aplica — estado de reposo permanente |

**Entradas:**
- `SUCCESS` → timer 3 s completado
- `SPEAKING` → playback terminado sin follow-up pendiente
- `DASHBOARD` → timeout 60 s o sin persona detectada
- `ERROR` → auto-recovery exitoso
- `ALERT` → alerta normalizada o cancelada por usuario
- `SEARCHING` → timeout 120 s sin encontrar al usuario

**Salidas:**
- → `WAKE`: wake word "Atlas" detectado (Porcupine)
- → `REMINDER`: `scheduler_node` dispara horario de medicación
- → `DASHBOARD`: botón trackpad o comando de voz "ver panel"

**Nodos ROS2 / Sistemas:**
- `atlas_ros2_node` (Porcupine activo 24/7)
- `/atlas/listening` → `Bool = false`
- `scheduler_node` (poll cada 30 s contra tabla `horarios_medicacion`)
- `/ultrasonic/front` (detección de presencia)

---

#### Estado 2: WAKE

**Descripción:** Transición animada al detectar la wake word. Duración fija ~1.2 s. No acepta input de voz ni comandos de movimiento durante este tiempo.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos cerrados → abren con efecto bloom (radius `0 → normal` con overshoot) / destello blanco rápido / ondas de sonar irradiando desde el centro |
| **Texto en pantalla** | Ninguno |
| **Duración** | 1.2 s fijo, luego transición automática a LISTENING |

**Entradas:**
- `IDLE` → wake word "Atlas" detectado (Porcupine)

**Salidas:**
- → `LISTENING`: animación completada (timer 1.2 s)

**Nodos ROS2 / Sistemas:**
- `/atlas/listening` → `Bool = true`
- `atlas_ros2_node` (evento `WAKE_WORD_DETECTED` en bus interno)

---

#### Estado 3: LISTENING

**Descripción:** Atlas escuchando activamente. VAD y Vosk corren en paralelo. Vosk puede interceptar y saltar a SPEAKING directamente si detecta comando local (~480 ms, sin pasar por cloud).

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos azul `#378ADD` con halo pulsante sincronizado con amplitud del micrófono / anillo de onda reactivo alrededor de los ojos / texto "Escuchando..." muy sutil en parte inferior |
| **Texto en pantalla** | `"Escuchando..."` — fuente pequeña, baja opacidad |

**Entradas:**
- `WAKE` → animación completada
- `SPEAKING` → robot hizo pregunta y espera respuesta del usuario

**Salidas:**
- → `THINKING`: `SPEECH_END` detectado por VAD (audio capturado)
- → `SPEAKING`: `COMMAND_DETECTED` local (Vosk) — respuesta directa ~480 ms
- → `IDLE`: timeout 10 s sin detección de voz

**Nodos ROS2 / Sistemas:**
- `/atlas/listening` → `Bool = true`
- `atlas_ros2_node` (VAD WebRTC + Vosk — 9 comandos / 5 categorías)
- `audio_buffer` (PCM frames acumulados)
- PyAudio stream 16 kHz mono

---

#### Estado 4: THINKING

**Descripción:** Procesando con Groq LLM. Duración variable ~0.4–1.5 s. Construye contexto del paciente desde la BD antes de llamar al LLM. El intent extraído aquí determina el siguiente estado.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos ámbar `#BA7517` / mirada desplazada ~15% arriba-izquierda (expresión "pensativa") / 3 puntos pequeños orbitando lentamente alrededor de los ojos |
| **Texto en pantalla** | Ninguno |

**Entradas:**
- `LISTENING` → `SPEECH_END` con audio capturado listo para STT

**Salidas:**
- → `SPEAKING`: respuesta LLM lista → Azure TTS generando
- → `DISPENSING`: intent = dispensar + `/patient/identified` confirmado
- → `MEASURING`: intent = medir signos vitales
- → `DASHBOARD`: intent = ver historial / panel de datos
- → `ERROR`: timeout 15 s o fallo total de API sin fallback disponible

**Nodos ROS2 / Sistemas:**
- `atlas_ros2_node` (Groq Whisper STT → Llama 3.3 70B)
- `medical_db.get_resumen_paciente()` + `get_proxima_dosis()` (contexto dinámico)

---

#### Estado 5: SPEAKING

**Descripción:** Atlas hablando. Onda de boca sincronizada con amplitud real del audio TTS a través de WebSocket dedicado. El nivel de audio sale desde `sounddevice` → FastAPI `/ws/audio` → Canvas.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos blancos ligeramente más grandes (expresión "entusiasta") / onda senoidal animada en zona boca con amplitud proporcional al nivel de audio / sin texto |
| **Sincronización** | `sounddevice` output level → `audio_level.py` → WebSocket `/ws/audio` → `baymax_face.js` — requiere implementación explícita |

**Entradas:**
- `THINKING` → respuesta LLM generada y TTS listo
- `GREETING` → saludo animado completado

**Salidas:**
- → `LISTENING`: robot terminó con pregunta abierta (espera respuesta)
- → `IDLE`: monólogo terminado sin pregunta pendiente
- → `DISPENSING`: confirmación verbal de dispensar recibida
- → `MEASURING`: instrucción verbal "apoya el dedo" dada

**Nodos ROS2 / Sistemas:**
- `atlas_ros2_node` (Azure TTS Camila `es-PE-CamilaNeural`)
- `/robot/speak` (`std_msgs/String`) — TTS proactivo
- `sounddevice` output level → FastAPI WebSocket `/ws/audio` → HMI Canvas

> **Nota de implementación:** La sincronización de la boca es la parte más compleja del HMI. `audio_level.py` debe capturar el RMS del buffer de `sounddevice` en intervalos de ~20 ms y publicarlo vía WebSocket al frontend. No es automático con la implementación actual de Atlas.

---

### Grupo B — Movilidad

#### Estado 6: MOVING

**Descripción:** Desplazamiento a destino conocido con `goal_pose` definido. No hay búsqueda activa. El dispensador queda bloqueado durante todo el movimiento.

> **Nombre anterior:** NAVIGATING (renombrado para claridad — MOVING = destino conocido, SEARCHING = exploración activa)

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos blancos con pupila desplazada hacia adelante / overlay sutil: flecha direccional + `"Dirigiéndome a [zona]"` / mini-indicador de batería opcional |
| **🔒 Bloquea** | Dispensador — `medication_node` rechaza comandos de dispensación |

**Entradas:**
- `REMINDER` → misión activa, destino = última posición conocida del usuario
- `SPEAKING` → comando de voz "ven aquí" o "regresa a base"

**Salidas:**
- → `SEARCHING`: llegó a destino pero sin usuario presente
- → `APPROACHING`: persona detectada durante el trayecto
- → `IDLE`: llegó a base sin misión activa pendiente
- → `ERROR`: Nav2 falla o path completamente bloqueado

**Nodos ROS2 / Sistemas:**
- Nav2 (`/goal_pose`)
- `/cmd_vel` (`geometry_msgs/Twist`)
- `esp32_bridge_node` → STM32 → ESP32 Movilidad → motores BLDC
- `state_machine_node` (tracking del goal activo)

---

#### Estado 7: SEARCHING

**Descripción:** Búsqueda activa del usuario. Robot explora zonas conocidas del apartamento. Kinect y `person_detector_node` corriendo continuamente. Si hay un REMINDER activo, el banner del medicamento es siempre visible en la parte superior.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos blancos moviéndose suavemente izquierda→derecha en loop (efecto scan) / línea de scan horizontal pulsante / si REMINDER activo: banner superior persistente con nombre del medicamento y urgencia progresiva |

**Entradas:**
- `REMINDER` → inicio de misión de búsqueda (inmediato al disparar)
- `MOVING` → llegó a destino sin usuario presente
- `IDLE` → comando de voz "búscame"

**Salidas:**
- → `APPROACHING`: `/person/detected = true` (Kinect skeleton tracking)
- → `IDLE`: timeout 120 s sin encontrar al usuario (misión no urgente)
- → `ALERT`: misión REMINDER crítica — timeout >60 min sin entrega de medicación

**Nodos ROS2 / Sistemas:**
- `person_detector_node` (`/person/detected`, `/person/position`)
- Nav2 (patrón de exploración por zonas conocidas del mapa)
- `/kinect2/sd/points` (skeleton tracking)
- `/ultrasonic/front` y `/ultrasonic/rear`

---

#### Estado 8: APPROACHING

**Descripción:** Persona detectada geométricamente. Robot se aproxima. Cámara portátil activa para reconocimiento facial paralelo al movimiento. Nav2 usa `/person/position` como goal dinámico.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos blancos ligeramente agrandados (expresión expectante/amigable) / animación zoom-in sutil en los ojos / `"?"` pequeño visible mientras no confirma identidad del usuario |

**Entradas:**
- `SEARCHING` → `/person/detected = true`
- `MOVING` → persona detectada durante el trayecto hacia destino

**Salidas:**
- → `GREETING`: `/patient/identified` recibido con confianza ≥ umbral configurado
- → `SPEAKING`: dentro de rango, reconocimiento no exitoso → `"¿Eres tú, [nombre]?"`
- → `SEARCHING`: persona se movió y se perdió de vista (timeout 8 s)

**Nodos ROS2 / Sistemas:**
- `face_recognition_node` (`/patient/identified`, `/patient/confidence`)
- Nav2 (goal dinámico — `/person/position` actualizado a 2 Hz)
- Cámara portátil USB
- `/patient/confidence` (`std_msgs/Float32`) — umbral configurable en `settings.py`

---

### Grupo C — Reconocimiento y Tareas Médicas

#### Estado 9: GREETING

**Descripción:** Usuario reconocido exitosamente. Estado de celebración breve (~2–3 s). `scheduler_node` consultado: ¿hay misión médica pendiente para esta persona?

> **Nombre anterior:** IDENTIFIED (renombrado — GREETING describe mejor el visual y la interacción)

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos → medias lunas (sonrisa Baymax clásica) / flash verde suave / `"¡Hola, [nombre]!"` centrado en fuente grande / partículas sutiles opcionales |
| **Duración** | 2–3 s fijo antes de transición |

**Entradas:**
- `APPROACHING` → `/patient/identified` recibido con confianza ≥ umbral

**Salidas:**
- → `DISPENSING`: REMINDER activo para este usuario en este momento
- → `MEASURING`: medición programada urgente para este usuario
- → `SPEAKING`: saludo verbal + `"¿En qué puedo ayudarte?"` (sin misión pendiente)

**Nodos ROS2 / Sistemas:**
- `/patient/identified` (`std_msgs/String`) — ID del paciente
- `medical_db.get_resumen_paciente()` — nombre, medicamentos activos
- `scheduler_node` — consulta si hay misión pendiente para `patient_id`
- `atlas_ros2_node` (TTS saludo personalizado con nombre real)

---

#### Estado 10: DISPENSING 🔒

**Descripción:** Dispensación en ejecución. Estado bloqueante: robot completamente inmóvil y sin aceptar comandos de voz (excepto "cancelar"). Load cell confirma el resultado de la dispensación por comparación de peso pre/post.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos ámbar concentrados / animación píldora cayendo (overlay) / `"[Medicamento] — [N] tabletas"` visible / barra de progreso lineal / aviso `"Por favor, no se mueva"` |
| **🔒 Bloquea** | Robot inmóvil (`/cmd_vel` bloqueado) / sistema de voz desactivado (excepto "cancelar") |

**Entradas:**
- `GREETING` → REMINDER activo para este usuario
- `SPEAKING` → confirmación verbal de dispensar
- `THINKING` → intent = dispensar + usuario confirmado en `/patient/identified`

**Salidas:**
- → `SUCCESS`: load cell confirma peso correcto post-dispensación
- → `ERROR`: fallo mecánico del carrusel o timeout del dispensador
- → `ALERT`: load cell detecta peso incorrecto (pastilla no salió del compartimento)

**Nodos ROS2 / Sistemas:**
- `medication_node` (`/dispense_medication`)
- Servicio `/dispense` → respuesta `{éxito / error / timeout}`
- `esp32_medical_node` (carrusel stepper + servo escapement)
- HX711 + load cell (verificación peso pre/post por compartimento)
- `medical_db.registrar_dispensacion()` — timestamp + usuario + medicamento + estado

---

#### Estado 11: MEASURING

**Descripción:** Midiendo signos vitales. Requiere cooperación activa del usuario. Valores BPM, SpO₂ y temperatura aparecen progresivamente en tiempo real. Semáforo visual de normalidad por cada valor. Guardado automático en BD al completar.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos azul sereno `#378ADD` / heartbeat SVG pulsante central / secuencia: `"Apoya el dedo..."` → BPM aparece → SpO₂ aparece → Temp aparece / semáforo de normalidad (verde / ámbar / rojo) por valor |
| **Rangos de referencia** | BPM: 60–100 / SpO₂: ≥ 95% / Temperatura: 36.1–37.2°C |

**Entradas:**
- `SPEAKING` → instrucción "mide mis signos vitales" dada verbalmente
- `THINKING` → intent = medir confirmado
- `GREETING` → medición programada urgente para este usuario
- `DASHBOARD` → botón `"Medir ahora"` presionado con trackpad

**Salidas:**
- → `SPEAKING`: resultados listos → Atlas los verbaliza con contexto
- → `SUCCESS`: todos los valores registrados correctamente en BD
- → `ALERT`: algún valor fuera del rango de referencia configurado
- → `ERROR`: sensor MAX30102 no responde (timeout 30 s)

**Nodos ROS2 / Sistemas:**
- `/health/bpm` (`std_msgs/Int32`)
- `/health/spo2` (`std_msgs/Int32`)
- `/health/temperature` (`std_msgs/Float32`)
- `vital_signs_node` (ESP32 Médica → STM32 → micro-ROS → PC)
- `medical_db.registrar_signos_vitales()` — trío BPM/SpO₂/Temp por fila

---

#### Estado 12: REMINDER

**Descripción:** Estado de misión activa disparado por el scheduler. Robot sale a buscar al usuario con propósito definido. El banner del medicamento pendiente es visible en todo momento y su urgencia visual aumenta con el tiempo transcurrido.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Banner superior persistente `"Hora de [Medicamento] — [N] tabletas"` (color teal, progresivamente más visible) / cara de SEARCHING debajo con ojos color teal `#1D9E75` |
| **Urgencia progresiva** | 0–15 min: banner discreto / 15–30 min: banner ámbar / >30 min: banner rojo pulsante |

**Entradas:**
- `IDLE` → `scheduler_node` dispara horario (verificación cada 30 s contra tabla `horarios_medicacion`)

**Salidas:**
- → `SEARCHING`: inicio de búsqueda inmediata (sub-estado visual, mismo REMINDER activo)
- → `ALERT`: timeout crítico >60 min sin entregar la medicación

**Nodos ROS2 / Sistemas:**
- `scheduler_node` (topic `/scheduler/reminder` con payload: `patient_id`, `medication_id`, `scheduled_time`)
- `medical_db.get_proxima_dosis()` — nombre, dosis, compartimento
- `state_machine_node` (registra misión activa con timestamp de inicio)

---

#### Estado 13: SUCCESS

**Descripción:** Confirmación visual de tarea completada. Estado breve (~3 s) con animación de celebración antes de volver a reposo o dashboard. Sin este estado el usuario no tiene feedback claro de que la tarea terminó correctamente.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos → medias lunas felices / checkmark SVG animado (trazo que se dibuja en 0.6 s) / `"[Tarea] completada ✓"` / fade-out suave hacia IDLE |
| **Duración** | 3 s fijo |

**Entradas:**
- `DISPENSING` → load cell confirma dispensación correcta
- `MEASURING` → todos los valores registrados sin errores en BD

**Salidas:**
- → `IDLE`: timer 3 s completado (sin misión adicional pendiente)
- → `DASHBOARD`: usuario toca el trackpad para ver resultados detallados
- → `SPEAKING`: follow-up verbal `"Tus valores están bien"` o `"Medicación entregada"`

**Nodos ROS2 / Sistemas:**
- `medical_db` — confirmación de escritura en BD
- `scheduler_node` — marcar tarea como completada, calcular próxima dosis

---

### Grupo D — Pantallas Complejas y Alertas

#### Estado 14: DASHBOARD

**Descripción:** Única pantalla sin cara Baymax dominante. Panel de datos completo del paciente. La cara aparece en miniatura en la esquina superior como avatar de estado. Timeout agresivo por privacidad: si no hay persona presente, vuelve a IDLE.

| Elemento | Detalle |
|----------|---------|
| **Layout** | Cards de datos: últimos signos vitales / próxima dosis con tiempo restante / historial de dispensaciones / mini-cara Baymax esquina sup-izquierda |
| **Controles** | 3 botones grandes táctiles (optimizados para trackpad): `"Medir ahora"` / `"Ver historial completo"` / `"Volver"` |
| **Fuente de datos** | `medical_db` vía REST endpoints FastAPI — no datos hardcodeados |
| **Privacidad** | Timeout 60 s sin interacción → IDLE / `/ultrasonic/front` sin persona 10 s → IDLE |

**Entradas:**
- `THINKING` / `SPEAKING` → intent = ver panel detectado
- Botón físico trackpad en cualquier estado
- `SUCCESS` → usuario quiere ver resultados detallados

**Salidas:**
- → `IDLE`: timeout 60 s sin interacción
- → `IDLE`: `/ultrasonic/front` sin persona (timeout 10 s)
- → `LISTENING`: wake word "Atlas" detectado (Porcupine sigue activo)
- → `MEASURING`: botón `"Medir ahora"` presionado
- → `DISPENSING`: botón `"Dar medicamento"` + confirmación verbal

**Nodos ROS2 / Sistemas:**
- `medical_db` (READ: `signos_vitales`, `horarios_medicacion`, `registros_dispensacion`)
- FastAPI REST endpoints (`/api/patient/{id}/vitals`, `/api/patient/{id}/medications`)
- `scheduler_node` (próximas dosis con tiempo relativo)
- `/ultrasonic/front` (detección de presencia para timeout de privacidad)

---

#### Estado 15: ALERT

**Descripción:** Alerta médica o de emergencia. Dos severidades implementadas como variantes del mismo estado: `VITALS` (valores anómalos de sensores) y `EMERGENCY` (botón físico GPIO PA0 del STM32). Countdown visible antes de notificar al contacto de emergencia.

| Elemento | Detalle |
|----------|---------|
| **Visual — VITALS** | Fondo rojo pulsante / ojos rojos en modo alarma / `"SpO₂ bajo: 91%"` en texto grande / countdown `"Notificando en 10 s"` / botón grande `"Cancelar — estoy bien"` |
| **Visual — EMERGENCY** | Ídem pero con `"EMERGENCIA"` y countdown reducido a 5 s / sin posibilidad de cancelar por voz |
| **Countdown** | VITALS: 10 s / EMERGENCY: 5 s — configurable en `settings.py` |

**Entradas:**
- `MEASURING` → valor fuera de rango configurado (`/health/*`)
- `REMINDER` → timeout crítico >60 min sin entrega de medicación
- GPIO PA0 STM32 → botón físico de emergencia en la base del robot

**Salidas:**
- → `SPEAKING`: Atlas verbaliza la alerta en voz alta
- → `IDLE`: alerta cancelada por usuario antes del countdown (`"Cancelar — estoy bien"`)
- → `IDLE`: notificación Wi-Fi enviada, monitoreo continúa normalmente

**Nodos ROS2 / Sistemas:**
- `atlas_ros2_node` (TTS alerta con prioridad máxima)
- `/health/*` (topics de trigger con valores anómalos)
- STM32 GPIO PA0 (botón físico) → micro-ROS → `/emergency_button`
- Wi-Fi HTTP POST → contacto de emergencia configurado en `pacientes`
- `medical_db.registrar_alerta()` — tipo + valores + timestamp + acción tomada

---

#### Estado 16: ERROR

**Descripción:** Error del sistema. No es urgencia médica. El robot intenta auto-recovery. Código de error legible en pantalla con acción sugerida al operador. No debe ser alarmante visualmente.

| Elemento | Detalle |
|----------|---------|
| **Visual cara** | Ojos en `"×"` color ámbar / código de error legible: p.ej. `ERR_DISPENSER_TIMEOUT` / `"Reiniciando módulo medication_node..."` / barra de progreso de recovery |
| **Tono visual** | Ámbar — no rojo — para no alarmar al usuario. El error es técnico, no médico |

**Entradas:**
- `THINKING` → API timeout total sin fallback disponible (todos los niveles agotados)
- `MOVING` → Nav2 path failure (path planner no encuentra ruta)
- `DISPENSING` → fallo mecánico del carrusel o timeout
- `MEASURING` → sensor MAX30102 no responde en 30 s

**Salidas:**
- → `IDLE`: error resuelto por auto-recovery exitoso
- → `ALERT`: error crítico que compromete la seguridad del usuario

**Nodos ROS2 / Sistemas:**
- `state_machine_node` (recovery logic — reintentos por módulo)
- `/rosout` (logging centralizado de errores)
- `atlas_ros2_node` (TTS descripción del error si `severity = alta`)

---

## 5. MAPA DE TRANSICIONES

### Tabla de Transiciones Completa

| Estado origen | Condición / trigger | Estado destino |
|---------------|---------------------|----------------|
| IDLE | Wake word "Atlas" (Porcupine) | WAKE |
| IDLE | `scheduler_node` dispara horario | REMINDER |
| IDLE | Botón trackpad / comando voz | DASHBOARD |
| WAKE | Timer 1.2 s completado | LISTENING |
| LISTENING | `SPEECH_END` (VAD) | THINKING |
| LISTENING | `COMMAND_DETECTED` (Vosk local) | SPEAKING |
| LISTENING | Timeout 10 s sin voz | IDLE |
| THINKING | Respuesta LLM lista | SPEAKING |
| THINKING | Intent = dispensar + usuario confirmado | DISPENSING |
| THINKING | Intent = medir | MEASURING |
| THINKING | Intent = ver panel | DASHBOARD |
| THINKING | Timeout 15 s / fallo API total | ERROR |
| SPEAKING | Terminó con pregunta abierta | LISTENING |
| SPEAKING | Monólogo terminado | IDLE |
| SPEAKING | Instrucción dispensar confirmada | DISPENSING |
| SPEAKING | Instrucción "apoya el dedo" dada | MEASURING |
| MOVING | Llegó sin usuario / path OK | SEARCHING |
| MOVING | Persona detectada en trayecto | APPROACHING |
| MOVING | Llegó a base sin misión | IDLE |
| MOVING | Nav2 falla | ERROR |
| SEARCHING | `/person/detected = true` | APPROACHING |
| SEARCHING | Timeout 120 s | IDLE |
| SEARCHING | Timeout crítico REMINDER >60 min | ALERT |
| APPROACHING | `/patient/identified` ≥ umbral | GREETING |
| APPROACHING | En rango, no reconoció | SPEAKING |
| APPROACHING | Persona perdida de vista 8 s | SEARCHING |
| GREETING | REMINDER activo para usuario | DISPENSING |
| GREETING | Medición urgente programada | MEASURING |
| GREETING | Sin misión pendiente | SPEAKING |
| DISPENSING | Load cell confirma dispensación | SUCCESS |
| DISPENSING | Fallo mecánico / timeout | ERROR |
| DISPENSING | Peso incorrecto post-dispensación | ALERT |
| MEASURING | Todos los valores registrados | SUCCESS |
| MEASURING | Valor fuera de rango | ALERT |
| MEASURING | Sensor no responde 30 s | ERROR |
| REMINDER | Inmediato tras activación | SEARCHING |
| REMINDER | Timeout >60 min sin entrega | ALERT |
| SUCCESS | Timer 3 s completado | IDLE |
| SUCCESS | Usuario toca trackpad | DASHBOARD |
| SUCCESS | Follow-up verbal necesario | SPEAKING |
| DASHBOARD | Timeout 60 s sin interacción | IDLE |
| DASHBOARD | Sin persona en ultrasónico 10 s | IDLE |
| DASHBOARD | Wake word "Atlas" | LISTENING |
| DASHBOARD | Botón "Medir ahora" | MEASURING |
| ALERT | Cancelada antes del countdown | IDLE |
| ALERT | Notificación enviada | IDLE |
| ERROR | Auto-recovery exitoso | IDLE |
| ERROR | Error crítico de seguridad | ALERT |

### Reglas Generales de Transición

```
1. Wake word "Atlas" tiene prioridad global — activa WAKE desde cualquier estado
   excepto: DISPENSING (🔒), ALERT (la alerta no se interrumpe por voz)

2. GPIO PA0 (botón emergencia) tiene máxima prioridad global — activa ALERT
   desde cualquier estado, incluyendo DISPENSING y MEASURING

3. Los estados 🔒 (DISPENSING) bloquean /cmd_vel — Nav2 no puede moverlo

4. Porcupine corre 24/7 en background, independientemente del estado HMI activo

5. scheduler_node hace poll cada 30 s — solo dispara REMINDER desde IDLE
   (no interrumpe conversaciones activas o tareas médicas en curso)
```

---

## 6. FLUJOS PRINCIPALES DE USO

### Flujo 1 — Conversación Pura (más frecuente)

```
IDLE → WAKE → LISTENING → THINKING → SPEAKING → IDLE
```

Subsistemas involucrados: `atlas_ros2_node` + `medical_db`. Sin hardware de robot activo.  
Latencia total: ~1.6–2.5 s desde fin del habla hasta respuesta audible.

---

### Flujo 2 — Misión de Medicación (flujo más completo)

```
IDLE → REMINDER → SEARCHING → APPROACHING → GREETING → DISPENSING → SUCCESS → IDLE
```

Subsistemas involucrados: `scheduler_node` → Nav2 → `person_detector_node` → `face_recognition_node` → `medication_node` → HX711 → `medical_db`.  
Toca absolutamente todos los subsistemas del robot. Es el flujo de validación integral del sistema.

---

### Flujo 3 — Medición de Signos Vitales por Comando

```
IDLE → WAKE → LISTENING → THINKING → SPEAKING → MEASURING → SUCCESS → IDLE
                                                                  ↓
                                                               ALERT (si valores anómalos)
```

Subsistemas involucrados: `atlas_ros2_node` → `vital_signs_node` (ESP32 Médica) → `medical_db`.  
Bifurcación crítica en MEASURING: valores normales → SUCCESS; cualquier valor fuera de rango → ALERT.

---

### Flujo 4 — Dashboard con Cierre Automático por Privacidad

```
(cualquier estado) → DASHBOARD → IDLE
                         ↓
                    LISTENING (si wake word activo)
                         ↓
                    MEASURING (botón "Medir ahora")
```

El DASHBOARD tiene dos mecanismos de cierre automático independientes que corren en paralelo:
1. **Timeout de interacción:** 60 s sin que el usuario toque el trackpad → IDLE
2. **Ausencia de persona:** `/ultrasonic/front` sin detección durante 10 s → IDLE

Ambos protegen la privacidad de los datos de salud si el usuario se aleja de la pantalla.

---

### Flujo 5 — Emergencia por Botón Físico

```
(cualquier estado) → ALERT[EMERGENCY] → SPEAKING → IDLE
```

GPIO PA0 del STM32 tiene **máxima prioridad global** — interrumpe cualquier estado activo,
incluyendo DISPENSING y MEASURING. Countdown reducido a 5 s. No cancelable por voz.

---

## 7. DISEÑO VISUAL — CARA BAYMAX

### Filosofía Visual

La cara de Baymax tiene cuatro reglas inquebrantables:

1. **Fondo siempre negro `#000000`** — no cambia en ningún estado. El negro total hace que los ojos "floten" en la pantalla y es no intrusivo en entornos nocturnos domésticos.
2. **Sin texto en la cara durante estados conversacionales** — los ojos comunican todo. El texto solo aparece en estados de tarea (DISPENSING, MEASURING) o como indicador muy sutil en LISTENING.
3. **Los ojos son el único elemento que cambia color** — nada más. Consistencia visual extrema.
4. **Todas las transiciones de estado duran exactamente 300 ms** — `easeInOutCubic`. Sin excepciones. Esto hace que el robot se sienta "vivo" sin ser errático.

---

### Sistema de Coordenadas Canvas

```
Resolución objetivo: 1366 × 768 px (pantalla Samsung laptop en kiosko)
Centro canvas: (683, 384)

Ojo izquierdo:
  Centro:    (503, 350)
  Ancho:     180 px  (eje X)
  Alto:      90 px   (eje Y)
  rx normal: 90      ry normal: 45

Ojo derecho:
  Centro:    (863, 350)
  Ancho:     180 px
  Alto:      90 px

Distancia entre centros: 360 px
Zona boca (SPEAKING):    y = 480–530, centrado en x = 683, ancho = 400 px
Zona texto sutil:        y = 680–710, centrado en x = 683
```

> **Nota de escalado:** Todos los valores están normalizados para 1366×768.
> En `baymax_face.js`, usar `canvas.width / 1366` como factor de escala para soportar
> otras resoluciones sin refactorizar coordenadas.

---

### Paleta de Color por Estado

| Estado | Color ojos | Hex | Notas |
|--------|-----------|-----|-------|
| IDLE | Blanco | `#FFFFFF` | Brillo base |
| WAKE | Blanco → destello | `#FFFFFF` → `#FFFFEE` | Flash en transición |
| LISTENING | Azul | `#378ADD` | Mismo azul que paleta ROS2 |
| THINKING | Ámbar | `#BA7517` | "Luz cálida" de concentración |
| SPEAKING | Blanco brillante | `#FFFFFF` + glow | Ligeramente mayor que IDLE |
| MOVING | Blanco | `#FFFFFF` | Pupila desplazada hacia adelante |
| SEARCHING | Blanco | `#FFFFFF` | Ojos en movimiento lateral |
| APPROACHING | Blanco | `#FFFFFF` | Ojos agrandados |
| GREETING | Verde → blanco | `#1D9E75` → `#FFFFFF` | Flash verde, luego medias lunas |
| DISPENSING | Ámbar concentrado | `#BA7517` | Igual que THINKING pero ojos normales |
| MEASURING | Azul sereno | `#378ADD` | Igual que LISTENING pero sin halo |
| REMINDER | Teal | `#1D9E75` | Misión activa |
| SUCCESS | Blanco (medias lunas) | `#FFFFFF` | Forma cambia a media luna |
| DASHBOARD | N/A | — | Mini-cara — ver sección DASHBOARD |
| ALERT | Rojo | `#E24B4A` | Único uso del rojo en la cara |
| ERROR | Ámbar + forma × | `#BA7517` | Forma cambia a × |

---

### Especificaciones de Animación por Estado

#### IDLE — Parpadeo y Respiración

```javascript
// Parpadeo: aleatorio cada 3000–6000 ms
// Duración del parpadeo: 150 ms cerrar + 150 ms abrir
// Implementación: escalar ry de 45 → 2 → 45

blinkAnimation = {
  duration: 300,          // ms total
  closeTime: 150,         // ms hasta ry=2
  easing: 'easeInOutCubic',
  interval: random(3000, 6000)
}

// Micro-respiración: loop continuo
// Toda la cara (ambos ojos) escala entre 1.0 y 1.02
breathAnimation = {
  scale: { min: 1.0, max: 1.02 },
  duration: 4000,          // ms por ciclo completo
  easing: 'easeInOutSine'  // suave, orgánico
}
```

#### WAKE — Apertura con Bloom

```javascript
// Fase 1 (0–400 ms): ojos abren desde ry=2 a ry=55 (overshoot)
// Fase 2 (400–600 ms): retroceden de ry=55 a ry=45 (settle)
// Simultáneo: ondas de sonar — 3 anillos expansivos desde el centro
// Simultáneo: flash blanco — opacidad overlay 0→0.4→0 en 300 ms

wakeAnimation = {
  eyeOpen: { from: 2, overshoot: 55, settle: 45, duration: 600 },
  sonarRings: { count: 3, delay: 100, maxRadius: 300, duration: 800 },
  flash: { peakOpacity: 0.4, duration: 300 }
}
```

#### LISTENING — Halo Reactivo al Micrófono

```javascript
// El halo es un anillo alrededor de cada ojo
// Su radio exterior varía con la amplitud del micrófono (0.0–1.0 normalizada)
// Radio base del halo: eyeRy + 15 px
// Radio máximo del halo: eyeRy + 45 px
// Suavizado: exponential moving average α=0.3 para evitar jitter

haloRadius = baseRadius + (amplitude * 30)  // px adicionales
haloOpacity = 0.3 + (amplitude * 0.5)       // 0.3 en silencio → 0.8 con voz fuerte
haloColor = '#378ADD'
haloLineWidth = 2  // px
```

#### THINKING — Puntos Orbitantes

```javascript
// 3 puntos orbitan alrededor del centro de la cara (683, 384)
// Radio de órbita: 220 px desde el centro
// Velocidad angular: 0.8 rad/s (una vuelta cada ~7.8 s)
// Los puntos están separados 120° entre sí
// Tamaño de cada punto: radio 8 px
// Opacidad: el punto "líder" 1.0, los otros 0.6 y 0.3

// Desplazamiento de mirada: ambos ojos se mueven
// dx = -20 px (izquierda), dy = -15 px (arriba)
// Transición: 300 ms easeInOutCubic al entrar/salir del estado

thinkingDots = {
  count: 3,
  orbitRadius: 220,
  angularVelocity: 0.8,    // rad/s
  dotRadius: 8,
  opacities: [1.0, 0.6, 0.3]
}
gazeOffset = { dx: -20, dy: -15 }
```

#### SPEAKING — Onda de Boca Sincronizada

```javascript
// La boca es una onda senoidal dibujada en Canvas con lineTo
// Parámetros base (silencio):
//   amplitude: 0 px  →  línea recta horizontal
// Parámetros con voz:
//   amplitude: audioLevel * 60 px  (máximo 60 px)
//   frequency: 2 ciclos en el ancho total de la boca (400 px)
//   phase: avanza a 3 rad/s (movimiento de onda)

// Suavizado: EMA α=0.4 sobre audioLevel para transiciones suaves
// Color línea: #FFFFFF, lineWidth: 4 px, lineCap: 'round'

mouthWave = {
  x: 483, y: 505,          // esquina izquierda
  width: 400,              // px
  baseAmplitude: 0,
  maxAmplitude: 60,        // px
  frequency: 2,            // ciclos en el ancho
  phaseSpeed: 3.0,         // rad/s
  smoothingAlpha: 0.4
}
```

#### GREETING / SUCCESS — Medias Lunas

```javascript
// Los ojos elipse se transforman en arcos (medias lunas)
// Implementación: cambiar de drawEllipse() a drawArc()
// Arco: desde Math.PI a 0 (semicírculo inferior = sonrisa)
// La transición morph dura 300 ms interpolando entre las dos formas

// Para SUCCESS además: checkmark SVG animado
// El checkmark se "dibuja" incrementalmente en 600 ms
// Posición: centro de pantalla, entre los ojos y la zona boca
// Tamaño: 80×60 px
// Color: #1D9E75 (verde)
// StrokeWidth: 5 px, lineCap: 'round'
```

#### SEARCHING — Ojos en Movimiento Lateral

```javascript
// Ambos ojos se desplazan en X en loop sinusoidal
// Rango de desplazamiento: ±40 px desde posición base
// Período: 3 s por ciclo completo (ida y vuelta)
// Easing: easeInOutSine (movimiento orgánico, no mecánico)

// Overlay: línea de scan horizontal
// y varía de 200 a 560 px (zona facial) a 0.5 px/ms
// Color: #FFFFFF, opacidad: 0.15, lineWidth: 1.5 px

searchGaze = {
  amplitude: 40,           // px desplazamiento máximo
  period: 3000,            // ms por ciclo
  easing: 'easeInOutSine'
}
```

#### ALERT — Ojos Parpadeantes Rojos

```javascript
// Los ojos cambian a rojo #E24B4A
// Parpadeo de alerta: rápido e involuntario
//   encendido 400 ms → apagado 200 ms → encendido 400 ms → ...
// El fondo de la pantalla cambia a rojo muy oscuro con pulso
//   background oscila entre #0D0000 y #1A0000 a 1 Hz

alertBlink = {
  onDuration: 400,         // ms encendido
  offDuration: 200,        // ms apagado
  eyeColor: '#E24B4A'
}
backgroundPulse = {
  min: '#000000',
  max: '#1A0000',
  frequency: 1.0           // Hz
}
```

#### ERROR — Ojos en ×

```javascript
// Los ojos elipse se reemplazan por dos líneas cruzadas (×)
// Cada × se dibuja con dos lineTo de 60 px de largo, centradas en la posición del ojo
// Color: #BA7517 (ámbar — no rojo para no alarmar)
// StrokeWidth: 6 px, lineCap: 'round'
// Los × tienen una animación de "aparición" en 200 ms (escala 0 → 1)
```

---

### Estructura del Archivo `baymax_face.js`

```javascript
// baymax_face.js — estructura de clases

class BaymaxFace {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = 'IDLE';
    this.audioLevel = 0.0;      // 0.0–1.0, actualizado por WebSocket
    this.micLevel  = 0.0;       // 0.0–1.0, amplitud del micrófono
    this.scale = canvas.width / 1366;
    this.eyes = {
      left:  { x: 503, y: 350, rx: 90, ry: 45 },
      right: { x: 863, y: 350, rx: 90, ry: 45 }
    };
    this.animationFrame = null;
    this.stateParams = {};       // parámetros interpolados del estado actual
  }

  setState(newState, params = {}) {
    // Transición de 300 ms easeInOutCubic entre estado anterior y nuevo
    this.previousState = this.state;
    this.state = newState;
    this.transitionProgress = 0;
    this.stateParams = params;
  }

  setAudioLevel(level) {
    // EMA suavizado — llamado desde WebSocket /ws/audio
    this.audioLevel = this.audioLevel * 0.6 + level * 0.4;
  }

  setMicLevel(level) {
    this.micLevel = this.micLevel * 0.7 + level * 0.3;
  }

  draw(timestamp) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    this._applyScale();
    this._drawBackground();  // estado ALERT modifica el fondo
    this._drawEyes();
    this._drawMouth();       // solo en SPEAKING
    this._drawOverlay();     // elementos específicos por estado
    this._drawSubtleText();  // solo en LISTENING
    this.animationFrame = requestAnimationFrame((ts) => this.draw(ts));
  }

  // Métodos internos: _drawEyes(), _drawMouth(), _drawHalo(),
  // _drawThinkingDots(), _drawScanLine(), _drawCheckmark(),
  // _drawSonarRings(), _easeInOutCubic(t), _lerp(a, b, t)
}

// Inicialización en index.html
const face = new BaymaxFace(document.getElementById('baymax-canvas'));
face.draw(0);

// Recibir cambios de estado desde el backend
stateSocket.onmessage = (e) => {
  const { state, params } = JSON.parse(e.data);
  face.setState(state, params);
};

// Recibir nivel de audio para la boca
audioSocket.onmessage = (e) => {
  const { level, source } = JSON.parse(e.data);
  if (source === 'tts')  face.setAudioLevel(level);
  if (source === 'mic')  face.setMicLevel(level);
};
```

---

## 8. INTEGRACIÓN CON ROS2 Y SISTEMAS BACKEND

### Arquitectura FastAPI ↔ ROS2

```
ROS2 Graph
  /atlas/detected_command  →┐
  /atlas/listening         →│
  /robot/speak             →│  ros2_bridge.py
  /health/bpm              →│  (hilo rclpy separado,
  /health/spo2             →│   thread-safe con asyncio)
  /health/temperature      →│
  /patient/identified      →│
  /ultrasonic/front        →┘
        ↕
  FastAPI (uvicorn, asyncio event loop)
        ↕
  WebSocket /ws/state   → state_machine.js → BaymaxFace.setState()
  WebSocket /ws/audio   → baymax_face.js   → BaymaxFace.setAudioLevel()
  REST GET /api/patient → dashboard.js     → DOM update
```

### Archivo `ros2_bridge.py`

```python
# ros2_bridge.py — suscriptor/publicador ROS2 en hilo separado
# Se comunica con FastAPI mediante asyncio.Queue thread-safe

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool, Int32, Float32
import asyncio
import threading

class HMIBridgeNode(Node):
    def __init__(self, state_queue: asyncio.Queue, audio_queue: asyncio.Queue):
        super().__init__('hmi_bridge_node')
        self.state_queue = state_queue
        self.audio_queue = audio_queue

        # Suscripciones
        self.create_subscription(String, '/atlas/detected_command',
                                 self._on_command, 10)
        self.create_subscription(Bool, '/atlas/listening',
                                 self._on_listening, 10)
        self.create_subscription(String, '/robot/speak',
                                 self._on_speak, 10)
        self.create_subscription(Int32, '/health/bpm',
                                 self._on_bpm, 10)
        self.create_subscription(Int32, '/health/spo2',
                                 self._on_spo2, 10)
        self.create_subscription(Float32, '/health/temperature',
                                 self._on_temp, 10)
        self.create_subscription(String, '/patient/identified',
                                 self._on_patient, 10)
        self.create_subscription(String, '/hmi/set_state',
                                 self._on_set_state, 10)

        # Publicaciones
        self.hmi_action_pub = self.create_publisher(String, '/hmi/action', 10)

    def _push_state(self, state: str, params: dict = {}):
        """Thread-safe: empuja un cambio de estado al event loop de FastAPI."""
        import json
        asyncio.run_coroutine_threadsafe(
            self.state_queue.put(json.dumps({'state': state, 'params': params})),
            self._loop
        )

    def _on_set_state(self, msg: String):
        self._push_state(msg.data)

    def _on_listening(self, msg: Bool):
        if msg.data:
            self._push_state('LISTENING')

    def _on_speak(self, msg: String):
        self._push_state('SPEAKING', {'text': msg.data})

    def _on_patient(self, msg: String):
        self._push_state('GREETING', {'patient_id': msg.data})

    def _on_bpm(self, msg: Int32):
        asyncio.run_coroutine_threadsafe(
            self.state_queue.put(
                __import__('json').dumps({'type': 'health', 'bpm': msg.data})
            ), self._loop
        )

    # _on_spo2, _on_temp: análogo a _on_bpm

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop


def run_ros2_bridge(state_queue, audio_queue, loop):
    """Lanzar en threading.Thread separado."""
    rclpy.init()
    node = HMIBridgeNode(state_queue, audio_queue)
    node.set_loop(loop)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
```

### Archivo `server.py` — FastAPI App

```python
# server.py — entrypoint FastAPI

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import threading
import json

from ros2_bridge import run_ros2_bridge
from audio_level import AudioLevelStreamer
from routers import dashboard

app = FastAPI()
app.include_router(dashboard.router, prefix='/api')
app.mount('/static', StaticFiles(directory='static'), name='static')

state_queue: asyncio.Queue = asyncio.Queue()
audio_queue: asyncio.Queue = asyncio.Queue()

@app.on_event('startup')
async def startup():
    loop = asyncio.get_event_loop()
    # Hilo ROS2
    threading.Thread(
        target=run_ros2_bridge,
        args=(state_queue, audio_queue, loop),
        daemon=True
    ).start()
    # Hilo nivel de audio TTS
    threading.Thread(
        target=AudioLevelStreamer(audio_queue, loop).run,
        daemon=True
    ).start()

@app.get('/')
async def index():
    return FileResponse('static/index.html')

@app.websocket('/ws/state')
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await state_queue.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass

@app.websocket('/ws/audio')
async def ws_audio(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await audio_queue.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
```

### Archivo `audio_level.py` — Stream de Amplitud

```python
# audio_level.py — captura RMS del buffer sounddevice y lo publica
# Frecuencia de muestreo: 50 Hz (cada 20 ms)
# Esto alimenta la animación de la boca en SPEAKING

import sounddevice as sd
import numpy as np
import asyncio
import json
import time

class AudioLevelStreamer:
    """
    Captura el nivel RMS del stream de audio de salida (TTS)
    y lo empuja a audio_queue para el WebSocket /ws/audio.

    Requiere que sounddevice esté usando el mismo device que Azure TTS.
    El nivel se normaliza a 0.0–1.0 con clipping en el percentil 95.
    """
    SAMPLE_RATE = 16000
    CHUNK_SIZE  = 320        # 20 ms a 16 kHz
    MAX_RMS     = 3000.0     # valor RMS de referencia para normalización

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop  = loop

    def run(self):
        def callback(indata, frames, time_info, status):
            rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            level = min(rms / self.MAX_RMS, 1.0)
            msg = json.dumps({'level': round(level, 3), 'source': 'tts'})
            asyncio.run_coroutine_threadsafe(
                self.queue.put(msg), self.loop
            )

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype='int16',
            blocksize=self.CHUNK_SIZE,
            callback=callback
        ):
            while True:
                time.sleep(0.1)
```

> **Nota:** `audio_level.py` captura el loopback del audio de salida, no el micrófono.
> En Ubuntu 22.04 esto requiere configurar PulseAudio con un monitor source:
> ```bash
> pactl load-module module-loopback latency_msec=1
> # O usar el monitor del sink por defecto como input device en sounddevice
> ```

### Archivo `routers/dashboard.py` — Endpoints REST

```python
# routers/dashboard.py

from fastapi import APIRouter
from ..medical_db import MedicalDB   # reutiliza el módulo existente de Atlas

router = APIRouter()
db = MedicalDB()

@router.get('/patient/{patient_id}/summary')
async def get_patient_summary(patient_id: int):
    """Resumen completo para el dashboard — una sola llamada."""
    return {
        'patient':      db.get_paciente(patient_id),
        'vitals':       db.get_ultimo_registro_signos(patient_id),
        'next_dose':    db.get_proxima_dosis(patient_id),
        'dispensations': db.get_historial_dispensacion(patient_id, limit=5)
    }

@router.get('/patient/{patient_id}/vitals')
async def get_vitals(patient_id: int, limit: int = 10):
    return db.get_historial_signos_vitales(patient_id, limit=limit)

@router.get('/patient/{patient_id}/medications')
async def get_medications(patient_id: int):
    return db.get_medicamentos_activos(patient_id)
```

### Topics ROS2 del Módulo HMI

| Topic | Tipo | Dirección | Descripción |
|-------|------|-----------|-------------|
| `/hmi/set_state` | `std_msgs/String` | → HMI | Fuerza cambio de estado desde `state_machine_node` |
| `/hmi/action` | `std_msgs/String` | HMI → | Acción del usuario desde el dashboard (p.ej. `"measure_now"`) |
| `/hmi/active` | `std_msgs/Bool` | → HMI | El HMI está corriendo y conectado |
| `/atlas/listening` | `std_msgs/Bool` | → HMI | Atlas en escucha activa → LISTENING |
| `/robot/speak` | `std_msgs/String` | → HMI | Texto que Atlas va a decir → SPEAKING |
| `/patient/identified` | `std_msgs/String` | → HMI | ID del paciente reconocido → GREETING |
| `/health/bpm` | `std_msgs/Int32` | → HMI | BPM en tiempo real durante MEASURING |
| `/health/spo2` | `std_msgs/Int32` | → HMI | SpO₂ en tiempo real durante MEASURING |
| `/health/temperature` | `std_msgs/Float32` | → HMI | Temperatura en tiempo real durante MEASURING |
| `/scheduler/reminder` | `std_msgs/String` | → HMI | JSON con datos de la misión activa → REMINDER |
| `/ultrasonic/front` | `std_msgs/Float32` | → HMI | Distancia frontal → timeout privacidad DASHBOARD |

### FSM del Frontend (`state_machine.js`)

```javascript
// state_machine.js — espejo del state_machine_node en el frontend
// Gestiona qué elementos del DOM son visibles en cada estado

const STATE_CONFIG = {
  IDLE:       { canvas: true,  dashboard: false, overlay: null         },
  WAKE:       { canvas: true,  dashboard: false, overlay: null         },
  LISTENING:  { canvas: true,  dashboard: false, overlay: 'listening'  },
  THINKING:   { canvas: true,  dashboard: false, overlay: null         },
  SPEAKING:   { canvas: true,  dashboard: false, overlay: null         },
  MOVING:     { canvas: true,  dashboard: false, overlay: 'moving'     },
  SEARCHING:  { canvas: true,  dashboard: false, overlay: 'searching'  },
  APPROACHING:{ canvas: true,  dashboard: false, overlay: null         },
  GREETING:   { canvas: true,  dashboard: false, overlay: 'greeting'   },
  DISPENSING: { canvas: true,  dashboard: false, overlay: 'dispensing' },
  MEASURING:  { canvas: true,  dashboard: false, overlay: 'measuring'  },
  REMINDER:   { canvas: true,  dashboard: false, overlay: 'reminder'   },
  SUCCESS:    { canvas: true,  dashboard: false, overlay: 'success'    },
  DASHBOARD:  { canvas: false, dashboard: true,  overlay: null         },
  ALERT:      { canvas: true,  dashboard: false, overlay: 'alert'      },
  ERROR:      { canvas: true,  dashboard: false, overlay: 'error'      }
};

class StateMachine {
  constructor(face) {
    this.face = face;
    this.current = 'IDLE';
    this.socket = new WebSocket('ws://localhost:8000/ws/state');
    this.socket.onmessage = (e) => this.transition(JSON.parse(e.data));
  }

  transition({ state, params }) {
    if (state === this.current) return;
    const config = STATE_CONFIG[state];
    if (!config) return console.warn(`Estado desconocido: ${state}`);
    this.current = state;
    this.face.setState(state, params);
    document.getElementById('baymax-canvas').style.display =
      config.canvas ? 'block' : 'none';
    document.getElementById('dashboard-panel').style.display =
      config.dashboard ? 'flex' : 'none';
    this._updateOverlay(config.overlay, params);
  }

  _updateOverlay(overlayId, params) {
    document.querySelectorAll('.state-overlay').forEach(el => {
      el.style.display = 'none';
    });
    if (overlayId) {
      const el = document.getElementById(`overlay-${overlayId}`);
      if (el) {
        el.style.display = 'flex';
        this._populateOverlay(overlayId, params);
      }
    }
  }

  _populateOverlay(id, params) {
    // Inyecta datos dinámicos en cada overlay
    // p.ej. overlay-dispensing muestra params.medication_name, params.dose
    // overlay-greeting muestra params.patient_name
    // overlay-reminder muestra params.medication_name con urgencia
  }
}
```

---

## 9. INTERACCIÓN FÍSICA — TRACKPAD

### Hardware

- **Dispositivo:** Samsung laptop con trackpad integrado, cableado al Dell Inspiron por USB
- **Montaje:** Pecho del robot — Linda/Sergio deben incluir recorte en el diseño CAD de la carcasa
- **Cable:** USB-A a USB-A, ruteado por el interior del cuello del robot
- **Modo de uso:** El Samsung opera como dispositivo de entrada externo únicamente (trackpad + teclado opcional durante desarrollo)

### Comportamiento por Estado

| Estado | Comportamiento del trackpad |
|--------|-----------------------------|
| IDLE | Cualquier toque → DASHBOARD |
| DASHBOARD | Navegación normal entre cards y botones |
| LISTENING | Toque → cancela escucha → IDLE |
| SPEAKING | Toque → interrumpe reproducción → IDLE |
| DISPENSING 🔒 | **Deshabilitado** — toque ignorado |
| MEASURING | Toque → cancela medición → IDLE |
| ALERT | Solo el botón "Cancelar — estoy bien" es activo |
| Resto de estados | Toque → DASHBOARD si hay usuario identificado, si no → IDLE |

### Botones del Dashboard

Los botones del dashboard están optimizados para uso con trackpad (no pantalla táctil):

```css
/* Tamaño mínimo para uso cómodo con trackpad */
.dashboard-btn {
  min-width: 200px;
  min-height: 64px;
  font-size: 18px;
  border-radius: var(--border-radius-lg);
  cursor: pointer;
  /* Sin hover states complejos — el trackpad puede hacer hover accidental */
}
```

| Botón | Acción | Topic publicado |
|-------|--------|-----------------|
| `"Medir ahora"` | → MEASURING | `/hmi/action: "measure_now"` |
| `"Ver historial"` | Expande panel de historial (in-page) | — |
| `"Volver"` | → IDLE | `/hmi/action: "go_idle"` |
| `"Dar medicamento"` | Solicita confirmación vocal → DISPENSING | `/hmi/action: "dispense_request"` |

### Prevención de Activaciones Accidentales

El botón `"Dar medicamento"` requiere confirmación de dos pasos antes de activar DISPENSING:

```
1. Click en botón → aparece confirmación: "¿Confirmar dispensación de [medicamento]?"
                    Botones: "Sí, dar" / "Cancelar"
2. Click en "Sí, dar" → Atlas pide confirmación verbal: "¿Confirmas que quieres [medicamento]?"
3. Respuesta afirmativa por voz → DISPENSING activado
```

Este triple-lock (click → click → voz) previene dispensaciones accidentales por
contacto involuntario con el trackpad.

---

## 10. ESTADO ACTUAL Y PENDIENTES

> **Última actualización:** 2026-03-16

### Resumen

| Componente | Estado | Detalle |
|------------|--------|---------|
| Decisión tecnológica | ✅ Cerrada | FastAPI + Chromium kiosk — 2026-03-16 |
| 16 estados definidos | ✅ Completo | Visual, entradas, salidas y nodos para cada estado |
| Mapa de transiciones | ✅ Completo | Tabla completa + reglas generales |
| Arquitectura FastAPI | ✅ Diseñada | `server.py`, `ros2_bridge.py`, `audio_level.py` definidos |
| Especificaciones Canvas | ✅ Diseñadas | Coordenadas, colores, animaciones por estado |
| `baymax_face.js` | ❌ Pendiente | Implementar clase `BaymaxFace` con todos los estados |
| `state_machine.js` | ❌ Pendiente | Implementar FSM frontend + overlays |
| `dashboard.js` | ❌ Pendiente | Panel de datos + actualización via REST |
| `server.py` | ❌ Pendiente | FastAPI app completa con WebSockets |
| `ros2_bridge.py` | ❌ Pendiente | Hilo rclpy + asyncio queues |
| `audio_level.py` | ❌ Pendiente | Stream RMS sounddevice → WS |
| `routers/dashboard.py` | ❌ Pendiente | Endpoints REST (reutiliza `medical_db.py`) |
| `index.html` | ❌ Pendiente | Layout kiosk + Canvas + overlays + dashboard |
| Configuración PulseAudio | ❌ Pendiente | Monitor source para loopback audio TTS |
| Pruebas en Ubuntu 22.04 | ❌ Pendiente | Verificar RAM con todos los nodos activos |
| Integración en `bringup.launch.py` | ❌ Pendiente | Launch del HMI como nodo ROS2 |

### Orden de Implementación Recomendado

```
1. index.html skeleton + baymax_face.js (IDLE + SPEAKING)
   → Validar cara y animación de boca en navegador standalone

2. server.py + WebSocket /ws/state mock
   → Poder cambiar estado desde terminal sin ROS2

3. state_machine.js + overlays básicos
   → Transiciones visuales funcionando

4. ros2_bridge.py
   → Conectar con ROS2 real (requiere robot armado para estados de movilidad)

5. audio_level.py + WebSocket /ws/audio
   → Sincronización de boca con TTS (el más complejo de calibrar)

6. routers/dashboard.py + dashboard.js
   → Panel de datos con BD real

7. Todos los overlays de estado (DISPENSING, MEASURING, ALERT, etc.)
   → Requiere hardware médico funcional para probar

8. Integración launch + pruebas de RAM simultáneas
   → Fase final, con robot físico armado
```

### Dependencias Bloqueantes

| Tarea HMI | Bloqueada por |
|-----------|---------------|
| Overlays MOVING, SEARCHING, APPROACHING | Nav2 funcionando (robot físico) |
| Overlay DISPENSING | Firmware ESP32 Médica + dispensador físico |
| Overlay MEASURING + valores en tiempo real | Firmware ESP32 Médica + MAX30102 calibrado |
| `audio_level.py` calibración | Pruebas de audio TTS en Ubuntu 22.04 |
| Prueba de RAM total | Robot físico con todos los nodos simultáneos |

Los primeros 4 pasos de implementación (cara + servidor mock + FSM + bridge básico)
son **completamente independientes del hardware** y pueden hacerse ahora.

---

## 11. COMANDOS DE REFERENCIA RÁPIDA

### Desarrollo

```bash
# Lanzar servidor FastAPI en modo desarrollo (hot-reload)
cd ~/Meadlease/atlas/hmi
uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Abrir en navegador normal (durante desarrollo, sin kiosko)
xdg-open http://localhost:8000

# Cambiar estado manualmente para testear animaciones (sin ROS2)
ros2 topic pub /hmi/set_state std_msgs/String "data: 'LISTENING'" --once
ros2 topic pub /hmi/set_state std_msgs/String "data: 'SPEAKING'" --once
ros2 topic pub /hmi/set_state std_msgs/String "data: 'ALERT'" --once

# Simular nivel de audio para testear boca
# (publicar al WS directamente desde Python en modo test)
python3 -c "
import asyncio, websockets, json, math, time
async def test():
    async with websockets.connect('ws://localhost:8000/ws/audio') as ws:
        for i in range(100):
            level = abs(math.sin(i * 0.3)) * 0.8
            await ws.send(json.dumps({'level': round(level,3), 'source': 'tts'}))
            await asyncio.sleep(0.05)
asyncio.run(test())
"
```

### Producción (Robot Físico)

```bash
# Lanzar Chromium en modo kiosko
chromium-browser \
  --kiosk \
  --app=http://localhost:8000 \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --disable-translate \
  --no-default-browser-check

# Salir del kiosko durante desarrollo
# Ctrl+W o Alt+F4

# Configurar monitor de audio PulseAudio para loopback TTS
pactl list short sources | grep monitor    # encontrar el monitor source
# Resultado esperado: "alsa_output.pci-XXXX.analog-stereo.monitor"
# Usar ese nombre como device en AudioLevelStreamer

# Verificar RAM con todos los nodos activos
free -h
# Esperado con todos corriendo:
#   ROS2 base:      ~500 MB
#   RTAB-Map:      ~3-4 GB
#   kinect2_bridge: ~200 MB
#   atlas_ros2_node: ~300 MB
#   Chromium:       ~300 MB
#   Total estimado: ~5-6 GB de 12 GB disponibles
```

### Debugging

```bash
# Ver logs del servidor FastAPI
uvicorn server:app --host 127.0.0.1 --port 8000 --log-level debug

# Ver mensajes WebSocket en tiempo real (Chrome DevTools)
# F12 → Network → WS → /ws/state o /ws/audio → Messages

# Verificar que ros2_bridge recibe topics
ros2 topic echo /hmi/set_state
ros2 topic echo /hmi/action

# Verificar nodo HMI activo
ros2 node list | grep hmi

# Test de overlay DISPENSING (sin hardware)
ros2 topic pub /hmi/set_state std_msgs/String \
  "data: '{\"state\": \"DISPENSING\", \"params\": {\"medication\": \"Metformina\", \"dose\": 2}}'" \
  --once

# Monitor de recursos durante demo
htop   # buscar: uvicorn, chromium-browser, rtabmap, kinect2_bridge
```

### Estructura de Mensajes WebSocket

```javascript
// /ws/state — cambio de estado (FastAPI → frontend)
{
  "state": "SPEAKING",
  "params": {
    "text": "Texto que va a decir Atlas",  // opcional
    "patient_name": "Juan",               // opcional — para GREETING
    "medication": "Metformina",           // opcional — para DISPENSING/REMINDER
    "dose": 2,                            // opcional — para DISPENSING/REMINDER
    "severity": "vitals"                  // opcional — para ALERT: "vitals"|"emergency"
  }
}

// /ws/audio — nivel de amplitud (FastAPI → frontend)
{
  "level": 0.742,    // 0.0–1.0 normalizado, EMA aplicado en servidor
  "source": "tts"    // "tts" = salida TTS | "mic" = entrada micrófono
}
```

---

*Para el sistema conversacional Atlas: ver `DOCUMENTACION_CONVERSACIONAL.md`*
*Para arquitectura ROS2, Nav2 y Kinect: ver `DOCUMENTACION_ROS2.md`*
*Para contexto general del proyecto: ver `PROYECTO_GENERAL.md`*