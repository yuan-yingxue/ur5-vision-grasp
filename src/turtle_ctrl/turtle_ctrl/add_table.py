"""往 MoveIt 规划场景里加一张"桌子"，防止机械臂穿到 z<0 去。

用法（MoveIt 起来之后再运行）:
    ros2 run turtle_ctrl add_table

参数（可选）:
    -p top_z:=-0.005    桌面顶面的高度（默认 -5mm，避免和 URDF 的 base_link 接触）
    -p size:=1.2        桌面边长（米）
"""
import rclpy
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, ObjectColor, PlanningScene
from rclpy.node import Node
from shape_msgs.msg import SolidPrimitive


class TableAdder(Node):
    def __init__(self):
        super().__init__('add_table')
        self.declare_parameter('top_z', -0.005)
        self.declare_parameter('size', 1.2)
        self.declare_parameter('thickness', 0.05)

        self.top_z = float(self.get_parameter('top_z').value)
        self.size = float(self.get_parameter('size').value)
        self.thick = float(self.get_parameter('thickness').value)

        self.pub = self.create_publisher(PlanningScene, '/planning_scene', 10)
        # 每隔 2 秒重发一次，保证 MoveIt 重启后也能收到
        self.create_timer(2.0, self.tick)
        self.get_logger().info(
            f'桌子: {self.size:.2f}m x {self.size:.2f}m, '
            f'顶面 z={self.top_z:.3f}m')

    def tick(self):
        ps = PlanningScene()
        ps.is_diff = True

        co = CollisionObject()
        co.header.frame_id = 'base_link'
        co.header.stamp = self.get_clock().now().to_msg()
        co.id = 'table'

        prim = SolidPrimitive()
        prim.type = SolidPrimitive.BOX
        prim.dimensions = [self.size, self.size, self.thick]

        pose = Pose()
        pose.position.x = 0.0
        pose.position.y = 0.0
        pose.position.z = self.top_z - self.thick / 2.0   # 盒子上表面落在 top_z
        pose.orientation.w = 1.0

        co.primitives.append(prim)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD

        ps.world.collision_objects.append(co)

        # 给桌面一个浅灰绿色，看起来像张桌子
        color = ObjectColor()
        color.id = 'table'
        color.color.r = 0.55
        color.color.g = 0.68
        color.color.b = 0.55
        color.color.a = 1.0
        ps.object_colors.append(color)

        self.pub.publish(ps)


def main():
    rclpy.init()
    node = TableAdder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
