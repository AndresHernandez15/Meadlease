# DOCUMENTACIÓN DE HARDWARE — MEADLESE
## Robot Asistente Médico Domiciliario

> **Audiencia:** Equipo completo (Andrés, Linda, Sergio, Juan)  
> **Estado:** Pre-fabricación — validado antes de impresión 3D  
> **Última actualización:** 2026-03-24  
> **Reemplaza a:** Sección 6 de `PROYECTO_GENERAL.md` + `REVISION_COMPLETA_HARDWARE.md`

---

## ÍNDICE

1. [Inventario Completo de Componentes](#1-inventario-completo-de-componentes)
2. [Distribución Física y Centro de Masa](#2-distribución-física-y-centro-de-masa)
3. [Sistema de Energía](#3-sistema-de-energía)
4. [Conexiones Eléctricas por Subsistema](#4-conexiones-eléctricas-por-subsistema)
5. [Arquitectura de Comunicaciones](#5-arquitectura-de-comunicaciones)
6. [Leyenda del Diagrama de Comunicaciones](#6-leyenda-del-diagrama-de-comunicaciones)
7. [Routing de Cables — Cuello](#7-routing-de-cables--cuello)
8. [Gestión Térmica y Ventilación](#8-gestión-térmica-y-ventilación)
9. [Sensores de Obstáculos — Montaje](#9-sensores-de-obstáculos--montaje)
10. [Decisiones Técnicas Documentadas](#10-decisiones-técnicas-documentadas)
11. [Checklist de Fabricación](#11-checklist-de-fabricación)

---

## 1. INVENTARIO COMPLETO DE COMPONENTES

### 1.1 COMPUTACIÓN Y PROCESAMIENTO

| Componente | Especificación | Ubicación | Estado |
|------------|----------------|-----------|--------|
| **Dell Inspiron 3421** | Placa madre sin carcasa · i3-3227U · 12GB RAM · Ubuntu 22.04 | Cabeza (trasera) | ✅ Funcional |
| **Pantalla Samsung** | Panel LED 14–15" reusado | Cabeza (frontal) | ✅ Funcional |
| **Trackpad Samsung** | Trackpad original Samsung — conector ZIF compatible con Dell | Pecho (izquierda) | ✅ Funcional |
| **Cámara Dell** | Cámara integrada en placa madre — reconocimiento facial | Cabeza (con placa) | ✅ Funcional |
| **STM32F411 Blackpill** | MCU auxiliar · micro-ROS · columna vertebral comunicaciones | Base | ✅ micro-ROS validado |
| **ESP32 S3 — Movilidad** | Control motores BLDC · encoders Hall · ultrasonidos | Base | ✅ Conectado y probado |
| **ESP32 S3 — Médica** | Control dispensador · signos vitales · sensores médicos | Torso | ⏳ Pendiente firmware |
| **ESP32-CAM** | Verificación visual pastilla — booleano vía UART | Torso | ⏳ Pendiente integración |

> **Nota importante sobre el Samsung:** del laptop Samsung solo se reutilizan la pantalla y el trackpad como periféricos de la placa Dell. El trackpad se conecta mediante el conector ZIF interno de la placa Dell (compatible con el trackpad original), no por USB. La placa Dell es la única computadora del sistema.

---

### 1.2 SENSORES DE PERCEPCIÓN

**Visión y mapeo:**

| Sensor | Modelo | Función | Alimentación | Ubicación |
|--------|--------|---------|--------------|-----------|
| Kinect V2 | Microsoft Kinect V2 | SLAM RGB-D + detección personas + array micrófono 4 canales | 12V @ 2.5A (21W) | Pecho (~88 cm) |
| Cámara Dell | Integrada placa madre | Reconocimiento facial | Incluida en Dell | Cabeza |
| ESP32-CAM | Módulo ESP32-CAM | Verificación visual pastilla en cajón de salida | 5V @ 300mA | Torso (vista compartimento salida) |

**Detección de obstáculos:**

| Sensor | Cantidad | Posición | Alimentación | Rango |
|--------|----------|----------|--------------|-------|
| **JSN-SR04T** | 5 | 2 frontales (bordes) · 2 laterales (esquinas delanteras) · 1 trasero (centrado) | 5V @ 30mA c/u | 0.2–4.5 m |

> **E18-D80NK (IR anticaída) — ELIMINADOS DEL PROYECTO**  
> Evaluados durante diseño. Descartados por: limitación de detección en superficies oscuras (no funcionan sobre objetos negros), restricciones de integración mecánica (túnel de 9.4 cm de profundidad con agujero de salida de 50 mm compromete estructura de la carcasa), y cobertura redundante por Nav2 en entorno mapeado.  
> *Documentado como mejora futura para entornos no mapeados (ver sección 10.4).*

**Sensores biomédicos:**

| Sensor | Modelo | Medición | Alimentación | Comunicación | Estado |
|--------|--------|----------|--------------|--------------|--------|
| Pulso + SpO₂ | MAX30102 | BPM + SpO₂ | 3.3V @ 20mA | I2C → ESP32 Médica | ✅ Disponible |
| Temperatura | MLX90614 o MAX30205 | Temperatura corporal | 3.3V @ 5mA | I2C → ESP32 Médica | ⏳ Decisión pendiente |

**Sensores del sistema de dispensación:**

| Sensor | Modelo | Función | Alimentación | Comunicación | Estado |
|--------|--------|---------|--------------|--------------|--------|
| IR pastilla | FC-51 | Detecta cuando la pastilla cae hacia el compartimento de salida (reflexivo, activo bajo) | 5V | GPIO digital → ESP32 Médica (pull-up 10kΩ) | ✅ Disponible |
| Presión manguera | MPS20N0040D | Verifica succión activa de la bomba — confirma captura de pastilla | 3.3V | I2C → ESP32 Médica | ✅ Disponible |

> **Nota I2C ESP32 Médica:** el bus I2C comparte MAX30102 + sensor temperatura + MPS20N0040D. Verificar direcciones I2C de cada componente antes del firmware para evitar colisiones. El MPS20N0040D tiene dirección I2C variable según modelo — confirmar con datasheet del ejemplar específico.

**Odometría:**

| Sensor | Tipo | Función | Conexión |
|--------|------|---------|----------|
| Encoders Hall | Integrados en motores BLDC | Velocidad, RPM, odometría | GPIO → ESP32 Movilidad (3 señales Hall × 2 motores = 6 pines) |

---

### 1.3 ACTUADORES Y MOVILIDAD

**Locomoción:**

| Componente | Especificación | Consumo medido | Estado |
|------------|----------------|----------------|--------|
| **Motores BLDC × 2** | Hoverboard 6.5" · 24V · encoders Hall integrados | 640mA @ 24V vacío (15.4W) · ~250mA crucero (6W c/u) · ~2A pico (48W c/u) | ✅ Probados |
| **Drivers ZS-X11H × 2** | Control PWM · disipador integrado | Pérdidas ~10% (1.5W crucero · 10W pico) | ✅ Probados |
| **Rueda loca × 1** | Frontal · equilibrio | — | ✅ |

**Dispensación:**

| Componente | Especificación | Consumo | Estado |
|------------|----------------|---------|--------|
| **Steppers 28BYJ-48 × 3** | 1 carrusel + 2 brazo 2DOF | 5V @ 400mA c/u (2W c/u) | ✅ Disponibles |
| **Drivers ULN2003 × 3** | Control steppers | Pérdidas ~0.5W c/u activo | ✅ Disponibles |
| **Bomba vacío ZT370-K3.7A** | Nominal 3.7V @ 440mA · operando 5V @ 650mA | 3.25W @ 5V | ✅ Disponible |
| **Módulo relé 5V 1 canal** | Con optoacoplador · verificar trigger 3.3V compatible | — | ⏳ Compra pendiente |

> **Control bomba vacío:** el módulo relé entrega 5V completos a la bomba sin caída de voltaje. Si el módulo relé solo acepta 5V en el trigger, usar TIP122 (NPN Darlington) como driver: resistor 1kΩ en base, GPIO ESP32 (3.3V) → resistor → base TIP122 → activa bobina relé. Diodo 1N4007 en antiparalelo con la bobina del relé como flyback.

---

### 1.4 INTERFAZ FÍSICA DE USUARIO

| Componente | Ubicación | Conexión | Alimentación |
|------------|-----------|----------|--------------|
| Pantalla Samsung | Cabeza (~110 cm) | Cable LVDS/eDP interno → placa Dell | Incluida en Dell |
| Trackpad Samsung | Pecho (izquierda, ~95 cm) | Conector ZIF interno → placa Dell | Incluida en Dell |
| Numpad MPR121 | Pecho (derecha, ~95 cm) | I2C → STM32F411 | 3.3V desde STM32 |
| Switch encendido | Pecho (centro abajo) | Línea principal batería | ≥ 10A @ 30V DC rating |
| Botón emergencia trasero | Base trasera · 20 cm altura · 55° inclinado arriba | GPIO PA0 → STM32 (pull-up 10kΩ) | 3.3V |
| Botón emergencia cabeza | Tope de la cabeza (zona plana) | GPIO PA1 → STM32 (pull-up 10kΩ) | 3.3V |

> **Botón emergencia cabeza — recomendado:** TTP223 capacitivo 40×40mm con LED rojo. Activación con contacto sostenido 2 segundos (evita falsas activaciones). Flush con la superficie, sin presión mecánica sobre la unión del cuello.

---

### 1.5 AUDIO

| Componente | Modelo | Ubicación | Alimentación | Conexión |
|------------|--------|-----------|--------------|----------|
| Micrófono | Array Kinect V2 (4 micrófonos) | Kinect en pecho | Incluido en Kinect | USB 3.0 → Dell |
| Parlante | HK-5002 (3W RMS) | Cabeza trasera (apuntando abajo con rejillas) | 5V USB @ 400mA pico | USB → Dell |

> El array del Kinect está validado con Atlas en ROS2 y funciona correctamente como micrófono del sistema conversacional.

---

### 1.6 ESTRUCTURA FÍSICA

| Elemento | Especificación |
|----------|----------------|
| Varillas roscadas | 3/8" × 4 unidades + tuercas + arandelas |
| Base | Triangular 55 × 60 cm (3 puntos de apoyo) |
| Altura total | ~120 cm |
| Material carcasa | PET-G (~6 kg disponibles) |
| Uniones | Sistema cola de milano |
| Acabado | Masilla automotriz + pintura |
| Mantenimiento | Puertas traseras de acceso (base y torso) |
| Movimiento cabeza | Inclinación manual 0°–50° por fricción (tornillo + tuercas apretadas) · sin motorización |

---

## 2. DISTRIBUCIÓN FÍSICA Y CENTRO DE MASA

### 2.1 DISTRIBUCIÓN POR NIVELES

```
NIVEL 4 — CABEZA (~115 cm):
├─ Placa madre Dell sin carcasa        ~900g
├─ Pantalla Samsung                    ~800g
├─ Parlante HK-5002                    ~100g
├─ Cables                              ~50g
└─ SUBTOTAL:                           ~1.85 kg

NIVEL 3 — PECHO (~88 cm):
├─ Kinect V2                           ~600g
├─ Trackpad Samsung                    ~150g
├─ Numpad MPR121                       ~30g
└─ SUBTOTAL:                           ~0.78 kg

NIVEL 2 — TORSO (~50 cm):
├─ Carrusel pastillero                 ~300g
├─ Steppers 28BYJ-48 × 3              ~450g
├─ Drivers ULN2003 × 3                ~60g
├─ Bomba vacío + módulo relé          ~80g
├─ ESP32 S3 Médica                    ~20g
├─ ESP32-CAM                          ~20g
└─ SUBTOTAL:                           ~0.93 kg

NIVEL 1 — BASE (<30 cm):
├─ Pack baterías 7S4P                  ~1.5 kg
├─ BMS                                 ~100g
├─ Step-downs × 3                      ~200g
├─ Drivers ZS-X11H × 2                ~150g
├─ ESP32 S3 Movilidad                 ~20g
├─ STM32F411                          ~10g
└─ SUBTOTAL:                           ~2.0 kg

PESO COMPONENTES:                      ~5.56 kg
+ Carcasa PET-G (estimado):            ~2.5 kg
─────────────────────────────────────────────
PESO TOTAL ESTIMADO:                   ~8.06 kg
```

### 2.2 CÁLCULO DE CENTRO DE MASA

```
Nivel 1 (base):    2.0 kg  ×  15 cm  =   30.0 kg·cm
Nivel 2 (torso):   0.93 kg ×  50 cm  =   46.5 kg·cm
Nivel 3 (pecho):   0.78 kg ×  88 cm  =   68.6 kg·cm
Nivel 4 (cabeza):  1.85 kg × 115 cm  =  212.8 kg·cm
                   ──────────────────────────────────
                   5.56 kg             357.9 kg·cm

Centro de masa sin carcasa = 357.9 / 5.56 = 64.4 cm

Con carcasa PET-G distribuida (~2.5 kg):
Centro de masa final estimado: ~55–60 cm ✅
```

**Validación de estabilidad:**

| Métrica | Valor | Evaluación |
|---------|-------|------------|
| Centro de masa | ~55–60 cm | ✅ Aceptable |
| Altura total | ~120 cm | Ratio altura/CM = 2:1 ✅ |
| Base | Triangular 55×60 cm | Polígono amplio ✅ |
| Batería en base | 1.5 kg en nivel 1 | ✅ Crítico para estabilidad |

> **Regla de oro:** la batería debe permanecer siempre en el nivel 1 (base). Si se reubica en torso o cabeza, el centro de masa sube y el robot pierde estabilidad.

---

## 3. SISTEMA DE ENERGÍA

### 3.1 BATERÍA PRINCIPAL

| Componente | Especificación |
|------------|----------------|
| **Pack 7S4P** | 7 serie × 4 paralelo · celdas 18650 mixtas validadas · 25.9V nominal (29.4V cargado · 21V mínimo) · ~6Ah · ~155 Wh |
| **BMS** | HXYP-C47-MA18 (7S · balance) · 10A continuo · 15A pico · conector balance 8 pines (7 celdas + común) |
| **Cargador** | SJT-65E 29.4V @ 2A · tiempo carga ~3–4 horas |

### 3.2 REGULADORES DE VOLTAJE

| Regulador | Entrada | Salida ajustada | Corriente max | Carga real | Margen | Asignación |
|-----------|---------|-----------------|---------------|------------|--------|------------|
| **XL4016 #1** | 29V | **19.7V** (compensa caída cable cuello) | 9A | 2.3A | 74% | Dell Inspiron |
| **XL4016 #2** | 29V | 12.0V ± 0.1V | 9A | 2.5A pico | 72% | Kinect V2 |
| **XL4015** | 29V | 5.0V ± 0.05V | 5A | 2.8A pico | 44% | Lógica (MCUs · sensores · steppers · bomba) |

> **Por qué XL4016 #1 se ajusta a 19.7V y no 19.5V:** el cable AWG 16 de 2m (ida + vuelta) que recorre el cuello tiene una resistencia de 0.082Ω. A 2.3A de carga máxima la caída es 0.19V. Ajustando la fuente a 19.7V, el Dell recibe 19.51V ✅ dentro del rango aceptable 18.5–20V.

### 3.3 FUSIBLES

| Fusible | Valor | Tipo | Ubicación | Protege |
|---------|-------|------|-----------|---------|
| **Principal** | **15A** | **Slow-blow (tipo "T")** | Entre BMS y distribución 29V | Pico arranque motores 7.8A — fast-blow 10A saltaría en arranque normal |
| 19.5V | 3A | Fast-blow | Salida XL4016 #1 | Sobrecarga Dell |
| 12V | 3A | Fast-blow | Salida XL4016 #2 | Sobrecarga Kinect |
| 5V | 5A | Fast-blow | Salida XL4015 | Sobrecarga lógica |

> **Identificar slow-blow en tienda:** el elemento interno visible tiene forma de espiral o resorte, no filamento recto. Etiquetados con "T" en algunas tiendas. Alternativa equivalente: breaker rearmable push-to-reset 15A.

### 3.4 CONSUMO POR ESTADO DE OPERACIÓN

| Estado | Consumo total | Corriente batería | C-rate | Autonomía (80% DoD) |
|--------|--------------|-------------------|--------|---------------------|
| IDLE | 59W | 2.28A | 0.38C ✅ | ~2h 5min |
| Conversación | 71.5W | 2.76A | 0.46C ✅ | ~1h 44min |
| Navegación crucero | 94.5W | 3.65A | 0.61C ✅ | ~1h 19min |
| Navegación pico (arranque) | 187W | 7.8A | 1.3C ✅ | — (2–3s) |
| Dispensando | 68.5W | 2.64A | 0.44C ✅ | ~1h 49min |
| Midiendo signos vitales | 61.3W | 2.37A | 0.39C ✅ | ~2h 2min |
| **Demo típica mixta** | **~77W promedio** | **~2.97A** | **~0.50C** | **~1h 37min** ✅ |

> **Expansión de batería recomendada (post-entrega):** pasar de 7S4P a 7S6P añadiendo 14 celdas. Autonomía demo sube a ~2h. El BMS actual es compatible. Costo estimado: $10–30 USD en celdas recicladas validadas.

### 3.5 CABLEADO DE POTENCIA

| Línea | Voltaje | Corriente | Longitud | Calibre | Notas |
|-------|---------|-----------|----------|---------|-------|
| Batería → BMS | 29V | 10A | 20 cm | AWG 14 | XT60 |
| BMS → Distribución | 29V | 10A | 15 cm | AWG 14 | XT60 |
| 29V → Drivers BLDC | 29V | 8A pico | 30 cm | AWG 14 | XT60 |
| **19.5V cuello** | **19.7V ajustado** | **2.3A** | **1m × 2** | **AWG 16** | Loop holgura 10–15 cm en unión cuello-cabeza |
| 12V → Kinect | 12V | 2.5A | 30 cm | AWG 18 | JST-XH |
| 5V distribución | 5V | Variable | 10–50 cm | AWG 20–22 | Terminal block |
| Señales | 3.3–5V | <100mA | Variable | AWG 26–28 | Código colores |

---

## 4. CONEXIONES ELÉCTRICAS POR SUBSISTEMA

### 4.1 LÍNEA 5V — DISTRIBUCIÓN DETALLADA

```
BORNERA CENTRAL 5V (salida XL4015)
    │
    ├─[Branch 1: CONTROL MOVILIDAD]
    │    ├─ STM32F411 (~150mA)
    │    └─ ESP32 S3 Movilidad (~250mA)
    │
    ├─[Branch 2: SENSORES OBSTÁCULOS]
    │    └─ JSN-SR04T × 5 (~150mA total)
    │
    ├─[Branch 3: DISPENSACIÓN]
    │    ├─ ESP32 S3 Médica (~250mA)
    │    ├─ ESP32-CAM (~300mA streaming)
    │    ├─ Steppers 28BYJ-48 × 3 via ULN2003 (~1200mA pico · no simultáneos)
    │    ├─ Módulo relé → Bomba ZT370 (~650mA durante succión)
    │    └─ FC-51 sensor IR pastilla (~20mA)
    │
    ├─[Branch 4: SENSORES MÉDICOS]
    │    ├─ MAX30102 (3.3V via LDO del ESP32, ~20mA)
    │    ├─ Sensor temperatura (3.3V via LDO, ~5mA)
    │    └─ MPS20N0040D (3.3V via LDO, ~10mA)
    │
    ├─[Branch 5: HMI]
    │    ├─ Parlante USB HK-5002 (~400mA pico) — via USB Dell
    │    ├─ Trackpad Samsung — via ZIF interno Dell
    │    └─ Numpad MPR121 I2C (~3mA, 3.3V desde STM32)
    │
    └─[Branch 6: INDICADORES]
         └─ LED RGB brazo (~60mA máx via resistores 220Ω)
```

### 4.2 SISTEMA DE MOVILIDAD

```
BATERÍA 29.4V (directo, post-fusible 15A)
    │
    ├── Driver ZS-X11H #1 ← PWM/Dir/Enable ← ESP32 Movilidad
    │       └── Motor BLDC Izquierdo (Hall A/B/C → ESP32 Movilidad)
    │
    └── Driver ZS-X11H #2 ← PWM/Dir/Enable ← ESP32 Movilidad
            └── Motor BLDC Derecho (Hall A/B/C → ESP32 Movilidad)

ODOMETRÍA:
Hall × 3 por motor → ESP32 Movilidad → calcula RPM/velocidad/distancia
→ UART → STM32 → micro-ROS → /odom en ROS2
```

> **Level shifters (3.3V → 5V):** probados sin level shifters y los drivers ZS-X11H respondieron correctamente con las señales 3.3V del ESP32. Se omiten en esta versión. Si durante pruebas de carga real aparece comportamiento errático en los motores, agregar 74HCT125 en las señales PWM/Dir/Enable como primer diagnóstico.

### 4.3 SISTEMA DE DISPENSACIÓN

```
ESP32 S3 Médica:
├── GPIO × 4 → ULN2003 #1 → Stepper carrusel 28BYJ-48
├── GPIO × 4 → ULN2003 #2 → Stepper brazo DOF1 28BYJ-48
├── GPIO × 4 → ULN2003 #3 → Stepper brazo DOF2 28BYJ-48
├── GPIO → [Módulo relé IN] → Bomba ZT370 (5V completos)
│          [1N4007 flyback en bobina relé si TIP122 como driver]
├── GPIO ← FC-51 OUT (pull-up 10kΩ) — pastilla en canal de caída
├── I2C → MPS20N0040D — presión manguera (confirma succión)
├── I2C → MAX30102 — BPM + SpO₂
├── I2C → Sensor temperatura (MLX90614 o MAX30205)
├── GPIO × 3 → LED RGB brazo (R/G/B via resistores 220Ω)
└── UART RX ← ESP32-CAM (booleano: 0xA1 pastilla presente / 0xA0 vacío)
```

**Protocolo ESP32-CAM → ESP32 Médica:**
- Interfaz: UART a 9600 baud
- Trama: 1 byte por detección
  - `0xA1` = pastilla detectada en cajón
  - `0xA0` = cajón vacío / sin objeto
- La detección se realiza localmente en el ESP32-CAM, no se transmiten imágenes

---

## 5. ARQUITECTURA DE COMUNICACIONES

```
┌─────────────────────────────────────────────────────────┐
│            DELL INSPIRON (ROS2 MASTER)                  │
│            Ubuntu 22.04 · ROS2 Humble                   │
│                                                         │
│  Periféricos internos placa:                            │
│  • Pantalla Samsung ── LVDS/eDP (cable interno)         │
│  • Trackpad Samsung ── ZIF interno (conector compatible)│
│  • Cámara Dell      ── Ribbon interno                   │
│                                                         │
│  Periféricos USB:                                       │
│  • Kinect V2    ── USB 3.0 (datos + array micrófono)    │
│  • Parlante     ── USB 2.0                              │
│  • STM32F411    ── USB 2.0 (CDC, micro-ROS)             │
└────────────────────────┬────────────────────────────────┘
                         │ USB-CDC (micro-ROS)
              ┌──────────▼──────────┐
              │    STM32F411        │
              │    Blackpill        │
              │                     │
              │ Publica:            │
              │ • /odom             │
              │ • /ultrasonic/*     │
              │ • /emergency_button │
              │                     │
              │ Suscribe:           │
              │ • /cmd_vel          │
              │                     │
              │ I2C → MPR121 numpad │
              │ GPIO PA0 → btn emerg│
              │ GPIO PA1 → btn emerg│
              └──────┬──────┬───────┘
                UART1 │      │ UART2
                DMA   │      │ DMA
                115200│      │ 115200
                      │      │
         ┌────────────▼┐     └──────────────┐
         │ESP32 S3      │                    │
         │MOVILIDAD     │           ┌────────▼────────┐
         │              │           │ESP32 S3         │
         │PWM → Drivers │           │MÉDICA           │
         │Hall ← Motores│           │                 │
         │GPIO ← JSN×5  │           │Steppers × 3     │
         │UART → STM32  │           │Relé → Bomba     │
         └──────────────┘           │I2C sensores     │
                                    │GPIO ← FC-51     │
                                    │UART ← ESP32-CAM │
                                    └────────┬────────┘
                                             │ UART 9600
                                    ┌────────▼────────┐
                                    │   ESP32-CAM     │
                                    │ Detección local │
                                    │ TX booleano     │
                                    └─────────────────┘
```

---

## 6. LEYENDA DEL DIAGRAMA DE COMUNICACIONES

Para el diagrama de Lucidchart — todos los colores en un único diagrama unificado.

### Alimentación

| Color | Hex | Línea |
|-------|-----|-------|
| 🟢 Verde oscuro | `#CC0000` | 29V batería (directo a motores) |
| 🟠 Naranja | `#FF6600` | 19.5V Dell |
| 🟡 Amarillo | `#FFD700` | 12V Kinect |
| 🔴 Rojo oscuro | `#CC0000` | 5V lógica |

### Comunicación digital

| Color | Hex | Tipo |
|-------|-----|------|
| 🔵 Azul oscuro | `#0066CC` | USB (USB 2.0 y USB 3.0) |
| 🟦 Azul claro | `#6699FF` | UART |
| 🟪 Púrpura | `#9966CC` | I2C |
| ⚫ Negro | `#333333` | SPI |
| 🟠 Naranja | `#FF8800` | Conector interno placa (LVDS pantalla · ribbon cámara · ZIF trackpad) |

### Señales de control

| Color | Hex | Tipo |
|-------|-----|------|
| ⚪ Gris claro | `#CCCCCC` | Digital GPIO |
| 🟤 Café | `#996633` | Analógico |
| 🟢 Verde lima | `#66CC00` | PWM motores |

---

## 7. ROUTING DE CABLES — CUELLO

**Dimensiones internas del cuello:** 95 mm × 137 mm = 13,015 mm²

| Cable | Diámetro aprox | Función |
|-------|----------------|---------|
| Alimentación 19.5V (AWG 16) | ~6 mm | Dell |
| Cable pantalla LVDS/eDP | ~5 mm | Display |
| USB 3.0 Kinect | ~8 mm | Datos + audio |
| Cable ZIF trackpad | ~3 mm | HMI input |
| USB parlante | ~5 mm | Audio |

**Área ocupada estimada:** ~15–20 cm²  
**Área disponible:** 130 cm²  
**Utilización:** ~15% ✅ Margen excelente

**Reglas de routing:**
1. Dividir en dos grupos verticales: Zona A potencia (19.5V) · Zona B datos (pantalla, USB, ZIF)
2. Malla expandible o espiral protectora sobre el conjunto
3. **Loop de holgura 10–15 cm** en la unión cuello-cabeza — obligatorio para acomodar inclinación manual 0°–50°
4. **No amarrar cables rígidamente** en la zona de movimiento

---

## 8. GESTIÓN TÉRMICA Y VENTILACIÓN

**Componentes generadores de calor:**

| Zona | Componente | Disipación | Solución |
|------|------------|------------|----------|
| Base | Step-downs × 3 | ~5.5W total | Disipadores 20×20×10mm + pasta térmica + separación ≥5 cm entre módulos |
| Base | Drivers ZS-X11H × 2 | ~10–30W pico | Disipadores integrados ✅ + rejilla salida trasera |
| Torso | Steppers (intermitente) | ~6W pico | Convección natural desde base |
| Pecho | Kinect V2 | ~10W | Ventilador interno ✅ + rejillas laterales |
| Cabeza | Dell placa madre | ~25–30W | Ventilador interno ✅ + rejilla trasera salida |

**Rejillas de ventilación (integrar en CAD):**

| Ubicación | Tamaño | Tipo |
|-----------|--------|------|
| Base lateral × 2 | 40 cm² c/u | Entrada aire fresco (con filtro espuma) |
| Torso trasero | 60 cm² | Salida |
| Pecho lateral × 2 | 15 cm² c/u | Kinect |
| Cabeza trasera | 30 cm² | Salida Dell |

---

## 9. SENSORES DE OBSTÁCULOS — MONTAJE

### JSN-SR04T × 5

```
Vista superior base:

        [Front-L]    [Front-R]
            ○            ○        ← 2 frontales, bordes
          ╱────────────────╲        mirando adelante 0°
         ╱                  ╲
        │  ○              ○  │    ← 2 laterales, esquinas
        │                    │      mirando perpendicular 90°
         ╲        ○         ╱
          ╲────────────────╱       ← 1 trasero, centrado
                                     mirando atrás 180°
```

- Altura de montaje: 10–15 cm del suelo
- Carcasas impresas integradas en carcasa base con ángulos fijos
- Protección contra golpes incluida en el diseño del montaje

### E18-D80NK — ELIMINADOS

*Ver sección 10.4 para justificación y documentación del proceso de evaluación.*

---

## 10. DECISIONES TÉCNICAS DOCUMENTADAS

### 10.1 Configuración batería: 7S4P

**Decisión:** mantener 7S4P.  
Los motores BLDC de 24V (componente dominante en consumo) funcionan directamente con 7S sin convertidor boost. Con 4S se necesitaría boost que perdería ~28W solo en los motores, reduciendo autonomía 36 minutos y añadiendo $70–110 USD en hardware.

### 10.2 Regulador en base vs en cabeza

**Decisión:** XL4016 #1 en la base + cable AWG 16 + ajuste compensatorio a 19.7V.  
Poner el regulador en la cabeza añadiría 2.4W de calor junto al Dell, dificultaría el acceso para ajuste del potenciómetro, y la ganancia en eficiencia de cable (0.43W → 0.21W) no justifica las desventajas.

### 10.3 Control bomba de vacío: módulo relé

**Decisión:** módulo relé 5V 1 canal con optoacoplador.  
El MOSFET IRF520 (opción original) no satura completamente con 3.3V del ESP32 — queda en región lineal con Rds(on) elevado y comportamiento no determinista. El TIP122 (Darlington NPN) es válido pero tiene caída de 0.8–1.2V que reduce el voltaje efectivo a la bomba. El módulo relé entrega 5V completos a la bomba con conmutación limpia y vida útil de >100,000 ciclos, más que suficiente para el uso real del sistema (máximo 3–4 dispensaciones/día).

### 10.4 Sensores anticaída E18-D80NK — eliminados

**Decisión:** eliminar del proyecto en acuerdo de equipo.

**Proceso de evaluación:**
- Probados físicamente a distintas alturas
- Altura mínima de funcionamiento correcto: 15 cm desde el suelo
- Profundidad de montaje resultante en carcasa: 9.4 cm (15 cm – 5.6 cm base)
- Diámetro de agujero de salida requerido: 50 mm (calculado por expansión del haz ±10° en 9.4 cm)
- Problema adicional descubierto: no detectan objetos de color negro (superficies oscuras generan falsos negativos)

**Justificación de eliminación:**
1. El túnel de 9.4 cm con salida de 50 mm compromete estructuralmente la carcasa base
2. Fallos de detección en superficies oscuras hacen el comportamiento no determinista
3. Cobertura redundante por Nav2 en entorno mapeado — el planificador de rutas no genera paths hacia escalones conocidos
4. Velocidad máxima 0.25 m/s da tiempo de reacción suficiente ante cualquier detección ultrasónica

**Documentado como mejora futura:** implementar sensores anticaída en versión 2 con montaje externo en bracket, para operación en entornos no mapeados o con usuarios que reconfiguren el apartamento frecuentemente.

### 10.5 Level shifters para drivers BLDC

**Decisión:** omitir en esta versión.  
Los drivers ZS-X11H fueron probados directamente con señales 3.3V del ESP32 S3 y funcionaron correctamente. A velocidad máxima de 0.25 m/s el ruido eléctrico de los motores es bajo. Si durante pruebas de integración real aparece comportamiento errático (motor no responde, velocidades incorrectas, arranques inconsistentes), el primer diagnóstico es agregar 74HCT125 en las tres señales de control por driver.

---

## 11. CHECKLIST DE FABRICACIÓN

### Pre-impresión 3D

```
☐ Centro de masa validado (~55–60 cm OK)
☐ Batería confirmada en BASE (nivel 1)
☐ Espacio torso suficiente para carrusel + brazo + steppers (mockup cartón si necesario)
☐ Cuello 95×137 mm confirmado para cables
☐ Rejillas ventilación diseñadas:
   ├─☐ Base lateral entrada × 2 (40 cm² c/u)
   ├─☐ Torso trasero salida (60 cm²)
   ├─☐ Pecho lateral × 2 (15 cm² c/u)
   └─☐ Cabeza trasera salida (30 cm²)
☐ Montajes JSN-SR04T × 5 con ángulos fijos (10–15 cm altura)
☐ Recorte pecho para trackpad + numpad + switch ON
☐ Compartimento salida dispensador 58–60 cm tipo cajón extraíble
☐ Soporte Kinect 88 cm estable
☐ Soporte pantalla 110 cm estable
☐ Puertas traseras de mantenimiento (base y torso)
☐ Routing cuello con holgura 10–15 cm en unión cuello-cabeza
☐ Espacio disipadores aluminio en reguladores (separación ≥5 cm entre módulos)
☐ Vista directa ESP32-CAM al punto de depósito del brazo
```

### Ensamblaje electrónico (orden recomendado)

```
1. ☐ Pack 7S4P:
   ├─☐ Soldar celdas en configuración 7S4P
   ├─☐ Balance charge completo
   ├─☐ Conectar BMS (conector balance 8 pines)
   └─☐ Test descarga controlada

2. ☐ Sistema de potencia base:
   ├─☐ Montar reguladores separados ≥5 cm
   ├─☐ Instalar disipadores + pasta térmica
   ├─☐ Cablear batería → BMS → switch → fusible 15A slow-blow → distribución
   ├─☐ Cablear salidas reguladores con fusibles individuales
   └─☐ Ajustar potenciómetros: XL4016#1→19.7V · XL4016#2→12.0V · XL4015→5.0V

3. ☐ Test sin cargas:
   ├─☐ Medir voltajes en todas las salidas
   └─☐ Verificar estabilidad sin deriva

4. ☐ Conectar cargas una por una:
   ├─☐ Dell (medir voltaje bajo carga → debe llegar ~19.5V en la placa)
   ├─☐ Kinect (verificar 12V estable)
   ├─☐ Lógica 5V (bornera + MCUs)
   └─☐ Motores (probar con drivers)

5. ☐ Cable cuello:
   ├─☐ Pasar AWG 16 (19.5V) con loop holgura
   ├─☐ Organizar con malla/espiral
   └─☐ Medir voltaje al final del cable bajo carga: ~19.5V

6. ☐ MCUs y sensores:
   ├─☐ STM32F411 en base
   ├─☐ ESP32 Movilidad en base
   ├─☐ ESP32 Médica en torso
   ├─☐ ESP32-CAM en torso (vista directa cajón)
   └─☐ JSN-SR04T × 5 en montajes fijos

7. ☐ Test funcional por subsistema:
   ├─☐ Movilidad: motores + encoders + ultrasonidos
   ├─☐ Dispensación: steppers + bomba + FC-51 + MPS20N0040D
   ├─☐ Sensores médicos: MAX30102 + sensor temperatura
   └─☐ Comunicaciones: UART STM32 ↔ ESP32s
```

### Validaciones de seguridad

```
☐ Botón emergencia trasero detiene motores instantáneamente
☐ Botón emergencia cabeza detiene motores instantáneamente
☐ JSN-SR04T detienen robot ante obstáculo <30 cm
☐ Fusibles se activan correctamente ante sobrecorriente
☐ BMS protege contra sobredescarga (<21V)
☐ Robot no vuelca con cabeza inclinada 50°
☐ Movimiento estable con carrusel cargado
```

---

*Para arquitectura de software y ROS2: ver `DOCUMENTACION_ROS2.md`*  
*Para sistema conversacional Atlas: ver `DOCUMENTACION_CONVERSACIONAL.md`*  
*Para interfaz gráfica HMI: ver `DOCUMENTACION_HMI.md`*  
*Para contexto general del proyecto: ver `PROYECTO_GENERAL.md`*
