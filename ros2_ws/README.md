# ROS2 Workspace — Meadlease

> **Plataforma:** Ubuntu 22.04 · ROS2 Humble · Python 3.10  
> **Responsable:** Andrés

## Instalación rápida

```bash
# 1. Clonar el repo y entrar al workspace
cd Meadlease/ros2_ws

# 2. Instalar dependencias
rosdep install --from-paths src --ignore-src -r -y

# 3. Compilar
colcon build --packages-select robot_medical
source install/setup.bash
```

## Variables de entorno requeridas

Agregar al `~/.bashrc`:

```bash
source /opt/ros/humble/setup.bash
source ~/Meadlease/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

## Lanzar el sistema

```bash
# Solo Kinect
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml

# SLAM + Kinect
ros2 launch robot_medical slam.launch.py

# Navegación completa
ros2 launch robot_medical bringup.launch.py
```

## Estructura del paquete principal

```
robot_medical/
├── launch/          # Launch files
├── config/          # Parámetros YAML (Nav2, RTAB-Map)
├── maps/            # Mapas generados (no versionados)
└── robot_medical/   # Nodos Python
```

Ver [DOCUMENTACION_ROS2.md](../docs/DOCUMENTACION_ROS2.md) para referencia completa.
