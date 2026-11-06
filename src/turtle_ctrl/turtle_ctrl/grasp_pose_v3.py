import math
import os

import cv2
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


def yaw_down_to_quat(yaw):
    """工具朝下 + 绕世界 z 转 yaw"""
    q_down = np.array([0.0, 1.0, 0.0, 0.0])
    q_yaw = np.array([0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)])
    x1, y1, z1, w1 = q_yaw
    x2, y2, z2, w2 = q_down
    return np.array([
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ])


def normalize_yaw(yaw):
    while yaw > math.pi / 2:
        yaw -= math.pi
    while yaw <= -math.pi / 2:
        yaw += math.pi
    return yaw


class GraspPoseV3(Node):
    def __init__(self):
        super().__init__('grasp_pose_v3')

        d = np.load(os.path.expanduser('~/ros2_ws/calib/camera_params.npz'))
        self.K = d['K640']
        self.Kinv = np.linalg.inv(self.K)

        self.plane_z = 0.0
        self.gripper_max = 0.085
        self.margin = 0.01

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.sub = self.create_subscription(
            Float32MultiArray, '/seg_polygons', self.cb, 10)
        self.pub = self.create_publisher(PoseArray, '/grasp_poses_v3', 10)
        self.pub_info = self.create_publisher(Float32MultiArray, '/grasp_info_v3', 10)

        self.get_logger().info('grasp_pose_v3 ready')

    def to_base(self, u, v, R, t):
        d_cam = self.Kinv @ np.array([u, v, 1.0])
        d_base = R @ d_cam
        if abs(d_base[2]) < 1e-6:
            return None
        s = (self.plane_z - t[2]) / d_base[2]
        if s <= 0:
            return None
        return R @ (s * d_cam) + t

    def cb(self, msg):
        data = list(msg.data)
        if not data:
            return

        try:
            tr = self.tf_buffer.lookup_transform(
                'base_link', 'camera_link', rclpy.time.Time())
        except Exception as e:
            self.get_logger().warn(f'tf not ready: {e}')
            return

        t_ = tr.transform.translation
        q_ = tr.transform.rotation
        R = quat_to_mat(q_.x, q_.y, q_.z, q_.w)
        t = np.array([t_.x, t_.y, t_.z])

        poses = PoseArray()
        poses.header.frame_id = 'base_link'
        poses.header.stamp = self.get_clock().now().to_msg()
        info = []

        i = 0
        while i < len(data):
            n = int(round(data[i]))
            i += 1
            if n < 3 or i + 2 * n + 2 > len(data):
                break

            pts_px = np.array(data[i:i + 2 * n], float).reshape(-1, 2)
            i += 2 * n
            cls = data[i]
            conf = data[i + 1]
            i += 2

            # 全部点反投影到桌面（方法 B 的关键）
            world = []
            ok = True
            for u, v in pts_px:
                p = self.to_base(u, v, R, t)
                if p is None:
                    ok = False
                    break
                world.append([p[0], p[1]])
            if not ok:
                continue

            world = np.array(world, np.float32)
            rect = cv2.minAreaRect(world)          # 世界坐标（米）里的最小外接矩形
            box = cv2.boxPoints(rect)

            e1 = box[1] - box[0]
            e2 = box[3] - box[0]
            l1 = float(np.linalg.norm(e1))
            l2 = float(np.linalg.norm(e2))
            long_edge, short_side = (e1, l2) if l1 >= l2 else (e2, l1)

            yaw = normalize_yaw(math.atan2(long_edge[1], long_edge[0]))
            width = float(np.clip(short_side + self.margin, 0.0, self.gripper_max))
            center = world.mean(axis=0)

            pose = Pose()
            pose.position.x = float(center[0])
            pose.position.y = float(center[1])
            pose.position.z = float(self.plane_z)

            qx, qy, qz, qw = yaw_down_to_quat(yaw)
            pose.orientation.x = float(qx)
            pose.orientation.y = float(qy)
            pose.orientation.z = float(qz)
            pose.orientation.w = float(qw)

            poses.poses.append(pose)
            info += [float(cls), float(conf), float(width), float(math.degrees(yaw))]

            self.get_logger().info(
                f'cls={int(cls)} conf={conf:.2f} 点={n} '
                f'长边={max(l1, l2) * 100:.1f}cm 短边={short_side * 100:.1f}cm '
                f'yaw={math.degrees(yaw):+.0f}° 开度={width * 100:.1f}cm '
                f'center=({center[0]:.3f},{center[1]:.3f})')

        self.pub.publish(poses)
        mi = Float32MultiArray()
        mi.data = info
        self.pub_info.publish(mi)


def main():
    rclpy.init()
    node = GraspPoseV3()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()