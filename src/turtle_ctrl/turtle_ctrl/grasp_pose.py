import os

import numpy as np
import rclpy
import tf2_ros
from geometry_msgs.msg import Pose, PoseArray
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


def quat_to_mat(x, y, z, w):
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def euler_yaw_down(yaw):
    """构造"工具朝下 + 绕世界 z 转 yaw"的四元数，返回 (x, y, z, w)"""
    # q_down: 绕 y 转 180°，让工具 z 轴指向 -z
    q_down = np.array([0.0, 1.0, 0.0, 0.0])          # (x,y,z,w)
    # q_yaw: 绕 z 转 yaw
    q_yaw = np.array([0.0, 0.0, np.sin(yaw / 2), np.cos(yaw / 2)])
    # 四元数乘法 q = q_yaw * q_down（先 down 后 yaw，绕世界轴）
    x1, y1, z1, w1 = q_yaw
    x2, y2, z2, w2 = q_down
    return np.array([
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ])


class GraspPose(Node):
    def __init__(self):
        super().__init__('grasp_pose')

        d = np.load(os.path.expanduser('~/ros2_ws/calib/camera_params.npz'))
        self.K = d['K640']
        self.Kinv = np.linalg.inv(self.K)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.sub = self.create_subscription(
            Float32MultiArray, '/detections', self.cb, 10)
        self.pub = self.create_publisher(PoseArray, '/grasp_poses', 10)

        self.plane_z = 0.0
        self.get_logger().info('grasp_pose (pose version) ready')

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

        arr = PoseArray()
        arr.header.frame_id = 'base_link'
        arr.header.stamp = self.get_clock().now().to_msg()

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

            pose = Pose()
            pose.position.x = float(p[0])
            pose.position.y = float(p[1])
            pose.position.z = float(p[2])

            # 今天 yaw 固定 0；Day 9 用最小外接矩形算真实 yaw
            qx, qy, qz, qw = euler_yaw_down(0.0)
            pose.orientation.x = float(qx)
            pose.orientation.y = float(qy)
            pose.orientation.z = float(qz)
            pose.orientation.w = float(qw)

            arr.poses.append(pose)
            self.get_logger().info(
                f'cls={int(cls)} conf={conf:.2f} '
                f'pos=({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})')

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
