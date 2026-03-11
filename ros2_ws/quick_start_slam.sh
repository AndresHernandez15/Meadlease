#!/bin/bash
# Quick Start - Lanzamiento rápido sin verificaciones
# Usa esto cuando ya sepas que todo está funcionando bien

WORKSPACE_DIR="$HOME/ros2_ws"
cd "$WORKSPACE_DIR"

# Source entorno
source install/setup.bash

# Lanzar kinect2_bridge
gnome-terminal --title="Kinect2 Bridge" -- bash -c "
    cd $WORKSPACE_DIR
    source install/setup.bash
    ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
" &

sleep 5

# Lanzar RTAB-Map
gnome-terminal --title="RTAB-Map SLAM" -- bash -c "
    cd $WORKSPACE_DIR
    source install/setup.bash
    ros2 launch robot_medical slam_real_kinect.launch.py
" &

echo "✓ Sistema lanzado"
echo "  - Kinect2 Bridge: Iniciado"
echo "  - RTAB-Map: Iniciado"
echo ""
echo "Espera 5-10 segundos para que rtabmap_viz aparezca"
