import os

import numpy as np
import rclpy
import tf2_ros
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


def quat_to_mat(x, y, z, w):
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


class GraspPose(Node):
    def __init__(self):
        super().__init__('grasp_pose')

        d = np.load(os.path.expanduser('~/ros2_ws/calib/camera_params.npz'))
        self.K = d['K640']
        self.Kinv = np.linalg.inv(self.K)
        self.get_logger().info(f'K640 loaded, fx={self.K[0,0]:.1f} cx={self.K[0,2]:.1f}')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.sub = self.create_subscription(
            Float32MultiArray, '/detections', self.cb, 10)
        self.pub = self.create_publisher(
            Float32MultiArray, '/grasp_points', 10)

        self.plane_z = 0.0          # 桌面在 base_link 里的高度
        self.get_logger().info('grasp_pose ready')

    def cb(self, msg):
        data = list(msg.data)
        if not data or len(data) % 6 != 0:
            return

        try:
            tr = self.tf_buffer.lookup_transform(
                'base_link', 'camera_link', rclpy.time.Time())
        except Exception as e:
            self.get_logger().warn(f'tf not ready: {e}')
            return

        t = tr.transform.translation
        q = tr.transform.rotation
        R = quat_to_mat(q.x, q.y, q.z, q.w)
        tvec = np.array([t.x, t.y, t.z])

        out = []
        for i in range(0, len(data), 6):
            x1, y1, x2, y2, cls, conf = data[i:i + 6]
            u, v = (x1 + x2) / 2.0, (y1 + y2) / 2.0

            d_cam = self.Kinv @ np.array([u, v, 1.0])
            d_base = R @ d_cam
            if abs(d_base[2]) < 1e-6:
                continue
            s = (self.plane_z - tvec[2]) / d_base[2]
            if s <= 0:
                continue
            p = R @ (s * d_cam) + tvec

            out += [float(p[0]), float(p[1]), float(p[2]), float(cls), float(conf)]
            self.get_logger().info(
                f'cls={int(cls)} conf={conf:.2f}  uv=({u:.0f},{v:.0f})  '
                f'base=({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})')

        arr = Float32MultiArray()
        arr.data = out
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = GraspPose()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
