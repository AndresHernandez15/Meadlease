# Visión Artificial — Meadlease

> **Responsable:** Juan  
> **Estado:** ❌ Pendiente — por iniciar

## Objetivo

- Detección de personas en el entorno del robot (silueta/skeleton con Kinect V2)
- Reconocimiento facial para identificar usuarios registrados (mínimo 2 usuarios)

## Integración con ROS2

Este módulo publicará en los siguientes topics:

```
/person/detected        # std_msgs/Bool
/person/position        # geometry_msgs/Point
/patient/identified     # std_msgs/String  (nombre del usuario)
/patient/confidence     # std_msgs/Float32 (confianza del reconocimiento)
```

## Sensores disponibles

- **Kinect V2** — detección de personas a mayor rango (skeleton tracking)
- **Cámara portátil** — reconocimiento facial en corta distancia

## Restricciones de hardware

- Sin GPU dedicada (Intel i3 solamente)
- No usar modelos que requieran CUDA
- Optimización de CPU es crítica

## Estructura sugerida

```
vision/
├── README.md
├── requirements.txt
├── person_detector_node.py     # Nodo ROS2 — detección
├── face_recognition_node.py    # Nodo ROS2 — identificación
├── models/                     # Modelos (no versionados)
└── test/
```
