"""检测可视化（自动裁剪到桌面区域，可排除画面底部）。

订阅: /camera/image_raw, /seg_polygons, /grasp_poses_v3
发布: /detection_view  (bgr8)
查看: ros2 run rqt_image_view rqt_image_view  -> 选 /detection_view

参数:
  auto_crop:=true        是否自动裁剪
  min_crop:=260          裁剪框最小边长（原图像素）
  pad:=0.10              裁剪框相对目标的余量比例
  exclude_bottom:=0.25   画面底部这么大比例永不出现在裁剪结果里
                         （用来避开腿脚等无关内容）
"""
import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import PoseArray
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray

CLASS_NAMES = {0: 'counter', 1: 'cup', 2: 'earphone'}
COLORS = {0: (60, 200, 60), 1: (230, 160, 60), 2: (200, 120, 230)}


def imgmsg_to_bgr(msg):
    if msg.encoding not in ('rgb8', 'bgr8'):
        return None
    arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    arr = arr[:, : msg.width * 3].reshape(msg.height, msg.width, 3)
    if msg.encoding == 'rgb8':
        arr = arr[:, :, ::-1]
    return np.ascontiguousarray(arr)


class DetView(Node):
    def __init__(self):
        super().__init__('det_view')
        self.declare_parameter('target_class', 0)
        self.declare_parameter('conf_target', 0.9)
        self.declare_parameter('auto_crop', True)
        self.declare_parameter('min_crop', 260)
        self.declare_parameter('pad', 0.10)
        self.declare_parameter('exclude_bottom', 0.25)

        self.TC = int(self.get_parameter('target_class').value)
        self.CT = float(self.get_parameter('conf_target').value)
        self.AUTO = bool(self.get_parameter('auto_crop').value)
        self.MIN_CROP = int(self.get_parameter('min_crop').value)
        self.PAD = float(self.get_parameter('pad').value)
        self.EXB = float(self.get_parameter('exclude_bottom').value)

        self.img = None
        self.polys = []
        self.poses = []
        self.roi = None

        self.create_subscription(Image, '/camera/image_raw', self.on_img, 10)
        self.create_subscription(Float32MultiArray, '/seg_polygons', self.on_poly, 10)
        self.create_subscription(PoseArray, '/grasp_poses_v3', self.on_pose, 10)
        self.pub = self.create_publisher(Image, '/detection_view', 10)
        self.create_timer(1.0 / 15.0, self.draw)
        self.get_logger().info(
            f'det_view: auto_crop={self.AUTO} pad={self.PAD} '
            f'exclude_bottom={self.EXB} -> /detection_view')

    def on_img(self, msg):
        img = imgmsg_to_bgr(msg)
        if img is not None:
            self.img = img

    def on_poly(self, msg):
        data = list(msg.data)
        out = []
        i = 0
        while i < len(data):
            n = int(round(data[i]))
            i += 1
            if n < 3 or i + 2 * n + 2 > len(data):
                break
            pts = np.array(data[i:i + 2 * n], np.float32).reshape(-1, 2)
            i += 2 * n
            out.append((pts, int(round(data[i])), float(data[i + 1])))
            i += 2
        self.polys = out

    def on_pose(self, msg):
        self.poses = list(msg.poses)

    def _update_roi(self, pts):
        x0, y0 = pts.min(axis=0)
        x1, y1 = pts.max(axis=0)
        if self.roi is None:
            self.roi = [x0, y0, x1, y1]
        else:
            self.roi[0] = min(self.roi[0], x0)
            self.roi[1] = min(self.roi[1], y0)
            self.roi[2] = max(self.roi[2], x1)
            self.roi[3] = max(self.roi[3], y1)

    def _crop_box(self, w, h):
        if self.roi is None:
            return 0, 0, w, h

        x0, y0, x1, y1 = self.roi
        bw, bh = x1 - x0, y1 - y0
        x0 -= bw * self.PAD
        x1 += bw * self.PAD
        y0 -= bh * self.PAD
        y1 += bh * self.PAD

        # 底部禁区：超过这条线的部分一律不出现
        y_limit = int(h * (1.0 - self.EXB))
        y1 = min(y1, y_limit)

        cx = (x0 + x1) / 2
        bw = max(x1 - x0, self.MIN_CROP)
        bh = max(y1 - y0, self.MIN_CROP)

        # 补成 4:3
        if bw / bh > 4 / 3:
            bh = bw * 3 / 4
        else:
            bw = bh * 4 / 3

        # 高度不能超过禁区
        if bh > y_limit:
            bh = y_limit
            bw = bh * 4 / 3

        x0, x1 = cx - bw / 2, cx + bw / 2
        y0, y1 = y1 - bh, y1

        # 平移进图像（不缩小）
        if x0 < 0:
            x1 -= x0
            x0 = 0
        if x1 > w:
            x0 -= (x1 - w)
            x1 = w
        if y0 < 0:
            y1 -= y0
            y0 = 0
        if y1 > y_limit:
            y0 -= (y1 - y_limit)
            y1 = y_limit

        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(w, int(x1))
        y1 = min(h, int(y1))
        if x1 - x0 < 40 or y1 - y0 < 40:
            return 0, 0, w, h
        return x0, y0, x1, y1

    def draw(self):
        if self.img is None:
            return
        canvas = self.img.copy()
        h, w = canvas.shape[:2]
        target = None

        for idx, (pts, cls, conf) in enumerate(self.polys):
            color = COLORS.get(cls, (200, 200, 200))
            is_target = (cls == self.TC and conf >= self.CT)
            if is_target:
                color = (0, 255, 0)
                if self.AUTO:
                    self._update_roi(pts)

            cv2.polylines(canvas, [pts.astype(np.int32)], True, color, 2)
            rect = cv2.minAreaRect(pts.astype(np.float32))
            cv2.drawContours(canvas, [cv2.boxPoints(rect).astype(np.int32)], 0,
                             (0, 255, 255), 1)

            name = CLASS_NAMES.get(cls, str(cls))
            org = (max(2, int(pts[:, 0].min())), max(14, int(pts[:, 1].min()) - 6))
            cv2.putText(canvas, f'{name} {conf:.2f}', org,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(canvas, f'{name} {conf:.2f}', org,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if idx < len(self.poses):
                p = self.poses[idx].position
                t2 = f'({p.x*100:.1f},{p.y*100:.1f})cm'
                cv2.putText(canvas, t2, (org[0], org[1] + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
                cv2.putText(canvas, t2, (org[0], org[1] + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 220, 255), 1)
                if is_target:
                    target = (name, p, conf)

        x0, y0, x1, y1 = self._crop_box(w, h) if self.AUTO else (0, 0, w, h)
        view = canvas[y0:y1, x0:x1].copy()
        vh, vw = view.shape[:2]

        cv2.rectangle(view, (0, 0), (vw, 26), (30, 30, 30), -1)
        if target is not None:
            txt = (f'TARGET {target[0]}  conf={target[2]:.2f}  '
                   f'({target[1].x*100:.1f}, {target[1].y*100:.1f}) cm')
            cv2.putText(view, txt, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 255, 0), 2)
        else:
            cv2.putText(view, 'NO TARGET  (waiting counter conf >= %.2f)' % self.CT,
                        (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 80, 255), 2)

        scale = 960.0 / vw
        out = cv2.resize(view, (int(vw * scale), int(vh * scale)),
                         interpolation=cv2.INTER_LINEAR)

        msg = Image()
        msg.header.frame_id = 'camera_link'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.height, msg.width = out.shape[:2]
        msg.encoding = 'bgr8'
        msg.is_bigendian = 0
        msg.step = int(out.shape[1] * 3)
        msg.data = out.tobytes()
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = DetView()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
