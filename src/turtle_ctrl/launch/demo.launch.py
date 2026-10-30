from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 读取命令行传入的 use_circle 参数（默认 true）
    use_circle = LaunchConfiguration('use_circle')

    return LaunchDescription([
        # 声明一个可以在命令行改的参数
        DeclareLaunchArgument(
            'use_circle',
            default_value='true',
            description='是否启动 circle 节点；回放 bag 时设为 false',
        ),

        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
            output='screen',
        ),

        # 只有 use_circle 为 true 时才启动这个节点
        Node(
            package='turtle_ctrl',
            executable='circle',
            name='circle',
            output='screen',
            condition=IfCondition(use_circle),
        ),

        Node(
            package='turtle_ctrl',
            executable='pose_listener',
            name='listener',
            output='screen',
        ),
    ])
