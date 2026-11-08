"""循环发布一组图片到 /camera/image_raw，用来代替静态假相机。

每 period 秒换一张，让下游节点持续收到不同的场景。
"""
import glob
import os

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class ImageCycler(Node):
    def __init__(self):
        super().__init__('image_cycler')
        self.declare_parameter('dir', '~/ros2_ws/datasets/grasp/valid/images')
        self.declare_parameter('period', 6.0)

        d = os.path.expanduser(self.get_parameter('dir').value)
        self.period = float(self.get_parameter('period').value)
        self.files = sorted(glob.glob(os.path.join(d, '*.jpg')))
        if not self.files:
            self.get_logger().error(f'{d} 里没有 jpg')
            raise SystemExit(1)

        self.i = 0
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.timer = self.create_timer(self.period, self.tick)
        self.get_logger().info(
            f'{len(self.files)} 张图，每 {self.period}s 换一张')

    def tick(self):
        path = self.files[self.i % len(self.files)]
        img = cv2.imread(path)
        if img is None:
            self.get_logger().warn(f'读不到 {path}')
            return
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        msg = Image()
        msg.header.frame_id = 'camera_link'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.height = int(rgb.shape[0])
        msg.width = int(rgb.shape[1])
        msg.encoding = 'rgb8'
        msg.is_bigendian = 0
        msg.step = int(rgb.shape[1] * 3)
        msg.data = rgb.tobytes()
        self.pub.publish(msg)

        self.get_logger().info(
            f'[{self.i % len(self.files) + 1}/{len(self.files)}] '
            f'{os.path.basename(path)}')
        self.i += 1


def main():
    rclpy.init()
    node = ImageCycler()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
