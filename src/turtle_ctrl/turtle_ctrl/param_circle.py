import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class ParamCircle(Node):
    def __init__(self):
        super().__init__('param_circle')
        self.declare_parameter('radius', 1.0)
        self.declare_parameter('speed', 1.0)
        self.pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.create_timer(0.1, self.tick)

    def tick(self):
        r = self.get_parameter('radius').value
        v = self.get_parameter('speed').value
        msg = Twist()
        msg.linear.x = v
        msg.angular.z = v / r
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ParamCircle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
