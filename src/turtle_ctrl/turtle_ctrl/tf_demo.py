import rclpy
from rclpy.node import Node
import tf2_ros
import numpy as np


class TfDemo(Node):
    def __init__(self):
        super().__init__('tf_demo')
        self.buffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.buffer, self)
        self.create_timer(1.0, self.tick)
        # 相机系里的一个点：正前方 1m，水平偏移 0.2m
        self.p_cam = np.array([0.2, 0.0, 1.0, 1.0])

    def tick(self):
        try:
            tr = self.buffer.lookup_transform(
                'base_link', 'camera_link', rclpy.time.Time())
        except Exception as e:
            self.get_logger().warn(f'no tf yet: {e}')
            return

        t = tr.transform.translation
        q = tr.transform.rotation
        R = self.quat_to_matrix(q.x, q.y, q.z, q.w)
        p_base = R @ self.p_cam[:3] + np.array([t.x, t.y, t.z])
        self.get_logger().info(f'p_cam={self.p_cam[:3]} -> p_base={np.round(p_base, 3)}')

    @staticmethod
    def quat_to_matrix(x, y, z, w):
        return np.array([
            [1-2*(y*y+z*z), 2*(x*y-z*w),   2*(x*z+y*w)],
            [2*(x*y+z*w),   1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w),   2*(y*z+x*w),   1-2*(x*x+y*y)],
        ])


def main():
    rclpy.init()
    node = TfDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
