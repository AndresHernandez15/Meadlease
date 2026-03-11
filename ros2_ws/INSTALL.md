# Instalación desde cero — ROS2 Workspace (robot médico)

Sistema probado: **Ubuntu 22.04** + **ROS2 Humble**

---

## 1. Requisitos previos del sistema

```bash
# ROS2 Humble (si no está instalado)
# Seguir: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html

# Dependencias del sistema
sudo apt update && sudo apt install -y \
  ros-humble-rtabmap-ros \
  ros-humble-nav2-bringup \
  ros-humble-tf2-tools \
  libusb-1.0-0-dev \
  libturbojpeg0-dev \
  libglfw3-dev \
  mesa-common-dev \
  ocl-icd-libopencl1 \
  opencl-headers \
  ocl-icd-opencl-dev \
  cmake \
  pkg-config \
  python3-colcon-common-extensions
```

---

## 2. Clonar el repositorio

```bash
# (desde el directorio raíz de Meadlease, ya clonado)
cd ~/Meadlease/ros2_ws
```

---

## 3. Instalar libfreenect2

`libfreenect2` es la librería que comunica el Kinect V2 con el sistema.
No está incluida en el repositorio — hay que clonarla y compilarla.

```bash
# Clonar dentro de src/
cd ~/Meadlease/ros2_ws
git clone https://github.com/OpenKinect/libfreenect2.git src/libfreenect2

# Compilar e instalar (instala en /usr via sudo make install)
./recompile_libfreenect2_opencl.sh
```

> El script compila con soporte **OpenCL** para máximo rendimiento.
> Si no tienes GPU compatible, sigue funcionando por CPU (más lento).

---

## 4. Reglas udev para el Kinect (permisos USB)

```bash
# Copiar regla para acceso sin sudo al Kinect V2
sudo cp 81-kinect2-uvcvideo.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# Desconectar y reconectar el Kinect por USB
```

---

## 5. Configurar el entorno en `.bashrc`

Añade estas líneas al final de `~/.bashrc`:

```bash
# ROS2 Humble
source /opt/ros/humble/setup.bash

# Workspace del robot
source ~/Meadlease/ros2_ws/install/setup.bash

# Parámetros de red ROS2 (solo local)
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1
```

Aplica los cambios:

```bash
source ~/.bashrc
```

---

## 6. Compilar el workspace

```bash
cd ~/Meadlease/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

Para recompilar solo los paquetes propios (más rápido):

```bash
colcon build --symlink-install \
  --packages-select robot_medical mi_robot \
                    kinect2_registration kinect2_bridge
```

---

## 7. Verificar la instalación

```bash
# El Kinect aparece como dispositivo
lsusb | grep -i "045e:02c4\|045e:02d8"

# ROS2 reconoce los paquetes
ros2 pkg list | grep -E "robot_medical|kinect2"

# Arrancar el sistema completo (ver QUICK_START.md)
./start_slam_system.sh
```

---

## Estructura del workspace

```
ros2_ws/
├── src/
│   ├── robot_medical/      # Paquete principal (launch files, nodos)
│   ├── mi_robot/           # Paquete base ROS2
│   ├── kinect2_ros2/       # Driver Kinect V2 para ROS2
│   │   ├── kinect2_bridge/
│   │   ├── kinect2_calibration/
│   │   └── kinect2_registration/
│   └── libfreenect2/       # ← NO en el repo, clonar en paso 3
├── config/
│   └── rviz/
│       └── slam.rviz       # Configuración RViz preconfigurada para SLAM
├── Documentacion/
│   └── DOCUMENTACION_ROS2.md
├── maps/                   # Generado en runtime (ignorado por git)
├── recompile_libfreenect2_opencl.sh
├── start_slam_system.sh
├── quick_start_slam.sh
├── reset_rtabmap_db.sh
├── reset_kinect_usb.sh
├── diagnose_mapping.sh
└── 81-kinect2-uvcvideo.rules
```

---

## Próximos pasos

- Ver [QUICK_START.md](QUICK_START.md) para iniciar el sistema SLAM
- Ver [MAPPING_GUIDE.md](MAPPING_GUIDE.md) para generar mapas
- Ver [RTABMAP_SETUP.md](RTABMAP_SETUP.md) para configuración avanzada de RTAB-Map
