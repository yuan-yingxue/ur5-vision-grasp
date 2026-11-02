import glob
import os

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from ultralytics import YOLO


def imgmsg_to_bgr(msg):
    """把 sensor_msgs/Image 转成 HxWx3 的 BGR 数组（替代 cv_bridge）"""
    if msg.encoding not in ('rgb8', 'bgr8'):
        raise ValueError(f'不支持的编码: {msg.encoding}')

    arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    arr = arr[:, : msg.width * 3].reshape(msg.height, msg.width, 3)

    if msg.encoding == 'rgb8':
        arr = arr[:, :, ::-1]
    return np.ascontiguousarray(arr)


class Detector(Node):
    def __init__(self):
        super().__init__('detector')

        ws = os.path.expanduser('~/ros2_ws')
        weights = max(glob.glob(f'{ws}/runs/detect/*/weights/best.pt'),
                      key=os.path.getmtime)
        self.model = YOLO(weights)
        self.get_logger().info(f'loaded weights: {weights}')

        self.sub = self.create_subscription(Image, '/camera/image_raw', self.cb, 10)
        self.pub = self.create_publisher(Float32MultiArray, '/detections', 10)

        self.CONF_TH = 0.5
        self.get_logger().info('detector ready')

    def cb(self, msg):
        img = imgmsg_to_bgr(msg)
        res = self.model(img, verbose=False, conf=self.CONF_TH, iou=0.45)[0]

        best = {}
        for box, cls, conf in zip(res.boxes.xyxy, res.boxes.cls, res.boxes.conf):
            c, f = int(cls), float(conf)
            if c not in best or f > best[c][0]:
                best[c] = (f, [float(v) for v in box])

        out = []
        for c, (f, box) in best.items():
            out += box + [float(c), f]

        arr = Float32MultiArray()
        arr.data = out
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = Detector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
