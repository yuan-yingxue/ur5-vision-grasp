"""UR5e + MoveIt2 + 小窗口 RViz

用法:
    ros2 launch turtle_ctrl ur5e_moveit_small.launch.py
    ros2 launch turtle_ctrl ur5e_moveit_small.launch.py ur_type:=ur5
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# 自定义的小窗口 rviz 配置（原版是 2560x1381，改成了 1200x780）
RVIZ_CONFIG = os.path.expanduser('~/ros2_ws/rviz/ur5e_small.rviz')


def generate_launch_description():
    ur_type = LaunchConfiguration('ur_type')

    # 复用官方 launch，但不要它自带的 RViz
    ur_moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ur_moveit_config'),
                'launch', 'ur_moveit.launch.py',
            )
        ),
        launch_arguments={
            'ur_type': ur_type,
            'launch_rviz': 'false',
        }.items(),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_moveit',
        arguments=['-d', RVIZ_CONFIG],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('ur_type', default_value='ur5e',
                              description='ur3e/ur5e/ur10e（老款 ur3/ur5/ur10）'),
        ur_moveit,
        rviz,
    ])
