import glob
import os

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from ultralytics import YOLO

MAX_POINTS = 32      # 每个多边形最多这么多点
EPS_PX = 3.0         # approxPolyDP 的简化精度（像素）


def imgmsg_to_bgr(msg):
    """sensor_msgs/Image -> HxWx3 BGR（替代 cv_bridge）"""
    if msg.encoding not in ('rgb8', 'bgr8'):
        raise ValueError(f'不支持的编码: {msg.encoding}')
    arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    arr = arr[:, : msg.width * 3].reshape(msg.height, msg.width, 3)
    if msg.encoding == 'rgb8':
        arr = arr[:, :, ::-1]
    return np.ascontiguousarray(arr)


class DetectorSeg(Node):
    def __init__(self):
        super().__init__('detector_seg')

        ws = os.path.expanduser('~/ros2_ws')
        weights = max(glob.glob(f'{ws}/runs/segment/*/weights/best.pt'),
                      key=os.path.getmtime)
        self.model = YOLO(weights)
        self.get_logger().info(f'loaded weights: {weights}')

        self.CONF = 0.5
        self.IOU = 0.45

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.cb, 10)
        self.pub = self.create_publisher(
            Float32MultiArray, '/seg_polygons', 10)

        self.get_logger().info('detector_seg ready')

    def simplify(self, poly):
        """像素多边形 -> 简化并限制点数"""
        poly = cv2.approxPolyDP(
            poly.reshape(-1, 1, 2).astype(np.float32), EPS_PX, True
        ).reshape(-1, 2).astype(np.float32)
        if len(poly) < 3:
            return None
        if len(poly) > MAX_POINTS:
            idx = np.linspace(0, len(poly) - 1, MAX_POINTS).round().astype(int)
            poly = poly[idx]
        return poly

    def cb(self, msg):
        img = imgmsg_to_bgr(msg)
        res = self.model(img, verbose=False, conf=self.CONF, iou=self.IOU)[0]

        if res.masks is None or len(res.boxes) == 0:
            return

        # 场景先验：每类只保留置信度最高的一个
        best = {}
        for i, (cls, conf) in enumerate(zip(res.boxes.cls, res.boxes.conf)):
            c, f = int(cls), float(conf)
            if c not in best or f > best[c][1]:
                best[c] = (i, f)

        out = []
        for c, (idx, conf) in best.items():
            poly = self.simplify(res.masks.xy[idx])
            if poly is None:
                continue
            out.append(float(len(poly)))
            for x, y in poly:
                out += [float(x), float(y)]
            out += [float(c), float(conf)]

        arr = Float32MultiArray()
        arr.data = out
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = DetectorSeg()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()