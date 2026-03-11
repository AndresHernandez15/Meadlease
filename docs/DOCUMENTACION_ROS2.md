# DOCUMENTACIÓN TÉCNICA ROS2
## Robot Asistente Médico Domiciliario Meadlese

> **Audiencia:** Andrés (líder software), Juan (apoyo visión)
> **Estado:** Kinect ✅ · SLAM ⏳ · Nav2 ❌ · Nodos médicos ❌ · Atlas-ROS2 ❌
> **Plataforma:** Ubuntu 22.04.5 LTS · ROS2 Humble Hawksbill · Python 3.10
> **Hardware:** Dell Inspiron 3421 · i3-3227U · 12 GB RAM
> **Última actualización:** 2026-03-10

---

## ÍNDICE

1. [Configuración del Sistema](#1-configuración-del-sistema)
2. [Workspace y Estructura de Paquetes](#2-workspace-y-estructura-de-paquetes)
3. [Kinect V2 en ROS2](#3-kinect-v2-en-ros2)
4. [SLAM con RTAB-Map](#4-slam-con-rtab-map)
5. [Navegación con Nav2](#5-navegación-con-nav2)
6. [Arquitectura de Nodos Target](#6-arquitectura-de-nodos-target)
7. [Topics, Services y Actions](#7-topics-services-y-actions)
8. [TF Tree](#8-tf-tree)
9. [Comunicación con Microcontroladores](#9-comunicación-con-microcontroladores)
10. [Estado Actual y Pendientes](#10-estado-actual-y-pendientes)
11. [Problemas Conocidos y Soluciones](#11-problemas-conocidos-y-soluciones)
12. [Comandos de Referencia Rápida](#12-comandos-de-referencia-rápida)

---

## 1. CONFIGURACIÓN DEL SISTEMA

### Software Instalado

```bash
# Sistema base
Ubuntu Desktop 22.04.5 LTS (Jammy Jellyfish)
ROS2 Humble Hawksbill (LTS, soporte hasta 2027)
Python 3.10 (default Ubuntu 22.04)
Build system: colcon

# Paquetes ROS2
ros-humble-desktop              # Core + RViz2 + rqt
ros-humble-navigation2          # Nav2 stack completo
ros-humble-robot-localization
ros-humble-teleop-twist-keyboard

# SLAM RGB-D
rtabmap-ros                     # SLAM 3D nativo para Kinect (no slam-toolbox)

# Driver Kinect V2
kinect2_bridge                  # krepa098/kinect2_ros2 (compilado desde source)
libfreenect2                    # Compilado desde source con soporte OpenCL

# Herramientas
ros-humble-rqt*
ros-humble-tf2-tools
```

### Variables de Entorno

```bash
# Agregar al ~/.bashrc
source /opt/ros/humble/setup.bash
source ~/Meadlease/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1
```

### Información del PC

```
Usuario Ubuntu:  robot
Hostname:        robot-brain
Workspace:       ~/Meadlease/ros2_ws
Kinect Serials:  204763633847 · 299150235147
```

---

## 2. WORKSPACE Y ESTRUCTURA DE PAQUETES

### Estructura Actual

```
~/Meadlease/ros2_ws/
├── src/
│   ├── robot_medical/               # PAQUETE PRINCIPAL ⭐
│   │   ├── launch/
│   │   │   ├── slam_real_kinect.launch.py
│   │   │   ├── slam_simulation.launch.py
│   │   │   └── navigation_simulation.launch.py
│   │   ├── config/                  # YAML configs (en desarrollo)
│   │   ├── maps/
│   │   │   ├── mi_primer_mapa.pgm   # Mapa de prueba (no es el entorno real)
│   │   │   └── mi_primer_mapa.yaml
│   │   └── robot_medical/           # Nodos Python
│   │       ├── __init__.py
│   │       ├── kinect_node.py       # Suscriptor de prueba del Kinect
│   │       └── kinect_mic_test.py   # Test de audio con Kinect
│   │
│   ├── kinect2_ros2/                # Driver Kinect V2
│   │   ├── kinect2_bridge/
│   │   ├── kinect2_calibration/
│   │   └── kinect2_registration/
│   │
│   └── mi_robot/                    # Paquete legacy (pruebas iniciales)
│
├── build/                           # Archivos compilación — ignorar en git
├── install/                         # Ejecutables — ignorar en git
└── log/                             # Logs ROS2 — ignorar en git
```

### Estructura Target del Paquete `robot_medical`

```
robot_medical/
├── launch/
│   ├── bringup.launch.py              # Launch completo del robot
│   ├── slam.launch.py                 # Solo SLAM
│   ├── navigation.launch.py           # Nav2 con mapa existente
│   ├── perception.launch.py           # Visión artificial
│   └── medical.launch.py             # Signos vitales + dispensador
├── config/
│   ├── rtabmap_params.yaml            # Parámetros RTAB-Map optimizados
│   ├── nav2_params.yaml               # Parámetros Nav2
│   ├── robot_description.urdf         # Descripción URDF del robot
│   └── sensors.yaml                   # Configuración sensores
├── maps/
│   └── [mapa real del apartamento]
└── robot_medical/                     # Módulos Python
    ├── __init__.py
    ├── stm32_bridge_node.py           # /cmd_vel → Serial → STM32 → Motores
    ├── ultrasonic_node.py             # Lectura sensores obstáculos
    ├── vital_signs_node.py            # Signos vitales desde ESP32
    ├── medication_node.py             # Control dispensador
    ├── person_detector_node.py        # Detección de personas (Kinect)
    ├── face_recognition_node.py       # Reconocimiento facial
    ├── state_machine_node.py          # Coordinador central
    ├── scheduler_node.py              # Horarios medicamentos
    └── atlas_ros2_node.py             # Bridge Atlas conversacional → ROS2
```

### Comandos de Build

```bash
# Compilar solo robot_medical
cd ~/Meadlease/ros2_ws
colcon build --packages-select robot_medical
source install/setup.bash

# Compilar paquetes propios (más rápido, recomendado en desarrollo)
colcon build --symlink-install \
  --packages-select robot_medical mi_robot \
              kinect2_registration kinect2_bridge

# Compilar todo el workspace
colcon build --symlink-install
source install/setup.bash

# Limpiar y recompilar desde cero
rm -rf build/ install/ log/
colcon build --symlink-install
```

---

## 3. KINECT V2 EN ROS2

### Estado: ✅ Funcionando

El driver `kinect2_bridge` está compilado y estable. El Kinect publica correctamente en todos los topics esperados.

### Topics Disponibles

```bash
# Imágenes QHD — alta resolución, uso pesado
/kinect2/qhd/image_color_rect          # RGB rectificada  (sensor_msgs/Image)
/kinect2/qhd/image_depth_rect          # Depth rectificada (sensor_msgs/Image)
/kinect2/qhd/camera_info               # Parámetros cámara

# Imágenes SD — baja resolución, recomendada para procesamiento
/kinect2/sd/image_color_rect           # RGB SD
/kinect2/sd/image_depth_rect           # Depth SD
/kinect2/sd/camera_info

# PointCloud — muy pesado, usar siempre con filtros
/kinect2/sd/points                     # sensor_msgs/PointCloud2

# Frame de referencia principal
kinect2_rgb_optical_frame
```

### Lanzar el Driver

```bash
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
```

### QoS — Importante

El Kinect publica con QoS **Best Effort**. Al suscribirse desde nodos Python o desde RViz, se debe configurar la misma política:

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)
self.create_subscription(Image, '/kinect2/sd/image_color_rect', callback, qos)
```

```bash
# En RViz: PointCloud2 → Reliability Policy → Best Effort
```

### Verificación

```bash
# Verificar que el Kinect está conectado por USB
lsusb | grep Xbox

# Test raw (ejecutar en la terminal física del Dell, no por SSH)
~/libfreenect2/build/bin/Protonect

# Ver topics activos
ros2 topic list | grep kinect2

# Verificar frecuencia de publicación
ros2 topic hz /kinect2/qhd/image_color_rect
ros2 topic hz /kinect2/sd/points
```

---

## 4. SLAM CON RTAB-MAP

### Estado: ⏳ Funcionando, en optimización

RTAB-Map genera mapas correctamente con el Kinect. La tasa inicial de procesamiento (~0.2 Hz) fue mejorada significativamente con los parámetros optimizados documentados abajo.

### Por Qué RTAB-Map y No SLAM Toolbox

| Criterio | SLAM Toolbox | RTAB-Map |
|----------|-------------|----------|
| Sensor diseñado para | LIDAR 2D | RGB-D (Kinect) |
| Con Kinect | Requiere conversión PointCloud → LaserScan (costoso) | Nativo |
| Resultado | Mapa 2D solamente | Mapa 3D + OccupancyGrid 2D para Nav2 |
| CPU con hardware limitado | Más bajo | Mayor, pero más eficiente para nuestro sensor |
| **Decisión** | ❌ | ✅ |

### Parámetros Optimizados (Producción)

```bash
ros2 launch rtabmap_launch rtabmap.launch.py \
  rgb_topic:=/kinect2/sd/image_color_rect \
  depth_topic:=/kinect2/sd/image_depth_rect \
  camera_info_topic:=/kinect2/sd/camera_info \
  frame_id:=kinect2_rgb_optical_frame \
  subscribe_rgb:=true \
  subscribe_depth:=true \
  approx_sync:=true \
  qos:=2 \
  args:="--delete_db_on_start \
    --Rtabmap/DetectionRate=3.0 \
    --Kp/MaxFeatures=100 \
    --Vis/MaxFeatures=200 \
    --Mem/ImagePostDecimation=4 \
    --Grid/RangeMax=2.5"
```

> **Nota:** Se usan topics `sd` (baja resolución) en lugar de `qhd` para reducir carga computacional. Con el hardware disponible (i3, 12 GB RAM) esto es crítico para mantener fluidez.

### Parámetros Clave Explicados

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| `Rtabmap/DetectionRate` | 3.0 Hz | Limita cuántos frames procesa (no los 30fps del Kinect) |
| `Kp/MaxFeatures` | 100 | Reduce puntos clave por frame → menos CPU |
| `Mem/ImagePostDecimation` | 4 | Reduce resolución interna 4× → menos RAM |
| `Grid/RangeMax` | 2.5 m | Ignora lo que está a más de 2.5 m → menos procesamiento |
| `qos:=2` | Best Effort | Debe coincidir con QoS del Kinect |

### Guardar un Mapa

```bash
# Durante el mapeo, guardar en formato compatible con Nav2
ros2 run nav2_map_server map_saver_cli \
  -f ~/Meadlease/ros2_ws/src/robot_medical/maps/apartamento

# Genera:
# apartamento.pgm    → imagen del mapa (blanco=libre, negro=ocupado, gris=desconocido)
# apartamento.yaml   → metadatos (resolución, origen, etc.)
```

### Diagnóstico RTAB-Map

```bash
# Estado en tiempo real
ros2 topic echo /rtabmap/info

# Visualizar mapa en RViz: Add → /map (nav_msgs/OccupancyGrid)

# Monitor de recursos durante mapeo
htop   # Buscar proceso "rtabmap" → verificar CPU y RAM (esperado ~3-4 GB)
```

---

## 5. NAVEGACIÓN CON NAV2

### Estado: ❌ Pendiente — espera robot físico armado

Nav2 fue probado exitosamente en simulación con TurtleBot3 en Gazebo. Pendiente configuración y prueba en el robot real.

### Arquitectura Nav2

```
[Mapa guardado] ──→ [map_server] ──→ /map
[Kinect + RTAB-Map] ──→ Localización (AMCL o rtabmap_loc) ──→ /odom → /map
[state_machine_node] ──→ /goal_pose
Nav2 ──→ /cmd_vel ──→ [esp32_bridge_node] ──→ STM32 ──→ ESP32 ──→ Motores
```

### Parámetros Clave a Configurar (`nav2_params.yaml`)

```yaml
controller_server:
  ros__parameters:
    max_vel_x: 0.25         # Velocidad máxima 0.25 m/s (restricción de seguridad)
    min_vel_x: -0.1
    max_vel_theta: 0.5
    min_speed_xy: 0.0

local_costmap:
  ros__parameters:
    robot_radius: 0.30      # Radio conservador (base de 55 × 60 cm)

inflation_radius: 0.35      # Margen de seguridad alrededor de obstáculos
```

### Mapa del Entorno Real

El mapa real del apartamento de prueba está pendiente de generarse cuando el robot esté físicamente armado. Los mapas actuales en `maps/` son de prueba y no representan el entorno real de despliegue.

---

## 6. ARQUITECTURA DE NODOS TARGET

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────┐
│                CAPA HMI / USUARIO                   │
│  [atlas_ros2_node]  [hmi_node]  [scheduler_node]    │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│               CAPA DE DECISIÓN                      │
│              [state_machine_node]                   │
└──────┬──────────┬──────────┬────────────┬───────────┘
       │          │          │            │
┌──────▼──┐  ┌───▼────┐ ┌───▼────┐ ┌────▼──────┐
│PERCEPCIÓN│  │NAVEG.  │ │MÉDICA  │ │CONVERSA.  │
│person_   │  │rtabmap │ │vital_  │ │atlas_node │
│detector  │  │nav2    │ │signs   │ │           │
│face_recog│  │        │ │medic.  │ │           │
└──────┬───┘  └───┬────┘ └───┬────┘ └───────────┘
       │          │          │
┌──────▼──────────▼──────────▼────────────────────────┐
│                  CAPA ACTUACIÓN                     │
│  [esp32_bridge_node]       [esp32_medical_node]     │
│  /cmd_vel → Serial → Motores  Serial → Dispensador  │
└─────────────────────────────────────────────────────┘
```

### Nodos Detallados

#### `esp32_bridge_node.py` — Próximo a implementar ⚡

```python
# Función: Convierte /cmd_vel (Twist) a comandos Serial para ESP32
# Input:  /cmd_vel (geometry_msgs/Twist)
# Output: Puerto serial USB → STM32 → UART → ESP32 S3 → Drivers ZS-X11H → Motores BLDC

# Cinemática diferencial:
# wheel_base = 0.40 m
# v_left  = linear.x - angular.z * (wheel_base / 2)
# v_right = linear.x + angular.z * (wheel_base / 2)
#
# Protocolo serial propuesto:
# "VL:{vel_izq:.3f},VR:{vel_der:.3f}\n"   baud: 115200

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial

class ESP32BridgeNode(Node):
    def __init__(self):
        super().__init__('esp32_bridge_node')
        self.wheel_base = 0.40
        self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

    def cmd_vel_callback(self, msg):
        v_l = msg.linear.x - msg.angular.z * (self.wheel_base / 2)
        v_r = msg.linear.x + msg.angular.z * (self.wheel_base / 2)
        self.ser.write(f"VL:{v_l:.3f},VR:{v_r:.3f}\n".encode())
```

#### `state_machine_node.py` — Estados del robot

```
IDLE         → Robot en espera, escuchando wake word "Atlas"
SEARCHING    → Buscando al usuario (navegación + visión)
APPROACHING  → Aproximándose al usuario detectado
IDENTIFIED   → Usuario reconocido (cara verificada)
DISPENSING   → Ejecutando dispensación de medicamento
MEASURING    → Midiendo signos vitales
CONVERSING   → En conversación activa con Atlas
ERROR        → Error, requiere intervención
```

#### `atlas_ros2_node.py` — Bridge conversacional

Encapsula el sistema Atlas existente como nodo ROS2. Ver sección 11 de `DOCUMENTACION_CONVERSACIONAL.md` para la interfaz completa de topics y services.

---

## 7. TOPICS, SERVICES Y ACTIONS

### Sensores (Entrada)

```bash
# Kinect V2
/kinect2/qhd/image_color_rect     # sensor_msgs/Image
/kinect2/qhd/image_depth_rect     # sensor_msgs/Image
/kinect2/qhd/camera_info          # sensor_msgs/CameraInfo
/kinect2/sd/points                # sensor_msgs/PointCloud2

# Odometría (pendiente — desde STM32 + encoders Hall)
/odom                             # nav_msgs/Odometry

# Sensores de obstáculos (pendiente — desde ESP32 Movilidad)
/ultrasonic/front                 # std_msgs/Float32 (cm)
/ultrasonic/rear                  # std_msgs/Float32 (cm)
/ultrasonic/left                  # std_msgs/Float32 (cm)
/ultrasonic/right                 # std_msgs/Float32 (cm)
/anticaida/front_left             # std_msgs/Bool
/anticaida/front_right            # std_msgs/Bool

# Signos vitales (pendiente — desde ESP32 Médica)
/health/bpm                       # std_msgs/Int32
/health/spo2                      # std_msgs/Int32
/health/temperature               # std_msgs/Float32
```

### Control y Actuación (Salida)

```bash
# Movilidad
/cmd_vel                          # geometry_msgs/Twist

# Dispensador
/dispense_medication              # std_msgs/String (nombre medicamento)

# Sistema conversacional
/robot/speak                      # std_msgs/String  (TTS proactivo del robot)
/atlas/listening                  # std_msgs/Bool    (Atlas en escucha activa)
/atlas/detected_command           # std_msgs/String  (comando local detectado)
```

### Navegación

```bash
/map                              # nav_msgs/OccupancyGrid
/goal_pose                        # geometry_msgs/PoseStamped
/rtabmap/info                     # rtabmap_ros/Info
```

### Percepción (Target)

```bash
/person/detected                  # std_msgs/Bool
/person/position                  # geometry_msgs/Point
/patient/identified               # std_msgs/String  (nombre del usuario)
/patient/confidence               # std_msgs/Float32 (confianza del reconocimiento)
```

---

## 8. TF TREE

### Estado Actual

```
kinect2_rgb_optical_frame    ✅  publicado por kinect2_bridge
kinect2_ir_optical_frame     ✅  publicado por kinect2_bridge
map                          ⏳  publicado por RTAB-Map (cuando está activo)
base_link                    ❌  pendiente — requiere URDF del robot
kinect_link                  ❌  pendiente — requiere medición física en robot armado
odom                         ❌  pendiente — requiere odometría desde ESP32 + encoders
```

### TF Tree Target (Completo)

```
map
 └─ odom
     └─ base_link           (centro geométrico del robot, a nivel del suelo)
         ├─ kinect_link      (posición física del Kinect en el robot — medir al armar)
         │   ├─ kinect2_rgb_optical_frame
         │   └─ kinect2_ir_optical_frame
         ├─ camera_link      (cámara portátil para reconocimiento facial)
         ├─ front_ultrasonic_link
         ├─ rear_ultrasonic_link
         ├─ wheel_left_link
         └─ wheel_right_link
```

### Publicar TF Estático Provisional (Hasta Tener URDF)

```python
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped

# VALORES PENDIENTES: medir físicamente en el robot ensamblado
transform = TransformStamped()
transform.header.frame_id = 'base_link'
transform.child_frame_id  = 'kinect_link'
transform.transform.translation.x = 0.0    # TBD: offset frontal (m)
transform.transform.translation.z = 0.88   # TBD: altura del Kinect (aprox 88 cm del suelo)
```

```bash
# Alternativa rápida desde terminal
ros2 run tf2_ros static_transform_publisher 0 0 0.88 0 0 0 base_link kinect_link
```

### Verificar TF Tree

```bash
ros2 run tf2_tools view_frames          # Genera frames.pdf
ros2 run tf2_ros tf2_echo base_link kinect2_rgb_optical_frame
```

---

## 9. COMUNICACIÓN CON MICROCONTROLADORES

### Arquitectura General

```
PC (ROS2) ←── USB-CDC (micro-ROS) ──→ STM32F411 Blackpill
                                           ├── UART1 DMA ──→ ESP32 S3 Movilidad
                                           │                  PWM motores, encoders Hall
                                           │                  Sensores ultrasonido
                                           ├── UART2 DMA ──→ ESP32 S3 Médica
                                           │                  Dispensador + signos vitales
                                           └── GPIO PA0/PA1 ← Botones HMI
```

> El STM32F411 fue elegido como columna vertebral sobre un ESP32 adicional por: 6 UARTs hardware, DMA por canal, latencia determinista en `/cmd_vel` (decisión 2026-03-04). Ver `PROYECTO_GENERAL.md` sección 6 para la justificación completa.

### STM32F411 — micro-ROS

**Estado:** ✅ micro-ROS base validado | ❌ Integración con ESP32s pendiente (espera robot armado)

El STM32 corre como nodo ROS2 nativo vía micro-ROS (USB-CDC): se suscribe a `/cmd_vel` y publica topics de sensores directamente en el grafo ROS2 sin necesidad de un nodo intermediario en el PC.

### ESP32 S3 — Movilidad

**Estado:** ❌ Firmware pendiente

| Elemento | Detalle |
|----------|---------|
| Función | PWM motores BLDC, lectura encoders Hall, sensores ultrasonido |
| Conexión | UART desde STM32F411 |
| Protocolo propuesto | `"VL:{vel:.3f},VR:{vel:.3f}\n"` a 115200 baud |
| Feedback | RPM encoders → `/odom` (vía STM32) |

### ESP32 S3 — Médica

**Estado:** ❌ Firmware pendiente (espera diseño mecánico del dispensador)

| Elemento | Detalle |
|----------|---------|
| Función | Control dispensador + MAX30102 (BPM/SpO₂) + sensor temperatura |
| Topics que publicará | `/health/bpm`, `/health/spo2`, `/health/temperature` |
| Services que recibirá | `/dispense` → {nombre_medicamento} → {éxito / error} |

---

## 10. ESTADO ACTUAL Y PENDIENTES

> **Última actualización:** 2026-03-10

### Resumen por Componente

| Componente | Estado | Detalle |
|------------|--------|---------|
| **Kinect V2** | ✅ Completado | Driver compilado, topics disponibles, SLAM probado |
| **RTAB-Map SLAM** | ⏳ En optimización | Funciona; pendiente mapa real del apartamento |
| **Nav2** | ❌ Pendiente | Probado en simulación; espera robot físico armado |
| **TF tree completo** | ❌ Pendiente | Solo `kinect2_*` disponibles; faltan `base_link`, `odom` |
| **URDF del robot** | ❌ Pendiente | Espera diseño CAD finalizado |
| **`esp32_bridge_node`** | ❌ Pendiente | Próximo nodo crítico a implementar |
| **`vital_signs_node`** | ❌ Pendiente | Espera firmware ESP32 Médica |
| **`medication_node`** | ❌ Pendiente | Espera diseño mecánico del dispensador |
| **`person_detector_node`** | ❌ Pendiente | Port desde Windows a ROS2 |
| **`face_recognition_node`** | ❌ Pendiente | Port desde Windows a ROS2 |
| **`atlas_ros2_node`** | ❌ Pendiente | Atlas completo en Windows ✅; port a ROS2 pendiente |
| **`state_machine_node`** | ❌ Pendiente | Diseñado; pendiente implementación |
| **`scheduler_node`** | ❌ Pendiente | Lógica de horarios en BD ✅; nodo ROS2 pendiente |
| **micro-ROS STM32** | ✅ Base validado | Comunicación básica OK; integración con ESP32 pendiente |
| **Mapa apartamento real** | ❌ Pendiente | Espera robot físico para generarlo con RTAB-Map |

### Próximos Pasos (Orden de Prioridad)

1. **Robot físicamente armado** → desbloquea Nav2, TF tree, URDF, odometría
2. **`esp32_bridge_node`** → primer nodo de actuación real
3. **Port `atlas_ros2_node`** → sistema conversacional en Ubuntu
4. **Port visión artificial** → detección + reconocimiento facial en ROS2
5. **Mapa real del apartamento** → habilita navegación autónoma

---

## 11. PROBLEMAS CONOCIDOS Y SOLUCIONES

### 1. RTAB-Map Lento (0.2 Hz inicial → mejorado con parámetros)

**Causa:** PointCloud QHD pesado + hardware limitado (i3, 12 GB RAM)

**Solución aplicada:**
- Usar topics `sd` en lugar de `qhd`
- `DetectionRate=3.0`, `MaxFeatures=100`, `ImagePostDecimation=4`, `Grid/RangeMax=2.5`

**Si persiste la lentitud:**
```bash
# Agregar VoxelGrid filter antes de RTAB-Map
# Reducir MaxFeatures a 50 si la precisión del mapa lo permite
# Agregar PassThrough filter (solo altura 0.1–1.5 m del suelo)
```

### 2. Kinect "Resource Busy" (LIBUSB_ERROR_BUSY)

**Causa:** Dos procesos intentando usar el Kinect simultáneamente.

**Solución:**
```bash
killall -9 kinect2_bridge Protonect
sleep 2
# Lanzar el proceso deseado
```

### 3. PointCloud2 No Visible en RViz

**Causa:** QoS mismatch — Kinect publica Best Effort, RViz espera Reliable.

**Solución:** RViz → PointCloud2 → **Reliability Policy: Best Effort**

### 4. Sin Ventanas Gráficas por SSH

**Causa:** Sin display X11 forwarding activo.

**Solución:** Ejecutar RViz y herramientas gráficas directamente en la terminal física del Dell. Si hay sesión gráfica activa: `export DISPLAY=:0`

### 5. TF Frames Incompletos

**Causa:** URDF del robot aún no publicado.

**Síntoma:** Warnings `"No transform from [X] to [base_link]"`

**Solución temporal:**
```bash
ros2 run tf2_ros static_transform_publisher 0 0 0.88 0 0 0 base_link kinect_link
```

---

## 12. COMANDOS DE REFERENCIA RÁPIDA

### Kinect V2

```bash
# Verificar conexión USB
lsusb | grep Xbox

# Test raw (ejecutar en PC físico, no SSH)
~/libfreenect2/build/bin/Protonect

# Lanzar driver ROS2
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml

# Verificar topics y frecuencia
ros2 topic list | grep kinect2
ros2 topic hz /kinect2/sd/points
ros2 topic hz /kinect2/qhd/image_color_rect
```

### RTAB-Map (Versión Optimizada)

```bash
# 1. Lanzar Kinect
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml &

# 2. Lanzar RTAB-Map
ros2 launch rtabmap_launch rtabmap.launch.py \
  rgb_topic:=/kinect2/sd/image_color_rect \
  depth_topic:=/kinect2/sd/image_depth_rect \
  camera_info_topic:=/kinect2/sd/camera_info \
  frame_id:=kinect2_rgb_optical_frame \
  subscribe_rgb:=true subscribe_depth:=true \
  approx_sync:=true qos:=2 \
  args:="--delete_db_on_start \
    --Rtabmap/DetectionRate=3.0 --Kp/MaxFeatures=100 \
    --Vis/MaxFeatures=200 --Mem/ImagePostDecimation=4 \
    --Grid/RangeMax=2.5"

# 3. Guardar mapa
ros2 run nav2_map_server map_saver_cli \
  -f ~/Meadlease/ros2_ws/src/robot_medical/maps/apartamento
```

### Workspace

```bash
cd ~/Meadlease/ros2_ws

# Compilar paquete específico
colcon build --packages-select robot_medical && source install/setup.bash

# Compilar todo
colcon build --symlink-install && source install/setup.bash

# Limpiar y recompilar
rm -rf build/ install/ log/ && colcon build --symlink-install
```

### Debugging General

```bash
# Nodos y topics activos
ros2 node list
ros2 topic list

# Info detallada
ros2 node info /kinect2_bridge
ros2 topic echo /rtabmap/info
ros2 topic echo /cmd_vel

# TF tree
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo base_link kinect2_rgb_optical_frame

# Monitor de recursos
htop   # Buscar: rtabmap, kinect2_bridge, python3

# Logs ROS2
ros2 topic echo /rosout

# Teleoperación manual (pruebas)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

*Para contexto general del proyecto: ver `PROYECTO_GENERAL.md`*
*Para el sistema conversacional Atlas: ver `DOCUMENTACION_CONVERSACIONAL.md`*
