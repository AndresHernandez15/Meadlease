import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Rutas de paquetes
    turtlebot3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    turtlebot3_carto = get_package_share_directory('turtlebot3_cartographer')
    
    # Lanzar Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo, 'launch', 'turtlebot3_world.launch.py')
        )
    )
    
    # Lanzar SLAM
    cartographer = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_carto, 'launch', 'cartographer.launch.py')
        ),
        launch_arguments={'use_sim_time': 'True'}.items()
    )
    
    return LaunchDescription([
        gazebo,
	cartographer,
    ])
