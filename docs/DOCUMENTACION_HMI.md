# INTERFAZ HUMANO-MÁQUINA (HMI)
## Robot Asistente Médico Domiciliario Meadlese

> **Audiencia:** Andrés (líder software)
> **Estado:** Diseño completo · `baymax_face.js` v4.0 implementado (8/16 estados)
> **Tecnología:** FastAPI + Chromium Kiosk + HTML/CSS/JS (Canvas 2D)
> **Plataforma destino:** Ubuntu 22.04 + ROS2 Humble
> **Última actualización:** 2026-03-17

---

## ÍNDICE

1. [Visión General](#1-visión-general)
2. [Decisión Tecnológica](#2-decisión-tecnológica)
3. [Estructura de Archivos](#3-estructura-de-archivos)
4. [Filosofía Visual — Cara Baymax](#4-filosofía-visual--cara-baymax)
5. [Estados del Sistema](#5-estados-del-sistema)
6. [Mapa de Transiciones](#6-mapa-de-transiciones)
7. [Flujos Principales de Uso](#7-flujos-principales-de-uso)
8. [Especificaciones Técnicas — baymax_face.js](#8-especificaciones-técnicas--baymax_facejs)
9. [Integración con ROS2 y Backend](#9-integración-con-ros2-y-backend)
10. [Interacción Física — Trackpad](#10-interacción-física--trackpad)
11. [Estado Actual y Pendientes](#11-estado-actual-y-pendientes)
12. [Comandos de Referencia Rápida](#12-comandos-de-referencia-rápida)

---

## 1. VISIÓN GENERAL

El módulo HMI es la capa de presentación del robot Meadlese. Tiene dos responsabilidades:

1. **Cara expresiva de Baymax** — pantalla de estado permanente. Animaciones que comunican qué está haciendo el robot en cada momento, con la filosofía del personaje original: máxima expresividad con mínimos elementos (dos círculos + una línea).
2. **Dashboard médico** — panel de datos del paciente, accesible por voz o trackpad.

### Principios de Diseño

| Principio | Descripción |
|-----------|-------------|
| **Fiel al personaje** | Dos círculos sólidos negros + línea horizontal. Fondo blanco. Exactamente como Baymax original |
| **Una idea por estado** | Cada estado tiene un solo concepto visual claro, sin efectos apilados |
| **El cuerpo habla** | Las expresiones se comunican con movimiento (nod, shake, lean, bob), no con íconos ni texto |
| **No intrusivo** | Fondo blanco limpio, no compite con el entorno doméstico ni con la carcasa blanca del robot |
| **Reactivo** | Animaciones sincronizadas con audio real (amplitud de micrófono y TTS) |
| **Robusto** | Si el HMI falla, el robot sigue funcionando — es capa de presentación, no de control |

### Hardware de Pantalla

- **Dispositivo:** Samsung laptop (trackpad integrado como entrada)
- **Montaje:** Pecho del robot, cable ruteado por el cuello hacia el Dell
- **Modo:** Chromium en pantalla completa (kiosk mode)
- **Resolución objetivo:** 1366×768 px
- **Nota CAD:** Linda/Sergio deben incluir recorte para trackpad en la carcasa frontal

---

## 2. DECISIÓN TECNOLÓGICA

### Stack: FastAPI + Chromium Kiosk

**Decisión cerrada:** 2026-03-17  
**Alternativa descartada:** PyQt5/6

**Argumento definitivo:** La cara Baymax animada es la feature más visible del proyecto. HTML Canvas 2D con `requestAnimationFrame` permite física de springs, interpolación de color, animaciones por estado y ciclos de iteración de segundos. PyQt requeriría QGraphicsScene y cada cambio implica reiniciar el proceso ROS2.

**Overhead de RAM:** ~200–400 MB de Chromium sobre los ~3–4 GB de RTAB-Map. Con 12 GB disponibles hay margen suficiente. Verificar en pruebas con todos los nodos simultáneos.

### Arquitectura de Capas

```
ROS2 graph ──> FastAPI (Python, proceso separado, mismo PC)
                  |  suscribe a /health/*, /atlas/*, /robot/speak, /patient/*
                  |  publica a /hmi/state, /hmi/action
                  |
                  +-- REST endpoints  (datos dashboard -> BD)
                  +-- WebSocket /ws/state   (cambios de estado -> cara)
                  +-- WebSocket /ws/audio   (nivel de amplitud -> boca/anillo)
                              |
                    Chromium (kiosk, localhost:8000)
                              |
                    index.html + baymax_face.js + state_machine.js
                    + dashboard.js + style.css
```

---

## 3. ESTRUCTURA DE ARCHIVOS

### Ubicación en el Repositorio

```
Meadlease/
+-- hmi/                              <- Módulo HMI (desarrollo standalone aquí)
|   +-- README.md                     [OK] existe
|   +-- requirements.txt              <- pendiente crear
|   +-- .env.example                  <- pendiente (si necesita vars de entorno)
|   +-- server.py                     <- FastAPI entrypoint
|   +-- ros2_bridge.py                <- hilo rclpy thread-safe con asyncio
|   +-- audio_level.py                <- RMS sounddevice -> WebSocket /ws/audio
|   +-- routers/
|   |   +-- dashboard.py              <- REST endpoints (reutiliza medical_db)
|   |   +-- state.py                  <- WebSocket /ws/state
|   +-- static/
|       +-- index.html                <- App HTML única (kiosk layout)
|       +-- baymax_face.js            [OK] v4.0 implementado
|       +-- state_machine.js          <- FSM frontend (16 estados)
|       +-- dashboard.js              <- Panel de datos del paciente
|       +-- style.css                 <- Variables CSS + layout kiosk
|
+-- ros2_ws/src/robot_medical/        <- Al migrar a ROS2, hmi/ se linkea aquí
```

### Por Qué hmi/ en Raíz (No Dentro de atlas/)

El HMI consume topics de todo el sistema ROS2, no solo de Atlas. Si Atlas se cae, el dashboard sigue siendo útil. Si el HMI se cae, Atlas sigue hablando. Son procesos con ciclos de vida independientes.

La migración a ROS2 será trivial: a diferencia de Atlas (que cambió de plataforma Windows→Ubuntu), el HMI usa FastAPI desde el día uno — el mismo servidor que correrá en el robot. Solo se añade `ros2_bridge.py` encima.

---

## 4. FILOSOFÍA VISUAL — CARA BAYMAX

### Modo Claro

- **Fondo:** `#FFFFFF` — blanco puro. No cambia en ningún estado.
- **Ojos:** `#111111` — casi negro. Son lo único que cambia color entre estados.
- **Línea:** `#111111` — misma tinta que los ojos.

El robot físico es blanco. La pantalla blanca se integra con la carcasa en lugar de contrastar con ella.

### Anatomía de la Cara

```
         o-----------------o
      ojo izq    linea   ojo der

Ojos: circulos solidos con sombra sutil de elevacion
Linea: conecta exactamente los centros de los circulos
       (en SPEAKING se convierte en onda de voz)
```

Geometría base a resolución 1366×768:
- Radio de cada ojo: 58 px
- Distancia centro-a-centro: 178 × 2 = 356 px
- Grosor de línea: 4.5 px
- Todo escalado con factor `S = canvas.width / 1366`

### Cuatro Reglas Inquebrantables

1. **El fondo es siempre blanco** — sin excepciones
2. **Sin íconos ni símbolos sobre los ojos** — el movimiento lo dice todo
3. **Una sola idea visual por estado** — no apilar efectos
4. **Todas las transiciones duran 320 ms** con `easeInOutCubic`. Excepción: WAKE→LISTENING dura 480 ms para que el color "se tiña" gradualmente

### Paleta de Color por Estado

| Estado | Color ojos | RGB | Concepto visual |
|--------|-----------|-----|-----------------|
| IDLE | Negro | `(17,17,17)` | Reposo |
| WAKE | Negro | `(17,17,17)` | Activación con movimiento |
| LISTENING | Azul profundo | `(21,101,192)` | Atención activa |
| THINKING | Ámbar vivo | `(205,105,15)` | Concentración |
| SPEAKING | Negro | `(17,17,17)` | Habla con onda |
| MOVING | Negro | `(17,17,17)` | Movimiento neutral |
| SEARCHING | Negro / Teal | `(17,17,17)` / `(13,122,90)` | Búsqueda / Misión activa |
| APPROACHING | Negro | `(17,17,17)` | Análisis con movimiento |
| GREETING | Negro | `(17,17,17)` | Alegría (medias lunas) |
| DISPENSING | Ámbar | `(205,105,15)` | Concentración médica |
| MEASURING | Azul | `(21,101,192)` | Calma médica |
| REMINDER | Teal | `(13,122,90)` | Misión activa |
| SUCCESS | Negro | `(17,17,17)` | Celebración (medias lunas + check) |
| DASHBOARD | N/A | — | Pantalla de datos completa |
| ALERT | Rojo | `(200,30,30)` | Urgencia médica |
| ERROR | Ámbar | `(205,105,15)` | Error técnico (no alarmar) |

---

## 5. ESTADOS DEL SISTEMA

Los estados se organizan en cuatro grupos. Los marcados con [OK] están implementados en `baymax_face.js` v4.0.

---

### Grupo A — Núcleo Conversacional

#### IDLE [OK]

**Concepto:** Cara en reposo pura. Porcupine corre en background 24/7.

**Visual:**
- Parpadeo aleatorio cada 3–7.5 s con posibilidad de doble parpadeo (15% de probabilidad). El cierre usa `easeInQuad` (115 ms), la apertura usa `easeOutCubic` (160 ms).
- Micro-drift sinusoidal muy sutil (±1.5 px, período ~5–6 s) que hace que los ojos "floten" orgánicamente.
- Respiración solo en eje Y de los ojos (±1.5%, período 4.5 s).

**Entradas:** SUCCESS, SPEAKING, DASHBOARD, ERROR, ALERT, SEARCHING  
**Salidas:** → WAKE (wake word), → REMINDER (scheduler), → DASHBOARD (trackpad)  
**Nodos:** `atlas_ros2_node` (Porcupine 24/7), `scheduler_node`, `/ultrasonic/front`

---

#### WAKE [OK]

**Concepto:** Activación al detectar "Atlas". Sincronizado con el "¿Sí?" de Camila.

**Visual en 3 actos:**
1. **(0–220 ms)** Pulso oscuro parte del centro de la línea y viaja hacia ambos ojos con gradiente (transparente → 90% opacidad en la punta). Flash de impacto al llegar.
2. **(180–480 ms)** Bloom: `shadowBlur` de 24→79 px, sube rápido (35% del tiempo) y decae suavemente.
3. **(200 ms en adelante)** Dos anillos expansivos emergen desde cada ojo (no desde el centro de la cara).
4. **(0–1200 ms)** Nod: sube con `easeOutQuart` hasta 18 px en 600 ms, baja con `easeInOutCubic` en 600 ms. Sincronizado con la duración del "¿Sí?".
5. Ojos hacen overshoot con spring underdamped (kick `vel += 5.5`, `k=180, d=14`).

**Transición a LISTENING:** El bloom blanco se tiñe de azul conforme `transT` avanza (480 ms). El anillo de LISTENING aterriza desde el radio del bloom con `easeOutCubic` en 500 ms.

**Entradas:** IDLE (wake word)  
**Salidas:** → LISTENING (automático a 1.2 s)

---

#### LISTENING [OK]

**Concepto:** Escuchando activamente. El anillo reacciona a la voz del usuario.

**Visual:**
- Ojos cambian a azul profundo `(21,101,192)`.
- Un anillo rodea cada ojo. Radio base + hasta 26 px extra según amplitud del micrófono. Pulso de respiración suave independiente.
- Al venir de WAKE: el anillo hereda el radio del bloom y "aterriza" en posición normal con `easeOutCubic` en 500 ms.
- Texto "E S C U C H A N D O" muy sutil en la parte inferior (38% de opacidad).

**Entradas:** WAKE, SPEAKING (robot hizo pregunta)  
**Salidas:** → THINKING (SPEECH_END), → SPEAKING (Vosk local ~480 ms), → IDLE (timeout 10 s)  
**Nodos:** `atlas_ros2_node` (VAD + Vosk), `/atlas/listening = true`

---

#### THINKING [OK]

**Concepto:** Procesando. El cabeceo y el punto viajero expresan concentración.

**Visual:**
- Ojos cambian a ámbar vivo `(205,105,15)`.
- Toda la cara rota suavemente ±6.3° con período ~8 s (`easeInOutSine`). El cabeceo comunica "estoy pensando" sin necesitar ningún ícono.
- Un punto oscuro viaja de lado a lado sobre la línea de conexión con movimiento sinusoidal suavizado.

**Entradas:** LISTENING (SPEECH_END)  
**Salidas:** → SPEAKING, → DISPENSING, → MEASURING, → DASHBOARD, → ERROR  
**Nodos:** `atlas_ros2_node` (Groq Whisper STT + Llama 3.3 70B), `medical_db`

---

#### SPEAKING [OK]

**Concepto:** La línea se convierte en la voz.

**Visual:**
- La línea de conexión se transforma en onda senoidal (4 ciclos en el ancho). La amplitud sigue el nivel RMS del TTS en tiempo real.
- Envolvente de Hanning: la onda llega a cero en los extremos, sin discontinuidades donde la línea toca los ojos.
- En picos bruscos de audio (delta > 0.35): los ojos hacen un jiggle vertical con spring underdamped (`k=100, d=12`). El ojo "rebota" con la sílaba fuerte.

**Sincronización:** `sounddevice` output → `audio_level.py` → `/ws/audio` → `setAudioLevel()`  
**Entradas:** THINKING, GREETING  
**Salidas:** → LISTENING, → IDLE, → DISPENSING, → MEASURING  
**Nodos:** `atlas_ros2_node` (Azure TTS Camila), `/robot/speak`

---

### Grupo B — Movilidad

#### MOVING [OK]

**Concepto:** El robot "camina contento". Efecto chill — todo bajo control.

**Visual:**
- Bob de caminata con dos frecuencias superpuestas:
  - Onda lenta 1.2 Hz, amplitud 6 px: balanceo del cuerpo
  - Onda rápida 2.4 Hz, amplitud 2.5 px: impacto de cada paso
- La rotación sigue el balanceo lento (±1.26°).
- Cara completamente inexpresiva. El movimiento hace todo el trabajo expresivo.
- Al entrar/salir del estado, el bob se mezcla suavemente (blend con `transT`).

**Bloquea:** Dispensador (`medication_node` rechaza comandos)  
**Entradas:** REMINDER, SPEAKING (comando "ven aquí")  
**Salidas:** → SEARCHING, → APPROACHING, → IDLE, → ERROR  
**Nodos:** Nav2, `/cmd_vel`, `esp32_bridge_node`

---

#### SEARCHING [OK]

**Concepto:** Escaneando el entorno. Con misión activa, los ojos cambian a teal.

**Visual:**
- Ojos barren ±42 px lateralmente con seno natural (período 2.5 s). El movimiento es orgánico, no mecánico.
- Un shimmer elíptico (gradiente radial brillante, ~28×7 px) viaja sobre la línea cada 1.8 s, como un ping de sonar.
- Con `setReminderActive(true)`: los ojos transicionan suavemente a teal `(13,122,90)` mediante `_reminderBlend` (EMA con factor 0.003/ms).

**API:** `setReminderActive(bool)` — transición suave de color blanco ↔ teal  
**Entradas:** REMINDER, MOVING, IDLE (comando "búscame")  
**Salidas:** → APPROACHING, → IDLE (timeout 120 s), → ALERT (REMINDER >60 min)  
**Nodos:** `person_detector_node`, Nav2, `/kinect2/sd/points`

---

#### APPROACHING [OK]

**Concepto:** Analizando. El movimiento del cuerpo comunica los tres momentos.

**Visual — seeking:** La cara se inclina de lado a lado con oscilación sinusoidal lenta (período 2.2 s, ángulo ±8°). Cara completamente inexpresiva. El lean comunica "estoy analizando" sin ningún ícono añadido.

**Visual — recognized:** La inclinación para inmediatamente. Un kick al spring vertical dispara 2–3 nods naturales que decaen solos. Spring underdamped deliberadamente (`k=140, d=9`): el movimiento tiene overshoot y rebote orgánico, igual que cuando alguien dice "sí" con la cabeza.

**Visual — rejected:** Kick al spring horizontal dispara 3–4 sacudidas que decaen solos (`k=160, d=8`). Cara inexpresiva durante todo el movimiento. El "no" es el movimiento, no una expresión facial.

**API:**
- `setConfidence(0–1)`: umbral ≥ 0.75 dispara `recognized`
- `rejectApproach()`: dispara `rejected`

**Entradas:** SEARCHING, MOVING  
**Salidas:** → GREETING (reconocido), → SEARCHING (rechazado/timeout 8 s)  
**Nodos:** `face_recognition_node`, `/patient/identified`, `/patient/confidence`

---

### Grupo C — Reconocimiento y Tareas Médicas

#### GREETING — pendiente

**Concepto:** Celebración al reconocer al usuario. Baymax clásico.

**Visual:** Ojos se transforman en medias lunas (de `ellipse()` a `drawArc()`). Transición de morph en 300 ms. Texto "¡Hola, [nombre]!" centrado en fuente grande. Duración ~2.5 s fijo.

**Entradas:** APPROACHING (reconocido)  
**Salidas:** → DISPENSING (REMINDER activo), → MEASURING (medición urgente), → SPEAKING (sin misión)  
**Nodos:** `medical_db.get_resumen_paciente()`, `scheduler_node`, `atlas_ros2_node` (TTS saludo)

---

#### DISPENSING — pendiente

**Concepto:** Dispensación en ejecución. Estado bloqueante.

**Visual:** Ojos ámbar concentrados. Overlay: `"[Medicamento] — [N] tabletas"`, barra de progreso lineal, `"Por favor no se mueva"`. Load cell confirma el resultado.

**Bloquea:** Robot inmóvil (`/cmd_vel` bloqueado), voz desactivada excepto "cancelar"  
**Entradas:** GREETING, SPEAKING (confirmación verbal), THINKING (intent dispensar)  
**Salidas:** → SUCCESS (load cell OK), → ERROR (fallo mecánico), → ALERT (peso incorrecto)  
**Nodos:** `medication_node`, `esp32_medical_node`, HX711 load cell, `medical_db.registrar_dispensacion()`

---

#### MEASURING — pendiente

**Concepto:** Midiendo signos vitales. Requiere cooperación del usuario.

**Visual:** Ojos azul sereno. SVG de heartbeat pulsante central. Secuencia progresiva: "Apoya el dedo..." → BPM aparece → SpO₂ → Temperatura. Semáforo de normalidad por valor (verde / ámbar / rojo). Rangos: BPM 60–100, SpO₂ ≥95%, Temp 36.1–37.2°C.

**Entradas:** SPEAKING, THINKING, GREETING, DASHBOARD (botón "Medir ahora")  
**Salidas:** → SUCCESS, → ALERT (valor fuera de rango), → ERROR (sensor timeout 30 s)  
**Nodos:** `/health/bpm`, `/health/spo2`, `/health/temperature`, `vital_signs_node`, `medical_db.registrar_signos_vitales()`

---

#### REMINDER — pendiente

**Concepto:** Misión activa de medicación. El robot sale a buscar al usuario con propósito.

**Visual:** Banner superior persistente `"Hora de [Medicamento] — [N] tabletas"` en teal. Cara de SEARCHING debajo con ojos teal. Urgencia visual progresiva: 0–15 min discreto, 15–30 min ámbar, >30 min rojo pulsante.

**Entradas:** IDLE (scheduler_node dispara, poll cada 30 s)  
**Salidas:** → SEARCHING (inmediato), → ALERT (timeout >60 min sin entrega)  
**Nodos:** `scheduler_node` (`/scheduler/reminder`), `medical_db.get_proxima_dosis()`, `state_machine_node`

---

#### SUCCESS — pendiente

**Concepto:** Confirmación visual de tarea completada. Sin este estado el usuario no sabe si terminó bien.

**Visual:** Ojos → medias lunas felices. Checkmark SVG animado (trazo que se dibuja en 600 ms). `"[Tarea] completada"`. Fade-out suave hacia IDLE. Duración 3 s fijo.

**Entradas:** DISPENSING (load cell OK), MEASURING (valores registrados)  
**Salidas:** → IDLE (timer 3 s), → DASHBOARD (trackpad), → SPEAKING (follow-up verbal)  
**Nodos:** `medical_db` (confirmación escritura), `scheduler_node` (marcar completado)

---

### Grupo D — Pantallas Complejas y Alertas

#### DASHBOARD — pendiente

**Concepto:** Única pantalla sin cara Baymax dominante. Panel de datos completo.

**Visual:** Cards: últimos signos vitales, próxima dosis con tiempo restante, historial de dispensaciones. Mini-cara Baymax en esquina superior izquierda como avatar de estado. 3 botones táctiles optimizados para trackpad (min-height 64 px): "Medir ahora", "Ver historial", "Volver".

**Privacidad:** Timeout 60 s sin interacción → IDLE. `/ultrasonic/front` sin persona 10 s → IDLE. Los dos corren en paralelo.

**Entradas:** THINKING/SPEAKING (intent = ver panel), trackpad en cualquier estado, SUCCESS  
**Salidas:** → IDLE, → LISTENING (wake word), → MEASURING (botón), → DISPENSING (botón + voz)  
**Nodos:** `medical_db` (REST), `scheduler_node` (próximas dosis), `/ultrasonic/front`

---

#### ALERT — pendiente

**Concepto:** Alerta médica o emergencia. Dos severidades con el mismo estado.

**Visual:** Tinte rojo muy sutil sobre el fondo blanco (pulsante, no agresivo). Ojos rojos. Texto grande según tipo: `"SpO₂ bajo: 91%"` o `"EMERGENCIA"`. Countdown visible. Botón grande "Cancelar — estoy bien". VITALS: countdown 10 s, cancelable. EMERGENCY: countdown 5 s, no cancelable por voz.

**Entradas:** MEASURING (valor fuera de rango), REMINDER (>60 min), GPIO PA0 STM32  
**Salidas:** → SPEAKING (Atlas verbaliza), → IDLE (cancelada o notificación enviada)  
**Nodos:** `atlas_ros2_node` (TTS prioridad máxima), STM32 GPIO, Wi-Fi HTTP POST, `medical_db.registrar_alerta()`

---

#### ERROR — pendiente

**Concepto:** Error técnico del sistema. No es urgencia médica. Tono ámbar, no rojo.

**Visual:** Ojos en forma de `×` ámbar (dos lineas cruzadas, no elipses). Código de error legible: `ERR_DISPENSER_TIMEOUT`. `"Reiniciando módulo..."`. Barra de progreso de recovery. Deliberadamente no alarmante.

**Entradas:** THINKING (API timeout), MOVING (Nav2 falla), DISPENSING (fallo mecánico), MEASURING (sensor timeout 30 s)  
**Salidas:** → IDLE (recovery exitoso), → ALERT (error crítico de seguridad)  
**Nodos:** `state_machine_node` (recovery logic), `/rosout`

---

## 6. MAPA DE TRANSICIONES

### Tabla Completa

| Estado origen | Condición / trigger | Estado destino |
|---------------|---------------------|----------------|
| IDLE | Wake word "Atlas" | WAKE |
| IDLE | `scheduler_node` dispara horario | REMINDER |
| IDLE | Botón trackpad / "ver panel" | DASHBOARD |
| WAKE | Timer 1.2 s completado | LISTENING |
| LISTENING | `SPEECH_END` (VAD) | THINKING |
| LISTENING | `COMMAND_DETECTED` (Vosk) | SPEAKING |
| LISTENING | Timeout 10 s | IDLE |
| THINKING | Respuesta LLM lista | SPEAKING |
| THINKING | Intent = dispensar + usuario confirmado | DISPENSING |
| THINKING | Intent = medir | MEASURING |
| THINKING | Intent = ver panel | DASHBOARD |
| THINKING | Timeout 15 s / fallo API | ERROR |
| SPEAKING | Terminó con pregunta abierta | LISTENING |
| SPEAKING | Monólogo terminado | IDLE |
| SPEAKING | Confirmación dispensar | DISPENSING |
| SPEAKING | Instrucción "apoya el dedo" | MEASURING |
| MOVING | Llegó sin usuario | SEARCHING |
| MOVING | Persona detectada en trayecto | APPROACHING |
| MOVING | Llegó a base sin misión | IDLE |
| MOVING | Nav2 falla | ERROR |
| SEARCHING | `/person/detected = true` | APPROACHING |
| SEARCHING | Timeout 120 s | IDLE |
| SEARCHING | REMINDER crítico >60 min | ALERT |
| APPROACHING | `setConfidence(>=0.75)` | GREETING |
| APPROACHING | `rejectApproach()` / timeout 8 s | SEARCHING |
| GREETING | REMINDER activo para usuario | DISPENSING |
| GREETING | Medición programada urgente | MEASURING |
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
| DASHBOARD | `/ultrasonic/front` sin persona 10 s | IDLE |
| DASHBOARD | Wake word "Atlas" | LISTENING |
| DASHBOARD | Botón "Medir ahora" | MEASURING |
| ALERT | Cancelada antes del countdown | IDLE |
| ALERT | Notificación enviada | IDLE |
| ERROR | Auto-recovery exitoso | IDLE |
| ERROR | Error crítico de seguridad | ALERT |

### Reglas Globales de Transición

```
1. Wake word "Atlas" tiene prioridad global desde cualquier estado
   EXCEPTO: DISPENSING (bloqueado) y ALERT (no se interrumpe por voz)

2. GPIO PA0 (boton emergencia STM32) tiene maxima prioridad absoluta
   -> Activa ALERT desde CUALQUIER estado, incluyendo DISPENSING y MEASURING

3. DISPENSING bloquea /cmd_vel -- Nav2 no puede mover el robot

4. Porcupine corre 24/7 en background, independientemente del estado activo

5. scheduler_node hace poll cada 30 s -- solo dispara REMINDER desde IDLE
   (nunca interrumpe conversaciones activas o tareas medicas en curso)
```

---

## 7. FLUJOS PRINCIPALES DE USO

### Flujo 1 — Conversación Pura (más frecuente)
```
IDLE -> WAKE -> LISTENING -> THINKING -> SPEAKING -> IDLE
```
Latencia total: ~1.6–2.5 s. Solo `atlas_ros2_node` + `medical_db`.

### Flujo 2 — Misión de Medicación (flujo más completo)
```
IDLE -> REMINDER -> SEARCHING -> APPROACHING -> GREETING -> DISPENSING -> SUCCESS -> IDLE
```
Toca todos los subsistemas: scheduler → Nav2 → Kinect → visión → dispensador → BD.

### Flujo 3 — Signos Vitales por Comando
```
IDLE -> WAKE -> LISTENING -> THINKING -> SPEAKING -> MEASURING -> SUCCESS -> IDLE
                                                                       |
                                                              ALERT (valores anomalos)
```

### Flujo 4 — Dashboard con Cierre por Privacidad
```
(cualquier estado) -> DASHBOARD -> IDLE
```
Dos mecanismos independientes en paralelo: timeout 60 s de inactividad + ausencia de persona (ultrasonido 10 s).

### Flujo 5 — Emergencia por Botón Físico
```
(cualquier estado) -> ALERT[EMERGENCY] -> SPEAKING -> IDLE
```
GPIO PA0 STM32. Countdown 5 s. No cancelable por voz. Máxima prioridad global.

---

## 8. ESPECIFICACIONES TÉCNICAS — baymax_face.js

### Estado: v4.0 — 8/16 estados implementados

Archivo: `hmi/static/baymax_face.js`  
Expone: `window.BaymaxFace`

### API Pública Completa

```javascript
// Instanciar y arrancar
const face = new BaymaxFace(document.getElementById('canvas'));
face.start();
face.stop();

// Control de estado FSM
face.setState('LISTENING', params)   // params: { patient_name, medication, dose, severity }
face.setAudioLevel(0.742)            // nivel TTS (0–1), desde /ws/audio source='tts'
face.setMicLevel(0.35)               // nivel mic (0–1), desde /ws/audio source='mic'

// APPROACHING — API de reconocimiento facial
face.setConfidence(0.85)             // umbral 0.75 -> fase 'recognized' (nods)
face.rejectApproach()                // fase 'rejected' (shake)

// SEARCHING — modo misión activa
face.setReminderActive(true)         // ojos -> teal progresivamente
```

### Sistema de Springs

`_updateSpring(spring, target, config, dtS)` — spring-damper genérico reutilizable en toda la clase.

| Spring | Uso | k | d | Comportamiento |
|--------|-----|---|---|----------------|
| `_eyeScaleL/R` | Ojos saltones WAKE | 180 | 14 | Underdamped, overshoot ~12% |
| `_jiggleL/R` | Jiggle vertical SPEAKING | 100 | 12 | Decae en ~400 ms |
| `_nodSpring` | Nod "sí" APPROACHING | 140 | 9 | 2–3 oscilaciones naturales |
| `_shakeSpring` | Shake "no" APPROACHING | 160 | 8 | 3–4 oscilaciones naturales |

### Escala Proporcional

Todas las coordenadas se definen a `BASE_W = 1366 px`. Factor `S = canvas.width / 1366`. Método `_s(v)` aplica el factor a cualquier valor. Soporta cualquier resolución sin refactorizar.

### Teclado de Desarrollo (oculto en producción)

| Tecla | Acción |
|-------|--------|
| `1–5` | IDLE, WAKE, LISTENING, THINKING, SPEAKING |
| `6–8` | MOVING, SEARCHING, APPROACHING |
| `A` | Toggle simulación de audio (en SPEAKING) |
| `D` | Toggle debug overlay |
| `R` | Toggle REMINDER teal (en SEARCHING) |
| `C` | Ciclar fases seeking → recognized → rejected (en APPROACHING) |

---

## 9. INTEGRACIÓN CON ROS2 Y BACKEND

### Topics del Módulo HMI

| Topic | Tipo | Dirección | Descripción |
|-------|------|-----------|-------------|
| `/hmi/set_state` | `std_msgs/String` | -> HMI | Fuerza cambio de estado desde `state_machine_node` |
| `/hmi/action` | `std_msgs/String` | HMI -> | Acción del usuario desde dashboard |
| `/atlas/listening` | `std_msgs/Bool` | -> HMI | -> LISTENING |
| `/robot/speak` | `std_msgs/String` | -> HMI | -> SPEAKING |
| `/patient/identified` | `std_msgs/String` | -> HMI | -> GREETING |
| `/patient/confidence` | `std_msgs/Float32` | -> HMI | `setConfidence()` en APPROACHING |
| `/health/bpm` | `std_msgs/Int32` | -> HMI | Valor en tiempo real durante MEASURING |
| `/health/spo2` | `std_msgs/Int32` | -> HMI | Valor en tiempo real durante MEASURING |
| `/health/temperature` | `std_msgs/Float32` | -> HMI | Valor en tiempo real durante MEASURING |
| `/scheduler/reminder` | `std_msgs/String` | -> HMI | JSON payload -> REMINDER |
| `/ultrasonic/front` | `std_msgs/Float32` | -> HMI | Timeout privacidad DASHBOARD |

### Estructura de Mensajes WebSocket

```javascript
// /ws/state — FastAPI -> frontend
{
  "state": "SPEAKING",
  "params": {
    "patient_name": "Juan",        // para GREETING
    "medication": "Metformina",    // para DISPENSING / REMINDER
    "dose": 2,                     // para DISPENSING / REMINDER
    "severity": "vitals"           // para ALERT: "vitals" | "emergency"
  }
}

// /ws/audio — FastAPI -> frontend (50 Hz / cada 20 ms)
{
  "level": 0.742,    // 0.0–1.0 normalizado, EMA aplicado en servidor
  "source": "tts"    // "tts" = salida TTS | "mic" = entrada microfono
}
```

### Nota Crítica: Sincronización de la Boca

`audio_level.py` captura el RMS del buffer de `sounddevice` cada 20 ms y lo publica via WebSocket. En Ubuntu 22.04 requiere un monitor source de PulseAudio para capturar el loopback del TTS:

```bash
pactl list short sources | grep monitor
# Resultado esperado: "alsa_output.pci-XXXX.analog-stereo.monitor"
# Usar ese nombre como input device en sounddevice
```

---

## 10. INTERACCIÓN FÍSICA — TRACKPAD

**Hardware:** Samsung laptop, cable USB-A ruteado por interior del cuello del robot.

| Estado | Comportamiento |
|--------|---------------|
| IDLE | Cualquier toque -> DASHBOARD |
| DASHBOARD | Navegación normal entre cards y botones |
| LISTENING | Toque -> cancela -> IDLE |
| SPEAKING | Toque -> interrumpe -> IDLE |
| DISPENSING | **Deshabilitado** — toque ignorado |
| MEASURING | Toque -> cancela -> IDLE |
| ALERT | Solo botón "Cancelar — estoy bien" activo |
| Resto | Toque -> DASHBOARD (si usuario identificado) o -> IDLE |

### Triple-Lock para Dispensación desde Dashboard

Previene dispensaciones accidentales por contacto involuntario:
```
1. Click "Dar medicamento" -> confirmacion: "[Medicamento]?"
2. Click "Si, dar"         -> Atlas pide confirmacion verbal
3. Respuesta afirmativa    -> DISPENSING activado
```

### Botones del Dashboard (optimizados para trackpad)

| Botón | Acción | Topic publicado |
|-------|--------|-----------------|
| "Medir ahora" | -> MEASURING | `/hmi/action: "measure_now"` |
| "Ver historial" | Expande panel in-page | — |
| "Volver" | -> IDLE | `/hmi/action: "go_idle"` |
| "Dar medicamento" | Triple-lock -> DISPENSING | `/hmi/action: "dispense_request"` |

---

## 11. ESTADO ACTUAL Y PENDIENTES

> **Última actualización:** 2026-03-17

| Componente | Estado | Detalle |
|------------|--------|---------|
| Decisión tecnológica | OK | FastAPI + Chromium kiosk — 2026-03-17 |
| Filosofía visual | OK | Modo claro, fondo blanco, ojos negros |
| 16 estados definidos | OK | Visual, entradas, salidas y nodos para cada estado |
| Mapa de transiciones | OK | Tabla completa + reglas generales |
| `baymax_face.js` IDLE | OK | Parpadeo + doble parpadeo + micro-drift + respiración |
| `baymax_face.js` WAKE | OK | Pulso línea + ojos saltones + bloom + nod "¿Sí?" + anillos |
| `baymax_face.js` LISTENING | OK | Azul + anillo reactivo + entry animation desde WAKE |
| `baymax_face.js` THINKING | OK | Ámbar vivo + cabeceo + punto viajero |
| `baymax_face.js` SPEAKING | OK | Onda de voz + jiggle en picos de audio |
| `baymax_face.js` MOVING | OK | Bob 2 frecuencias + rotación — "chill" |
| `baymax_face.js` SEARCHING | OK | Barrido + shimmer + teal REMINDER |
| `baymax_face.js` APPROACHING | OK | Lean curioso + nod sí + shake no |
| `baymax_face.js` GREETING | pendiente | Medias lunas + texto nombre |
| `baymax_face.js` DISPENSING | pendiente | Ojos ámbar + overlay medicamento + progreso |
| `baymax_face.js` MEASURING | pendiente | Heartbeat + valores en tiempo real + semáforo |
| `baymax_face.js` REMINDER | pendiente | Banner persistente + urgencia progresiva |
| `baymax_face.js` SUCCESS | pendiente | Medias lunas + checkmark animado |
| `baymax_face.js` DASHBOARD | pendiente | Pantalla de datos completa |
| `baymax_face.js` ALERT | pendiente | Tinte rojo + countdown |
| `baymax_face.js` ERROR | pendiente | Ojos x ambar + codigo de error |
| `server.py` | pendiente | FastAPI + WebSockets |
| `ros2_bridge.py` | pendiente | hilo rclpy + asyncio queues |
| `audio_level.py` | pendiente | Stream RMS sounddevice -> WS |
| `routers/dashboard.py` | pendiente | REST endpoints BD |
| `state_machine.js` | pendiente | FSM frontend + overlays |
| `dashboard.js` | pendiente | Panel de datos |
| `index.html` | pendiente | Layout kiosk completo |
| PulseAudio loopback | pendiente | Monitor source para TTS |
| Pruebas RAM simultáneas | pendiente | Con todos los nodos activos |

### Orden de Implementación Recomendado

```
Etapa 1 — Independiente del hardware (hacer ahora):
  1. baymax_face.js: 8 estados restantes (GREETING -> ERROR)
  2. index.html skeleton + HUD de desarrollo
  3. server.py + WebSocket /ws/state con mock (sin ROS2)
  4. state_machine.js + overlays basicos

Etapa 2 — Requiere Ubuntu con ROS2:
  5. ros2_bridge.py — conectar con grafo ROS2 real
  6. audio_level.py + calibracion PulseAudio
  7. routers/dashboard.py + dashboard.js con BD real

Etapa 3 — Requiere robot fisico armado:
  8. Overlays DISPENSING, MEASURING — requiere hardware medico
  9. Integracion en bringup.launch.py
  10. Pruebas de RAM con todos los nodos simultaneos
```

---

## 12. COMANDOS DE REFERENCIA RÁPIDA

```bash
# Testear standalone (sin servidor, solo el canvas)
# Abrir index_test.html en el navegador directamente con File://
# Shortcuts: 1-8 estados, A audio sim, D debug, R reminder, C ciclar APPROACHING

# Servidor FastAPI en desarrollo (cuando este implementado)
cd ~/Meadlease/hmi
uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Chromium modo kiosk (robot fisico)
chromium-browser \
  --kiosk \
  --app=http://localhost:8000 \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0

# Cambiar estado desde terminal (con ROS2 corriendo)
ros2 topic pub /hmi/set_state std_msgs/String "data: 'LISTENING'" --once
ros2 topic pub /hmi/set_state std_msgs/String "data: 'SPEAKING'" --once
ros2 topic pub /hmi/set_state std_msgs/String "data: 'APPROACHING'" --once

# Simular nivel de audio para testear la onda de boca
python3 -c "
import asyncio, websockets, json, math
async def test():
    async with websockets.connect('ws://localhost:8000/ws/audio') as ws:
        for i in range(200):
            level = abs(math.sin(i*0.3)) * abs(math.sin(i*0.07)) * 0.85
            await ws.send(json.dumps({'level': round(level,3), 'source': 'tts'}))
            await asyncio.sleep(0.04)
asyncio.run(test())
"

# Verificar RAM con todos los nodos activos (estimado)
free -h
# ROS2 base:        ~500 MB
# RTAB-Map:        ~3-4 GB
# kinect2_bridge:   ~200 MB
# atlas_ros2_node:  ~300 MB
# Chromium (HMI):  ~300 MB
# Total estimado:  ~5-6 GB de 12 GB disponibles

# Monitor de recursos durante demo
htop  # buscar: uvicorn, chromium-browser, rtabmap, kinect2_bridge
```

---

*Para el sistema conversacional Atlas: `DOCUMENTACION_CONVERSACIONAL.md`*
*Para arquitectura ROS2, Nav2 y Kinect: `DOCUMENTACION_ROS2.md`*
*Para contexto general del proyecto: `PROYECTO_GENERAL.md`*
