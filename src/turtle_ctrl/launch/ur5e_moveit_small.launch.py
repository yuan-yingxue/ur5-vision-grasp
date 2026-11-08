"""UR5e + 假硬件 + MoveIt + 小窗口 RViz（一条命令）。

  1. ur_control.launch.py       假硬件：/joint_states + robot_state_publisher
  2. ur_moveit_small.launch.py  官方 launch 副本，只改了 rviz 配置路径
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    ur_type = LaunchConfiguration('ur_type')
    robot_ip = LaunchConfiguration('robot_ip')
    my_launch = os.path.join(get_package_share_directory('turtle_ctrl'), 'launch')

    control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ur_robot_driver'),
                         'launch', 'ur_control.launch.py')),
        launch_arguments={
            'ur_type': ur_type,
            'robot_ip': robot_ip,
            'use_fake_hardware': 'true',
            'launch_rviz': 'false',
        }.items(),
    )

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(my_launch, 'ur_moveit_small.launch.py')),
        launch_arguments={
            'ur_type': ur_type,
            'launch_rviz': 'true',
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('ur_type', default_value='ur5e'),
        DeclareLaunchArgument('robot_ip', default_value='0.0.0.0'),
        control,
        moveit,
    ])
