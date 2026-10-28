import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class Listener(Node):
    def __init__(self):
        super().__init__('pose_listener')
        self.create_subscription(Pose, '/turtle1/pose', self.cb, 10)

    def cb(self, msg):
        self.get_logger().info(
            f'x={msg.x:.2f} y={msg.y:.2f} theta={msg.theta:.2f}')


def main():
    rclpy.init()
    node = Listener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
