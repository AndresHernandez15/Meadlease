# 🚀 RTAB-MAP con Kinect V2 - Guía Rápida

## ✅ Cambios Aplicados

### 1. Configuración Kinect Optimizada
- ✅ `publish_tf: true` (reactivado para RTAB-Map)
- ✅ `bilateral_filter: false` (optimización rendimiento)
- ✅ `edge_aware_filter: false` (optimización rendimiento)
- ✅ `queue_size: 2` (menor latencia)

### 2. Launch File RTAB-Map Creado
- **Archivo:** `src/robot_medical/launch/slam_real_kinect.launch.py`
- **Configuración:** Topics SD (512×424) para mejor rendimiento
- **Parámetros optimizados para hardware limitado**

## 🎯 Cómo Usar

### Opción A: Script Automático (Recomendado)
```bash
cd ~/ros2_ws
./test_rtabmap_kinect.sh
```

Luego en **otra terminal**:
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch robot_medical slam_real_kinect.launch.py
```

### Opción B: Comandos Manuales

**Terminal 1 - Kinect:**
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch kinect2_bridge kinect2_bridge_launch.yaml
```

**Terminal 2 - RTAB-Map:**
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch robot_medical slam_real_kinect.launch.py
```

**Terminal 3 - Monitoreo (Opcional):**
```bash
source ~/ros2_ws/install/setup.bash

# Ver rendimiento RTAB-Map (objetivo: 1-2 Hz)
ros2 topic hz /rtabmap/info

# Ver rendimiento Kinect
ros2 topic hz /kinect2/sd/image_color_rect
ros2 topic hz /kinect2/sd/image_depth_rect

# Ver mapa en RViz
rviz2
```

## 📊 Rendimiento Esperado

### Con CPU (actual):
- **Kinect SD:** ~5-15 Hz
- **RTAB-Map:** ~0.5-1.5 Hz (mejorado vs antes)

### Con OpenCL (futuro, si recompilas):
- **Kinect SD:** ~25-30 Hz
- **RTAB-Map:** ~2-4 Hz

## 🔍 Verificación

### Comprobar que funciona:
```bash
# Topics activos
ros2 topic list | grep -E "kinect2|rtabmap"

# Debería mostrar:
# /kinect2/sd/image_color_rect
# /kinect2/sd/image_depth_rect
# /rtabmap/info
# /rtabmap/mapData
# /odom
# /map

# Ver TF tree
ros2 run tf2_tools view_frames
# Genera frames.pdf mostrando: map → odom → base_link → kinect2_rgb_optical_frame
```

## 🛠️ Troubleshooting

### Problema: "No publishers on /kinect2/sd/..."
**Solución:** Verifica que kinect2_bridge esté corriendo:
```bash
ros2 node list | grep kinect2
```

### Problema: RTAB-Map muy lento (<0.5 Hz)
**Solución:** 
1. Configura `DetectionRate` más alto (3-4 Hz) en el launch file
2. O recompila libfreenect2 con OpenCL (mejora 100x)

### Problema: "No transform from base_link to kinect2_rgb_optical_frame"
**Solución:** Verifica que `publish_tf: true` en kinect2_bridge_launch.yaml

## 🎯 Próximos Pasos

1. **Ahora:** Prueba el sistema y mapea una habitación pequeña
2. **Si funciona bien:** Mapea todo el apartamento moviendo el robot
3. **Si es lento:** Ejecuta `./recompile_libfreenect2_opencl.sh` para 100x mejora

## 📝 Configuración para Nav2

Una vez tengas un mapa guardado, puedes usarlo con Nav2:

```bash
# Guardar mapa RTAB-Map
ros2 service call /rtabmap/save_map std_srvs/srv/Empty

# Luego usar con Nav2 (próximo paso del proyecto)
ros2 launch robot_medical navigation_real.launch.py
```

---

**Creado:** 26 Febrero 2026  
**Hardware:** Dell 12GB RAM, 4 cores, Kinect V2  
**Objetivo:** SLAM 3D para robot médico en apartamento
