# 🤖 GUÍA RÁPIDA - SISTEMA SLAM ROBOT MÉDICO

## 🚀 Inicio Rápido

### Opción 1: Lanzamiento Completo (Recomendado)
Verifica todo el sistema y lanza con monitoreo:
```bash
./start_slam_system.sh
```

**Características:**
- ✅ Verifica Kinect conectado
- ✅ Verifica RAM disponible  
- ✅ Detecta si OpenCL está habilitado
- ✅ Lanza kinect2_bridge
- ✅ Lanza RTAB-Map con visualización
- ✅ Monitor en tiempo real con estadísticas
- ✅ Opción de resetear mapa

---

### Opción 2: Inicio Rápido (Avanzado)
Si ya sabes que todo funciona:
```bash
./quick_start_slam.sh
```

**Solo lanza:**
- kinect2_bridge
- RTAB-Map SLAM

---

## 📊 Monitoreo Manual

### Ver frecuencia de topics:
```bash
# Kinect RGB
ros2 topic hz /kinect2/sd/image_color_rect

# Kinect Depth  
ros2 topic hz /kinect2/sd/image_depth_rect

# RTAB-Map
ros2 topic hz /rtabmap/info
```

### Ver nodos activos:
```bash
ros2 node list | grep -E 'kinect|rtabmap'
```

### Ver estadísticas RTAB-Map:
```bash
ros2 topic echo /rtabmap/info
```

---

## 🗺️ Técnica de Mapeo

### Reglas de Oro:
1. **VELOCIDAD:** 5-10 cm/segundo (MUY LENTO)
2. **PAUSAS:** 2-3 segundos cada 20-30cm
3. **TEXTURA:** Apunta a muebles, cuadros, objetos (NO paredes lisas)
4. **OBSERVA:** Verde en rtabmap_viz = OK, Rojo = perdió tracking
5. **LOOP CLOSURE:** Vuelve al punto inicial para cerrar el bucle

### Estrategia de Mapeo:
```
1. Comienza en un punto con buena textura (ej: esquina con muebles)
2. Avanza lentamente en sentido horario/antihorario
3. Pausa cada 20cm
4. Mapea perímetro completo de la habitación
5. Vuelve al punto inicial (loop closure)
6. Repite para cada habitación
```

---

## 🔧 Utilidades

### Resetear mapa:
```bash
./reset_rtabmap_db.sh
```

### Diagnosticar sistema:
```bash
./diagnose_mapping.sh
```

### Mejorar rendimiento (OpenCL):
```bash
./recompile_libfreenect2_opencl.sh
```
**Mejora:** 100-300x más rápido  
**Tiempo:** 10-15 minutos

---

## 💾 Guardar y Cargar Mapas

### Guardar mapa actual:
```bash
ros2 service call /rtabmap/save_map std_srvs/srv/Empty
```

### Ver estadísticas del mapa:
```bash
rtabmap-databaseViewer ~/.ros/rtabmap.db
```

---

## 🛑 Detener Sistema

1. **Ctrl+C** en cada terminal
2. O simplemente cierra las ventanas

---

## ⚡ Indicadores de Rendimiento

### Excelente:
- Kinect RGB: **10-30 Hz**
- Kinect Depth: **10-30 Hz** (con OpenCL)
- RTAB-Map: **2-5 Hz**
- Color: **VERDE** constante en rtabmap_viz

### Aceptable:
- Kinect RGB: **5-15 Hz**
- Kinect Depth: **0.5-5 Hz** (sin OpenCL)
- RTAB-Map: **0.5-1 Hz**
- Color: Verde con **amarillo ocasional**

### Problemático:
- Kinect Depth: **< 0.5 Hz**
- RTAB-Map: **< 0.3 Hz**
- Color: **ROJO** frecuente
- **Solución:** Recompila con OpenCL

---

## 📝 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `start_slam_system.sh` | Script maestro con verificaciones |
| `quick_start_slam.sh` | Lanzamiento rápido |
| `diagnose_mapping.sh` | Diagnóstico del sistema |
| `reset_rtabmap_db.sh` | Borrar mapa |
| `recompile_libfreenect2_opencl.sh` | Optimizar con OpenCL |
| `~/.ros/rtabmap.db` | Base de datos del mapa |

---

## 🎯 Resumen de Comandos

```bash
# INICIAR
./start_slam_system.sh              # Completo con verificaciones
./quick_start_slam.sh               # Rápido

# MONITOREAR  
./diagnose_mapping.sh               # Estado del sistema
ros2 topic hz /rtabmap/info         # Frecuencia RTAB-Map

# MANTENIMIENTO
./reset_rtabmap_db.sh               # Borrar mapa
./recompile_libfreenect2_opencl.sh  # Optimizar rendimiento

# GUARDAR
ros2 service call /rtabmap/save_map std_srvs/srv/Empty
```

---

## ⚠️ Troubleshooting

### Problema: Kinect no detectado
```bash
lsusb | grep 045e:02c4  # Debe aparecer
# Si no: reconecta USB y alimentación
```

### Problema: "Resource busy"
```bash
sudo modprobe -r uvcvideo
# Reconecta Kinect
```

### Problema: Tracking rojo constante
1. Muévete MÁS LENTO
2. Apunta a zonas con textura
3. Verifica OpenCL habilitado
4. Aumenta iluminación

### Problema: Rendimiento muy bajo
```bash
./recompile_libfreenect2_opencl.sh
# Luego recompila:
cd ~/ros2_ws
colcon build --packages-select kinect2_registration kinect2_bridge
```

---

## 📚 Documentación Completa

- `RTABMAP_SETUP.md` - Configuración RTAB-Map
- `MAPPING_GUIDE.md` - Guía completa de mapeo
- `PROJECT_CONTEXT.MD` - Contexto del proyecto

---

**Autor:** Robot Médico - Proyecto TFG  
**Fecha:** Febrero 2026  
**Hardware:** Kinect V2 + RTAB-Map + ROS2 Humble
