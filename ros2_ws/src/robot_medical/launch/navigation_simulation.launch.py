import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Rutas
    pkg_share = get_package_share_directory('robot_medical')
    turtlebot3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    turtlebot3_nav = get_package_share_directory('turtlebot3_navigation2')
    
    # Ruta del mapa (directo, sin LaunchConfiguration)
    map_yaml = os.path.join(pkg_share, 'maps', 'mi_primer_mapa.yaml')
    
    # Lanzar Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo, 'launch', 'turtlebot3_world.launch.py')
        )
    )
    
    # Lanzar Nav2
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_nav, 'launch', 'navigation2.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'True',
            'map': map_yaml
        }.items()
    )
    
    return LaunchDescription([
        gazebo,
        navigation,
    ])
