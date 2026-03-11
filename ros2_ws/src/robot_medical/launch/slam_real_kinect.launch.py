#!/usr/bin/env python3
"""
Launch file para SLAM 3D con RTAB-Map usando Kinect V2 real
Configuración optimizada para hardware limitado (12GB RAM, 4 cores)
Usa topics SD (512x424) para mejor rendimiento
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Parámetros configurables
    use_sim_time = LaunchConfiguration('use_sim_time')
    localization = LaunchConfiguration('localization')
    
    # Configurar RTAB-Map para modo visual SLAM
    parameters = {
        'frame_id': 'kinect2_link',  # Usar frame del Kinect (no hay base_link aún)
        'subscribe_depth': True,
        'subscribe_rgb': True,
        'subscribe_scan': False,
        'subscribe_scan_cloud': False,
        'use_sim_time': use_sim_time,
        'approx_sync': True,  # Importante para kinect2_bridge
        'qos': 2,  # Best Effort (compatible con kinect2_bridge)
        
        # Tasa de detección (Hz) - Ultra lenta para máxima estabilidad
        'Rtabmap/DetectionRate': '1.0',  # 1 Hz = 1 frame por segundo (máxima estabilidad)
        
        # Optimizaciones de memoria (ajustado para mejor tracking)
        'Mem/ImagePostDecimation': '2',  # Menos decimación = mejor calidad (era 4)
        'Mem/IncrementalMemory': 'true',  # Guardar mapa incremental
        'Mem/InitWMWithAllNodes': 'false',
        'Mem/STMSize': '50',  # Mantener más nodos en Short-Term Memory (era 30)
        'Mem/RehearsalSimilarity': '0.4',  # Threshold para rehearsal
        'Rtabmap/TimeThr': '0',  # Sin límite de tiempo (0 = infinito)
        'Rtabmap/MemoryThr': '0',  # Sin límite de memoria (mantener todo el mapa)
        'Rtabmap/LoopThr': '0.11',  # Threshold para loop closure (más estricto)
        
        # Features visuales (ultra-optimizado para tracking robusto)
        'Kp/MaxFeatures': '300',  # Features para detección loop closure (más)
        'Vis/MaxFeatures': '600',  # Features para odometría visual (muchas más)
        'Vis/MinInliers': '8',  # Mínimo de inliers (muy tolerante)
        'Vis/FeatureType': '6',  # GFTT/BRIEF (rápido y robusto)
        'Vis/CorFlowMaxLevel': '4',  # Pyramid levels aumentado
        'Vis/CorNNType': '1',  # Feature matching con KNN
        'Vis/CorGuessWinSize': '40',  # Ventana de búsqueda más grande
        'Vis/EstimationType': '1',  # PnP para estimación más robusta
        
        # Configuración de grid (mapa 2D para Nav2)
        'Grid/RangeMax': '3.0',  # Máximo rango para obstáculos (metros)
        'Grid/RangeMin': '0.5',  # Mínimo rango
        'Grid/CellSize': '0.05',  # Tamaño celda 5cm
        'Grid/FromDepth': 'true',
        
        # Odometría visual (configuración más robusta)
        'Odom/Strategy': '0',  # Frame-to-Map (0) más estable que Frame-to-Frame
        'Odom/ResetCountdown': '5',  # Intentos antes de reset (aumentado)
        'Odom/GuessSmoothingDelay': '0.0',  # Sin suavizado (más reactivo)
        'Odom/FillInfoData': 'true',  # Publicar datos de diagnóstico
        'Odom/ImageDecimation': '1',  # Sin decimación (mejor tracking)
        'OdomF2M/MaxSize': '2000',  # Tamaño máximo del mapa local (aumentado)
        'Odom/AlignWithGround': 'false',  # No asumir plano de suelo
        
        # Optimizer
        'Optimizer/Strategy': '0',  # TORO
        'Optimizer/Iterations': '10',
        
        # RGBD configuración (más tolerante para movimiento manual)
        'RGBD/OptimizeFromGraphEnd': 'false',
        'RGBD/NeighborLinkRefining': 'true',
        'RGBD/ProximityBySpace': 'true',
        'RGBD/ProximityMaxGraphDepth': '50',  # Profundidad del grafo
        'RGBD/LinearUpdate': '0.1',  # Actualizar cada 10cm (más tolerante)
        'RGBD/AngularUpdate': '0.1',  # Actualizar cada ~6 grados (más tolerante)
        'RGBD/OptimizeMaxError': '3.0',  # Error máximo de optimización
    }
    
    # Si es modo localización, ajustar parámetros
    parameters_localization = parameters.copy()
    parameters_localization['Mem/IncrementalMemory'] = 'false'
    
    # Remappings para topics del Kinect (SD resolution)
    remappings = [
        ('rgb/image', '/kinect2/sd/image_color_rect'),
        ('rgb/camera_info', '/kinect2/sd/camera_info'),
        ('depth/image', '/kinect2/sd/image_depth_rect'),
    ]
    
    return LaunchDescription([
        # Argumentos
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time'
        ),
        
        DeclareLaunchArgument(
            'localization',
            default_value='false',
            description='Modo localización (usa mapa existente)'
        ),
        
        # Variable de entorno para logs RTAB-Map
        SetEnvironmentVariable('RTABMAP_PRINT_WARNINGS', 'true'),
        
        # Nodo RTABMAP (SLAM)
        Node(
            package='rtabmap_slam',
            executable='rtabmap',
            output='screen',
            parameters=[parameters],
            remappings=remappings,
            # arguments=['--delete_db_on_start']  # COMENTADO: mantener mapa persistente
        ),
        
        # Nodo de visualización RTABMAP
        Node(
            package='rtabmap_viz',
            executable='rtabmap_viz',
            output='screen',
            parameters=[parameters],
            remappings=remappings
        ),
        
        # RGBD Odometry (odometría visual)
        Node(
            package='rtabmap_odom',
            executable='rgbd_odometry',
            output='screen',
            parameters=[parameters],
            remappings=remappings,
        ),
    ])
