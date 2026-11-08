import math
import tf2_ros
import numpy as np
import rclpy
from geometry_msgs.msg import PoseArray
from rclpy.node import Node
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (Constraints, PositionConstraint,
                             OrientationConstraint, MoveItErrorCodes)
from shape_msgs.msg import SolidPrimitive


class Executor(Node):
    def __init__(self):
        super().__init__('grasp_executor')
        self.group = 'ur_manipulator'
        self.tip_link = 'tool0'          # 装了夹爪会变成 gripper_tcp，注意核对
        self.frame = 'base_link'

        self.client = ActionClient(self, MoveGroup, '/move_action')
        self.get_logger().info('等待 move_action ...')
        self.client.wait_for_server()

        self.sub = self.create_subscription(
            PoseArray, '/grasp_target', self.cb, 10)
        self.busy = False
        self.target = None
        self.last_target = None       # 上一帧已执行的目标，用于去重
        self._retry_pending = False
        self._retry_count = 0
        self._max_retry = 2
        # 演示用 0.35（约 12 秒一次动作）；调试可降到 0.1
        self.declare_parameter('vel_scale', 0.35)
        self.vel_scale = float(self.get_parameter('vel_scale').value)
        self.create_timer(0.5, self._tick_retry)
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.get_logger().info('grasp_executor ready')

    @staticmethod
    def _same_pose(a, b, pos_tol=0.01, ang_tol_deg=5.0):
        """两个位姿是否足够接近（位置 1cm、朝向 5 度以内算同一个）"""
        if a is None:
            return False
        dp = math.dist((a.position.x, a.position.y, a.position.z),
                       (b.position.x, b.position.y, b.position.z))
        qa = np.array([a.orientation.x, a.orientation.y, a.orientation.z, a.orientation.w])
        qb = np.array([b.orientation.x, b.orientation.y, b.orientation.z, b.orientation.w])
        dot = min(1.0, abs(float(np.dot(qa, qb))))
        ang = math.degrees(2.0 * math.acos(dot))
        return dp < pos_tol and ang < ang_tol_deg

    def cb(self, msg):
        if self.busy or not msg.poses:
            return
        p = msg.poses[0]
        # 同一张图会以 10Hz 重复发同一目标，位姿没变就不重复执行
        if self._same_pose(self.last_target, p):
            return
        self.last_target = p
        self.busy = True
        self.send_goal(p)                # 只抓第一个（计算器）

    def send_goal(self, pose):
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = self.group
        req.num_planning_attempts = 10
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = self.vel_scale
        req.max_acceleration_scaling_factor = self.vel_scale

        c = Constraints()

        pc = PositionConstraint()
        pc.header.frame_id = self.frame
        pc.link_name = self.tip_link
        pc.constraint_region.primitives.append(
            SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01]))
        pc.constraint_region.primitive_poses.append(pose)
        pc.weight = 1.0
        c.position_constraints.append(pc)

        oc = OrientationConstraint()
        oc.header.frame_id = self.frame
        oc.link_name = self.tip_link
        oc.orientation = pose.orientation
        oc.absolute_x_axis_tolerance = 0.2
        oc.absolute_y_axis_tolerance = 0.2
        oc.absolute_z_axis_tolerance = 0.2
        oc.weight = 1.0
        c.orientation_constraints.append(oc)

        req.goal_constraints.append(c)

        self.target = pose          # 记下目标，成功后用来算到位误差
        future = self.client.send_goal_async(goal)
        future.add_done_callback(self.on_accepted)

    def on_accepted(self, future):
        gh = future.result()
        if not gh.accepted:
            self.get_logger().warn('目标被拒绝')
            self.busy = False
            return
        gh.get_result_async().add_done_callback(self.on_result)

    def _tick_retry(self):
        """0.5 秒检查一次：如果上次失败且还有重试次数，就重发同一个目标"""
        if not self._retry_pending:
            return
        self._retry_pending = False
        self._retry_count += 1
        self.get_logger().info(
            f'重试第 {self._retry_count}/{self._max_retry} 次')
        self.send_goal(self.last_target)

    def on_result(self, future):
        code = future.result().result.error_code.val
        if code == MoveItErrorCodes.SUCCESS:
            self._retry_count = 0
            try:
                tr = self.tf_buffer.lookup_transform(
                    self.frame, self.tip_link, rclpy.time.Time())
                t = tr.transform.translation
                err = np.linalg.norm([
                    t.x - self.target.position.x,
                    t.y - self.target.position.y,
                    t.z - self.target.position.z,
                ])
                # 位置约束本身是 10mm 直径的球，所以 10mm 内算达标
                ok = err < 0.010
                tag = 'OK ' if ok else 'BIG'
                self.get_logger().info(
                    f'{tag} 到位误差 = {err * 1000:.1f} mm  (容差 10 mm)')
            except Exception as e:
                self.get_logger().warn(f'success, but tf lookup failed: {e}')
        else:
            name = code_name(code)
            if self._retry_count < self._max_retry:
                self.get_logger().warn(
                    f'失败 [{name}] ({code})，将自动重试')
                self._retry_pending = True          # busy 保持 True，等重试
                return
            self.get_logger().error(
                f'失败 [{name}] ({code})，已达重试上限 {self._max_retry}，放弃')
            self._retry_count = 0
        self.busy = False


def main():
    rclpy.init()
    node = Executor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
