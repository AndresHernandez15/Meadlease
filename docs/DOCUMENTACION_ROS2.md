# DOCUMENTACIÓN TÉCNICA ROS2
## Robot Asistente Médico Domiciliario Meadlese

> **Audiencia:** Andrés (líder software), Juan (apoyo)  
> **Framework:** ROS2 Humble Hawksbill  
> **Sistema:** Ubuntu Desktop 22.04.5 LTS — Dell Inspiron 3421  
> **Última actualización:** 2026-03-10

---

## ÍNDICE

1. [Configuración del Sistema](#1-configuración-del-sistema)
2. [Workspace y Estructura de Paquetes](#2-workspace-y-estructura-de-paquetes)
3. [Kinect V2 en ROS2](#3-kinect-v2-en-ros2)
4. [SLAM con RTAB-Map](#4-slam-con-rtab-map)
5. [Navegación con Nav2](#5-navegación-con-nav2)
6. [Arquitectura de Nodos (Target)](#6-arquitectura-de-nodos-target)
7. [Topics, Services y Actions](#7-topics-services-y-actions)
8. [TF Tree](#8-tf-tree)
9. [Comunicación con Microcontroladores](#9-comunicación-con-microcontroladores)
10. [Problemas Conocidos y Soluciones](#10-problemas-conocidos-y-soluciones)
11. [Comandos de Referencia Rápida](#11-comandos-de-referencia-rápida)

---

## 1. CONFIGURACIÓN DEL SISTEMA

### Software Instalado

```bash
# Sistema base
Ubuntu Desktop 22.04.5 LTS (Jammy Jellyfish)
ROS2 Humble Hawksbill (LTS, soporte hasta 2027)
Python 3.10 (default Ubuntu 22.04)
Build System: colcon

# Paquetes ROS2
ros-humble-desktop              # Core + RViz2 + rqt
ros-humble-navigation2          # Nav2 stack completo
ros-humble-slam-toolbox         # SLAM (no se usa, Kinect es RGB-D)
ros-humble-robot-localization
ros-humble-teleop-twist-keyboard

# SLAM RGB-D
rtabmap-ros                     # SLAM 3D nativo para Kinect

# Driver Kinect V2
kinect2_bridge                  # krepa098/kinect2_ros2 (compilado desde source)
libfreenect2                    # Compilado desde source

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
Kinect Serial:   204763633847 / 299150235147
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
│   │   ├── maps/                    # Mapas guardados
│   │   │   ├── mi_primer_mapa.pgm
│   │   │   └── mi_primer_mapa.yaml
│   │   └── robot_medical/           # Nodos Python (en desarrollo)
│   │
│   ├── kinect2_ros2/                # Driver Kinect V2
│   │   ├── kinect2_bridge/
│   │   ├── kinect2_calibration/
│   │   └── kinect2_registration/
│   │
│   └── mi_robot/                    # Paquete pruebas iniciales (legacy)
│
├── build/                           # Archivos compilación (ignorar)
├── install/                         # Ejecutables (ignorar)
└── log/                             # Logs ROS2 (ignorar)
```

### Estructura Target (Paquete robot_medical)

```
robot_medical/
├── launch/
│   ├── bringup.launch.py              # Launch completo del robot
│   ├── slam.launch.py                 # Solo SLAM
│   ├── navigation.launch.py           # Nav2 con mapa existente
│   ├── perception.launch.py           # Visión artificial
│   └── medical.launch.py              # Signos vitales + dispensador
├── config/
│   ├── rtabmap_params.yaml            # Parámetros RTAB-Map optimizados
│   ├── nav2_params.yaml               # Parámetros Nav2
│   ├── robot_description.urdf         # Descripción URDF del robot
│   └── sensors.yaml                   # Configuración sensores
├── maps/
│   └── [mapas del apartamento]
├── robot_medical/                     # Módulos Python
│   ├── __init__.py
│   ├── esp32_bridge_node.py           # /cmd_vel → Serial → ESP32 → Motores
│   ├── ultrasonic_node.py             # Lectura sensores obstáculos
│   ├── vital_signs_node.py            # Signos vitales desde ESP32
│   ├── medication_node.py             # Control dispensador
│   ├── person_detector_node.py        # Detección de personas
│   ├── face_recognition_node.py       # Reconocimiento facial
│   ├── state_machine_node.py          # Coordinador central
│   ├── scheduler_node.py              # Horarios medicamentos
│   └── atlas_ros2_node.py             # Bridge Atlas conversacional → ROS2
├── package.xml
├── setup.py
└── CMakeLists.txt
```

### Comandos de Build

```bash
# Compilar solo robot_medical
cd ~/Meadlease/ros2_ws
colcon build --packages-select robot_medical
source install/setup.bash

# Compilar paquetes propios (más rápido)
colcon build --symlink-install \
  --packages-select robot_medical mi_robot \
              kinect2_registration kinect2_bridge

# Compilar todo el workspace
colcon build --symlink-install
source install/setup.bash

# Limpiar y recompilar desde cero
rm -rf build/ install/ log/
colcon build --symlink-install

# Ver estructura del workspace
tree ~/Meadlease/ros2_ws/src -L 2
```

---

## 3. KINECT V2 EN ROS2

### Estado: ✅ Funcionando

El driver `kinect2_bridge` está compilado y estable. El Kinect publica correctamente en todos los topics esperados.

### Topics Disponibles

```bash
# Imágenes QHD (alta resolución - pesado)
/kinect2/qhd/image_color_rect          # RGB rectificada (sensor_msgs/Image)
/kinect2/qhd/image_depth_rect          # Depth rectificada (sensor_msgs/Image)
/kinect2/qhd/camera_info               # Parámetros cámara

# Imágenes SD (baja resolución - optimizado para procesamiento)
/kinect2/sd/image_color_rect           # RGB SD
/kinect2/sd/image_depth_rect           # Depth SD
/kinect2/sd/camera_info

# PointCloud (muy pesado, usar con filtros)
/kinect2/sd/points                     # PointCloud2

# Frame principal
kinect2_rgb_optical_frame
```

### Lanzar el Driver

```bash
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
```

### QoS Importante

El Kinect publica con QoS **Best Effort**. Al suscribirse desde otros nodos o desde RViz, se debe configurar la misma política:

```python
# En Python (rclpy)
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)
subscription = self.create_subscription(Image, '/kinect2/sd/image_color_rect', callback, qos)
```

```bash
# En RViz: PointCloud2 settings → Reliability Policy: Best Effort
```

### Verificación

```bash
# Verificar que el Kinect está conectado
lsusb | grep Xbox

# Test directo (requiere estar físicamente en el PC, no SSH)
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

RTAB-Map está generando mapas correctamente con el Kinect. La tasa de procesamiento (~0.2 Hz inicial) fue mejorada aplicando los parámetros optimizados.

### Por qué RTAB-Map y no SLAM Toolbox

| Criterio | SLAM Toolbox | RTAB-Map |
|----------|-------------|----------|
| Sensor diseñado para | LIDAR 2D | RGB-D (Kinect) |
| Con Kinect | Requiere conversión PointCloud→LaserScan (hack costoso) | Nativo |
| Resultado | Mapa 2D solamente | Mapa 3D + OccupancyGrid 2D para Nav2 |
| CPU usage | Más bajo | Mayor, pero más eficiente para nuestro sensor |
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

> **Nota:** Se usan topics `sd` (baja resolución) en lugar de `qhd` para reducir carga computacional. Con hardware limitado (i3, 12GB RAM), esto es esencial.

### Parámetros Clave Explicados

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| `Rtabmap/DetectionRate` | 3.0 Hz | Limita cuántos frames procesa (no todos los 30fps del Kinect) |
| `Kp/MaxFeatures` | 100 | Reduce puntos clave por frame → menos CPU |
| `Mem/ImagePostDecimation` | 4 | Reduce resolución interna 4x → menos RAM |
| `Grid/RangeMax` | 2.5m | Ignora lo que está a más de 2.5m → menos procesamiento |
| `qos:=2` | Best Effort | Debe coincidir con QoS del Kinect |

### Guardar un Mapa

```bash
# Durante el mapeo, guardar en formato compatible con Nav2
ros2 run nav2_map_server map_saver_cli -f ~/Meadlease/ros2_ws/src/robot_medical/maps/apartamento

# Genera:
# apartamento.pgm    → imagen del mapa (blanco=libre, negro=ocupado, gris=desconocido)
# apartamento.yaml   → metadatos (resolución, origen, etc.)
```

### Diagnóstico RTAB-Map

```bash
# Ver estado en tiempo real
ros2 topic echo /rtabmap/info

# Ver mapa en RViz
# Abrir RViz → Add → /map (nav_msgs/OccupancyGrid)

# Monitor de recursos durante mapeo
htop
# Buscar proceso "rtabmap" → verificar RAM y CPU
```

---

## 5. NAVEGACIÓN CON NAV2

### Estado: ❌ Pendiente pruebas en robot físico

Nav2 fue probado exitosamente en simulación con TurtleBot3 en Gazebo. Pendiente configuración y prueba en el robot real cuando esté armado.

### Arquitectura Nav2

```
[Mapa guardado] → [map_server] → /map
[Kinect/RTAB-Map] → Localización (AMCL o rtabmap_localization) → /odom → /map
[Usuario/Estado Machine] → /goal_pose
Nav2 → /cmd_vel → [esp32_bridge_node] → ESP32 → Motores
```

### Parámetros Clave a Configurar (nav2_params.yaml)

```yaml
# Velocidades (seguridad = prioridad)
controller_server:
  ros__parameters:
    max_vel_x: 0.25         # Máximo 0.25 m/s (seguridad)
    min_vel_x: -0.1
    max_vel_theta: 0.5
    min_speed_xy: 0.0

# Footprint del robot (40cm x 50cm)
local_costmap:
  ros__parameters:
    robot_radius: 0.30      # Radio conservador para navegación segura

# Inflation para obstáculos
inflation_radius: 0.35      # Margen alrededor de obstáculos
```

### Mapa del Apartamento (Pendiente)

El mapa real del apartamento de prueba está pendiente de ser generado cuando el robot esté físicamente armado. Los mapas de prueba actuales (`mi_primer_mapa.pgm/yaml`) se encuentran en `~/Meadlease/ros2_ws/src/robot_medical/maps/` pero no representan el entorno real de despliegue.

---

## 6. ARQUITECTURA DE NODOS (TARGET)

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────┐
│                  CAPA HMI / USUARIO                  │
│   [atlas_ros2_node]  [hmi_node]  [scheduler_node]    │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│               CAPA DE DECISIÓN                       │
│              [state_machine_node]                     │
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
│                  CAPA ACTUACIÓN                       │
│  [esp32_bridge_node]     [esp32_medical_node]         │
│  /cmd_vel→Serial→Motores  Serial→Dispensador+Sensores │
└─────────────────────────────────────────────────────┘
```

### Nodos Detallados

#### esp32_bridge_node (Próximo a implementar ⚡)

```python
# Función: Convierte /cmd_vel (Twist) a comandos Serial para ESP32
# Input:  /cmd_vel (geometry_msgs/Twist)
# Output: Puerto serial USB → ESP32 S3 → Drivers ZS-X11H → Motores BLDC

# Cinemática diferencial:
# wheel_base = 0.40m (ancho de la base)
# v_left  = linear.x - angular.z * (wheel_base / 2)
# v_right = linear.x + angular.z * (wheel_base / 2)

# Protocolo serial (TBD, propuesta):
# Formato: "VL:{velocidad_izq},VR:{velocidad_der}\n"
# Baud rate: 115200
```

#### state_machine_node

```
Estados:
├── IDLE         → Robot en espera, escuchando wake word "Atlas"
├── SEARCHING    → Buscando al usuario (navegación + visión)
├── APPROACHING  → Aproximándose al usuario detectado
├── IDENTIFIED   → Usuario reconocido (cara verificada)
├── DISPENSING   → Ejecutando dispensación de medicamento
├── MEASURING    → Midiendo signos vitales
├── CONVERSING   → En conversación activa con Atlas
└── ERROR        → Error, requiere intervención
```

---

## 7. TOPICS, SERVICES Y ACTIONS

### Topics de Entrada (Sensores)

```bash
# Kinect
/kinect2/qhd/image_color_rect     # sensor_msgs/Image
/kinect2/qhd/image_depth_rect     # sensor_msgs/Image
/kinect2/qhd/camera_info          # sensor_msgs/CameraInfo
/kinect2/sd/points                # sensor_msgs/PointCloud2

# Odometría (pendiente)
/odom                             # nav_msgs/Odometry

# Sensores obstáculos (pendiente - desde ESP32)
/ultrasonic/front                 # std_msgs/Float32 (cm)
/ultrasonic/rear                  # std_msgs/Float32 (cm)
/ultrasonic/left                  # std_msgs/Float32 (cm)
/ultrasonic/right                 # std_msgs/Float32 (cm)
/anticaida/front_left             # std_msgs/Bool
/anticaida/front_right            # std_msgs/Bool

# Signos vitales (pendiente - desde ESP32)
/health/bpm                       # std_msgs/Int32
/health/spo2                      # std_msgs/Int32
/health/temperature               # std_msgs/Float32
```

### Topics de Control (Salida)

```bash
# Movilidad
/cmd_vel                          # geometry_msgs/Twist

# Dispensador
/dispense_medication              # std_msgs/String (nombre medicamento)

# Conversacional
/robot/speak                      # std_msgs/String (texto para Atlas)
/robot/listening                  # std_msgs/Bool (Atlas escuchando?)
```

### Topics de Navegación

```bash
/map                              # nav_msgs/OccupancyGrid
/goal_pose                        # geometry_msgs/PoseStamped
/rtabmap/info                     # rtabmap_ros/Info
```

### Topics de Percepción (Target)

```bash
/person/detected                  # std_msgs/Bool
/person/position                  # geometry_msgs/Point
/patient/identified               # std_msgs/String (nombre del usuario)
/patient/confidence               # std_msgs/Float32 (confianza reconocimiento)
```

---

## 8. TF TREE

### Estado Actual

```
kinect2_rgb_optical_frame    ✅ (publicado por kinect2_bridge)
kinect2_ir_optical_frame     ✅ (publicado por kinect2_bridge)
base_link                    ❌ PENDIENTE (necesita URDF del robot)
kinect_link                  ❌ PENDIENTE (posición exacta Kinect en robot)
odom                         ❌ PENDIENTE (necesita odometría ESP32)
map                          ⏳ (publicado por RTAB-Map cuando está activo)
```

### TF Tree Target (Completo)

```
map
 └─ odom
     └─ base_link  (centro geométrico del robot, a nivel del suelo)
         ├─ kinect_link  (posición física del Kinect en el robot)
         │   ├─ kinect2_rgb_optical_frame
         │   └─ kinect2_ir_optical_frame
         ├─ camera_link  (cámara del portátil para reconocimiento facial)
         ├─ front_ultrasonic_link
         ├─ rear_ultrasonic_link
         └─ wheel_left_link
         └─ wheel_right_link
```

### Cómo Publicar el TF base_link → kinect_link

```python
# En robot_description.urdf o en un nodo estático:
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped

# VALORES PENDIENTES: Medir físicamente en el robot ensamblado
# x = offset frontal del Kinect desde el centro del robot (metros)
# z = altura del Kinect desde el suelo (metros)
transform = TransformStamped()
transform.header.frame_id = 'base_link'
transform.child_frame_id = 'kinect_link'
transform.transform.translation.x = 0.0   # TBD: medir
transform.transform.translation.z = 0.8   # TBD: medir (aprox 80cm del suelo)
```

### Verificar TF Tree

```bash
ros2 run tf2_tools view_frames
# Genera: frames.pdf en el directorio actual

# Ver transform en tiempo real
ros2 run tf2_ros tf2_echo base_link kinect2_rgb_optical_frame
```

---

## 9. COMUNICACIÓN CON MICROCONTROLADORES

### ESP32 S3 - Movilidad (Próximo a implementar)

**Función:** Recibir comandos de velocidad desde ROS2 y controlar los motores BLDC vía drivers ZS-X11H.

**Protocolo propuesto:**

```
PC (ROS2) → USB Serial → ESP32 S3 → PWM → Drivers ZS-X11H → Motores BLDC
                                   ← Encoders Hall (RPM feedback)
```

**Nodo ROS2 (esp32_bridge_node.py):**

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial

class ESP32BridgeNode(Node):
    def __init__(self):
        super().__init__('esp32_bridge_node')
        
        # Parámetros del robot
        self.wheel_base = 0.40   # metros (ancho de la base)
        
        # Serial con ESP32
        self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        
        # Suscripción a cmd_vel
        self.subscription = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
    
    def cmd_vel_callback(self, msg):
        linear = msg.linear.x
        angular = msg.angular.z
        
        # Cinemática diferencial
        v_left  = linear - angular * (self.wheel_base / 2)
        v_right = linear + angular * (self.wheel_base / 2)
        
        # Enviar a ESP32 (protocolo TBD)
        command = f"VL:{v_left:.3f},VR:{v_right:.3f}\n"
        self.ser.write(command.encode())
```

**Estado:** ❌ Pendiente implementación (próximo paso crítico)

### ESP32 S3 - Médica

**Función:** Control del dispensador de medicamentos y lectura de sensores biomédicos.

**Topics que publicará:**
- `/health/bpm` → std_msgs/Int32
- `/health/spo2` → std_msgs/Int32
- `/health/temperature` → std_msgs/Float32

**Servicios que recibirá:**
- `/dispense` → request: nombre medicamento, response: éxito/error

**Estado:** ❌ Pendiente diseño del firmware (espera diseño mecánico)

### STM32F411 Blackpill — MCU Auxiliar (Decisión tomada 2026-03-04)

**Función:** Columna vertebral de comunicaciones. Corre micro-ROS (USB-CDC ↔ PC), enruta comandos por UART a ambos ESP32 y lee botones HMI por GPIO.

**Por qué STM32F411 sobre ESP32 adicional:**

| Criterio | STM32F411 ✅ | ESP32 adicional ❌ |
|----------|-------------|-------------------|
| UARTs hardware | 6 | 2-3 (con conflictos) |
| DMA por canal | Sí | Limitado |
| Latencia `/cmd_vel` | Determinista | Variable (WiFi/ESP-NOW) |
| micro-ROS | Validado ✅ | Compatible, no probado |

**Estado:** micro-ROS base validado ✅ | Integración con ESP32s ❌ (espera robot armado)

---

## 10. PROBLEMAS CONOCIDOS Y SOLUCIONES

### 1. RTAB-Map Lento (estaba a 0.2 Hz, mejorado)

**Causa:** PointCloud QHD pesado + hardware limitado (i3 + 12GB RAM)

**Solución aplicada:**
- Usar topics `sd` (baja resolución) en lugar de `qhd`
- Parámetros optimizados: `DetectionRate=3.0`, `MaxFeatures=100`, `ImagePostDecimation=4`
- `Grid/RangeMax=2.5` para ignorar datos lejanos

**Si sigue siendo lento (soluciones adicionales):**
```bash
# Agregar VoxelGrid filter antes de RTAB-Map
# Agregar PassThrough filter (solo altura entre 0.1m y 1.5m del suelo)
# Reducir aún más MaxFeatures si la precisión del mapa lo permite
```

### 2. Kinect "Resource Busy" (LIBUSB_ERROR_BUSY)

**Causa:** Dos procesos intentando usar el Kinect simultáneamente

**Solución:**
```bash
killall -9 kinect2_bridge Protonect
sleep 2
# Luego lanzar el proceso deseado
```

### 3. PointCloud2 No Visible en RViz

**Causa:** QoS mismatch (Kinect publica Best Effort, RViz espera Reliable)

**Solución:** RViz → PointCloud2 → Reliability Policy: **Best Effort**

### 4. Sin Ventanas Gráficas por SSH

**Causa:** Sin display X11 forwarding

**Solución:** Ejecutar RViz y herramientas gráficas directamente en terminal física del Dell (o usar `DISPLAY=:0` si hay sesión gráfica activa)

### 5. TF Frames Incompletos

**Causa:** URDF del robot no publicado aún

**Síntoma:** Warnings "No transform from [X] to [base_link]"

**Solución temporal:** Publicar transforms estáticos manualmente hasta tener el URDF completo:
```bash
ros2 run tf2_ros static_transform_publisher 0 0 0.8 0 0 0 base_link kinect_link
```

---

## 11. COMANDOS DE REFERENCIA RÁPIDA

### Kinect V2

```bash
# Verificar conexión USB
lsusb | grep Xbox

# Test raw (ejecutar directamente en PC, no SSH)
~/libfreenect2/build/bin/Protonect

# Lanzar driver ROS2
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml

# Verificar topics activos
ros2 topic list | grep kinect2

# Monitorear frecuencia
ros2 topic hz /kinect2/sd/points
ros2 topic hz /kinect2/qhd/image_color_rect
```

### RTAB-Map (Versión Optimizada)

```bash
# Asegurarse de que Kinect ya está corriendo
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml &

# Lanzar RTAB-Map optimizado
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

# Guardar mapa
ros2 run nav2_map_server map_saver_cli -f ~/Meadlease/ros2_ws/src/robot_medical/maps/apartamento
```

### Workspace

```bash
# Compilar paquete específico
cd ~/Meadlease/ros2_ws
colcon build --packages-select robot_medical
source install/setup.bash

# Compilar todo
colcon build --symlink-install && source install/setup.bash

# Limpiar todo
rm -rf build/ install/ log/ && colcon build --symlink-install

# Ver estructura
tree ~/Meadlease/ros2_ws/src -L 3
```

### Debugging General

```bash
# Ver todos los nodos activos
ros2 node list

# Info de un nodo
ros2 node info /kinect2_bridge

# Ver todos los topics
ros2 topic list

# Echo de un topic
ros2 topic echo /cmd_vel
ros2 topic echo /rtabmap/info

# TF Tree
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo base_link kinect2_rgb_optical_frame

# Monitor del sistema
htop
# Buscar: rtabmap, kinect2_bridge, python3

# Ver logs de un nodo
ros2 topic echo /rosout
```

### Teleoperación

```bash
# Control manual con teclado (para pruebas)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# Publica en /cmd_vel
```

---

## 12. NOTAS DE DESARROLLO

### Código Python ROS2
- Python 3.10 (Ubuntu 22.04)
- Usar `rclpy`, **nunca** `rospy` (eso es ROS1)
- Imports específicos: `from geometry_msgs.msg import Twist`
- PEP8 + type hints + docstrings
- Un nodo = una responsabilidad

### Restricciones de hardware
- CPU i3-3227U, 12 GB RAM → optimización crítica
- Sin GPU: no usar modelos de visión que requieran CUDA
- QoS Best Effort para todos los topics del Kinect
- Velocidad máxima `/cmd_vel`: `linear.x <= 0.25`, `angular.z <= 0.5`

### Estado del TF tree
- `kinect2_rgb_optical_frame` ✅ disponible
- `base_link` ❌ aún no publicado (requiere URDF)
- Usar `kinect2_rgb_optical_frame` como `frame_id` para RTAB-Map hasta tener URDF completo

---

*Para contexto general del proyecto: ver `PROYECTO_GENERAL.md`*  
*Para el módulo conversacional Atlas: ver `DOCUMENTACION_CONVERSACIONAL.md`*
